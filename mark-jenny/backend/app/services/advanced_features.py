import json
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.task import Task
from app.models.project import Project


def _call_ai(prompt: str, system: str = "", timeout: int = 120) -> str:
    """Call AI model."""
    try:
        from app.services.model_caller import model_caller
        return model_caller.call(prompt, system_prompt=system, timeout=timeout)
    except Exception:
        pass
    try:
        import httpx
        from app.core.config import get_settings
        settings = get_settings()
        base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            tags = httpx.get(f"{base}/api/tags", timeout=5).json()
            models = tags.get("models", [])
            model_name = models[0]["name"] if models else "qwen3-vl:8b"
        except:
            model_name = "qwen3-vl:8b"
        resp = httpx.post(
            f"{base}/api/generate",
            json={"model": model_name, "prompt": prompt, "system": system, "stream": False},
            timeout=timeout,
        )
        return resp.json().get("response", "")
    except Exception:
        return ""


class BlueprintManager:
    def save(self, db: Session, task: Task, user_id: int) -> Dict:
        blueprint = {
            "id": str(uuid.uuid4()),
            "goal": task.original_request,
            "steps": task.plan.get("subtasks", []) if task.plan else [],
            "skills": task.plan.get("skills", []) if task.plan else [],
            "tools": task.plan.get("tools", []) if task.plan else [],
            "approval_policy": task.autonomy_level,
            "output_format": task.result.get("type") if isinstance(task.result, dict) else "unknown",
            "created_from": task.id,
            "created_at": datetime.utcnow().isoformat()
        }
        if not task.plan:
            task.plan = {}
        if "blueprints" not in task.plan:
            task.plan["blueprints"] = []
        task.plan["blueprints"].append(blueprint)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(task, "plan")
        db.commit()
        return blueprint

    def list_for_project(self, db: Session, project_id: int, user_id: int) -> List[Dict]:
        tasks = db.query(Task).filter(Task.project_id == project_id, Task.owner_id == user_id).all()
        blueprints = []
        for t in tasks:
            if t.plan and "blueprints" in t.plan:
                blueprints.extend(t.plan["blueprints"])
        return blueprints


class SelfHealingEngine:
    def heal(self, task: Task, error: str, db: Session) -> Dict:
        system = (
            "You are an AI error recovery specialist. Analyze the error and task context, "
            "then suggest the best alternative approach. Consider: different tools, different strategies, "
            "simplified scope, or alternative resources. "
            "Output JSON: {\"diagnosis\": str, \"alternative\": str, \"strategy\": str, \"should_retry\": bool, "
            "\"backoff\": int, \"requires_intervention\": bool, \"confidence\": int}"
        )
        task_context = f"Task: {task.title}\nRequest: {task.original_request}\nError: {error}"
        if task.plan:
            task_context += f"\nPlan: {json.dumps(task.plan)[:500]}"

        ai_result = _call_ai(
            f"Diagnose this error and suggest recovery:\n{task_context}",
            system=system,
            timeout=90,
        )
        if ai_result:
            try:
                cleaned = ai_result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["ai_powered"] = True
                return result
            except:
                pass

        # Fallback
        from app.services.advanced_autonomy import error_recovery
        analysis = error_recovery.analyze(error)
        return {**analysis, "ai_powered": False, "requires_intervention": not analysis.get("retry", True)}


