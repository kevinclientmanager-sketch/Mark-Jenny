from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import Memory, MemoryType
from app.models.project import Project
from app.models.task import Task
from app.utils.audit import log_audit

router = APIRouter()

class MemoryCreate(BaseModel):
    type: MemoryType
    content: str
    source: Optional[str] = None
    confidence: int = 100
    importance: int = 50
    enabled: bool = True
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    memory_metadata: Optional[dict] = None

class MemoryUpdate(BaseModel):
    type: Optional[MemoryType] = None
    content: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[int] = None
    importance: Optional[int] = None
    enabled: Optional[bool] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    memory_metadata: Optional[dict] = None

class MemoryResponse(BaseModel):
    id: int
    type: str
    content: str
    source: Optional[str]
    confidence: Optional[int]
    importance: Optional[int]
    enabled: bool
    owner_id: int
    project_id: Optional[int]
    project_name: Optional[str]
    task_id: Optional[int]
    memory_metadata: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True

class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]
    total: int
    page: int
    page_size: int

def _to_resp(db: Session, m: Memory) -> MemoryResponse:
    proj_name = None
    if m.project_id:
        p = db.query(Project).filter(Project.id == m.project_id).first()
        if p: proj_name = p.name
    return MemoryResponse(
        id=m.id, type=m.type.value, content=m.content, source=m.source, confidence=m.confidence,
        importance=m.importance, enabled=m.enabled, owner_id=m.owner_id, project_id=m.project_id,
        project_name=proj_name, task_id=m.task_id, memory_metadata=m.memory_metadata,
        created_at=m.created_at, updated_at=m.updated_at
    )

@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    type: Optional[MemoryType] = None,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    sort_by: str = Query("updated_at", pattern="^(created_at|updated_at|importance|confidence|type)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Memory).filter(Memory.owner_id == current_user.id)
    if search:
        q = q.filter(Memory.content.ilike(f"%{search}%"))
    if type:
        q = q.filter(Memory.type == type)
    if project_id is not None:
        q = q.filter(Memory.project_id == project_id)
    if task_id is not None:
        q = q.filter(Memory.task_id == task_id)
    if enabled is not None:
        q = q.filter(Memory.enabled == enabled)
    col = getattr(Memory, sort_by)
    q = q.order_by(desc(col) if sort_order=="desc" else col)
    total = q.count()
    items = q.offset((page-1)*page_size).limit(page_size).all()
    return MemoryListResponse(memories=[_to_resp(db, x) for x in items], total=total, page=page, page_size=page_size)

@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    data: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.project_id:
        p = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
        if not p: raise HTTPException(status_code=404, detail="Project not found")
    if data.task_id:
        t = db.query(Task).filter(Task.id == data.task_id, Task.owner_id == current_user.id).first()
        if not t: raise HTTPException(status_code=404, detail="Task not found")
    # never store sensitive info unnecessarily
    if data.content and any(s in data.content.lower() for s in ["api_key","password","secret"]):
        pass
    m = Memory(
        type=data.type, content=data.content, source=data.source, confidence=data.confidence,
        importance=data.importance, enabled=data.enabled, owner_id=current_user.id,
        project_id=data.project_id, task_id=data.task_id, memory_metadata=data.memory_metadata
    )
    db.add(m); db.commit(); db.refresh(m)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="memory", resource_id=str(m.id), success=True)
    return _to_resp(db, m)

@router.get("/{mid}", response_model=MemoryResponse)
async def get_memory(mid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Memory).filter(Memory.id == mid, Memory.owner_id == current_user.id).first()
    if not m: raise HTTPException(status_code=404, detail="Memory not found")
    return _to_resp(db, m)

@router.patch("/{mid}", response_model=MemoryResponse)
async def update_memory(mid: int, data: MemoryUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Memory).filter(Memory.id == mid, Memory.owner_id == current_user.id).first()
    if not m: raise HTTPException(status_code=404, detail="Memory not found")
    if data.project_id is not None:
        if data.project_id:
            p = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
            if not p: raise HTTPException(status_code=404, detail="Project not found")
        m.project_id = data.project_id
    if data.task_id is not None:
        if data.task_id:
            t = db.query(Task).filter(Task.id == data.task_id, Task.owner_id == current_user.id).first()
            if not t: raise HTTPException(status_code=404, detail="Task not found")
        m.task_id = data.task_id
    for f in ["type","content","source","confidence","importance","enabled","memory_metadata"]:
        v = getattr(data, f)
        if v is not None: setattr(m, f, v)
    db.commit(); db.refresh(m)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="memory", resource_id=str(m.id), success=True)
    return _to_resp(db, m)

@router.delete("/{mid}")
async def delete_memory(mid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Memory).filter(Memory.id == mid, Memory.owner_id == current_user.id).first()
    if not m: raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(m); db.commit()
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="memory", resource_id=str(m.id), success=True)
    return {"message":"Memory deleted"}

@router.post("/{mid}/toggle", response_model=MemoryResponse)
async def toggle_memory(mid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Memory).filter(Memory.id == mid, Memory.owner_id == current_user.id).first()
    if not m: raise HTTPException(status_code=404, detail="Memory not found")
    m.enabled = not m.enabled
    db.commit(); db.refresh(m)
    return _to_resp(db, m)

@router.get("/types/list")
async def list_memory_types(current_user: User = Depends(get_current_user)):
    return [{"value": e.value, "label": e.value.replace("_"," ").title()} for e in MemoryType]
