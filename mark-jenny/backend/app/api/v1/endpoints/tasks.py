from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority, TaskRun, Subtask
from app.models.project import Project
from app.utils.audit import log_audit
from app.api.v1.endpoints.websocket import notify_task_update

router = APIRouter()


def _task_response(task: Task, db: Session) -> "TaskResponse":
    project_name = None
    if task.project_id:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project:
            project_name = project.name
    subtasks = db.query(Subtask).filter(Subtask.task_id == task.id).order_by(Subtask.order).all()
    runs = db.query(TaskRun).filter(TaskRun.task_id == task.id).order_by(TaskRun.run_number.desc()).all()
    return TaskResponse(
        id=task.id, title=task.title, description=task.description,
        original_request=task.original_request, status=task.status.value,
        priority=task.priority.value, autonomy_level=task.autonomy_level,
        owner_id=task.owner_id, project_id=task.project_id, project_name=project_name,
        parent_task_id=task.parent_task_id, plan=task.plan,
        current_step=task.current_step or 0, total_steps=task.total_steps or 0,
        model_used=task.model_used, agent_type=task.agent_type, result=task.result,
        error=task.error,
        subtasks=[SubtaskResponse.model_validate(s) for s in subtasks],
        runs=[TaskRunResponse.model_validate(r) for r in runs],
        started_at=task.started_at, completed_at=task.completed_at,
        created_at=task.created_at, updated_at=task.updated_at,
    )


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    original_request: Optional[str] = None
    project_id: Optional[int] = None
    priority: TaskPriority = TaskPriority.NORMAL
    autonomy_level: int = 1


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    autonomy_level: Optional[int] = None
    status: Optional[TaskStatus] = None


