from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import Chat, Message, MessageRole
from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.file import File
from app.utils.audit import log_audit
from app.api.v1.endpoints.websocket import notify_task_update

router = APIRouter()

class ChatCreate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None

class ChatUpdate(BaseModel):
    title: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    project_id: Optional[int] = None
    attachments: Optional[List[int]] = None  # file ids
    connectors: Optional[List[int]] = None

class MessageUpdate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    role: str
    content: Optional[str]
    tool_calls: Optional[List[dict]] = None
    message_metadata: Optional[dict] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    id: int
    title: Optional[str]
    owner_id: int
    project_id: Optional[int]
    project_name: Optional[str]
    task_id: Optional[int]
    model_used: Optional[str]
    message_count: int
    last_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True

class ChatDetailResponse(ChatResponse):
    messages: List[MessageResponse] = []

class ChatListResponse(BaseModel):
    chats: List[ChatResponse]
    total: int
    page: int
    page_size: int

def _chat_to_response(db: Session, chat: Chat) -> ChatResponse:
    project_name = None
    if chat.project_id:
        proj = db.query(Project).filter(Project.id == chat.project_id).first()
        if proj:
            project_name = proj.name
    msg_count = db.query(Message).filter(Message.chat_id == chat.id).count()
    last = db.query(Message).filter(Message.chat_id == chat.id).order_by(desc(Message.created_at)).first()
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        owner_id=chat.owner_id,
        project_id=chat.project_id,
        project_name=project_name,
        task_id=chat.task_id,
        model_used=chat.model_used,
        message_count=msg_count,
        last_message=last.content[:80] if last and last.content else None,
        created_at=chat.created_at,
        updated_at=chat.updated_at
    )

@router.get("", response_model=ChatListResponse)
async def list_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Chat).filter(Chat.owner_id == current_user.id)
    if project_id:
        q = q.filter(Chat.project_id == project_id)
    if search:
        q = q.filter(Chat.title.ilike(f"%{search}%"))
    q = q.order_by(desc(Chat.updated_at))
    total = q.count()
    chats = q.offset((page-1)*page_size).limit(page_size).all()
    return ChatListResponse(chats=[_chat_to_response(db, c) for c in chats], total=total, page=page, page_size=page_size)

