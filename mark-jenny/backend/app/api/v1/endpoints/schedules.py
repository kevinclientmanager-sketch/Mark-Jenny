from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, time

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.schedule import Schedule, ScheduleFrequency, ScheduleRunOption, ScheduleRun
from app.models.task import Task
from app.models.project import Project
from app.models.agent import Agent
from app.utils.audit import log_audit

router = APIRouter()


class ScheduleCreate(BaseModel):
    title: str
    prompt: str
    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    cron_expression: Optional[str] = None
    time_of_day: str
    timezone: str = "UTC"
    run_option: ScheduleRunOption = ScheduleRunOption.SAME_TASK
    skip_confirmations: bool = False
    project_id: Optional[int] = None
    agent_id: Optional[int] = None
    connectors: Optional[List[int]] = []
    config: Optional[dict] = None
    end_date: Optional[datetime] = None
    max_runs: Optional[int] = None
    computer: Optional[str] = None


class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    frequency: Optional[ScheduleFrequency] = None
    cron_expression: Optional[str] = None
    time_of_day: Optional[str] = None
    timezone: Optional[str] = None
    run_option: Optional[ScheduleRunOption] = None
    skip_confirmations: Optional[bool] = None
    project_id: Optional[int] = None
    agent_id: Optional[int] = None
    connectors: Optional[List[int]] = None
    config: Optional[dict] = None
    end_date: Optional[datetime] = None
    max_runs: Optional[int] = None
    is_active: Optional[bool] = None
    computer: Optional[str] = None


class ScheduleRunResponse(BaseModel):
    id: int
    schedule_id: int
    task_id: Optional[int]
    status: str
    error: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    class Config:
        from_attributes = True


