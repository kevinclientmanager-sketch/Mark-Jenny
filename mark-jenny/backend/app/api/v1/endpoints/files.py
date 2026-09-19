from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import hashlib
import uuid
from pathlib import Path

from app.db.base import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.file import File, FileType, Folder
from app.models.project import Project
from app.models.task import Task
from app.utils.audit import log_audit

router = APIRouter()
settings = get_settings()

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    project_id: Optional[int] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class FolderResponse(BaseModel):
    id: int
    name: str
    path: Optional[str]
    parent_id: Optional[int]
    project_id: Optional[int]
    owner_id: int
    children: List['FolderResponse'] = []
    file_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: int
    name: str
    original_name: str
    path: str
    storage_key: Optional[str]
    mime_type: Optional[str]
    file_type: str
    size: int
    hash: Optional[str]
    owner_id: int
    project_id: Optional[int]
    task_id: Optional[int]
    folder_id: Optional[int]
    is_public: bool
    file_metadata: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    page_size: int


def get_file_type(mime_type: Optional[str]) -> FileType:
    if not mime_type:
        return FileType.OTHER
    if mime_type.startswith("image/"):
        return FileType.IMAGE
    elif mime_type.startswith("video/"):
        return FileType.VIDEO
    elif mime_type.startswith("audio/"):
        return FileType.AUDIO
    elif mime_type in ["application/pdf", "application/msword", 
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       "text/plain", "text/markdown"]:
        return FileType.DOCUMENT
    elif mime_type in ["application/vnd.ms-excel",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       "text/csv"]:
        return FileType.SPREADSHEET
    elif mime_type in ["application/zip", "application/x-rar-compressed",
                       "application/x-tar", "application/gzip"]:
        return FileType.ARCHIVE
    elif mime_type.startswith("text/") or "json" in mime_type or "xml" in mime_type:
        return FileType.CODE
    return FileType.OTHER


def compute_file_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