class SubtaskResponse(BaseModel):
    id: int
    task_id: int
    title: str
    description: Optional[str]
    status: str
    order: int
    assigned_agent: Optional[str]
    required_skills: Optional[List[str]]
    required_tools: Optional[List[str]]
    result: Optional[dict]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskRunResponse(BaseModel):
    id: int
    task_id: int
    run_number: int
    status: str
    plan: Optional[dict]
    steps_completed: int
    tool_calls: Optional[List[dict]]
    model_usage: Optional[dict]
    files_created: Optional[List[dict]]
    errors: Optional[List[dict]]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    original_request: Optional[str]
    status: str
    priority: str
    autonomy_level: int
    owner_id: int
    project_id: Optional[int]
    project_name: Optional[str] = None
    parent_task_id: Optional[int]
    plan: Optional[dict]
    current_step: int
    total_steps: int
    model_used: Optional[str]
    agent_type: Optional[str]
    result: Optional[dict]
    error: Optional[str]
    subtasks: List[SubtaskResponse] = []
    runs: List[TaskRunResponse] = []
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskExecuteRequest(BaseModel):
    prompt: str
    project_id: Optional[int] = None
    agent_type: Optional[str] = None
    model_preference: Optional[str] = None
    autonomy_level: int = 1
    skip_confirmations: bool = False
    think: bool = False
    model: Optional[str] = None


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = None,
    project_id: Optional[int] = None,
    sort_by: str = Query("created_at", pattern="^(title|status|priority|created_at|updated_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.owner_id == current_user.id)
    
    if search:
        query = query.filter(
            Task.title.ilike(f"%{search}%") | 
            Task.description.ilike(f"%{search}%") |
            Task.original_request.ilike(f"%{search}%")
        )
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if priority:
        query = query.filter(Task.priority == priority)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    if sort_order == "desc":
        query = query.order_by(desc(getattr(Task, sort_by)))
    else:
        query = query.order_by(getattr(Task, sort_by))
    
    total = query.count()
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for t in tasks:
        project_name = None
        if t.project_id:
            project = db.query(Project).filter(Project.id == t.project_id).first()
            if project:
                project_name = project.name
        
        subtasks = db.query(Subtask).filter(Subtask.task_id == t.id).order_by(Subtask.order).all()
        runs = db.query(TaskRun).filter(TaskRun.task_id == t.id).order_by(TaskRun.run_number.desc()).all()
        
        result.append(TaskResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            original_request=t.original_request,
            status=t.status.value,
            priority=t.priority.value,
            autonomy_level=t.autonomy_level,
            owner_id=t.owner_id,
            project_id=t.project_id,
            project_name=project_name,
            parent_task_id=t.parent_task_id,
            plan=t.plan,
            current_step=t.current_step,
            total_steps=t.total_steps,
            model_used=t.model_used,
            agent_type=t.agent_type,
            result=t.result,
            error=t.error,
            subtasks=[SubtaskResponse.from_orm(s) for s in subtasks],
            runs=[TaskRunResponse.from_orm(r) for r in runs],
            started_at=t.started_at,
            completed_at=t.completed_at,
            created_at=t.created_at,
            updated_at=t.updated_at
        ))
    
    return TaskListResponse(tasks=result, total=total, page=page, page_size=page_size)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if task_data.project_id:
        project = db.query(Project).filter(
            Project.id == task_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    task = Task(
        title=task_data.title,
        description=task_data.description,
        original_request=task_data.original_request or task_data.title,
        project_id=task_data.project_id,
        priority=task_data.priority,
        autonomy_level=task_data.autonomy_level,
        owner_id=current_user.id,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_CREATE",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    return _task_response(task, db)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return _task_response(task, db)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.autonomy_level is not None:
        task.autonomy_level = task_data.autonomy_level
    if task_data.status is not None:
        task.status = task_data.status
        if task_data.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_UPDATE",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    await notify_task_update(db, task, "updated")
    
    return _task_response(task, db)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="TASK_DELETE",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    return {"message": "Task deleted"}


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: int,
    execute_data: TaskExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute the task for real.

    Previously this only set status=PLANNING and returned "queued" while no
    worker ever picked it up. It now runs the plan step by step and returns
    the actual outcome.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [TaskStatus.RUNNING, TaskStatus.PLANNING]:
        raise HTTPException(status_code=400, detail="Task is already running")

    task.original_request = execute_data.prompt or task.original_request
    if execute_data.project_id:
        task.project_id = execute_data.project_id
    if execute_data.autonomy_level:
        task.autonomy_level = execute_data.autonomy_level
    db.commit()

    await log_audit(db, user_id=current_user.id, action="TASK_START",
                   resource_type="task", resource_id=str(task.id), success=True)
    await notify_task_update(db, task, "started")

    from app.services.task_runner import run_task
    outcome = await run_task(
        db, task, current_user,
        prompt=execute_data.prompt,
        think=bool(getattr(execute_data, "think", False)),
        model=getattr(execute_data, "model", None),
    )

    await log_audit(db, user_id=current_user.id, action="TASK_COMPLETE",
                   resource_type="task", resource_id=str(task.id),
                   success=outcome["status"] == "COMPLETED")
    return outcome


@router.post("/{task_id}/pause")
async def pause_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.RUNNING, TaskStatus.PLANNING]:
        raise HTTPException(status_code=400, detail="Task is not running")
    
    task.status = TaskStatus.PAUSED
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_PAUSE",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    await notify_task_update(db, task, "paused")
    
    return {"message": "Task paused"}


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Task is not paused")
    
    task.status = TaskStatus.PENDING
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_RESUME",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    await notify_task_update(db, task, "resumed")
    
    return {"message": "Task resumed"}


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Task already finished")
    
    task.status = TaskStatus.CANCELLED
    task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_CANCEL",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    await notify_task_update(db, task, "cancelled")
    
    return {"message": "Task cancelled"}


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Task can only be retried if failed or cancelled")
    
    task.status = TaskStatus.PENDING
    task.error = None
    task.current_step = 0
    db.commit()
    db.refresh(task)
    
    await log_audit(db, user_id=current_user.id, action="TASK_RETRY",
                   resource_type="task", resource_id=str(task.id), success=True)
    
    await notify_task_update(db, task, "retry_queued")
    
    return {"message": "Task queued for retry"}


@router.get("/{task_id}/runs", response_model=List[TaskRunResponse])
async def list_task_runs(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    runs = db.query(TaskRun).filter(TaskRun.task_id == task_id).order_by(TaskRun.run_number.desc()).all()
    return [TaskRunResponse.from_orm(r) for r in runs]


@router.get("/{task_id}/runs/{run_id}", response_model=TaskRunResponse)
async def get_task_run(
    task_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    run = db.query(TaskRun).filter(
        TaskRun.id == run_id,
        TaskRun.task_id == task_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Task run not found")
    
    return TaskRunResponse.from_orm(run)