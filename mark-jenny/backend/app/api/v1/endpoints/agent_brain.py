from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import agent_brain

router = APIRouter()


class ThinkRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    project_id: Optional[int] = None
    task_type: str = "fast"


class RunRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    project_id: Optional[int] = None
    max_iterations: int = Field(5, ge=1, le=8)


@router.post("/think")
async def think(
    data: ThinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transparent reasoning trace: intent, recall, skills, model, plan, tools."""
    return await agent_brain.think(db, current_user, data.goal, data.project_id, data.task_type)


@router.post("/run")
async def run(
    data: RunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a goal with the bounded ReAct loop (act -> observe -> reflect)."""
    return await agent_brain.run_react(db, current_user, data.goal, data.project_id, data.max_iterations)


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proactive briefing: failure patterns, memory health, next actions."""
    return agent_brain.insights(db, current_user)
