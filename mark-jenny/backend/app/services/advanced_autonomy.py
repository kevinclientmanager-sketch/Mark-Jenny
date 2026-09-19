from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.task import Task, TaskStatus
from app.models.knowledge import Memory, MemoryType
from app.db.base import SessionLocal


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


class SelfCheckLoop:
    def evaluate(self, task: Task, db: Session) -> Dict[str, Any]:
        """AI-powered evaluation of task completion quality."""
        system = (
            "You are a quality assurance expert. Evaluate whether this task was completed successfully. "
            "Check: objective satisfaction, output quality, completeness, correctness, and edge cases. "
            "Output JSON: {\"satisfied\": bool, \"quality_score\": int 0-100, "
            "\"checks\": {\"objective_satisfied\": bool, \"output_quality\": str, \"completeness\": str, "
            "\"correctness\": str, \"edge_cases\": str}, "
            "\"issues\": [str], \"needs_correction\": bool}"
        )
        task_info = f"Title: {task.title}\nRequest: {task.original_request}\nStatus: {task.status.value}"
        if task.result:
            result_str = json.dumps(task.result) if isinstance(task.result, dict) else str(task.result)
            task_info += f"\nResult: {result_str[:3000]}"
        if task.error:
            task_info += f"\nError: {task.error}"

        ai_eval = _call_ai(
            f"Evaluate task completion:\n{task_info}",
            system=system, timeout=120,
        )
        if ai_eval:
            try:
                cleaned = ai_eval.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["ai_powered"] = True
                return result
            except:
                pass

        # Fallback: basic checks
        checks = {
            "objective_satisfied": bool(task.result),
            "files_present": self._check_files(task, db),
            "calculations_valid": True,
            "outputs_readable": self._check_outputs(task),
            "tool_failed": bool(task.error),
            "omitted_requirement": self._check_omission(task),
        }
        satisfied = all([
            checks["objective_satisfied"], checks["files_present"],
            checks["calculations_valid"], checks["outputs_readable"],
            not checks["tool_failed"], not checks["omitted_requirement"]
        ])
        return {"satisfied": satisfied, "checks": checks, "needs_correction": not satisfied, "ai_powered": False}

    def _check_files(self, task: Task, db: Session) -> bool:
        from app.models.file import File
        if task.result and isinstance(task.result, dict) and task.result.get("files"):
            return True
        count = db.query(File).filter(File.task_id == task.id).count()
        return count > 0 or task.status == TaskStatus.COMPLETED

    def _check_outputs(self, task: Task) -> bool:
        if task.error:
            return False
        if task.result and isinstance(task.result, dict) and task.result.get("error"):
            return False
        return True

    def _check_omission(self, task: Task) -> bool:
        if not task.original_request or not task.result:
            return False
        orig = task.original_request.lower()
        result_str = json.dumps(task.result).lower() if task.result else ""
        keywords = ["spreadsheet", "report", "website", "code", "image", "document"]
        for kw in keywords:
            if kw in orig and kw not in result_str and f"{kw}" not in result_str:
                return True
        return False

    def corrective_actions(self, evaluation: Dict) -> List[str]:
        if evaluation.get("ai_powered") and evaluation.get("issues"):
            return evaluation["issues"]
        actions = []
        checks = evaluation.get("checks", {})
        if not checks.get("objective_satisfied"):
            actions.append("Re-execute main goal with clarified prompt")
        if not checks.get("files_present"):
            actions.append("Regenerate missing files")
        if checks.get("omitted_requirement"):
            actions.append("Add omitted requirement")
        return actions


class CheckpointManager:
    def save(self, task: Task, step: int, state: Dict, db: Session):
        if not task.plan:
            task.plan = {}
        if "checkpoints" not in task.plan:
            task.plan["checkpoints"] = []
        task.plan["checkpoints"].append({
            "step": step, "state": state, "timestamp": datetime.utcnow().isoformat()
        })
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(task, "plan")
        db.commit()

    def restore(self, task: Task, checkpoint_idx: int = -1) -> Optional[Dict]:
        checkpoints = (task.plan or {}).get("checkpoints", [])
        if not checkpoints:
            return None
        return checkpoints[checkpoint_idx] if -len(checkpoints) <= checkpoint_idx < len(checkpoints) else None

    def list_checkpoints(self, task: Task) -> List[Dict]:
        return (task.plan or {}).get("checkpoints", [])