class ScheduleResponse(BaseModel):
    id: int
    title: str
    prompt: str
    frequency: str
    cron_expression: Optional[str]
    time_of_day: str
    timezone: str
    run_option: str
    skip_confirmations: bool
    project_id: Optional[int]
    project_name: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str]
    connectors: Optional[List[int]]
    config: Optional[dict]
    computer: Optional[str] = None
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    end_date: Optional[datetime]
    run_count: int
    max_runs: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    schedules: List[ScheduleResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    project_id: Optional[int] = None,
    sort_by: str = Query("created_at", pattern="^(title|next_run_at|created_at|frequency)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Schedule).filter(Schedule.owner_id == current_user.id)
    
    if search:
        query = query.filter(Schedule.title.ilike(f"%{search}%") | Schedule.prompt.ilike(f"%{search}%"))
    
    if is_active is not None:
        query = query.filter(Schedule.is_active == is_active)
    
    if project_id:
        query = query.filter(Schedule.project_id == project_id)
    
    if sort_order == "desc":
        query = query.order_by(desc(getattr(Schedule, sort_by)))
    else:
        query = query.order_by(getattr(Schedule, sort_by))
    
    total = query.count()
    schedules = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for s in schedules:
        project_name = None
        if s.project_id:
            project = db.query(Project).filter(Project.id == s.project_id).first()
            if project:
                project_name = project.name
        
        agent_name = None
        if s.agent_id:
            agent = db.query(Agent).filter(Agent.id == s.agent_id).first()
            if agent:
                agent_name = agent.name
        
        computer = (s.config or {}).get("computer") if s.config else None
        result.append(ScheduleResponse(
            id=s.id,
            title=s.title,
            prompt=s.prompt,
            frequency=s.frequency.value,
            cron_expression=s.cron_expression,
            time_of_day=s.time_of_day,
            timezone=s.timezone,
            run_option=s.run_option.value,
            skip_confirmations=s.skip_confirmations,
            project_id=s.project_id,
            project_name=project_name,
            agent_id=s.agent_id,
            agent_name=agent_name,
            connectors=s.connectors,
            config=s.config,
            computer=computer,
            is_active=s.is_active,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            end_date=s.end_date,
            run_count=s.run_count,
            max_runs=s.max_runs,
            created_at=s.created_at,
            updated_at=s.updated_at
        ))
    
    return ScheduleListResponse(schedules=result, total=total, page=page, page_size=page_size)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if schedule_data.project_id:
        project = db.query(Project).filter(
            Project.id == schedule_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    if schedule_data.agent_id:
        agent = db.query(Agent).filter(Agent.id == schedule_data.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
    
    config = dict(schedule_data.config or {})
    if schedule_data.computer:
        config["computer"] = schedule_data.computer
    schedule = Schedule(
        title=schedule_data.title,
        prompt=schedule_data.prompt,
        frequency=schedule_data.frequency,
        cron_expression=schedule_data.cron_expression,
        time_of_day=schedule_data.time_of_day,
        timezone=schedule_data.timezone,
        run_option=schedule_data.run_option,
        skip_confirmations=schedule_data.skip_confirmations,
        project_id=schedule_data.project_id,
        agent_id=schedule_data.agent_id,
        connectors=schedule_data.connectors,
        config=config if config else None,
        end_date=schedule_data.end_date,
        max_runs=schedule_data.max_runs,
        owner_id=current_user.id,
        is_active=True,
        run_count=0
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    await log_audit(db, user_id=current_user.id, action="SCHEDULE_CREATE",
                   resource_type="schedule", resource_id=str(schedule.id), success=True)
    
    project_name = None
    if schedule.project_id:
        project = db.query(Project).filter(Project.id == schedule.project_id).first()
        if project:
            project_name = project.name
    computer = (schedule.config or {}).get("computer") if schedule.config else None
    
    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        prompt=schedule.prompt,
        frequency=schedule.frequency.value,
        cron_expression=schedule.cron_expression,
        time_of_day=schedule.time_of_day,
        timezone=schedule.timezone,
        run_option=schedule.run_option.value,
        skip_confirmations=schedule.skip_confirmations,
        project_id=schedule.project_id,
        project_name=project_name,
        agent_id=schedule.agent_id,
        agent_name=None,
        connectors=schedule.connectors,
        config=schedule.config,
        computer=computer,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        end_date=schedule.end_date,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    project_name = None
    if schedule.project_id:
        project = db.query(Project).filter(Project.id == schedule.project_id).first()
        if project:
            project_name = project.name
    
    agent_name = None
    if schedule.agent_id:
        agent = db.query(Agent).filter(Agent.id == schedule.agent_id).first()
        if agent:
            agent_name = agent.name
    computer = (schedule.config or {}).get("computer") if schedule.config else None
    
    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        prompt=schedule.prompt,
        frequency=schedule.frequency.value,
        cron_expression=schedule.cron_expression,
        time_of_day=schedule.time_of_day,
        timezone=schedule.timezone,
        run_option=schedule.run_option.value,
        skip_confirmations=schedule.skip_confirmations,
        project_id=schedule.project_id,
        project_name=project_name,
        agent_id=schedule.agent_id,
        agent_name=agent_name,
        connectors=schedule.connectors,
        config=schedule.config,
        computer=computer,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        end_date=schedule.end_date,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule_data.title is not None:
        schedule.title = schedule_data.title
    if schedule_data.prompt is not None:
        schedule.prompt = schedule_data.prompt
    if schedule_data.frequency is not None:
        schedule.frequency = schedule_data.frequency
    if schedule_data.cron_expression is not None:
        schedule.cron_expression = schedule_data.cron_expression
    if schedule_data.time_of_day is not None:
        schedule.time_of_day = schedule_data.time_of_day
    if schedule_data.timezone is not None:
        schedule.timezone = schedule_data.timezone
    if schedule_data.run_option is not None:
        schedule.run_option = schedule_data.run_option
    if schedule_data.skip_confirmations is not None:
        schedule.skip_confirmations = schedule_data.skip_confirmations
    if schedule_data.project_id is not None:
        if schedule_data.project_id:
            project = db.query(Project).filter(
                Project.id == schedule_data.project_id,
                Project.owner_id == current_user.id
            ).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        schedule.project_id = schedule_data.project_id
    if schedule_data.agent_id is not None:
        if schedule_data.agent_id:
            agent = db.query(Agent).filter(Agent.id == schedule_data.agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
        schedule.agent_id = schedule_data.agent_id
    if schedule_data.connectors is not None:
        schedule.connectors = schedule_data.connectors
    if schedule_data.config is not None:
        schedule.config = schedule_data.config
    if schedule_data.computer is not None:
        cfg = dict(schedule.config or {})
        if schedule_data.computer:
            cfg["computer"] = schedule_data.computer
        else:
            cfg.pop("computer", None)
        schedule.config = cfg if cfg else None
    if schedule_data.end_date is not None:
        schedule.end_date = schedule_data.end_date
    if schedule_data.max_runs is not None:
        schedule.max_runs = schedule_data.max_runs
    if schedule_data.is_active is not None:
        schedule.is_active = schedule_data.is_active
    
    db.commit()
    db.refresh(schedule)
    
    await log_audit(db, user_id=current_user.id, action="SCHEDULE_UPDATE",
                   resource_type="schedule", resource_id=str(schedule.id), success=True)
    
    project_name = None
    if schedule.project_id:
        project = db.query(Project).filter(Project.id == schedule.project_id).first()
        if project:
            project_name = project.name
    
    agent_name = None
    if schedule.agent_id:
        agent = db.query(Agent).filter(Agent.id == schedule.agent_id).first()
        if agent:
            agent_name = agent.name
    computer = (schedule.config or {}).get("computer") if schedule.config else None
    
    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        prompt=schedule.prompt,
        frequency=schedule.frequency.value,
        cron_expression=schedule.cron_expression,
        time_of_day=schedule.time_of_day,
        timezone=schedule.timezone,
        run_option=schedule.run_option.value,
        skip_confirmations=schedule.skip_confirmations,
        project_id=schedule.project_id,
        project_name=project_name,
        agent_id=schedule.agent_id,
        agent_name=agent_name,
        connectors=schedule.connectors,
        config=schedule.config,
        computer=computer,
        is_active=schedule.is_active,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        end_date=schedule.end_date,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at
    )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="SCHEDULE_DELETE",
                   resource_type="schedule", resource_id=str(schedule.id), success=True)
    
    return {"message": "Schedule deleted"}


@router.post("/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.is_active = False
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="SCHEDULE_PAUSE",
                   resource_type="schedule", resource_id=str(schedule.id), success=True)
    
    return {"message": "Schedule paused"}


@router.post("/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.is_active = True
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="SCHEDULE_RESUME",
                   resource_type="schedule", resource_id=str(schedule.id), success=True)
    
    return {"message": "Schedule resumed"}


@router.post("/{schedule_id}/duplicate", response_model=ScheduleResponse)
async def duplicate_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    new_schedule = Schedule(
        title=f"{schedule.title} (Copy)",
        prompt=schedule.prompt,
        frequency=schedule.frequency,
        cron_expression=schedule.cron_expression,
        time_of_day=schedule.time_of_day,
        timezone=schedule.timezone,
        run_option=schedule.run_option,
        skip_confirmations=schedule.skip_confirmations,
        project_id=schedule.project_id,
        agent_id=schedule.agent_id,
        connectors=schedule.connectors,
        config=schedule.config,
        end_date=schedule.end_date,
        max_runs=schedule.max_runs,
        owner_id=current_user.id,
        is_active=False,
        run_count=0
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    computer = (new_schedule.config or {}).get("computer") if new_schedule.config else None
    project_name = None
    if new_schedule.project_id:
        proj = db.query(Project).filter(Project.id == new_schedule.project_id).first()
        if proj:
            project_name = proj.name
    return ScheduleResponse(
        id=new_schedule.id,
        title=new_schedule.title,
        prompt=new_schedule.prompt,
        frequency=new_schedule.frequency.value,
        cron_expression=new_schedule.cron_expression,
        time_of_day=new_schedule.time_of_day,
        timezone=new_schedule.timezone,
        run_option=new_schedule.run_option.value,
        skip_confirmations=new_schedule.skip_confirmations,
        project_id=new_schedule.project_id,
        project_name=project_name,
        agent_id=new_schedule.agent_id,
        agent_name=None,
        connectors=new_schedule.connectors,
        config=new_schedule.config,
        computer=computer,
        is_active=new_schedule.is_active,
        last_run_at=new_schedule.last_run_at,
        next_run_at=new_schedule.next_run_at,
        end_date=new_schedule.end_date,
        run_count=new_schedule.run_count,
        max_runs=new_schedule.max_runs,
        created_at=new_schedule.created_at,
        updated_at=new_schedule.updated_at
    )


@router.get("/{schedule_id}/runs", response_model=List[ScheduleRunResponse])
async def list_schedule_runs(
    schedule_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.owner_id == current_user.id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    runs = db.query(ScheduleRun).filter(
        ScheduleRun.schedule_id == schedule_id
    ).order_by(desc(ScheduleRun.started_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return [ScheduleRunResponse.from_orm(r) for r in runs]


@router.get("/upcoming/next")
async def get_upcoming_schedules(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    schedules = db.query(Schedule).filter(
        Schedule.owner_id == current_user.id,
        Schedule.is_active == True,
        Schedule.next_run_at.isnot(None)
    ).order_by(Schedule.next_run_at).limit(limit).all()
    
    result = []
    for s in schedules:
        project_name = None
        if s.project_id:
            project = db.query(Project).filter(Project.id == s.project_id).first()
            if project:
                project_name = project.name
        
        agent_name = None
        if s.agent_id:
            agent = db.query(Agent).filter(Agent.id == s.agent_id).first()
            if agent:
                agent_name = agent.name
        
        result.append({
            "id": s.id,
            "title": s.title,
            "next_execution": s.next_run_at.isoformat() if s.next_run_at else None,
            "frequency": s.frequency.value,
            "status": "ACTIVE" if s.is_active else "PAUSED",
            "project": project_name,
            "agent": agent_name,
            "connectors": s.connectors or []
        })
    
    return result