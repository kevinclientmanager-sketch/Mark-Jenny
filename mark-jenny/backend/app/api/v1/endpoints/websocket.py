from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

from app.db.base import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskRun

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.task_subscriptions: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def subscribe_to_task(self, websocket: WebSocket, task_id: int):
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(websocket)

    def unsubscribe_from_task(self, websocket: WebSocket, task_id: int):
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(websocket)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)

    async def broadcast_task_update(self, task_id: int, message: dict):
        if task_id in self.task_subscriptions:
            disconnected = set()
            for connection in self.task_subscriptions[task_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.task_subscriptions[task_id].discard(conn)

    async def broadcast_user_notification(self, user_id: int, message: dict):
        await self.send_personal_message(message, user_id)


manager = ConnectionManager()


async def get_user_from_token(token: str, db: Session) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user if user and user.is_active else None


# This router is mounted with prefix="/ws", so the route is "/tasks" and the
# public path is /api/v1/ws/tasks. It used to be declared "/ws/tasks", which
# produced /api/v1/ws/ws/tasks - the browser never matched it and every task
# WebSocket handshake failed with 403.
@router.websocket("/tasks")
async def websocket_tasks(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, user.id, message, db)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception as e:
        manager.disconnect(websocket, user.id)


async def handle_websocket_message(websocket: WebSocket, user_id: int, message: dict, db: Session):
    msg_type = message.get("type")
    
    if msg_type == "subscribe_task":
        task_id = message.get("task_id")
        if task_id:
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if task:
                manager.subscribe_to_task(websocket, task_id)
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "task_id": task_id
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Task not found or access denied"
                }))
    
    elif msg_type == "unsubscribe_task":
        task_id = message.get("task_id")
        if task_id:
            manager.unsubscribe_from_task(websocket, task_id)
            await websocket.send_text(json.dumps({
                "type": "unsubscribed",
                "task_id": task_id
            }))
    
    elif msg_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
    
    else:
        await websocket.send_text(json.dumps({"type": "error", "message": f"Unknown message type: {msg_type}"}))


async def notify_task_update(db: Session, task: Task, event: str):
    message = {
        "type": "task_update",
        "event": event,
        "task": {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "current_step": task.current_step,
            "total_steps": task.total_steps,
            "error": task.error,
            "result": task.result,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_task_update(task.id, message)
    await manager.broadcast_user_notification(task.owner_id, message)


async def notify_task_run_update(db: Session, task_run: TaskRun, event: str):
    message = {
        "type": "task_run_update",
        "event": event,
        "task_run": {
            "id": task_run.id,
            "task_id": task_run.task_id,
            "run_number": task_run.run_number,
            "status": task_run.status,
            "steps_completed": task_run.steps_completed,
            "duration_seconds": task_run.duration_seconds,
            "completed_at": task_run.completed_at.isoformat() if task_run.completed_at else None,
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_task_update(task_run.task_id, message)
    task = db.query(Task).filter(Task.id == task_run.task_id).first()
    if task:
        await manager.broadcast_user_notification(task.owner_id, message)