@router.post("", response_model=ChatDetailResponse)
async def create_chat(
    data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.project_id:
        proj = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
    chat = Chat(title=data.title or "New Chat", owner_id=current_user.id, project_id=data.project_id)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    await log_audit(db, user_id=current_user.id, action="CHAT_CREATE", resource_type="chat", resource_id=str(chat.id), success=True)
    return ChatDetailResponse(**_chat_to_response(db, chat).model_dump(), messages=[])

@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    return ChatDetailResponse(**_chat_to_response(db, chat).model_dump(), messages=[MessageResponse.model_validate(m) for m in msgs])

@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    data: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if data.title is not None:
        chat.title = data.title
    db.commit()
    db.refresh(chat)
    return _chat_to_response(db, chat)

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    await log_audit(db, user_id=current_user.id, action="CHAT_DELETE", resource_type="chat", resource_id=str(chat_id), success=True)
    return {"message": "Chat deleted"}

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    return [MessageResponse.model_validate(m) for m in msgs]

def _get_owned_message(db: Session, chat_id: int, message_id: int, current_user: User) -> Message:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    msg = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg

@router.patch("/{chat_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    chat_id: int,
    message_id: int,
    data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = _get_owned_message(db, chat_id, message_id, current_user)
    if msg.role != MessageRole.USER:
        raise HTTPException(status_code=400, detail="Only user messages can be edited")
    msg.content = data.content
    db.commit()
    db.refresh(msg)
    await log_audit(db, user_id=current_user.id, action="MESSAGE_EDIT", resource_type="message", resource_id=str(msg.id), success=True)
    return MessageResponse.model_validate(msg)

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = _get_owned_message(db, chat_id, message_id, current_user)
    db.delete(msg)
    db.commit()
    await log_audit(db, user_id=current_user.id, action="MESSAGE_DELETE", resource_type="message", resource_id=str(message_id), success=True)
    return {"message": "Message deleted"}

async def _run_autonomous_pipeline(db: Session, chat: Chat, user_msg: Message, current_user: User):
    """Intelligent pipeline: uses Agent Brain (intent + memory + skills) to generate real AI responses."""
    from app.services.agent_brain import AgentBrain

    content = (user_msg.content or "").strip()
    if len(content) < 3:
        return

    brain = AgentBrain(db)

    # Get context from brain (intent, memory, skills)
    brain_result = brain.think(content, user_id=current_user.id, project_id=chat.project_id)
    intent = brain_result["intent"]
    recalled = brain_result["recalled"]
    skill_matches = brain_result["skills"]

    # Get chat history for context
    chat_history = []
    try:
        from app.models.chat import Message as ChatMessage
        prev_msgs = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat.id
        ).order_by(ChatMessage.id.desc()).limit(6).all()
        chat_history = [{"role": m.role.value if hasattr(m.role, 'value') else str(m.role), "content": (m.content or "")[:300]} for m in reversed(prev_msgs)]
    except Exception:
        pass

    # Generate REAL AI response using the LLM
    reply = await brain.chat(
        user_message=content,
        user_id=current_user.id,
        project_id=chat.project_id,
        chat_history=chat_history,
    )
    if not reply or not reply.strip():
        reply = _generate_simple_reply(content, intent, recalled, skill_matches)
        provider_status = "unavailable_fallback"
    else:
        provider_status = "model_response"

    # Build metadata
    meta = {
        "intent": intent["intent"],
        "confidence": intent["confidence"],
        "complexity": intent["complexity"],
        "skills_matched": skill_matches.get("matched", []),
        "skill_gaps": skill_matches.get("gaps", []),
        "memory_recalled": [{"type": r["type"], "content": r["content"][:100], "score": round(r["score"], 2)} for r in recalled[:5]],
        "model_used": brain._call_llm.__module__ if hasattr(brain, '_call_llm') else "ollama",
        "provider_status": provider_status,
        "retryable": provider_status != "model_response",
    }

    # For task-like requests with high complexity — also create a tracked Task
    if intent["complexity"] in ("complex", "moderate") and intent["confidence"] >= 0.6:
        try:
            from app.services.agent_brain import plan_heuristic
            plan = plan_heuristic(content, intent, skill_matches.get("assigned", []))
            title = content[:80].replace("\n", " ")
            task = Task(
                title=title,
                description=content,
                original_request=content,
                status=TaskStatus.PLANNING,
                priority=TaskPriority.NORMAL,
                autonomy_level=2,
                owner_id=current_user.id,
                project_id=chat.project_id,
                plan={
                    "intent": intent["intent"],
                    "goal": content,
                    "strategy": plan.get("strategy", "sequential"),
                    "subtasks": [{"title": s["title"], "status": "PENDING", "tools": s.get("tools", []), "skills": s.get("skills", [])} for s in plan.get("subtasks", [])],
                    "missing_capabilities": skill_matches.get("gaps", []),
                },
                current_step=0,
                total_steps=len(plan.get("subtasks", [])),
            )
            db.add(task)
            db.flush()
            chat.task_id = task.id
            meta["task_id"] = task.id
        except Exception:
            pass

    db.add(Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content=reply, message_metadata=meta))
    db.commit()


def _generate_simple_reply(content: str, intent: dict, recalled: list, skills: dict) -> str:
    """Generate a reply for simple questions using memory and skills context."""
    parts = []
    intent_label = intent.get("intent", "general")

    if recalled:
        memory_snippets = [r["content"][:120] for r in recalled[:3]]
        parts.append(f"Based on what I know:\n" + "\n".join(f"- {m}" for m in memory_snippets))

    matched = skills.get("matched", [])
    if matched:
        parts.append(f"I can use these skills: {', '.join(matched[:5])}")

    if not parts:
        parts.append(f"I understand you're asking about **{intent_label}**. I'm ready to help — ask me to build something, research a topic, or create a task.")

    return "\n\n".join(parts)