class WorkflowSimulator:
    def simulate(self, user_request: str, project_id: Optional[int], db: Session) -> Dict:
        system = (
            "You are a workflow planner and risk analyst. Analyze the user's request and predict:\n"
            "1. All tools and resources needed\n"
            "2. Risk assessment (what could go wrong)\n"
            "3. Required approvals\n"
            "4. Estimated steps and complexity\n"
            "5. Dependencies between steps\n\n"
            "Output JSON: {\"tools\": [str], \"files\": [str], \"connectors\": [str], "
            "\"risks\": [{\"level\": str, \"action\": str, \"mitigation\": str, \"probability\": str}], "
            "\"estimated_steps\": int, \"complexity\": str, \"approval_required\": bool, "
            "\"safe_to_run\": bool, \"parallel_steps\": [[int]], \"critical_path\": [int]}"
        )
        ai_result = _call_ai(
            f"Analyze this request and create a workflow simulation:\n\n{user_request[:2000]}\n\n"
            "Consider: security risks, data access, external API calls, file operations, "
            "deployments, financial transactions, and email notifications.",
            system=system,
            timeout=120,
        )
        if ai_result:
            try:
                cleaned = ai_result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["prompt"] = user_request
                result["project_id"] = project_id
                result["ai_powered"] = True
                return result
            except:
                pass

        # Fallback: keyword-based
        risks = []
        lower = user_request.lower()
        if any(k in lower for k in ["delete", "remove", "drop"]):
            risks.append({"level": "high", "action": "Delete files", "mitigation": "Requires approval"})
        if "email" in lower or "send" in lower:
            risks.append({"level": "medium", "action": "Send email", "mitigation": "Approval Center"})
        if "publish" in lower or "deploy" in lower:
            risks.append({"level": "high", "action": "Publish", "mitigation": "Approval required"})
        if not risks:
            risks.append({"level": "low", "action": "Read/create files", "mitigation": "Auto within permissions"})
        return {
            "prompt": user_request, "project_id": project_id, "tools": [], "files": [], "connectors": [],
            "risks": risks, "estimated_steps": 3, "approval_required": any(r["level"] in ["high"] for r in risks),
            "safe_to_run": True, "ai_powered": False,
        }


class ApprovalCenter:
    def list_pending(self, db: Session, user_id: int) -> List[Dict]:
        from app.models.approval import Approval, ApprovalStatus
        approvals = db.query(Approval).filter(Approval.user_id==user_id, Approval.status==ApprovalStatus.PENDING).order_by(Approval.created_at.desc()).all()
        return [
            {"id": a.id, "type": a.type.value, "title": a.title, "description": a.description,
             "details": a.details, "risk_level": a.risk_level, "task_id": a.task_id,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in approvals
        ]


class ActivityTimeline:
    def get(self, task: Task, db: Session) -> List[Dict]:
        timeline = []
        for cp in (task.plan or {}).get("checkpoints", []):
            timeline.append({"event": "Checkpoint", "detail": f"Step {cp['step']}", "at": cp["timestamp"]})
        timeline.append({"event": "Planning", "detail": task.title, "at": task.created_at.isoformat() if task.created_at else None})
        if task.started_at:
            timeline.append({"event": "Execution started", "detail": f"Model {task.model_used or 'auto'}", "at": task.started_at.isoformat()})
        if task.completed_at:
            timeline.append({"event": "Completed" if task.status.value=="COMPLETED" else "Failed", "detail": task.result or task.error, "at": task.completed_at.isoformat()})
        timeline = [t for t in timeline if t["at"]]
        timeline.sort(key=lambda x: x["at"])
        return timeline


class SnapshotManager:
    def create(self, db: Session, project: Project, user_id: int, name: str) -> Dict:
        from app.models.file import File
        files = db.query(File).filter(File.project_id==project.id).all()
        snapshot = {
            "id": str(uuid.uuid4()), "project_id": project.id, "name": name,
            "created_at": datetime.utcnow().isoformat(), "created_by": user_id,
            "data": {
                "instructions": project.instructions,
                "files": [{"id":f.id, "name":f.name, "path":f.path} for f in files],
                "task_count": db.query(Task).filter(Task.project_id==project.id).count()
            }
        }
        snapshot_path = f"uploads/snapshots/project_{project.id}_{snapshot['id']}.json"
        import os
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot, f)
        return snapshot

    def list(self, project_id: int) -> List[Dict]:
        import glob
        pattern = f"uploads/snapshots/project_{project_id}_*.json"
        snaps = []
        for p in glob.glob(pattern):
            try:
                with open(p) as f:
                    snaps.append(json.load(f))
            except: pass
        snaps.sort(key=lambda x: x["created_at"], reverse=True)
        return snaps

    def restore(self, project_id: int, snapshot_id: str, db: Session) -> Dict:
        path = f"uploads/snapshots/project_{project_id}_{snapshot_id}.json"
        try:
            with open(path) as f:
                snap = json.load(f)
        except:
            raise ValueError("Snapshot not found")
        project = db.query(Project).filter(Project.id==project_id).first()
        if project:
            project.instructions = snap["data"]["instructions"]
            db.commit()
        return snap

    def diff(self, snap1: Dict, snap2: Dict) -> Dict:
        return {
            "instructions_changed": snap1["data"]["instructions"] != snap2["data"]["instructions"],
            "files_added": len(snap2["data"]["files"]) - len(snap1["data"]["files"]),
            "summary": f"Instructions {'changed' if snap1['data']['instructions'] != snap2['data']['instructions'] else 'same'}, files {len(snap1['data']['files'])}→{len(snap2['data']['files'])}"
        }


