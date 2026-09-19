from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task
from app.services.advanced_autonomy import self_check, checkpoint_mgr, error_recovery, memory_layer, delegation, supervisor
from app.utils.audit import log_audit

router = APIRouter()

class CheckpointCreate(BaseModel):
    step: int
    state: Dict[str, Any]

class MemoryCreate(BaseModel):
    type: str  # TASK, USER_PREFERENCE, PROJECT, PROCEDURAL, FAILURE
    content: str
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    confidence: Optional[int] = None

@router.post("/self-check/{task_id}")
async def run_self_check(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    result = self_check.evaluate(task, db)
    actions = self_check.corrective_actions(result) if not result["satisfied"] else []
    return {"task_id": task_id, "evaluation": result, "corrective_actions": actions}

@router.post("/checkpoint/{task_id}")
async def save_checkpoint(task_id: int, data: CheckpointCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    checkpoint_mgr.save(task, data.step, data.state, db)
    return {"message": "Checkpoint saved", "checkpoints": checkpoint_mgr.list_checkpoints(task)}

@router.get("/checkpoint/{task_id}")
async def list_checkpoints(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    return {"checkpoints": checkpoint_mgr.list_checkpoints(task)}

@router.post("/checkpoint/{task_id}/restore/{idx}")
async def restore_checkpoint(task_id: int, idx: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    cp = checkpoint_mgr.restore(task, idx)
    if not cp: raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"checkpoint": cp}

@router.post("/recover/{task_id}")
async def recover_error(task_id: int, error: str, attempt: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    analysis = error_recovery.analyze(error)
    should = error_recovery.should_retry(task, error, attempt)
    backoff = error_recovery.next_backoff(attempt)
    if should:
        # store failure memory for learning
        memory_layer.store_failure(db, task, error, analysis["type"])
    return {"analysis": analysis, "should_retry": should, "backoff_seconds": backoff, "attempt": attempt}

@router.post("/delegate/{task_id}")
async def delegate_task(task_id: int, subtasks: List[Dict[str, Any]], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    delegated = delegation.delegate(task, subtasks)
    # Log delegation
    await log_audit(db, user_id=current_user.id, action="TASK_CREATE", resource_type="delegation", resource_id=str(task_id), success=True)
    return {"delegated": delegated, "agents": list(delegation.SPECIALIZED_AGENTS.keys())}

@router.post("/verify/{task_id}")
async def verify_task(task_id: int, results: List[Dict[str, Any]], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    res = supervisor.verify(task, results, db)
    return res

# Memory layers
@router.post("/memory")
async def create_memory(data: MemoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Map type string to handler
    t = data.type.upper()
    if t == "TASK":
        if not data.task_id: raise HTTPException(status_code=400, detail="task_id required for TASK memory")
        task = db.query(Task).filter(Task.id == data.task_id, Task.owner_id == current_user.id).first()
        if not task: raise HTTPException(status_code=404, detail="Task not found")
        memory_layer.store_task_memory(db, task, data.content, data.confidence or 80)
    elif t == "USER_PREFERENCE":
        memory_layer.store_preference(db, current_user.id, data.content, data.project_id)
    elif t == "PROJECT":
        # need task to get project
        if data.project_id:
            # create dummy task for project memory
            class Dummy: pass
            d = Dummy(); d.owner_id=current_user.id; d.project_id=data.project_id
            memory_layer.store_project_memory(db, d, data.content)  # type: ignore
        else:
            raise HTTPException(status_code=400, detail="project_id required for PROJECT memory")
    elif t in ["PROCEDURAL","SKILL"]:
        memory_layer.store_skill_memory(db, current_user.id, data.content, data.project_id)
    elif t == "FAILURE":
        if not data.task_id: raise HTTPException(status_code=400, detail="task_id required for FAILURE")
        task = db.query(Task).filter(Task.id == data.task_id, Task.owner_id == current_user.id).first()
        if not task: raise HTTPException(status_code=404, detail="Task not found")
        memory_layer.store_failure(db, task, data.content, "manual")
    else:
        raise HTTPException(status_code=400, detail="Unknown memory type")
    return {"message": f"{t} memory stored"}

@router.get("/memory/failures")
async def get_failures(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patterns = memory_layer.get_failure_patterns(db, current_user.id)
    return {"failures": patterns, "count": len(patterns)}

@router.get("/agents/specialized")
async def list_specialized(current_user: User = Depends(get_current_user)):
    return delegation.SPECIALIZED_AGENTS