def _generate_task_reply(content: str, intent: dict, plan: dict, skills_used: list, gaps: list, recalled: list, task) -> str:
    """Generate a reply for task creation with full brain reasoning."""
    lines = [f"**Task created:** `{task.title}` (ID {task.id})"]

    # Intent and strategy
    strategy = plan.get("strategy", "sequential")
    lines.append(f"\n**Intent:** {intent['intent']} ({intent['confidence']:.0%} confidence, {intent['complexity']} complexity)")
    lines.append(f"**Strategy:** {strategy}")

    # Skills
    if skills_used:
        lines.append(f"\n**Skills selected:** {', '.join(skills_used[:8])}")
    if gaps:
        lines.append(f"**Skill gaps:** {', '.join(gaps)} — install from Skills to unlock.")

    # Plan subtasks
    subtasks = plan.get("subtasks", [])
    if subtasks:
        lines.append(f"\n**Plan** ({len(subtasks)} steps):")
        for i, s in enumerate(subtasks, 1):
            tools = s.get("tools", [])
            skill_list = s.get("skills", [])
            tool_str = f" [{', '.join(tools[:3])}]" if tools else ""
            skill_str = f" (skills: {', '.join(skill_list[:3])})" if skill_list else ""
            lines.append(f"  {i}. {s['title']}{tool_str}{skill_str}")

    # Memory context
    if recalled:
        lines.append(f"\n**Recalled from memory:** {len(recalled)} relevant items")
        for r in recalled[:2]:
            lines.append(f"  - {r['content'][:100]}")

    lines.append(f"\nTracking in Project `{task.project_id or 'General'}`. I'll update via WebSocket as steps complete.")
    return "\n".join(lines)

@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.owner_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not data.content or not data.content.strip():
        raise HTTPException(status_code=400, detail="Message content is required")
    if len(data.content) > 100000:
        raise HTTPException(status_code=400, detail="Message is too large (max 100KB)")

    # Attach project if provided
    if data.project_id:
        proj = db.query(Project).filter(Project.id == data.project_id, Project.owner_id == current_user.id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        chat.project_id = data.project_id

    # Handle file attachments metadata
    meta = {}
    if data.attachments:
        files = db.query(File).filter(File.id.in_(data.attachments), File.owner_id == current_user.id).all()
        meta["attachments"] = [{"id": f.id, "name": f.original_name, "type": f.file_type} for f in files]
    if data.connectors:
        meta["connectors"] = data.connectors

    user_msg = Message(chat_id=chat.id, role=MessageRole.USER, content=data.content, message_metadata=meta if meta else None)
    db.add(user_msg)
    # Update chat title from first message if still default
    if chat.title == "New Chat" and data.content:
        chat.title = data.content[:40]
    db.commit()
    db.refresh(user_msg)

    # Run autonomous pipeline (creates assistant reply + task if needed).
    # Keep the conversation usable even when an optional model/tool provider is offline.
    try:
        await _run_autonomous_pipeline(db, chat, user_msg, current_user)
    except Exception as exc:
        # Never leave a user message without an assistant turn. The provider error is
        # intentionally not exposed; the UI receives a recoverable status instead.
        db.rollback()
        fallback = (
            "I received your request, but the configured AI provider is temporarily "
            "unavailable. Your message is saved. Start or reconnect a model provider "
            "in Settings, then send it again."
        )
        db.add(Message(
            chat_id=chat.id,
            role=MessageRole.ASSISTANT,
            content=fallback,
            message_metadata={"status": "provider_unavailable", "retryable": True},
        ))
        db.commit()

    # Return the user message; frontend will refetch full thread
    return MessageResponse.model_validate(user_msg)
