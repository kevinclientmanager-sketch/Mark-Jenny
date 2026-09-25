from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.self_build_orchestrator import self_builder
from app.utils.audit import log_audit

router = APIRouter()
_session_owners: Dict[str, int] = {}


def _owned_session(session_id: str, user_id: int):
    session = self_builder.get_session(session_id)
    if not session or _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=404, detail="Build session not found")
    return session


class StartBuildRequest(BaseModel):
    user_request: str
    sandbox_mode: str = "web"
    target: str = "web"

    def normalized_mode(self) -> str:
        return "web"

    def normalized_target(self) -> str:
        return self.target if self.target in {"web", "android", "windows"} else "web"

class IntegrateRequest(BaseModel):
    session_id: str


@router.get("/access")
async def my_builder_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.v1.endpoints.admin import can_use_builder
    from app.core.master_admin import is_master_admin
    return {"allowed": can_use_builder(current_user, db), "is_master": is_master_admin(current_user)}

@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    return {"sessions": self_builder.list_sessions(), "stats": self_builder.get_stats()}

@router.post("/start")
async def start_build(data: StartBuildRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.v1.endpoints.admin import can_use_builder
    if not can_use_builder(current_user, db):
        raise HTTPException(status_code=403, detail="Self-builder access not granted. Ask a master admin to enable it for your account.")
    request = f"{data.user_request}\nBuild target: {data.normalized_target()}\nSandbox mode: {data.normalized_mode()}"
    session_id = await self_builder.start_build(request)
    _session_owners[session_id] = current_user.id
    await log_audit(db, user_id=current_user.id, action="SELF_BUILD_START", resource_type="build", resource_id=session_id, success=True)
    return {"session_id": session_id, "message": "Build started"}

@router.get("/{session_id}")
async def get_session(session_id: str, current_user: User = Depends(get_current_user)):
    return _owned_session(session_id, current_user.id)

@router.get("/{session_id}/logs")
async def get_logs(session_id: str, current_user: User = Depends(get_current_user)):
    _owned_session(session_id, current_user.id)
    return {"logs": self_builder.get_build_logs(session_id)}

@router.get("/{session_id}/files")
async def get_files(session_id: str, current_user: User = Depends(get_current_user)):
    _owned_session(session_id, current_user.id)
    return {"files": self_builder.get_sandbox_files(session_id)}

@router.post("/{session_id}/integrate")
async def integrate(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.v1.endpoints.admin import can_use_builder
    if not can_use_builder(current_user, db):
        raise HTTPException(status_code=403, detail="Self-builder access not granted. Ask a master admin to enable it for your account.")
    _owned_session(session_id, current_user.id)
    result = await self_builder.integrate_to_live(session_id)
    await log_audit(db, user_id=current_user.id, action="SELF_BUILD_INTEGRATE", resource_type="build", resource_id=session_id, success=result["success"])
    return result

@router.post("/{session_id}/rollback")
async def rollback(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_session(session_id, current_user.id)
    result = await self_builder.rollback(session_id)
    await log_audit(db, user_id=current_user.id, action="SELF_BUILD_ROLLBACK", resource_type="build", resource_id=session_id, success=result["success"])
    return result


# WebSocket for live build progress
@router.websocket("/ws/{session_id}")
async def build_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    events = []
    queue = asyncio.Queue()

    async def callback(event, data):
        await queue.put({"event": event, "data": data})

    self_builder.on_event(callback)

    # Send initial state
    session = self_builder.get_session(session_id)
    if session:
        await websocket.send_json({"event": "initial", "data": session})

    # Stream events
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"event": "heartbeat", "data": {}})
    except WebSocketDisconnect:
        pass
