"""Mark-Imti Work Agent API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.work_agent import WorkAgent, WorkTaskType

router = APIRouter(tags=["work-agent"])

_work_agent = None


def get_work_agent():
    global _work_agent
    if _work_agent is None:
        from app.core.model_caller import ModelCaller
        _work_agent = WorkAgent(model_caller=ModelCaller())
    return _work_agent


class CreateTaskRequest(BaseModel):
    task_type: str
    description: str
    params: dict = {}
    requires_approval: bool = True


class FileActionRequest(BaseModel):
    action: str
    params: dict = {}


class EmailRequest(BaseModel):
    to: str = ""
    subject: str = ""
    context: str = ""
    tone: str = "professional"


@router.get("/tasks")
async def list_tasks():
    agent = get_work_agent()
    pending = agent.get_pending_tasks()
    active = agent.get_active_tasks()
    completed = agent.get_completed_tasks()
    return {
        "status": "ok",
        "pending": [{"id": t.id, "type": t.task_type.value, "description": t.description,
                      "status": t.status.value, "created_at": t.created_at} for t in pending],
        "active": [{"id": t.id, "type": t.task_type.value, "description": t.description,
                     "status": t.status.value, "started_at": t.started_at} for t in active],
        "completed": [{"id": t.id, "type": t.task_type.value, "description": t.description,
                        "status": t.status.value, "completed_at": t.completed_at} for t in completed[:20]],
    }


@router.post("/tasks")
async def create_task(req: CreateTaskRequest):
    agent = get_work_agent()
    try:
        task_type = WorkTaskType(req.task_type)
    except ValueError:
        raise HTTPException(400, f"Invalid task type: {req.task_type}")
    task = agent.create_task(task_type, req.description, req.params, req.requires_approval)
    return {
        "status": "ok",
        "task": {"id": task.id, "type": task.task_type.value, "description": task.description,
                  "status": task.status.value, "requires_approval": task.requires_approval},
    }


@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str):
    agent = get_work_agent()
    if agent.approve_task(task_id):
        return {"status": "ok", "message": "Task approved and started"}
    raise HTTPException(404, "Task not found")


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, result: dict = {}):
    agent = get_work_agent()
    if agent.complete_task(task_id, result):
        return {"status": "ok", "message": "Task completed"}
    raise HTTPException(404, "Task not found")


@router.post("/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "Unknown error"):
    agent = get_work_agent()
    if agent.fail_task(task_id, error):
        return {"status": "ok", "message": "Task marked as failed"}
    raise HTTPException(404, "Task not found")


@router.post("/files")
async def file_action(req: FileActionRequest):
    agent = get_work_agent()
    result = await agent.execute_file_task(req.action, req.params)
    return {"status": "ok", "result": result}


@router.post("/email/draft")
async def draft_email(req: EmailRequest):
    agent = get_work_agent()
    result = await agent.draft_email({
        "to": req.to, "subject": req.subject,
        "context": req.context, "tone": req.tone,
    })
    return {"status": "ok", "result": result}


@router.get("/email/read")
async def read_email():
    agent = get_work_agent()
    result = await agent.read_email({})
    return {"status": "ok", "result": result}


@router.get("/patterns")
async def get_patterns():
    agent = get_work_agent()
    return {"status": "ok", "patterns": agent.get_learned_patterns()}


@router.post("/patterns/learn")
async def learn_pattern(trigger: str, action: str):
    agent = get_work_agent()
    agent.learn_pattern(trigger, action)
    return {"status": "ok", "message": "Pattern learned"}


@router.get("/predict")
async def predict_needs():
    agent = get_work_agent()
    predictions = agent.predict_needs()
    return {"status": "ok", "predictions": predictions}


@router.get("/records")
async def get_records(limit: int = 50):
    agent = get_work_agent()
    return {"status": "ok", "records": agent.get_records(limit)}


@router.get("/stats")
async def get_stats():
    agent = get_work_agent()
    return {"status": "ok", "stats": agent.get_stats()}
