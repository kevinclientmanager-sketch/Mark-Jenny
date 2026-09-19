from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.services.generative_engine import generative_engine
from app.utils.audit import log_audit

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str
    project_id: Optional[int] = None
    model: Optional[str] = None  # for Model Router selection

class GenerateResponse(BaseModel):
    task_id: int
    type: str
    files: List[dict]
    message: str
    preview_url: Optional[str] = None

def _create_task(db: Session, user: User, prompt: str, project_id: Optional[int], type: str) -> Task:
    t = Task(title=f"[{type}] {prompt[:50]}", description=prompt, original_request=prompt, status=TaskStatus.COMPLETED, priority=TaskPriority.NORMAL, owner_id=user.id, project_id=project_id, agent_type=type)
    t.completed_at = t.created_at
    db.add(t); db.commit(); db.refresh(t)
    return t

async def _generate(db: Session, user: User, req: GenerateRequest, method: str) -> GenerateResponse:
    if not req.prompt or len(req.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail="Prompt required")
    task = _create_task(db, user, req.prompt, req.project_id, method)
    func = getattr(generative_engine, f"generate_{method}")
    result = func(req.prompt, user.id, req.project_id, task.id)
    # Update task result
    task.result = result
    db.commit()
    await log_audit(db, user_id=user.id, action="TASK_CREATE", resource_type="task", resource_id=str(task.id), success=True)
    return GenerateResponse(task_id=task.id, type=result["type"], files=result["files"], message=result["message"], preview_url=result.get("preview_url"))

@router.post("/website", response_model=GenerateResponse)
async def generate_website(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "website")

@router.post("/app", response_model=GenerateResponse)
async def generate_app(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "app")

@router.post("/slides", response_model=GenerateResponse)
async def generate_slides(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "slides")

@router.post("/image", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "image")

@router.post("/image-edit", response_model=GenerateResponse)
async def edit_image(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "edit_image")

@router.post("/research", response_model=GenerateResponse)
async def generate_research(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "research")

@router.post("/spreadsheet", response_model=GenerateResponse)
async def generate_spreadsheet(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "spreadsheet")

@router.post("/video", response_model=GenerateResponse)
async def generate_video(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "video")

@router.post("/audio", response_model=GenerateResponse)
async def generate_audio(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "audio")

@router.post("/document", response_model=GenerateResponse)
async def generate_document(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "document")

@router.post("/code", response_model=GenerateResponse)
async def generate_code(req: GenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await _generate(db, current_user, req, "code")

@router.get("/types")
async def list_types(current_user: User = Depends(get_current_user)):
    return [
        {"id":"website","label":"Website","desc":"HTML site + preview","icon":"Globe"},
        {"id":"app","label":"Application","desc":"Next.js app code","icon":"Code2"},
        {"id":"slides","label":"Slides","desc":"PPTX or MD deck","icon":"Presentation"},
        {"id":"image","label":"Image","desc":"PIL placeholder or model","icon":"Image"},
        {"id":"image-edit","label":"Edit Image","desc":"Inpaint/transform","icon":"Wand2"},
        {"id":"research","label":"Research","desc":"Report with citations","icon":"Search"},
        {"id":"spreadsheet","label":"Spreadsheet","desc":"XLSX with formulas","icon":"Table"},
        {"id":"video","label":"Video","desc":"Script (needs video model)","icon":"Video"},
        {"id":"audio","label":"Audio","desc":"TTS script (needs TTS)","icon":"Music"},
        {"id":"document","label":"Document","desc":"Markdown report","icon":"FileText"},
        {"id":"code","label":"Code","desc":"Python/JS boilerplate","icon":"Code"},
    ]
