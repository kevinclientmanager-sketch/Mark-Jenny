from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, ProjectSkill
from app.models.task import Task, TaskStatus
from app.models.file import File
from app.models.skill import Skill
from app.utils.audit import log_audit

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    instructions: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    instructions: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectSkillAdd(BaseModel):
    skill_id: int
    enabled: bool = True
    config: Optional[dict] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    avatar_url: Optional[str]
    instructions: Optional[str]
    status: str
    owner_id: int
    task_count: int
    file_count: int
    skill_count: int
    last_modified: Optional[datetime]
    running_status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int


def compute_project_stats(db: Session, project_id: int) -> dict:
    task_count = db.query(func.count(Task.id)).filter(Task.project_id == project_id).scalar() or 0
    file_count = db.query(func.count(File.id)).filter(File.project_id == project_id).scalar() or 0
    skill_count = db.query(func.count(ProjectSkill.id)).filter(ProjectSkill.project_id == project_id).scalar() or 0
    
    running_task = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status.in_([TaskStatus.RUNNING, TaskStatus.PLANNING, TaskStatus.WAITING_APPROVAL])
    ).first()
    
    last_modified = db.query(func.max(File.updated_at)).filter(File.project_id == project_id).scalar()
    last_task_update = db.query(func.max(Task.updated_at)).filter(Task.project_id == project_id).scalar()
    if last_task_update and (not last_modified or last_task_update > last_modified):
        last_modified = last_task_update
    
    return {
        "task_count": task_count,
        "file_count": file_count,
        "skill_count": skill_count,
        "running_status": running_task.status.value if running_task else None,
        "last_modified": last_modified
    }


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
    sort_by: str = Query("updated_at", pattern="^(name|created_at|updated_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Project).filter(Project.owner_id == current_user.id)
    
    if search:
        query = query.filter(
            Project.name.ilike(f"%{search}%") | 
            Project.description.ilike(f"%{search}%")
        )
    
    if status:
        query = query.filter(Project.status == status)
    
    if sort_order == "desc":
        query = query.order_by(desc(getattr(Project, sort_by)))
    else:
        query = query.order_by(getattr(Project, sort_by))
    
    total = query.count()
    projects = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for p in projects:
        stats = compute_project_stats(db, p.id)
        result.append(ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            icon=p.icon,
            avatar_url=p.avatar_url,
            instructions=p.instructions,
            status=p.status.value,
            owner_id=p.owner_id,
            task_count=stats["task_count"],
            file_count=stats["file_count"],
            skill_count=stats["skill_count"],
            last_modified=stats["last_modified"],
            running_status=stats["running_status"],
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    return ProjectListResponse(
        projects=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = Project(
        name=project_data.name,
        description=project_data.description,
        icon=project_data.icon,
        instructions=project_data.instructions,
        owner_id=current_user.id,
        status=ProjectStatus.ACTIVE
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    await log_audit(db, user_id=current_user.id, action="PROJECT_CREATE", 
                   resource_type="project", resource_id=str(project.id), success=True)
    
    stats = compute_project_stats(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        icon=project.icon,
        avatar_url=project.avatar_url,
        instructions=project.instructions,
        status=project.status.value,
        owner_id=project.owner_id,
        task_count=stats["task_count"],
        file_count=stats["file_count"],
        skill_count=stats["skill_count"],
        last_modified=stats["last_modified"],
        running_status=stats["running_status"],
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    stats = compute_project_stats(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        icon=project.icon,
        avatar_url=project.avatar_url,
        instructions=project.instructions,
        status=project.status.value,
        owner_id=project.owner_id,
        task_count=stats["task_count"],
        file_count=stats["file_count"],
        skill_count=stats["skill_count"],
        last_modified=stats["last_modified"],
        running_status=stats["running_status"],
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.icon is not None:
        project.icon = project_data.icon
    if project_data.instructions is not None:
        project.instructions = project_data.instructions
    if project_data.status is not None:
        project.status = project_data.status
    
    db.commit()
    db.refresh(project)
    
    await log_audit(db, user_id=current_user.id, action="PROJECT_UPDATE",
                   resource_type="project", resource_id=str(project.id), success=True)
    
    stats = compute_project_stats(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        icon=project.icon,
        avatar_url=project.avatar_url,
        instructions=project.instructions,
        status=project.status.value,
        owner_id=project.owner_id,
        task_count=stats["task_count"],
        file_count=stats["file_count"],
        skill_count=stats["skill_count"],
        last_modified=stats["last_modified"],
        running_status=stats["running_status"],
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.status = ProjectStatus.DELETED
    project.deleted_at = datetime.utcnow()
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="PROJECT_DELETE",
                   resource_type="project", resource_id=str(project.id), success=True)
    
    return {"message": "Project deleted"}


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_project = Project(
        name=f"{project.name} (Copy)",
        description=project.description,
        icon=project.icon,
        instructions=project.instructions,
        owner_id=current_user.id,
        status=ProjectStatus.ACTIVE
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    project_skills = db.query(ProjectSkill).filter(ProjectSkill.project_id == project_id).all()
    for ps in project_skills:
        new_ps = ProjectSkill(
            project_id=new_project.id,
            skill_id=ps.skill_id,
            enabled=ps.enabled,
            config=ps.config
        )
        db.add(new_ps)
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="PROJECT_DUPLICATE",
                   resource_type="project", resource_id=str(new_project.id), success=True)
    
    stats = compute_project_stats(db, new_project.id)
    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        description=new_project.description,
        icon=new_project.icon,
        avatar_url=new_project.avatar_url,
        instructions=new_project.instructions,
        status=new_project.status.value,
        owner_id=new_project.owner_id,
        task_count=stats["task_count"],
        file_count=stats["file_count"],
        skill_count=stats["skill_count"],
        last_modified=stats["last_modified"],
        running_status=stats["running_status"],
        created_at=new_project.created_at,
        updated_at=new_project.updated_at
    )


@router.get("/{project_id}/skills")
async def list_project_skills(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_skills = db.query(ProjectSkill).filter(ProjectSkill.project_id == project_id).all()
    result = []
    for ps in project_skills:
        skill = db.query(Skill).filter(Skill.id == ps.skill_id).first()
        if skill:
            result.append({
                "id": skill.id,
                "name": skill.name,
                "display_name": skill.display_name,
                "description": skill.description,
                "version": skill.version,
                "source": skill.source.value,
                "status": ps.enabled and skill.status.value == "ENABLED" and "enabled" or "disabled",
                "enabled": ps.enabled,
                "config": ps.config,
                "last_updated": skill.updated_at
            })
    return result


@router.post("/{project_id}/skills")
async def add_project_skill(
    project_id: int,
    skill_data: ProjectSkillAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    existing = db.query(ProjectSkill).filter(
        ProjectSkill.project_id == project_id,
        ProjectSkill.skill_id == skill_data.skill_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Skill already added to project")
    
    project_skill = ProjectSkill(
        project_id=project_id,
        skill_id=skill_data.skill_id,
        enabled=skill_data.enabled,
        config=skill_data.config
    )
    db.add(project_skill)
    db.commit()
    
    return {"message": "Skill added to project"}


@router.patch("/{project_id}/skills/{skill_id}")
async def update_project_skill(
    project_id: int,
    skill_id: int,
    enabled: bool,
    config: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_skill = db.query(ProjectSkill).filter(
        ProjectSkill.project_id == project_id,
        ProjectSkill.skill_id == skill_id
    ).first()
    if not project_skill:
        raise HTTPException(status_code=404, detail="Skill not found in project")
    
    project_skill.enabled = enabled
    if config is not None:
        project_skill.config = config
    db.commit()
    
    return {"message": "Project skill updated"}


@router.delete("/{project_id}/skills/{skill_id}")
async def remove_project_skill(
    project_id: int,
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_skill = db.query(ProjectSkill).filter(
        ProjectSkill.project_id == project_id,
        ProjectSkill.skill_id == skill_id
    ).first()
    if not project_skill:
        raise HTTPException(status_code=404, detail="Skill not found in project")
    
    db.delete(project_skill)
    db.commit()
    
    return {"message": "Skill removed from project"}