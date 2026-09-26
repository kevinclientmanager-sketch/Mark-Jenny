from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.project import Project
from app.utils.audit import log_audit
from app.api.v1.endpoints.websocket import notify_task_update

router = APIRouter()

class QuickActionId(str, Enum):
    connect_computer = "connect-computer"
    build_website = "build-website"
    develop_apps = "develop-apps"
    create_slides = "create-slides"
    create_image = "create-image"
    edit_image = "edit-image"
    wide_research = "wide-research"
    scheduled_tasks = "scheduled-tasks"
    create_spreadsheet = "create-spreadsheet"
    create_video = "create-video"
    generate_audio = "generate-audio"
    playbook = "playbook"

ACTION_DEFS: Dict[str, Dict] = {
    "connect-computer": {"label":"Connect My Computer", "desc":"Pair device with permission (Tray consent)", "icon":"Laptop", "category":"system", "route":"/projects/{project}/connectors"},
    "build-website": {"label":"Build website", "desc":"Generate deployable site (Next.js)", "icon":"Code2", "category":"generative", "phase":12},
    "develop-apps": {"label":"Develop apps", "desc":"Generate full app with repo", "icon":"Code2", "category":"generative", "phase":12},
    "create-slides": {"label":"Create slides", "desc":"Deck from outline", "icon":"Presentation", "category":"generative", "phase":12},
    "create-image": {"label":"Create image", "desc":"Text-to-image via model router", "icon":"Wand2", "category":"generative", "phase":12},
    "edit-image": {"label":"Edit image", "desc":"Inpaint/transform uploaded image", "icon":"Wand2", "category":"generative", "phase":12, "needs_file":True},
    "wide-research": {"label":"Wide Research", "desc":"Query planning→parallel search→citations→report", "icon":"Search", "category":"research", "phase":12},
    "scheduled-tasks": {"label":"Scheduled tasks", "desc":"Create recurring automation", "icon":"Calendar", "category":"automation", "route":"/scheduled"},
    "create-spreadsheet": {"label":"Create spreadsheet", "desc":"Excel/CSV with formulas", "icon":"Table", "category":"generative", "phase":12},
    "create-video": {"label":"Create video", "desc":"Script → storyboard → video", "icon":"Video", "category":"generative", "phase":12},
    "generate-audio": {"label":"Generate audio", "desc":"TTS / music via model", "icon":"Music", "category":"generative", "phase":12},
    "playbook": {"label":"Playbook", "desc":"Save workflow as reusable blueprint", "icon":"BookOpen", "category":"system", "phase":14},
}

class QuickActionResponse(BaseModel):
    id: str
    label: str
    desc: str
    icon: str
    category: str
    route: Optional[str] = None
    needs_file: bool = False
    class Config:
        from_attributes = True

class QuickActionExecute(BaseModel):
    prompt: str
    project_id: Optional[int] = None
    file_ids: Optional[List[int]] = None
    connectors: Optional[List[int]] = None

@router.get("", response_model=List[QuickActionResponse])
async def list_quick_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return [QuickActionResponse(id=k, **v) for k,v in ACTION_DEFS.items()]

@router.get("/{action_id}", response_model=QuickActionResponse)
async def get_quick_action(
    action_id: QuickActionId,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if action_id.value not in ACTION_DEFS:
        raise HTTPException(status_code=404, detail="Action not found")
    return QuickActionResponse(id=action_id.value, **ACTION_DEFS[action_id.value])

@router.post("/{action_id}/execute")
async def execute_quick_action(
    action_id: QuickActionId,
    data: QuickActionExecute,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if action_id.value not in ACTION_DEFS:
        raise HTTPException(status_code=404, detail="Action not found")
    if not data.prompt or len(data.prompt.strip()) < 2:
        raise HTTPException(status_code=400, detail="Prompt required")
    if data.project_id:
        proj = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # Route-based actions don't create tasks, they navigate
    route = ACTION_DEFS[action_id.value].get("route")
    if route and action_id.value in ["connect-computer","scheduled-tasks"]:
        return {"message": "Navigate", "route": route.replace("{project}", str(data.project_id or "")), "action_id": action_id.value}

    # Generative / input actions create a Task and then actually run it.
    meta = ACTION_DEFS[action_id.value]
    title = f"[{meta['label']}] {data.prompt[:60]}"
    task = Task(
        title=title,
        description=data.prompt,
        original_request=data.prompt,
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        autonomy_level=2,
        owner_id=current_user.id,
        project_id=data.project_id,
        current_step=0,
        agent_type=action_id.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    await notify_task_update(db, task, "quick_action_created")
    await log_audit(db, user_id=current_user.id, action="TASK_CREATE", resource_type="task", resource_id=str(task.id), success=True)

    # Run it for real instead of leaving a task parked in PLANNING forever.
    try:
        from app.services.task_runner import run_task
        outcome = await run_task(db, task, current_user, prompt=data.prompt)
    except Exception as exc:
        return {
            "message": "Quick Action started but the run failed",
            "task_id": task.id,
            "action_id": action_id.value,
            "status": TaskStatus.FAILED.value,
            "title": task.title,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "message": f"{meta['label']} finished",
        "task_id": task.id,
        "action_id": action_id.value,
        "status": outcome.get("status"),
        "title": task.title,
        "result": outcome.get("result"),
        "files_created": outcome.get("files_created", []),
        "ai_steps": outcome.get("ai_steps", 0),
        "steps": outcome.get("steps", 0),
        "total_steps": outcome.get("total_steps", 0),
    }
