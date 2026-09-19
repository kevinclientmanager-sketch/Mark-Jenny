from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.code_execution_engine import code_execution_engine, SUPPORTED_LANGUAGES
from app.utils.audit import log_audit

router = APIRouter()

class ExecuteRequest(BaseModel):
    language: str
    code: str
    timeout: Optional[int] = None
    project_id: Optional[int] = None

class ExecuteResponse(BaseModel):
    success: bool
    language: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: Optional[int] = None
    duration: Optional[float] = None
    sandbox: Optional[str] = None
    files: Optional[List[dict]] = None
    error: Optional[str] = None
    timeout: Optional[bool] = None

@router.get("/capabilities")
async def get_capabilities(current_user: User = Depends(get_current_user)):
    return code_execution_engine.list_languages()

@router.get("/languages")
async def list_languages(current_user: User = Depends(get_current_user)):
    return {"supported": SUPPORTED_LANGUAGES, "details": code_execution_engine.list_languages()}

@router.post("/run", response_model=ExecuteResponse)
async def run_code(
    data: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not data.code or not data.code.strip():
        raise HTTPException(status_code=400, detail="Code required")
    if len(data.code) > 100000:
        raise HTTPException(status_code=400, detail="Code too large (max 100KB)")
    # Basic guard: never execute arbitrary code with unrestricted privileges - we sandbox via temp dir + timeout + limited env
    result = code_execution_engine.execute(data.language, data.code, timeout=data.timeout)
    # Audit - never log full code if contains secrets (basic filter)
    preview = data.code[:200] + ("..." if len(data.code)>200 else "")
    await log_audit(db, user_id=current_user.id, action="TASK_CREATE", resource_type="execution", resource_id=f"{data.language}:{len(data.code)}", success=result.get("success", False))
    # Map to response
    return ExecuteResponse(
        success=result.get("success", False),
        language=result.get("language", data.language),
        stdout=result.get("stdout"),
        stderr=result.get("stderr"),
        returncode=result.get("returncode"),
        duration=result.get("duration"),
        sandbox=result.get("sandbox"),
        files=result.get("files"),
        error=result.get("error"),
        timeout=result.get("timeout")
    )

@router.post("/python", response_model=ExecuteResponse)
async def run_python(data: ExecuteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data.language = "python"
    return await run_code(data, current_user, db)

@router.post("/javascript", response_model=ExecuteResponse)
async def run_javascript(data: ExecuteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data.language = "javascript"
    return await run_code(data, current_user, db)

@router.post("/powershell", response_model=ExecuteResponse)
async def run_powershell(data: ExecuteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data.language = "powershell"
    return await run_code(data, current_user, db)

@router.get("/sandbox/{sandbox_id}/files")
async def list_sandbox_files(sandbox_id: str, current_user: User = Depends(get_current_user)):
    from pathlib import Path
    from app.core.config import get_settings
    import os
    settings = get_settings()
    root = Path(settings.UPLOAD_DIR) / "exec_sandbox"
    # prevent path traversal
    if ".." in sandbox_id or "/" in sandbox_id or "\\" in sandbox_id:
        raise HTTPException(status_code=400, detail="Invalid sandbox id")
    # find sandbox dirs starting with prefix
    matches = list(root.glob(f"*{sandbox_id}*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Sandbox not found or cleaned")
    sandbox = matches[0]
    files = []
    for p in sandbox.iterdir():
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size, "path": str(p)})
    return {"sandbox": str(sandbox), "files": files}
