from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task
from app.models.file import File, FileType
from app.models.audit import AuditLog
from app.models.user_settings import UserSettings
from app.models.connector import Connector, ConnectorType, ConnectorStatus, ConnectorCredential
from app.models.knowledge import Knowledge, Memory
from app.models.skill import Skill
from app.utils.audit import log_audit

router = APIRouter()

# Settings are persisted per user in the user_settings table. The previous
# implementation used a module-level dict, which silently lost every toggle
# whenever the backend process restarted (i.e. on every deploy).


def _load_settings(db: Session, user_id: int) -> Dict[str, Any]:
    row = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    stored = dict(row.prefs or {}) if row and row.prefs else {}
    merged = {k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_SETTINGS.items()}
    for k, v in stored.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def _save_settings(db: Session, user_id: int, data: Dict[str, Any]) -> UserSettings:
    row = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not row:
        row = UserSettings(user_id=user_id)
        db.add(row)
    row.prefs = data
    db.commit()
    db.refresh(row)
    return row

DEFAULT_SETTINGS = {
    "appearance": {"theme": "system", "language": "en"},
    "notifications": {"email": True, "task_complete": True},
    "data_controls": {"share_tasks": True, "storage_local": True},
    "cloud_browser": {"persist_login": True, "cookies": {}},
    "mail": {"enabled": True, "approved_senders": [], "workflow_email": ""},
    "computer": {"mouse": True, "keyboard": True, "screenshots": True, "os_commands": False, "autonomy": "supervised"},
    "browser": {"enabled": True, "headless": True, "incognito": False, "max_concurrency": 3},
    "security": {"password_policy": True, "rate_limiting": True, "jwt": True, "rbac": True, "session_timeout_min": 60},
    "agents": {"multi_agent": True, "specialist_agents": True, "auto_upgrade": True, "self_evolution": False},
    "advanced": {"memory_engine": True, "task_recovery": True, "blueprints_enabled": True, "approval_mode": "auto"},
    "preferences": {
        "styleTone": "Professional",
        "fastAnswer": True,
        "customInstructions": "",
        "markCompanion": True,
        "nickname": "",
        "occupation": "",
        "moreAboutYou": "",
        "enableMemory": True,
        "memorySearch": True,
        "webSearch": True,
        "canvas": True,
        "librarySearch": True,
        "connectorSearch": True,
        "darkWeb": True,
    },
}

class SettingsUpdate(BaseModel):
    category: str  # appearance, data_controls, cloud_browser, mail, etc.
    data: Dict[str, Any]

