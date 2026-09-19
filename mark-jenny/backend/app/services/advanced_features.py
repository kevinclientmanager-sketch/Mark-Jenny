import json
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.task import Task
from app.models.project import Project

# Blueprint: reusable workflow from successful task
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
        # Store as Project knowledge or file? For now store in task.result blueprints
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

# Self-Healing: diagnose -> alternative -> retry
class SelfHealingEngine:
    def heal(self, task: Task, error: str, db: Session) -> Dict:
        from app.services.advanced_autonomy import error_recovery
        analysis = error_recovery.analyze(error)
        # Try alternative: if tool failed, try different tool
        alternatives = {
            "web_search": "Use browser_navigate",
            "file_write": "Try alternative path",
            "code_execute": "Try different language",
        }
        # Simple: pick first tool's alternative
        current_tools = task.plan.get("tools", []) if task.plan else []
        alt_tool = None
        for t in current_tools:
            if t in alternatives:
                alt_tool = alternatives[t]
                break
        should_retry = error_recovery.should_retry(task, error, 0)
        return {
            "diagnosis": analysis,
            "alternative": alt_tool or analysis["alternative"],
            "should_retry": should_retry,
            "backoff": error_recovery.next_backoff(0) if should_retry else 0,
            "requires_intervention": not should_retry
        }

# Dry Run / Workflow Simulator
class WorkflowSimulator:
    def simulate(self, user_request: str, project_id: Optional[int], db: Session) -> Dict:
        # Use planner to generate plan, then list risks without executing
        from app.services.agent_controller import TaskPlanner
        # Mock user for planner
        from app.models.user import User
        # For simulation, we don't need real user, just heuristic
        risks = []
        lower = user_request.lower()
        if any(k in lower for k in ["delete", "remove", "drop"]):
            risks.append({"level": "high", "action": "Delete files", "mitigation": "Requires approval L2+ and confirmation"})
        if "email" in lower or "send" in lower:
            risks.append({"level": "medium", "action": "Send email", "mitigation": "Approval Center"})
        if "publish" in lower or "deploy" in lower:
            risks.append({"level": "high", "action": "Publish website", "mitigation": "Approval required"})
        if "spend" in lower or "money" in lower or "pay" in lower:
            risks.append({"level": "critical", "action": "Spend money", "mitigation": "Explicit approval + credits check"})
        if not risks:
            risks.append({"level": "low", "action": "Read/create files", "mitigation": "Auto within permissions"})

        # Estimate tools/files/connectors
        tools = []
        if "research" in lower: tools.append("web_search")
        if "spreadsheet" in lower: tools.append("spreadsheet")
        if "code" in lower: tools.append("code_execute")
        if "browser" in lower: tools.append("browser_navigate")

        files = []
        if "spreadsheet" in lower: files.append("output.xlsx (to be created in project)")
        if "report" in lower: files.append("report.md (to be created)")

        connectors = []
        if "gmail" in lower: connectors.append("Gmail")
        if "drive" in lower: connectors.append("Google Drive")

        return {
            "prompt": user_request,
            "project_id": project_id,
            "tools": tools,
            "files": files,
            "connectors": connectors,
            "risks": risks,
            "estimated_steps": 3,
            "approval_required": any(r["level"] in ["high","critical"] for r in risks),
            "safe_to_run": len([r for r in risks if r["level"]=="critical"]) == 0
        }

# Approval Center
class ApprovalCenter:
    def list_pending(self, db: Session, user_id: int) -> List[Dict]:
        from app.models.approval import Approval, ApprovalStatus
        approvals = db.query(Approval).filter(Approval.user_id==user_id, Approval.status==ApprovalStatus.PENDING).order_by(Approval.created_at.desc()).all()
        return [
            {
                "id": a.id, "type": a.type.value, "title": a.title, "description": a.description,
                "details": a.details, "risk_level": a.risk_level, "task_id": a.task_id,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in approvals
        ]

# Agent Activity Timeline
class ActivityTimeline:
    def get(self, task: Task, db: Session) -> List[Dict]:
        # Build from task checkpoints + task runs + audit logs
        timeline = []
        # From checkpoints
        for cp in (task.plan or {}).get("checkpoints", []):
            timeline.append({"event": "Checkpoint", "detail": f"Step {cp['step']}", "at": cp["timestamp"]})
        # From task status
        timeline.append({"event": "Planning", "detail": task.title, "at": task.created_at.isoformat() if task.created_at else None})
        if task.started_at:
            timeline.append({"event": "Execution started", "detail": f"Model {task.model_used or 'auto'}", "at": task.started_at.isoformat()})
        if task.completed_at:
            timeline.append({"event": "Completed" if task.status.value=="COMPLETED" else "Failed", "detail": task.result or task.error, "at": task.completed_at.isoformat()})
        # Sort by time
        timeline = [t for t in timeline if t["at"]]
        timeline.sort(key=lambda x: x["at"])
        return timeline

# Project Snapshots
class SnapshotManager:
    def create(self, db: Session, project: Project, user_id: int, name: str) -> Dict:
        # Snapshot is JSON of project files + instructions + tasks
        from app.models.file import File
        files = db.query(File).filter(File.project_id==project.id).all()
        snapshot = {
            "id": str(uuid.uuid4()),
            "project_id": project.id,
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user_id,
            "data": {
                "instructions": project.instructions,
                "files": [{"id":f.id, "name":f.name, "path":f.path} for f in files],
                "task_count": db.query(Task).filter(Task.project_id==project.id).count()
            }
        }
        if not project.instructions:
            project.instructions = ""
        # Store snapshot in project.config JSON or separate table; for now store in project description json
        # Use a simple in-memory store via project.instructions snapshots list in plan-like field
        # For persistence, we store in a new table would be ideal, but for now use file storage
        snapshot_path = f"uploads/snapshots/project_{project.id}_{snapshot['id']}.json"
        import os, json
        os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot, f)
        return snapshot

    def list(self, project_id: int) -> List[Dict]:
        import os, json, glob
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
        import json
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

# Skill Dependency Engine
class SkillDependencyEngine:
    def validate(self, skill: Dict, available_skills: List[str]) -> Dict:
        deps = skill.get("dependencies", [])
        missing = [d for d in deps if d not in available_skills]
        return {"valid": len(missing)==0, "missing": missing, "dependencies": deps}

# Knowledge Graph
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
        # Edges: project -> files, project -> knowledge, skill -> dependencies
        edges = []
        for f in files:
            if f["project_id"]:
                edges.append({"from": f"project:{f['project_id']}", "to": f"file:{f['id']}", "label":"contains"})
        for k in knowledge:
            if k["project_id"]:
                edges.append({"from": f"project:{k['project_id']}", "to": f"knowledge:{k['id']}", "label":"has"})
        return {"nodes": projects + files + skills + knowledge, "edges": edges, "count": len(projects)+len(files)+len(skills)+len(knowledge)}

blueprint_mgr = BlueprintManager()
healing_engine = SelfHealingEngine()
simulator = WorkflowSimulator()
approval_center = ApprovalCenter()
timeline = ActivityTimeline()
snapshot_mgr = SnapshotManager()
dependency_engine = SkillDependencyEngine()
knowledge_graph = KnowledgeGraph()
