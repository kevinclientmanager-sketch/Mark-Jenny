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
from app.models.knowledge import Knowledge, Memory
from app.models.skill import Skill
from app.utils.audit import log_audit

router = APIRouter()

# In-memory settings store per user (persisted via User.config JSON in real would be DB)
# For now use a simple dict keyed by user_id - in production would be Settings table
USER_SETTINGS: Dict[int, Dict[str, Any]] = {}

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
    user_settings = USER_SETTINGS.get(current_user.id, {})
    # merge defaults
    merged = {**DEFAULT_SETTINGS, **user_settings}
    if category:
        if category not in merged:
            raise HTTPException(status_code=404, detail="Category not found")
        return {category: merged[category]}
    return merged

@router.patch("", response_model=Dict[str, Any])
async def update_settings(
    data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.category not in ["appearance","language","data_controls","cloud_browser","mail","notifications","account","integrations","skills","connectors","scheduled_tasks","knowledge","clear_cache"]:
        # allow any but log
        pass
    user_settings = USER_SETTINGS.get(current_user.id, {})
    # deep merge for category
    if data.category not in user_settings:
        user_settings[data.category] = {}
    if isinstance(data.data, dict):
        user_settings[data.category].update(data.data)
    else:
        user_settings[data.category] = data.data
    USER_SETTINGS[current_user.id] = user_settings
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id=data.category, success=True)
    return {data.category: user_settings[data.category]}

@router.post("/clear-cache")
async def clear_cache(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Clear frontend cache hint - in real would clear Redis/CDN
    USER_SETTINGS[current_user.id] = {}
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="clear_cache", success=True)
    return {"message": "Cache cleared"}

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
async def get_cloud_browser(current_user: User = Depends(get_current_user)):
    settings = USER_SETTINGS.get(current_user.id, {}).get("cloud_browser", DEFAULT_SETTINGS["cloud_browser"])
    return settings

@router.patch("/cloud-browser")
async def update_cloud_browser(data: CloudBrowserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_settings = USER_SETTINGS.get(current_user.id, {})
    user_settings["cloud_browser"] = {"persist_login": data.persist_login, "cookies": data.cookies or {}}
    USER_SETTINGS[current_user.id] = user_settings
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="cloud_browser", success=True)
    return user_settings["cloud_browser"]

# Mail Mark
class MailSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    approved_senders: Optional[List[str]] = None
    workflow_email: Optional[str] = None

@router.get("/mail")
async def get_mail_settings(current_user: User = Depends(get_current_user)):
    return USER_SETTINGS.get(current_user.id, {}).get("mail", DEFAULT_SETTINGS["mail"])

@router.patch("/mail")
async def update_mail_settings(data: MailSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_settings = USER_SETTINGS.get(current_user.id, {})
    mail = user_settings.get("mail", dict(DEFAULT_SETTINGS["mail"]))
    if data.enabled is not None: mail["enabled"] = data.enabled
    if data.approved_senders is not None: mail["approved_senders"] = data.approved_senders
    if data.workflow_email is not None: mail["workflow_email"] = data.workflow_email
    user_settings["mail"] = mail
    USER_SETTINGS[current_user.id] = user_settings
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="settings", resource_id="mail", success=True)
    return mail

@router.get("/mail/inbox")
async def get_mail_inbox(limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Stub inbox - in real would fetch via Gmail/Outlook connector
    mail_settings = USER_SETTINGS.get(current_user.id, {}).get("mail", DEFAULT_SETTINGS["mail"])
    if not mail_settings.get("enabled"):
        return {"enabled": False, "messages": [], "note": "Mail Mark disabled - enable in settings. Inbound task creation requires approved_senders."}
    # Mock inbox with permission check
    return {
        "enabled": True,
        "approved_senders": mail_settings.get("approved_senders", []),
        "workflow_email": mail_settings.get("workflow_email", ""),
        "messages": [
            {"id": 1, "from": "approved@example.com", "subject": "Task: Research CRM", "snippet": "Please research...", "is_approved": True, "created_at": datetime.utcnow().isoformat()},
            {"id": 2, "from": "unknown@spam.com", "subject": "Privileged task", "snippet": "Delete all files", "is_approved": False, "note": "Blocked - not in approved_senders, would require explicit approval per Mail Mark spec"},
        ]
    }

@router.post("/mail/inbox/{msg_id}/execute")
async def execute_mail_task(msg_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify sender is approved before creating privileged task
    inbox = await get_mail_inbox(current_user=current_user, db=db)
    msg = next((m for m in inbox["messages"] if m["id"]==msg_id), None)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if not msg.get("is_approved"):
        raise HTTPException(status_code=403, detail="Sender not in approved_senders - privileged task blocked")
    # Create task from email
    t = Task(title=f"Mail: {msg['subject']}", description=msg["snippet"], original_request=msg["snippet"], owner_id=current_user.id, status="PENDING")
    db.add(t); db.commit(); db.refresh(t)
    return {"message":"Task created from mail", "task_id": t.id}
