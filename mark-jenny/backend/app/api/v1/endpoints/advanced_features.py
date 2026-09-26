from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.models.approval import Approval, ApprovalStatus
from app.services.advanced_features import blueprint_mgr, healing_engine, simulator, approval_center, timeline, snapshot_mgr, dependency_engine, knowledge_graph
from app.utils.audit import log_audit

router = APIRouter()

# Blueprints
@router.post("/blueprints/{task_id}")
async def save_blueprint(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id, Task.owner_id==current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    if task.status.value != "COMPLETED":
        raise HTTPException(status_code=400, detail="Only completed tasks can be saved as blueprint")
    bp = blueprint_mgr.save(db, task, current_user.id)
    return bp

@router.get("/blueprints")
async def list_blueprints(project_id: Optional[int]=None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if project_id:
        return blueprint_mgr.list_for_project(db, project_id, current_user.id)
    # all projects
    all_bps = []
    projects = db.query(Project).filter(Project.owner_id==current_user.id).all()
    for p in projects:
        all_bps.extend(blueprint_mgr.list_for_project(db, p.id, current_user.id))
    return all_bps

# Self-Healing
class HealRequest(BaseModel):
    error: str

@router.post("/heal/{task_id}")
async def heal_task(task_id: int, data: HealRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id, Task.owner_id==current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    result = healing_engine.heal(task, data.error, db)
    if result["should_retry"]:
        task.status = "PENDING"
        db.commit()
    return result

# Dry Run / Simulator
class SimulateRequest(BaseModel):
    prompt: str
    project_id: Optional[int] = None

@router.post("/simulate")
async def simulate(data: SimulateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = simulator.simulate(data.prompt, data.project_id, db)
    return result

@router.post("/dry-run")
async def dry_run(data: SimulateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = simulator.simulate(data.prompt, data.project_id, db)
    result["mode"] = "dry_run"
    result["note"] = "No destructive operations performed - preview only"
    return result

# Approval Center
@router.get("/approvals/pending")
async def list_pending(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return approval_center.list_pending(db, current_user.id)

@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: int, reason: Optional[str]=None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appr = db.query(Approval).filter(Approval.id==approval_id, Approval.user_id==current_user.id).first()
    if not appr: raise HTTPException(status_code=404, detail="Approval not found")
    appr.status = ApprovalStatus.APPROVED
    appr.decided_by = current_user.id
    from datetime import datetime
    appr.decided_at = datetime.utcnow()
    appr.decision_reason = reason
    db.commit()
    await log_audit(db, user_id=current_user.id, action="TASK_APPROVE", resource_type="approval", resource_id=str(approval_id), success=True)
    return {"message":"Approved"}

@router.post("/approvals/{approval_id}/reject")
async def reject(approval_id: int, reason: Optional[str]=None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appr = db.query(Approval).filter(Approval.id==approval_id, Approval.user_id==current_user.id).first()
    if not appr: raise HTTPException(status_code=404, detail="Approval not found")
    appr.status = ApprovalStatus.REJECTED
    appr.decided_by = current_user.id
    from datetime import datetime
    appr.decided_at = datetime.utcnow()
    appr.decision_reason = reason
    db.commit()
    await log_audit(db, user_id=current_user.id, action="TASK_REJECT", resource_type="approval", resource_id=str(approval_id), success=True)
    return {"message":"Rejected"}

# Timeline
@router.get("/timeline/{task_id}")
async def get_timeline(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id==task_id, Task.owner_id==current_user.id).first()
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    return {"timeline": timeline.get(task, db)}

# Snapshots
class SnapshotCreate(BaseModel):
    name: str

@router.post("/snapshots/{project_id}")
async def create_snapshot(project_id: int, data: SnapshotCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id==project_id, Project.owner_id==current_user.id).first()
    if not proj: raise HTTPException(status_code=404, detail="Project not found")
    snap = snapshot_mgr.create(db, proj, current_user.id, data.name)
    return snap

@router.get("/snapshots/{project_id}")
async def list_snapshots(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id==project_id, Project.owner_id==current_user.id).first()
    if not proj: raise HTTPException(status_code=404, detail="Project not found")
    return snapshot_mgr.list(project_id)

@router.post("/snapshots/{project_id}/restore/{snapshot_id}")
async def restore_snapshot(project_id: int, snapshot_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id==project_id, Project.owner_id==current_user.id).first()
    if not proj: raise HTTPException(status_code=404, detail="Project not found")
    snap = snapshot_mgr.restore(project_id, snapshot_id, db)
    return {"message":"Restored", "snapshot": snap}

@router.get("/snapshots/{project_id}/diff")
async def diff_snapshots(project_id: int, id1: str, id2: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import json, glob
    proj = db.query(Project).filter(Project.id==project_id, Project.owner_id==current_user.id).first()
    if not proj: raise HTTPException(status_code=404, detail="Project not found")
    snaps = snapshot_mgr.list(project_id)
    s1 = next((s for s in snaps if s["id"]==id1), None)
    s2 = next((s for s in snaps if s["id"]==id2), None)
    if not s1 or not s2: raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot_mgr.diff(s1, s2)

# Skill Dependency
class DependencyCheck(BaseModel):
    skill: Dict[str, Any]
    available_skills: List[str]

@router.post("/skill-dependency/validate")
async def validate_dependency(data: DependencyCheck, current_user: User = Depends(get_current_user)):
    return dependency_engine.validate(data.skill, data.available_skills)

# Knowledge Graph
@router.get("/knowledge-graph")
async def get_graph(project_id: Optional[int]=None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return knowledge_graph.build(db, current_user.id, project_id)

# Security - rate limit info
@router.get("/security/rate-limit")
async def get_rate_limit(current_user: User = Depends(get_current_user), request: Request = None):
    from app.core.rate_limit import limiter, auth_limiter
    # Report the caller's actual remaining budget instead of a bare string.
    ip = None
    try:
        ip = request.client.host if request and request.client else None
    except Exception:
        ip = None
    used = 0
    if ip:
        try:
            used = len(limiter.clients.get(ip, []))
        except Exception:
            used = 0
    return {
        "general": f"{limiter.max_requests} req per {limiter.window}s per IP",
        "auth": f"{auth_limiter.max_requests} req per {auth_limiter.window}s per IP",
        "max_requests": limiter.max_requests,
        "window_seconds": limiter.window,
        "used": used,
        "remaining": max(0, limiter.max_requests - used),
        "note": "Enforced via middleware, 429 on exceed",
    }
