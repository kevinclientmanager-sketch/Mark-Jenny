from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.task import Task, TaskStatus
from app.models.knowledge import Memory, MemoryType
from app.db.base import SessionLocal

class SelfCheckLoop:
    def evaluate(self, task: Task, db: Session) -> Dict[str, Any]:
        checks = {
            "objective_satisfied": bool(task.result),
            "files_present": self._check_files(task, db),
            "calculations_valid": self._check_calculations(task),
            "outputs_readable": self._check_outputs(task),
            "tool_failed": bool(task.error),
            "omitted_requirement": self._check_omission(task),
        }
        satisfied = all([
            checks["objective_satisfied"],
            checks["files_present"],
            checks["calculations_valid"],
            checks["outputs_readable"],
            not checks["tool_failed"],
            not checks["omitted_requirement"]
        ])
        return {"satisfied": satisfied, "checks": checks, "needs_correction": not satisfied}

    def _check_files(self, task: Task, db: Session) -> bool:
        from app.models.file import File
        if task.result and isinstance(task.result, dict) and task.result.get("files"):
            return True
        # If task has files linked, consider present
        count = db.query(File).filter(File.task_id == task.id).count()
        return count > 0 or task.status == TaskStatus.COMPLETED

    def _check_calculations(self, task: Task) -> bool:
        # Stub: validate calculations in result if any
        if task.result and "calculations" in str(task.result).lower():
            # would validate math
            return True
        return True

    def _check_outputs(self, task: Task) -> bool:
        # Check if outputs are readable (not empty, not error)
        if task.error:
            return False
        if task.result and isinstance(task.result, dict) and task.result.get("error"):
            return False
        return True

    def _check_omission(self, task: Task) -> bool:
        # Check if original request keywords are covered in result
        if not task.original_request or not task.result:
            return False
        orig = task.original_request.lower()
        result_str = json.dumps(task.result).lower() if task.result else ""
        # Simple: if request mentions "spreadsheet" but result has no file, omission
        if "spreadsheet" in orig and "spreadsheet" not in result_str and "xlsx" not in result_str:
            return True
        return False

    def corrective_actions(self, evaluation: Dict) -> List[str]:
        actions = []
        checks = evaluation["checks"]
        if not checks["objective_satisfied"]:
            actions.append("Re-execute main goal with clarified prompt")
        if not checks["files_present"]:
            actions.append("Regenerate missing files")
        if not checks["calculations_valid"]:
            actions.append("Recalculate and validate")
        if not checks["outputs_readable"]:
            actions.append("Fix tool failure and retry")
        if checks["omitted_requirement"]:
            actions.append("Add omitted requirement (e.g., spreadsheet)")
        return actions

class CheckpointManager:
    def save(self, task: Task, step: int, state: Dict, db: Session):
        # Save checkpoint as TaskRun or in task.plan checkpoints
        if not task.plan:
            task.plan = {}
        if "checkpoints" not in task.plan:
            task.plan["checkpoints"] = []
        task.plan["checkpoints"].append({
            "step": step,
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Use flag to force update of JSON column
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
        if not analysis["retry"]:
            return False
        if attempt >= 3:
            return False
        return True

    def next_backoff(self, attempt: int) -> int:
        return min(2 ** attempt, 60)  # exponential up to 60s

class MemoryLayerManager:
    # Handles 5 Phase-14 memory types on top of existing 9-layer
    def store_task_memory(self, db: Session, task: Task, decision: str, confidence: int = 80):
        m = Memory(type=MemoryType.TASK, content=decision, source=f"task:{task.id}", owner_id=task.owner_id, project_id=task.project_id, task_id=task.id, confidence=confidence, importance=60)
        db.add(m); db.commit()

    def store_preference(self, db: Session, user_id: int, preference: str, project_id: Optional[int]=None):
        # Only store explicitly approved preferences
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
        # Simple verification: check all subtasks completed and no errors
        failed = [r for r in delegated_results if r.get("status") == "FAILED"]
        pending = [r for r in delegated_results if r.get("status") != "COMPLETED"]
        if failed:
            return {"verified": False, "reason": f"{len(failed)} subtasks failed", "needs_correction": True}
        if pending:
            return {"verified": False, "reason": f"{len(pending)} pending", "needs_correction": False}
        # Self-check via SelfCheckLoop
        checker = SelfCheckLoop()
        eval = checker.evaluate(task, db)
        if not eval["satisfied"]:
            return {"verified": False, "reason": f"Self-check failed: {eval['checks']}", "needs_correction": True, "actions": checker.corrective_actions(eval)}
        return {"verified": True, "reason": "All subtasks completed and self-check passed"}

# Singletons
self_check = SelfCheckLoop()
checkpoint_mgr = CheckpointManager()
error_recovery = ErrorRecovery()
memory_layer = MemoryLayerManager()
delegation = MultiAgentDelegation()
supervisor = Supervisor()