@router.get("/folders", response_model=List[FolderResponse])
async def list_folders(
    project_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Folder).filter(Folder.owner_id == current_user.id)
    
    if project_id:
        query = query.filter(Folder.project_id == project_id)
    else:
        query = query.filter(Folder.project_id.is_(None))
    
    if parent_id:
        query = query.filter(Folder.parent_id == parent_id)
    else:
        query = query.filter(Folder.parent_id.is_(None))
    
    folders = query.all()
    
    result = []
    for f in folders:
        file_count = db.query(func.count(File.id)).filter(File.folder_id == f.id).scalar() or 0
        result.append(FolderResponse(
            id=f.id,
            name=f.name,
            path=f.path,
            parent_id=f.parent_id,
            project_id=f.project_id,
            owner_id=f.owner_id,
            children=[],
            file_count=file_count,
            created_at=f.created_at,
            updated_at=f.updated_at
        ))
    return result


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if folder_data.project_id:
        project = db.query(Project).filter(
            Project.id == folder_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    if folder_data.parent_id:
        parent = db.query(Folder).filter(
            Folder.id == folder_data.parent_id,
            Folder.owner_id == current_user.id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")
    
    folder = Folder(
        name=folder_data.name,
        parent_id=folder_data.parent_id,
        project_id=folder_data.project_id,
        owner_id=current_user.id
    )
    if folder.parent_id:
        parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
        folder.path = f"{parent.path}/{folder.name}" if parent.path else folder.name
    else:
        folder.path = folder.name
    
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
    return FolderResponse.from_orm(folder)


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.owner_id == current_user.id
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if folder_data.name is not None:
        folder.name = folder_data.name
        if folder.parent_id:
            parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
            folder.path = f"{parent.path}/{folder.name}" if parent.path else folder.name
        else:
            folder.path = folder.name
    
    if folder_data.parent_id is not None:
        if folder_data.parent_id == folder_id:
            raise HTTPException(status_code=400, detail="Cannot set parent to self")
        if folder_data.parent_id:
            parent = db.query(Folder).filter(
                Folder.id == folder_data.parent_id,
                Folder.owner_id == current_user.id
            ).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")
        folder.parent_id = folder_data.parent_id
    
    db.commit()
    db.refresh(folder)
    return FolderResponse.from_orm(folder)


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.owner_id == current_user.id
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    db.delete(folder)
    db.commit()
    return {"message": "Folder deleted"}


@router.get("", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    file_type: Optional[FileType] = None,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    sort_by: str = Query("created_at", pattern="^(name|size|created_at|file_type)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(File).filter(
        File.owner_id == current_user.id,
        File.deleted_at.is_(None)
    )
    
    if search:
        query = query.filter(File.name.ilike(f"%{search}%") | File.original_name.ilike(f"%{search}%"))
    
    if file_type:
        query = query.filter(File.file_type == file_type)
    
    if project_id:
        query = query.filter(File.project_id == project_id)
    
    if task_id:
        query = query.filter(File.task_id == task_id)
    
    if folder_id:
        query = query.filter(File.folder_id == folder_id)
    else:
        query = query.filter(File.folder_id.is_(None))
    
    if sort_order == "desc":
        query = query.order_by(desc(getattr(File, sort_by)))
    else:
        query = query.order_by(getattr(File, sort_by))
    
    total = query.count()
    files = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return FileListResponse(
        files=[FileResponse.from_orm(f) for f in files],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    project_id: Optional[int] = Form(None),
    task_id: Optional[int] = Form(None),
    folder_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if project_id:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    if task_id:
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.owner_id == current_user.id
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
    
    if folder_id:
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.owner_id == current_user.id
        ).first()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
    
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    file_hash = hashlib.sha256(content).hexdigest()
    
    existing = db.query(File).filter(
        File.hash == file_hash,
        File.owner_id == current_user.id
    ).first()
    if existing:
        return FileResponse.from_orm(existing)
    
    ext = Path(file.filename).suffix
    storage_name = f"{uuid.uuid4()}{ext}"
    storage_path = UPLOAD_DIR / storage_name
    
    with open(storage_path, "wb") as f:
        f.write(content)
    
    file_type = get_file_type(file.content_type)
    
    db_file = File(
        name=storage_name,
        original_name=file.filename,
        path=str(storage_path),
        storage_key=storage_name,
        mime_type=file.content_type,
        file_type=file_type,
        size=len(content),
        hash=file_hash,
        owner_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        folder_id=folder_id,
        is_public=False
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    await log_audit(db, user_id=current_user.id, action="FILE_UPLOAD",
                   resource_type="file", resource_id=str(db_file.id), success=True)
    
    return FileResponse.from_orm(db_file)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == current_user.id,
        File.deleted_at.is_(None)
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse.from_orm(file)


@router.patch("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: int,
    name: Optional[str] = Form(None),
    folder_id: Optional[int] = Form(None),
    project_id: Optional[int] = Form(None),
    is_public: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == current_user.id,
        File.deleted_at.is_(None)
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if name is not None:
        file.name = name
    if folder_id is not None:
        if folder_id:
            folder = db.query(Folder).filter(
                Folder.id == folder_id,
                Folder.owner_id == current_user.id
            ).first()
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
        file.folder_id = folder_id
    if project_id is not None:
        if project_id:
            project = db.query(Project).filter(
                Project.id == project_id,
                Project.owner_id == current_user.id
            ).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        file.project_id = project_id
    if is_public is not None:
        file.is_public = is_public
    
    db.commit()
    db.refresh(file)
    return FileResponse.from_orm(file)


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file.deleted_at = datetime.utcnow()
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="FILE_DELETE",
                   resource_type="file", resource_id=str(file.id), success=True)
    
    return {"message": "File deleted"}


@router.post("/{file_id}/restore")
async def restore_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file.deleted_at = None
    db.commit()
    return {"message": "File restored"}


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import FileResponse
    file = db.query(File).filter(
        File.id == file_id,
        File.owner_id == current_user.id,
        File.deleted_at.is_(None)
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file.path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    await log_audit(db, user_id=current_user.id, action="FILE_DOWNLOAD",
                   resource_type="file", resource_id=str(file.id), success=True)
    
    return FileResponse(
        path=file.path,
        filename=file.original_name,
        media_type=file.mime_type
    )


@router.get("/types/categories")
async def get_file_categories(current_user: User = Depends(get_current_user)):
    return [
        {"value": "All", "label": "All"},
        {"value": "Websites", "label": "Websites"},
        {"value": "Documents", "label": "Documents"},
        {"value": "Images", "label": "Images"},
        {"value": "Videos", "label": "Videos"},
        {"value": "Audios", "label": "Audios"},
        {"value": "Spreadsheets", "label": "Spreadsheets"},
        {"value": "Others", "label": "Others"}
    ]