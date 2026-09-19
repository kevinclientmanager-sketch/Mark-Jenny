from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.computer_engine import computer_engine

router = APIRouter()

class WriteFileRequest(BaseModel):
    path: str
    content: str
    require_confirm: bool = True

class ClipboardWriteRequest(BaseModel):
    text: str

@router.get("/info")
async def get_info(current_user: User = Depends(get_current_user)):
    return computer_engine.get_system_info()

@router.get("/files")
async def list_files(path: str = ".", current_user: User = Depends(get_current_user)):
    result = computer_engine.list_files(path, current_user.id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/files/read")
async def read_file(path: str, current_user: User = Depends(get_current_user)):
    result = computer_engine.read_file(path)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/files/write")
async def write_file(data: WriteFileRequest, current_user: User = Depends(get_current_user)):
    result = computer_engine.write_file(data.path, data.content, data.require_confirm)
    if result.get("requires_confirmation"):
        raise HTTPException(status_code=403, detail=result.get("error"))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/processes")
async def list_processes(limit: int = 50, current_user: User = Depends(get_current_user)):
    result = computer_engine.list_processes(limit)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/processes/{pid}/kill")
async def kill_process(pid: int, confirm: bool = False, current_user: User = Depends(get_current_user)):
    result = computer_engine.kill_process(pid, require_confirm=not confirm)
    if result.get("requires_confirmation"):
        raise HTTPException(status_code=403, detail=result.get("error"))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/clipboard")
async def clipboard_read(current_user: User = Depends(get_current_user)):
    result = computer_engine.clipboard_read()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/clipboard")
async def clipboard_write(data: ClipboardWriteRequest, current_user: User = Depends(get_current_user)):
    result = computer_engine.clipboard_write(data.text)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/windows")
async def list_windows(current_user: User = Depends(get_current_user)):
    result = computer_engine.list_windows()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/permissions")
async def get_permissions(current_user: User = Depends(get_current_user)):
    return {
        "permissions": computer_engine.permissions,
        "note": "Dangerous ops require explicit enable + confirmation unless Autonomy L4. Configure via Settings -> Computer."
    }

@router.post("/permissions")
async def set_permission(action: str, allowed: bool, current_user: User = Depends(get_current_user)):
    if action not in computer_engine.permissions:
        raise HTTPException(status_code=400, detail="Unknown permission")
    computer_engine.permissions[action] = allowed
    return {"message": f"Permission {action} set to {allowed}", "permissions": computer_engine.permissions}
