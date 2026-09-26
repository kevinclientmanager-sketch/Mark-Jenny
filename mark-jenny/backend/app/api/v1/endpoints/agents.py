from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.agent import Agent

router = APIRouter()

class AgentResponse(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str]
    available_skills: Optional[list]
    is_active: bool
    created_at: str
    class Config:
        from_attributes = True

class AgentListResponse(BaseModel):
    agents: list
    total: int

@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Agent).filter(Agent.is_active == True)
    total = q.count()
    agents = q.offset((page - 1) * page_size).limit(page_size).all()
    model_names = {}
    try:
        from app.models.agent import Model
        for m in db.query(Model).all():
            model_names[m.id] = m.display_name or m.name
    except Exception:
        pass
    return AgentListResponse(
        agents=[
            {
                "id": a.id,
                "name": a.name,
                "type": a.type.value if hasattr(a.type, "value") else str(a.type),
                "description": a.description,
                "available_skills": a.available_skills or [],
                "available_tools": a.available_tools or [],
                "model_used": model_names.get(a.model_id),
                # Aliases so clients that expect agent_type/status (the Agents
                # page) and clients that expect type/is_active both work.
                "agent_type": a.type.value if hasattr(a.type, "value") else str(a.type),
                "status": "active" if a.is_active else "inactive",
                "is_active": a.is_active,
                "created_at": str(a.created_at) if a.created_at else "",
            }
            for a in agents
        ],
        total=total,
    )

@router.get("/{agent_id}")
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"detail": "Agent not found"}
    return {
        "id": agent.id,
        "name": agent.name,
        "type": agent.type.value if hasattr(agent.type, "value") else str(agent.type),
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "available_skills": agent.available_skills or [],
        "is_active": agent.is_active,
    }