class SkillDependencyEngine:
    def validate(self, skill: Dict, available_skills: List[str]) -> Dict:
        deps = skill.get("dependencies", [])
        missing = [d for d in deps if d not in available_skills]
        return {"valid": len(missing)==0, "missing": missing, "dependencies": deps}


class KnowledgeGraph:
    def build(self, db: Session, user_id: int, project_id: Optional[int]=None) -> Dict:
        from app.models.project import Project
        from app.models.knowledge import Knowledge, Memory
        from app.models.skill import Skill
        from app.models.file import File
        q_projects = db.query(Project).filter(Project.owner_id==user_id)
        if project_id:
            q_projects = q_projects.filter(Project.id==project_id)
        projects = [{"id":p.id, "name":p.name, "type":"project"} for p in q_projects.limit(10).all()]
        files = [{"id":f.id, "name":f.name, "type":"file", "project_id":f.project_id} for f in db.query(File).filter(File.owner_id==user_id).limit(10).all()]
        skills = [{"id":s.id, "name":s.name, "type":"skill"} for s in db.query(Skill).filter((Skill.owner_id==user_id)|(Skill.owner_id.is_(None))).limit(10).all()]
        knowledge = [{"id":k.id, "name":k.name, "type":"knowledge", "project_id":k.project_id} for k in db.query(Knowledge).filter(Knowledge.owner_id==user_id).limit(10).all()]

        # AI-powered relationship discovery
        all_entities = projects + files + skills + knowledge
        entity_names = [e["name"] for e in all_entities if e.get("name")]
        if entity_names:
            system = (
                "You are a knowledge graph architect. Analyze the entities and discover relationships. "
                "Output JSON: {\"edges\": [{\"from\": str, \"to\": str, \"label\": str, \"weight\": int}], "
                "\"clusters\": [[str]], \"insights\": [str]}"
            )
            ai_relations = _call_ai(
                f"Discover relationships between these entities:\n{json.dumps(entity_names[:20])}",
                system=system, timeout=15,
            )
            if ai_relations:
                try:
                    cleaned = ai_relations.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    ai_data = json.loads(cleaned.strip())
                    edges = [{"from": e["from"], "to": e["to"], "label": e["label"]} for e in ai_data.get("edges", []) if e.get("from") and e.get("to")]
                    return {"nodes": all_entities, "edges": edges, "count": len(all_entities),
                            "clusters": ai_data.get("clusters", []), "insights": ai_data.get("insights", []), "ai_powered": True}
                except:
                    pass

        # Fallback: structural edges
        edges = []
        for f in files:
            if f.get("project_id"):
                edges.append({"from": f"project:{f['project_id']}", "to": f"file:{f['id']}", "label":"contains"})
        for k in knowledge:
            if k.get("project_id"):
                edges.append({"from": f"project:{k['project_id']}", "to": f"knowledge:{k['id']}", "label":"has"})
        return {"nodes": all_entities, "edges": edges, "count": len(all_entities), "ai_powered": False}


blueprint_mgr = BlueprintManager()
healing_engine = SelfHealingEngine()
simulator = WorkflowSimulator()
approval_center = ApprovalCenter()
timeline = ActivityTimeline()
snapshot_mgr = SnapshotManager()
dependency_engine = SkillDependencyEngine()
knowledge_graph = KnowledgeGraph()
