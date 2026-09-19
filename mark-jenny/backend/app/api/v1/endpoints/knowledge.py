from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.knowledge import Knowledge
from app.models.project import Project
from app.utils.audit import log_audit

router = APIRouter()

class KnowledgeCreate(BaseModel):
    name: str
    use_when: Optional[str] = None
    content: str
    enabled: bool = True
    project_id: Optional[int] = None
    source: Optional[str] = None
    confidence: int = 100
    importance: int = 50
    tags: Optional[List[str]] = None

class KnowledgeUpdate(BaseModel):
    name: Optional[str] = None
    use_when: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None
    project_id: Optional[int] = None
    source: Optional[str] = None
    confidence: Optional[int] = None
    importance: Optional[int] = None
    tags: Optional[List[str]] = None

class KnowledgeResponse(BaseModel):
    id: int
    name: str
    use_when: Optional[str]
    content: str
    enabled: bool
    project_id: Optional[int]
    project_name: Optional[str]
    owner_id: Optional[int]
    source: Optional[str]
    confidence: Optional[int]
    importance: Optional[int]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True

class KnowledgeListResponse(BaseModel):
    knowledge: List[KnowledgeResponse]
    total: int
    page: int
    page_size: int

def _to_resp(db: Session, k: Knowledge) -> KnowledgeResponse:
    proj_name = None
    if k.project_id:
        p = db.query(Project).filter(Project.id == k.project_id).first()
        if p: proj_name = p.name
    return KnowledgeResponse(
        id=k.id, name=k.name, use_when=k.use_when, content=k.content, enabled=k.enabled,
        project_id=k.project_id, project_name=proj_name, owner_id=k.owner_id, source=k.source,
        confidence=k.confidence, importance=k.importance, tags=k.tags,
        created_at=k.created_at, updated_at=k.updated_at
    )

@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    project_id: Optional[int] = None,
    enabled: Optional[bool] = None,
    sort_by: str = Query("updated_at", pattern="^(name|created_at|updated_at|importance|confidence)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Knowledge).filter(Knowledge.owner_id == current_user.id)
    if search:
        q = q.filter(or_(Knowledge.name.ilike(f"%{search}%"), Knowledge.content.ilike(f"%{search}%"), Knowledge.use_when.ilike(f"%{search}%")))
    if project_id is not None:
        q = q.filter(Knowledge.project_id == project_id)
    if enabled is not None:
        q = q.filter(Knowledge.enabled == enabled)
    col = getattr(Knowledge, sort_by)
    q = q.order_by(desc(col) if sort_order=="desc" else col)
    total = q.count()
    items = q.offset((page-1)*page_size).limit(page_size).all()
    return KnowledgeListResponse(knowledge=[_to_resp(db, x) for x in items], total=total, page=page, page_size=page_size)

@router.post("", response_model=KnowledgeResponse, status_code=201)
async def create_knowledge(
    data: KnowledgeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.project_id:
        p = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
        if not p: raise HTTPException(status_code=404, detail="Project not found")
    # never store sensitive info unnecessarily - basic filter
    if data.content and any(s in data.content.lower() for s in ["api_key", "password", "secret"]):
        # allow but log warning; in real would scrub
        pass
    k = Knowledge(
        name=data.name, use_when=data.use_when, content=data.content, enabled=data.enabled,
        project_id=data.project_id, owner_id=current_user.id, source=data.source,
        confidence=data.confidence, importance=data.importance, tags=data.tags
    )
    db.add(k); db.commit(); db.refresh(k)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="knowledge", resource_id=str(k.id), success=True)
    return _to_resp(db, k)

@router.get("/{kid}", response_model=KnowledgeResponse)
async def get_knowledge(kid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    k = db.query(Knowledge).filter(Knowledge.id == kid, Knowledge.owner_id == current_user.id).first()
    if not k: raise HTTPException(status_code=404, detail="Knowledge not found")
    return _to_resp(db, k)

@router.patch("/{kid}", response_model=KnowledgeResponse)
async def update_knowledge(kid: int, data: KnowledgeUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    k = db.query(Knowledge).filter(Knowledge.id == kid, Knowledge.owner_id == current_user.id).first()
    if not k: raise HTTPException(status_code=404, detail="Knowledge not found")
    if data.project_id is not None:
        if data.project_id:
            p = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
            if not p: raise HTTPException(status_code=404, detail="Project not found")
        k.project_id = data.project_id
    for f in ["name","use_when","content","enabled","source","confidence","importance","tags"]:
        v = getattr(data, f)
        if v is not None: setattr(k, f, v)
    db.commit(); db.refresh(k)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="knowledge", resource_id=str(k.id), success=True)
    return _to_resp(db, k)

@router.delete("/{kid}")
async def delete_knowledge(kid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    k = db.query(Knowledge).filter(Knowledge.id == kid, Knowledge.owner_id == current_user.id).first()
    if not k: raise HTTPException(status_code=404, detail="Knowledge not found")
    db.delete(k); db.commit()
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="knowledge", resource_id=str(k.id), success=True)
    return {"message":"Knowledge deleted"}

@router.post("/{kid}/toggle", response_model=KnowledgeResponse)
async def toggle_knowledge(kid: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    k = db.query(Knowledge).filter(Knowledge.id == kid, Knowledge.owner_id == current_user.id).first()
    if not k: raise HTTPException(status_code=404, detail="Knowledge not found")
    k.enabled = not k.enabled
    db.commit(); db.refresh(k)
    return _to_resp(db, k)