class ErrorRecovery:
    def analyze(self, error: str) -> Dict:
        """AI-powered error analysis and recovery strategy."""
        system = (
            "You are an error recovery specialist. Analyze the error and provide a comprehensive recovery plan. "
            "Consider: root cause, immediate fix, long-term prevention, alternative approaches, "
            "and whether to retry or escalate. "
            "Output JSON: {\"type\": str, \"root_cause\": str, \"retry\": bool, \"alternative\": str, "
            "\"strategy\": str, \"prevention\": str, \"confidence\": int}"
        )
        ai_result = _call_ai(
            f"Analyze this error and provide recovery strategy:\n\nError: {error[:2000]}",
            system=system, timeout=60,
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
        err_lower = error.lower() if error else ""
        if "timeout" in err_lower:
            return {"type": "timeout", "retry": True, "alternative": "Increase timeout and retry with backoff"}
        if "not found" in err_lower or "404" in err_lower:
            return {"type": "not_found", "retry": False, "alternative": "Try alternative resource or search"}
        if "permission" in err_lower or "403" in err_lower:
            return {"type": "permission", "retry": False, "alternative": "Request approval or check credentials"}
        if "rate limit" in err_lower or "429" in err_lower:
            return {"type": "rate_limit", "retry": True, "alternative": "Exponential backoff"}
        return {"type": "unknown", "retry": True, "alternative": "Try alternative method"}

    def should_retry(self, task: Task, error: str, attempt: int) -> bool:
        analysis = self.analyze(error)
        if not analysis.get("retry", True):
            return False
        if attempt >= 3:
            return False
        return True

    def next_backoff(self, attempt: int) -> int:
        return min(2 ** attempt, 60)


class MemoryLayerManager:
    def store_task_memory(self, db: Session, task: Task, decision: str, confidence: int = 80):
        m = Memory(type=MemoryType.TASK, content=decision, source=f"task:{task.id}", owner_id=task.owner_id, project_id=task.project_id, task_id=task.id, confidence=confidence, importance=60)
        db.add(m); db.commit()

    def store_preference(self, db: Session, user_id: int, preference: str, project_id: Optional[int]=None):
        m = Memory(type=MemoryType.USER_PREFERENCE, content=preference, source="user_approved", owner_id=user_id, project_id=project_id, confidence=100, importance=90)
        db.add(m); db.commit()

    def store_project_memory(self, db: Session, task: Task, knowledge: str):
        m = Memory(type=MemoryType.PROJECT, content=knowledge, source=f"project:{task.project_id}", owner_id=task.owner_id, project_id=task.project_id, confidence=85, importance=75)
        db.add(m); db.commit()

    def store_skill_memory(self, db: Session, user_id: int, workflow: str, project_id: Optional[int]=None):
        m = Memory(type=MemoryType.PROCEDURAL, content=workflow, source="skill_success", owner_id=user_id, project_id=project_id, confidence=90, importance=80)
        db.add(m); db.commit()

    def store_failure(self, db: Session, task: Task, failure: str, pattern: str):
        m = Memory(type=MemoryType.FAILURE, content=f"Failure: {failure} | Pattern: {pattern}", source=f"task:{task.id}", owner_id=task.owner_id, project_id=task.project_id, task_id=task.id, confidence=95, importance=85)
        db.add(m); db.commit()

    def get_failure_patterns(self, db: Session, user_id: int) -> List[str]:
        failures = db.query(Memory).filter(Memory.owner_id==user_id, Memory.type==MemoryType.FAILURE, Memory.enabled==True).all()
        return [f.content for f in failures]


class MultiAgentDelegation:
    SPECIALIZED_AGENTS = {
        "research": {"type": "RESEARCH", "skills": ["research-agent"], "model": "research"},
        "coding": {"type": "CODING", "skills": ["code"], "model": "coding"},
        "browser": {"type": "BROWSER", "skills": ["browser_navigate"], "model": "vision"},
        "document": {"type": "DOCUMENT", "skills": ["document"], "model": "fast"},
        "spreadsheet": {"type": "SPREADSHEET", "skills": ["spreadsheet"], "model": "fast"},
        "design": {"type": "DESIGN", "skills": ["image_generation"], "model": "image_generation"},
        "data": {"type": "DATA", "skills": ["data"], "model": "deep_reasoning"},
        "security": {"type": "SECURITY", "skills": ["security"], "model": "deep_reasoning"},
        "qa": {"type": "QA", "skills": ["qa"], "model": "fast"},
    }

    def delegate(self, primary_task: Task, subtasks: List[Dict]) -> List[Dict]:
        """AI-powered task delegation to specialized agents."""
        system = (
            "You are a task delegation expert. Analyze each subtask and assign it to the optimal agent. "
            "Consider: task type, complexity, required skills, and agent capabilities. "
            "Output JSON: {\"delegations\": [{\"title\": str, \"agent\": str, \"reason\": str, \"priority\": str}]}"
        )
        task_descriptions = [f"- {st.get('title', 'Unknown')}" for st in subtasks]
        ai_result = _call_ai(
            f"Delegate these subtasks to optimal agents:\n{chr(10).join(task_descriptions)}\n\n"
            f"Available agents: {json.dumps(list(self.SPECIALIZED_AGENTS.keys()))}",
            system=system, timeout=60,
        )
        if ai_result:
            try:
                cleaned = ai_result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                ai_data = json.loads(cleaned.strip())
                delegations = ai_data.get("delegations", [])
                result = []
                for i, st in enumerate(subtasks):
                    agent_key = delegations[i]["agent"] if i < len(delegations) else "research"
                    if agent_key not in self.SPECIALIZED_AGENTS:
                        agent_key = "research"
                    result.append({
                        **st,
                        "assigned_agent": agent_key,
                        "agent_config": self.SPECIALIZED_AGENTS[agent_key],
                        "delegation_reason": delegations[i].get("reason", "") if i < len(delegations) else "",
                    })
                return result
            except:
                pass

        # Fallback: keyword matching
        delegated = []
        for st in subtasks:
            title = st.get("title","").lower()
            agent_key = "research"
            if any(k in title for k in ["code","build","app","develop"]): agent_key = "coding"
            elif any(k in title for k in ["browse","website","navigate"]): agent_key = "browser"
            elif any(k in title for k in ["document","report","write"]): agent_key = "document"
            elif any(k in title for k in ["spreadsheet","excel","sheet"]): agent_key = "spreadsheet"
            elif any(k in title for k in ["design","image","video"]): agent_key = "design"
            elif any(k in title for k in ["data","analysis"]): agent_key = "data"
            elif any(k in title for k in ["security","audit"]): agent_key = "security"
            elif any(k in title for k in ["test","qa","validate"]): agent_key = "qa"
            delegated.append({**st, "assigned_agent": agent_key, "agent_config": self.SPECIALIZED_AGENTS[agent_key]})
        return delegated


class Supervisor:
    def verify(self, task: Task, delegated_results: List[Dict], db: Session) -> Dict:
        """AI-powered verification of delegated task results."""
        failed = [r for r in delegated_results if r.get("status") == "FAILED"]
        pending = [r for r in delegated_results if r.get("status") != "COMPLETED"]
        if failed:
            return {"verified": False, "reason": f"{len(failed)} subtasks failed", "needs_correction": True}
        if pending:
            return {"verified": False, "reason": f"{len(pending)} pending", "needs_correction": False}

        # AI quality verification
        system = (
            "You are a quality supervisor. Verify that all subtask results meet the requirements. "
            "Check for: completeness, correctness, consistency between results, and overall quality. "
            "Output JSON: {\"verified\": bool, \"quality_score\": int, \"issues\": [str], \"suggestions\": [str]}"
        )
        results_summary = json.dumps([{k: v for k, v in r.items() if k != "code"} for r in delegated_results[:10]])
        ai_verify = _call_ai(
            f"Verify these task results:\nTask: {task.title}\nRequest: {task.original_request}\nResults: {results_summary[:4000]}",
            system=system, timeout=90,
        )
        if ai_verify:
            try:
                cleaned = ai_verify.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["ai_powered"] = True
                return result
            except:
                pass

        # Fallback: basic self-check
        checker = SelfCheckLoop()
        evaluation = checker.evaluate(task, db)
        if not evaluation["satisfied"]:
            return {"verified": False, "reason": f"Self-check failed", "needs_correction": True,
                    "actions": checker.corrective_actions(evaluation)}
        return {"verified": True, "reason": "All subtasks completed and self-check passed"}


# Singletons
self_check = SelfCheckLoop()
checkpoint_mgr = CheckpointManager()
error_recovery = ErrorRecovery()
memory_layer = MemoryLayerManager()
delegation = MultiAgentDelegation()
supervisor = Supervisor()