@router.get("", response_model=Dict[str, Any])
async def get_settings(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_settings = _load_settings(db, current_user.id)
    if category:
        if category not in user_settings:
            raise HTTPException(status_code=404, detail="Category not found")
        return {category: user_settings[category]}
    return user_settings

@router.patch("", response_model=Dict[str, Any])
async def update_settings(
    data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.category not in ["appearance","language","data_controls","cloud_browser","mail","notifications","account","integrations","skills","connectors","scheduled_tasks","knowledge","clear_cache"]:
        # allow any but log
        pass
    user_settings = _load_settings(db, current_user.id)
    # deep merge for category
    if data.category not in user_settings or not isinstance(user_settings.get(data.category), dict):
        user_settings[data.category] = {}
    if isinstance(data.data, dict):
        user_settings[data.category].update(data.data)
    else:
        user_settings[data.category] = data.data
    _save_settings(db, current_user.id, user_settings)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id=data.category, success=True)
    return {data.category: user_settings[data.category]}


class AIModelSettings(BaseModel):
    default_model: Optional[str] = None
    default_provider: Optional[str] = None
    routing_strategy: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    fast_answer: Optional[bool] = None


@router.get("/ai", response_model=Dict[str, Any])
async def get_ai_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Persisted AI Studio behaviour (default model, routing, temperature, tokens)."""
    row = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not row:
        row = UserSettings(user_id=current_user.id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return {
        "default_model": row.default_model,
        "default_provider": row.default_provider,
        "routing_strategy": row.routing_strategy or "balanced",
        "temperature": 0.3 if row.temperature is None else row.temperature,
        "max_tokens": 4096 if row.max_tokens is None else row.max_tokens,
        "fast_answer": True if row.fast_answer is None else row.fast_answer,
    }


@router.patch("/ai", response_model=Dict[str, Any])
async def update_ai_settings(data: AIModelSettings, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not row:
        row = UserSettings(user_id=current_user.id)
        db.add(row)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="ai", success=True)
    return await get_ai_settings(current_user=current_user, db=db)

@router.post("/clear-cache")
async def clear_cache(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Reset this user's persisted settings to defaults.
    _save_settings(db, current_user.id, {k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_SETTINGS.items()})
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="clear_cache", success=True)
    return {"message": "Settings cache cleared"}

# Data Controls
@router.get("/data-controls/overview")
async def data_controls_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shared_tasks = db.query(Task).filter(Task.owner_id == current_user.id).count()  # stub: shared would be via share table
    archived = db.query(Project).filter(Project.owner_id == current_user.id, Project.status == "ARCHIVED").count()
    shared_files = db.query(File).filter(File.owner_id == current_user.id, File.is_public == True).count()
    # Generated websites/apps would be from Generated tables
    from app.models.generated import GeneratedWebsite, GeneratedApp
    websites = db.query(GeneratedWebsite).filter(GeneratedWebsite.owner_id == current_user.id).count()
    apps = db.query(GeneratedApp).filter(GeneratedApp.owner_id == current_user.id).count()
    files_q = db.query(File).filter(File.owner_id == current_user.id, File.deleted_at.is_(None))
    return {
        "shared_tasks": shared_tasks,
        "archived_tasks": archived,
        "shared_files": shared_files,
        "deployed_websites": websites,
        "apps": apps,
        "uploads": files_q.count(),
        "images": files_q.filter(File.file_type == FileType.IMAGE).count(),
        "documents": files_q.filter(File.file_type == FileType.DOCUMENT).count(),
        "videos": files_q.filter(File.file_type == FileType.VIDEO).count(),
        "audio": files_q.filter(File.file_type == FileType.AUDIO).count(),
        "spreadsheets": files_q.filter(File.file_type == FileType.SPREADSHEET).count(),
        "code": files_q.filter(File.file_type == FileType.CODE).count(),
        "knowledge": db.query(Knowledge).filter(Knowledge.owner_id == current_user.id).count(),
        "memories": db.query(Memory).filter(Memory.owner_id == current_user.id).count(),
        "skills": db.query(Skill).filter(Skill.owner_id == current_user.id).count(),
    }

# Cloud Browser
class CloudBrowserUpdate(BaseModel):
    persist_login: bool
    cookies: Optional[Dict[str, Any]] = None

@router.get("/cloud-browser")
async def get_cloud_browser(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _load_settings(db, current_user.id).get("cloud_browser", DEFAULT_SETTINGS["cloud_browser"])

@router.patch("/cloud-browser")
async def update_cloud_browser(data: CloudBrowserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_settings = _load_settings(db, current_user.id)
    user_settings["cloud_browser"] = {"persist_login": data.persist_login, "cookies": data.cookies or {}}
    _save_settings(db, current_user.id, user_settings)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="cloud_browser", success=True)
    return user_settings["cloud_browser"]

# Mail Mark
class MailSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    approved_senders: Optional[List[str]] = None
    workflow_email: Optional[str] = None

@router.get("/mail")
async def get_mail_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _load_settings(db, current_user.id).get("mail", DEFAULT_SETTINGS["mail"])

@router.patch("/mail")
async def update_mail_settings(data: MailSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_settings = _load_settings(db, current_user.id)
    mail = dict(user_settings.get("mail", dict(DEFAULT_SETTINGS["mail"])))
    if data.enabled is not None: mail["enabled"] = data.enabled
    if data.approved_senders is not None: mail["approved_senders"] = data.approved_senders
    if data.workflow_email is not None: mail["workflow_email"] = data.workflow_email
    user_settings["mail"] = mail
    _save_settings(db, current_user.id, user_settings)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="mail", success=True)
    return mail

@router.get("/mail/inbox")
async def get_mail_inbox(limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Real mailbox read via a connected IMAP/Gmail credential.

    Returns no messages (and an explicit reason) when no mailbox is connected,
    rather than fabricating sample emails.
    """
    mail_settings = _load_settings(db, current_user.id).get("mail", DEFAULT_SETTINGS["mail"])
    if not mail_settings.get("enabled"):
        return {"enabled": False, "messages": [], "connected": False,
                "note": "Mail Mark is disabled. Enable it in Settings, then connect a mailbox."}

    creds = db.query(ConnectorCredential).filter(
        ConnectorCredential.user_id == current_user.id,
        ConnectorCredential.connector_id.in_(
            db.query(Connector.id).filter(Connector.type == ConnectorType.GMAIL)
        ),
        ConnectorCredential.status == ConnectorStatus.CONNECTED,
    ).all()

    if not creds:
        return {
            "enabled": True,
            "connected": False,
            "messages": [],
            "approved_senders": mail_settings.get("approved_senders", []),
            "workflow_email": mail_settings.get("workflow_email", ""),
            "note": "No mailbox is connected, so there is nothing to read. Connect Gmail or Outlook in "
                    "Settings > Connectors first. No messages are shown because none were fetched.",
        }

    try:
        from app.services.mail_reader import fetch_inbox
        messages = await fetch_inbox(creds[0], limit=limit)
    except Exception as exc:
        return {"enabled": True, "connected": True, "messages": [],
                "approved_senders": mail_settings.get("approved_senders", []),
                "workflow_email": mail_settings.get("workflow_email", ""),
                "note": f"Mailbox is connected but could not be read: {exc}"}

    approved = {s.lower() for s in (mail_settings.get("approved_senders") or [])}
    for m in messages:
        m["is_approved"] = (m.get("from", "").lower() in approved) if approved else False
    return {
        "enabled": True,
        "connected": True,
        "approved_senders": mail_settings.get("approved_senders", []),
        "workflow_email": mail_settings.get("workflow_email", ""),
        "messages": messages,
    }

@router.post("/mail/inbox/{msg_id}/execute")
async def execute_mail_task(msg_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify sender is approved before creating privileged task
    inbox = await get_mail_inbox(current_user=current_user, db=db)
    msg = next((m for m in inbox["messages"] if m["id"] == msg_id), None)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found in the connected mailbox")
    if not msg.get("is_approved"):
        raise HTTPException(status_code=403, detail="Sender not in approved_senders - privileged task blocked")
    t = Task(title=f"Mail: {msg['subject']}", description=msg["snippet"], original_request=msg["snippet"], owner_id=current_user.id, status="PENDING")
    db.add(t); db.commit(); db.refresh(t)
    return {"message": "Task created from mail", "task_id": t.id}
