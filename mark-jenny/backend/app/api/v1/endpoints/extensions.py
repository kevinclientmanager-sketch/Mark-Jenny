from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.extension_manager import extension_manager, EXTENSION_TYPES
from app.utils.audit import log_audit

router = APIRouter()


class InstallURLRequest(BaseModel):
    url: str
    type: str = "skill"

class InstallGitHubRequest(BaseModel):
    repo: str
    path: str = ""

class InstallSkillRequest(BaseModel):
    name: str
    content: str
    version: str = "1.0.0"
    files: Optional[Dict[str, str]] = None

class InstallModelRequest(BaseModel):
    model_id: str
    model_name: str = ""


@router.get("")
async def list_extensions(current_user: User = Depends(get_current_user)):
    return {
        "extensions": extension_manager.list_installed(),
        "stats": extension_manager.get_stats(),
    }

@router.get("/types")
async def list_extension_types():
    return {"types": EXTENSION_TYPES}

@router.get("/{ext_id}")
async def get_extension(ext_id: str, current_user: User = Depends(get_current_user)):
    ext = extension_manager.get_extension(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found")
    return {"id": ext_id, **ext}

@router.post("/install-url")
async def install_extension_url(data: InstallURLRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await extension_manager.install_from_url(data.url, data.type)
    await log_audit(db, user_id=current_user.id, action="EXTENSION_INSTALL", resource_type="extension", resource_id=data.url, success=result["success"])
    return result

@router.post("/install-github")
async def install_extension_github(data: InstallGitHubRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await extension_manager.install_from_github(data.repo, data.path)
    await log_audit(db, user_id=current_user.id, action="EXTENSION_INSTALL_GITHUB", resource_type="extension", resource_id=data.repo, success=result["success"])
    return result

@router.post("/install-skill")
async def install_extension_skill(data: InstallSkillRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await extension_manager.install_skill({
        "name": data.name,
        "content": data.content,
        "version": data.version,
        "files": data.files or {},
    })
    await log_audit(db, user_id=current_user.id, action="EXTENSION_INSTALL_SKILL", resource_type="skill", resource_id=data.name, success=result["success"])
    return result

@router.post("/install-model")
async def install_extension_model(data: InstallModelRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await extension_manager.install_model(data.model_id, data.model_name)
    await log_audit(db, user_id=current_user.id, action="EXTENSION_INSTALL_MODEL", resource_type="model", resource_id=data.model_id, success=result["success"])
    return result

@router.delete("/{ext_id}")
async def uninstall_extension(ext_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await extension_manager.uninstall(ext_id)
    await log_audit(db, user_id=current_user.id, action="EXTENSION_UNINSTALL", resource_type="extension", resource_id=ext_id, success=result["success"])
    return result

@router.get("/discover/auto")
async def auto_discover_extensions(current_user: User = Depends(get_current_user)):
    suggestions = await extension_manager.auto_discover()
    return {"suggestions": suggestions}

@router.get("/updates")
async def check_extension_updates(current_user: User = Depends(get_current_user)):
    updates = await extension_manager.check_updates()
    return {"updates": updates}
