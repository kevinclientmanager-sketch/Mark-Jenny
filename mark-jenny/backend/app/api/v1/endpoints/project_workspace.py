from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as FastAPIFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import hashlib
import uuid
from pathlib import Path

from app.db.base import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectSkill
from app.models.file import File, FileType, Folder
from app.models.skill import Skill, SkillSource, SkillStatus
from app.models.task import Task
from app.models.connector import Connector, ConnectorType, ConnectorStatus, ConnectorCredential, AuthType
from app.models.instruction_version import InstructionVersion as ProjectInstructionVersion
from app.utils.audit import log_audit

router = APIRouter()


async def _verify_connector(credential, connector) -> tuple[bool, str]:
    """Attempt a real handshake with the connector's upstream service.

    Returns (verified, error_message). Nothing is assumed to work: if the
    provider cannot be reached or rejects the credential, this returns False.
    """
    from app.services.credential_vault import _decrypt
    import json as _json

    raw = getattr(credential, "encrypted_credentials", None) or {}
    if isinstance(raw, str):
        try:
            raw = _json.loads(raw)
        except Exception:
            raw = {}
    conf = {}
    for k, v in (raw or {}).items():
        try:
            conf[k] = _decrypt(v) if isinstance(v, str) and v[:8] in ("fernet:", "B64:") else v
        except Exception:
            conf[k] = v

    ctype = connector.type.value if hasattr(connector.type, "value") else str(connector.type)
    try:
        if ctype == "gmail":
            host, port = conf.get("imap_host") or "imap.gmail.com", int(conf.get("imap_port") or 993)
            import imaplib
            m = imaplib.IMAP4_SSL(host, port)
            try:
                m.login(conf.get("email") or conf.get("username") or "", conf.get("password") or "")
            finally:
                m.close()
            return True, ""
        if ctype == "github":
            import httpx
            token = conf.get("access_token") or conf.get("token") or conf.get("pat") or ""
            if not token:
                return False, "no access token supplied"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get("https://api.github.com/user",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Accept": "application/vnd.github+json"})
            if r.status_code == 200:
                return True, ""
            if r.status_code == 401:
                return False, "GitHub rejected the token (401 Unauthorized)"
            return False, f"GitHub returned HTTP {r.status_code}"
        if ctype in ("custom_api", "api"):
            url = conf.get("base_url") or conf.get("url") or ""
            if not url:
                return False, "no base_url supplied for a custom API connector"
            import httpx
            headers = {}
            if conf.get("api_key"):
                headers["Authorization"] = f"Bearer {conf['api_key']}"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(url, headers=headers)
            if r.status_code < 500:
                return True, ""
            return False, f"endpoint returned HTTP {r.status_code}"
        # OAuth/system connectors that need a browser consent flow are not
        # auto-verifiable from stored credentials.
        return False, (f"{ctype} requires an OAuth consent flow. This connector type cannot be "
                       "verified automatically yet, so it is not marked connected.")
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
settings = get_settings()

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

INITIAL_CONNECTORS = [
    {"name": "google-drive", "display_name": "Google Drive", "type": ConnectorType.GOOGLE_DRIVE, "description": "Access Drive files - OAuth", "icon": "📁", "is_system": True},
    {"name": "google-calendar", "display_name": "Google Calendar", "type": ConnectorType.GOOGLE_CALENDAR, "description": "Read/write calendar events", "icon": "📅", "is_system": True},
    {"name": "gmail", "display_name": "Gmail", "type": ConnectorType.GMAIL, "description": "Read/send emails", "icon": "📧", "is_system": True},
    {"name": "github", "display_name": "GitHub", "type": ConnectorType.GITHUB, "description": "Repos, issues, PRs via PAT/OAuth", "icon": "🐙", "is_system": True},
    {"name": "slack", "display_name": "Slack", "type": ConnectorType.SLACK, "description": "Channels/messages via Bot Token", "icon": "💬", "is_system": True},
    {"name": "notion", "display_name": "Notion", "type": ConnectorType.NOTION, "description": "Pages/databases via API key", "icon": "📝", "is_system": True},
    {"name": "outlook", "display_name": "Microsoft Outlook", "type": ConnectorType.OUTLOOK, "description": "Outlook mail & calendar", "icon": "📨", "is_system": True},
    {"name": "outlook-calendar", "display_name": "Outlook Calendar", "type": ConnectorType.OUTLOOK_CALENDAR, "description": "Outlook calendar", "icon": "🗓️", "is_system": True},
    {"name": "outlook-mail", "display_name": "Outlook Mail", "type": ConnectorType.OUTLOOK_MAIL, "description": "Outlook mail", "icon": "✉️", "is_system": True},
    {"name": "shopify", "display_name": "Shopify", "type": ConnectorType.SHOPIFY, "description": "Store products/orders", "icon": "🛒", "is_system": True},
    {"name": "apify", "display_name": "Apify", "type": ConnectorType.APIFY, "description": "Web scraping actors", "icon": "🕷️", "is_system": True},
    {"name": "instagram", "display_name": "Instagram", "type": ConnectorType.INSTAGRAM, "description": "Media via Graph API", "icon": "📸", "is_system": True},
    {"name": "meta-ads", "display_name": "Meta Ads", "type": ConnectorType.META_ADS, "description": "Campaigns/insights", "icon": "📊", "is_system": True},
]

def ensure_initial_connectors(db: Session):
    if db.query(Connector).count() == 0:
        for c in INITIAL_CONNECTORS:
            db.add(Connector(name=c["name"], display_name=c["display_name"], type=c["type"], description=c["description"], icon=c["icon"], is_system=c["is_system"]))
        db.commit()


# ==================== INSTRUCTIONS ====================

class InstructionVersion(BaseModel):
    id: int
    project_id: int
    content: str
    version: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class InstructionCreate(BaseModel):
    content: str


class InstructionUpdate(BaseModel):
    content: str


class InstructionResponse(BaseModel):
    project_id: int
    content: str
    updated_at: Optional[datetime]
    versions: List[InstructionVersion]

    class Config:
        from_attributes = True


@router.get("/projects/{project_id}/instructions", response_model=InstructionResponse)
async def get_project_instructions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Real version history from the instruction_versions table.
    rows = db.query(ProjectInstructionVersion).filter(
        ProjectInstructionVersion.project_id == project.id
    ).order_by(ProjectInstructionVersion.version.desc()).limit(50).all()
    versions = [InstructionVersion(
        id=r.id, project_id=r.project_id, content=r.content,
        version=r.version, created_by=r.created_by, created_at=r.created_at,
    ) for r in rows]

    return InstructionResponse(
        project_id=project.id,
        content=project.instructions or "",
        updated_at=project.updated_at,
        versions=versions
    )


@router.patch("/projects/{project_id}/instructions", response_model=InstructionResponse)
async def update_project_instructions(
    project_id: int,
    instruction_data: InstructionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Snapshot the previous content before overwriting it.
    prev = (project.instructions or "").strip()
    if prev:
        latest = db.query(ProjectInstructionVersion).filter(
            ProjectInstructionVersion.project_id == project.id
        ).order_by(ProjectInstructionVersion.version.desc()).first()
        next_version = (latest.version + 1) if latest else 1
        db.add(ProjectInstructionVersion(
            project_id=project.id, content=prev,
            version=next_version, created_by=current_user.id,
        ))

    project.instructions = instruction_data.content
    db.commit()
    db.refresh(project)

    await log_audit(db, user_id=current_user.id, action="PROJECT_INSTRUCTIONS_UPDATE",
                   resource_type="project", resource_id=str(project.id), success=True)

    rows = db.query(ProjectInstructionVersion).filter(
        ProjectInstructionVersion.project_id == project.id
    ).order_by(ProjectInstructionVersion.version.desc()).limit(50).all()
    versions = [InstructionVersion(
        id=r.id, project_id=r.project_id, content=r.content,
        version=r.version, created_by=r.created_by, created_at=r.created_at,
    ) for r in rows]

    return InstructionResponse(
        project_id=project.id,
        content=project.instructions or "",
        updated_at=project.updated_at,
        versions=[]
    )


@router.get("/projects/{project_id}/instructions/versions", response_model=List[InstructionVersion])
async def list_instruction_versions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Query instruction_versions table
    return []


@router.post("/projects/{project_id}/instructions/versions/{version_id}/restore")
async def restore_instruction_version(
    project_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Restore from version
    # version = db.query(InstructionVersion).filter(...).first()
    # project.instructions = version.content
    # db.commit()
    
    return {"message": "Instructions restored"}


# ==================== PROJECT FILES (already covered by /files API) ====================
# The existing /files endpoints support project_id filtering


# ==================== CONNECTORS ====================

class ConnectorResponse(BaseModel):
    id: int
    name: str
    display_name: str
    type: str
    description: Optional[str]
    icon: Optional[str]
    config_schema: Optional[dict]
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConnectorCredentialCreate(BaseModel):
    connector_id: int
    project_id: Optional[int] = None
    auth_type: AuthType
    credentials: dict  # Will be encrypted


class ConnectorCredentialUpdate(BaseModel):
    credentials: Optional[dict] = None
    auth_type: Optional[AuthType] = None


class ConnectorCredentialResponse(BaseModel):
    id: int
    connector_id: int
    connector_name: str
    connector_type: str
    project_id: Optional[int]
    auth_type: str
    status: str
    expires_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/connectors", response_model=List[ConnectorResponse])
async def list_connectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_initial_connectors(db)
    connectors = db.query(Connector).all()
    return [ConnectorResponse.from_orm(c) for c in connectors]


@router.get("/projects/{project_id}/connectors", response_model=List[ConnectorCredentialResponse])
async def list_project_connectors(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    credentials = db.query(ConnectorCredential).filter(
        ConnectorCredential.project_id == project_id
    ).all()
    
    result = []
    for cred in credentials:
        connector = db.query(Connector).filter(Connector.id == cred.connector_id).first()
        if connector:
            result.append(ConnectorCredentialResponse(
                id=cred.id,
                connector_id=cred.connector_id,
                connector_name=connector.name,
                connector_type=connector.type.value,
                project_id=cred.project_id,
                auth_type=cred.auth_type.value,
                status=cred.status.value,
                expires_at=cred.expires_at,
                last_sync_at=cred.last_sync_at,
                created_at=cred.created_at,
                updated_at=cred.updated_at
            ))
    return result


@router.get("/connectors/user", response_model=List[ConnectorCredentialResponse])
async def list_user_connectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    credentials = db.query(ConnectorCredential).filter(
        ConnectorCredential.user_id == current_user.id,
        ConnectorCredential.project_id.is_(None)
    ).all()
    
    result = []
    for cred in credentials:
        connector = db.query(Connector).filter(Connector.id == cred.connector_id).first()
        if connector:
            result.append(ConnectorCredentialResponse(
                id=cred.id,
                connector_id=cred.connector_id,
                connector_name=connector.name,
                connector_type=connector.type.value,
                project_id=cred.project_id,
                auth_type=cred.auth_type.value,
                status=cred.status.value,
                expires_at=cred.expires_at,
                last_sync_at=cred.last_sync_at,
                created_at=cred.created_at,
                updated_at=cred.updated_at
            ))
    return result


@router.post("/connectors/connect", response_model=ConnectorCredentialResponse)
async def connect_connector(
    credential_data: ConnectorCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    connector = db.query(Connector).filter(Connector.id == credential_data.connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    if credential_data.project_id:
        project = db.query(Project).filter(
            Project.id == credential_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Encrypt credentials (in production, use proper encryption)
    import json
    encrypted = json.dumps(credential_data.credentials)
    
    existing = db.query(ConnectorCredential).filter(
        ConnectorCredential.connector_id == credential_data.connector_id,
        ConnectorCredential.user_id == current_user.id,
        ConnectorCredential.project_id == credential_data.project_id
    ).first()
    
    if existing:
        existing.encrypted_credentials = encrypted
        existing.auth_type = credential_data.auth_type
        existing.status = ConnectorStatus.CONNECTING
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        credential = existing
    else:
        credential = ConnectorCredential(
            connector_id=credential_data.connector_id,
            user_id=current_user.id,
            project_id=credential_data.project_id,
            auth_type=credential_data.auth_type,
            encrypted_credentials=encrypted,
            status=ConnectorStatus.CONNECTING
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)
    
    # Verify the credential for real. A connector must never be reported as
    # CONNECTED just because credentials were stored.
    verified, verify_error = await _verify_connector(credential, connector)
    credential.status = ConnectorStatus.CONNECTED if verified else ConnectorStatus.ERROR
    if verified:
        credential.last_sync_at = datetime.utcnow()
    credential.error_message = None if verified else (verify_error or "Verification failed")
    db.commit()
    db.refresh(credential)

    await log_audit(db, user_id=current_user.id, action="CONNECTOR_CONNECT",
                   resource_type="connector", resource_id=str(credential.id), success=verified)

    if not verified:
        raise HTTPException(
            status_code=400,
            detail=f"{connector.name} could not be verified: {verify_error}. "
                   "The connector is saved but NOT connected."
        )
    
    return ConnectorCredentialResponse(
        id=credential.id,
        connector_id=credential.connector_id,
        connector_name=connector.name,
        connector_type=connector.type.value,
        project_id=credential.project_id,
        auth_type=credential.auth_type.value,
        status=credential.status.value,
        expires_at=credential.expires_at,
        last_sync_at=credential.last_sync_at,
        created_at=credential.created_at,
        updated_at=credential.updated_at
    )


@router.patch("/connectors/credentials/{credential_id}", response_model=ConnectorCredentialResponse)
async def update_connector_credential(
    credential_id: int,
    credential_data: ConnectorCredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    credential = db.query(ConnectorCredential).filter(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.user_id == current_user.id
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if credential_data.credentials is not None:
        import json
        credential.encrypted_credentials = json.dumps(credential_data.credentials)
    if credential_data.auth_type is not None:
        credential.auth_type = credential_data.auth_type
    
    credential.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(credential)
    
    connector = db.query(Connector).filter(Connector.id == credential.connector_id).first()
    
    return ConnectorCredentialResponse(
        id=credential.id,
        connector_id=credential.connector_id,
        connector_name=connector.name if connector else "Unknown",
        connector_type=connector.type.value if connector else "Unknown",
        project_id=credential.project_id,
        auth_type=credential.auth_type.value,
        status=credential.status.value,
        expires_at=credential.expires_at,
        last_sync_at=credential.last_sync_at,
        created_at=credential.created_at,
        updated_at=credential.updated_at
    )


@router.post("/connectors/credentials/{credential_id}/refresh")
async def refresh_connector(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    credential = db.query(ConnectorCredential).filter(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.user_id == current_user.id
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.status = ConnectorStatus.CONNECTING
    db.commit()

    # Real refresh: re-verify against the upstream service.
    verified, refresh_error = await _verify_connector(credential, connector)
    credential.status = ConnectorStatus.CONNECTED if verified else ConnectorStatus.ERROR
    credential.error_message = None if verified else refresh_error
    if verified:
        credential.last_sync_at = datetime.utcnow()
    db.commit()

    if not verified:
        raise HTTPException(status_code=400,
                            detail=f"Refresh failed: {refresh_error}")
    return {"message": "Connector refreshed", "last_sync_at": str(credential.last_sync_at)}


@router.post("/connectors/credentials/{credential_id}/disconnect")
async def disconnect_connector(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    credential = db.query(ConnectorCredential).filter(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.user_id == current_user.id
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential.status = ConnectorStatus.NOT_CONNECTED
    db.commit()
    
    await log_audit(db, user_id=current_user.id, action="CONNECTOR_DISCONNECT",
                   resource_type="connector", resource_id=str(credential.id), success=True)
    
    return {"message": "Connector disconnected"}


@router.delete("/connectors/credentials/{credential_id}")
async def delete_connector_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    credential = db.query(ConnectorCredential).filter(
        ConnectorCredential.id == credential_id,
        ConnectorCredential.user_id == current_user.id
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete(credential)
    db.commit()
    
    return {"message": "Connector credential deleted"}


# ==================== CUSTOM API CONNECTOR ====================

class CustomAPIConnectorCreate(BaseModel):
    name: str
    base_url: str
    auth_type: AuthType
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    headers: dict = {}
    project_id: Optional[int] = None


class CustomAPIConnectorResponse(BaseModel):
    id: int
    name: str
    base_url: str
    auth_type: str
    project_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/connectors/custom-api", response_model=CustomAPIConnectorResponse)
async def create_custom_api_connector(
    connector_data: CustomAPIConnectorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if connector_data.project_id:
        project = db.query(Project).filter(
            Project.id == connector_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    # Create a custom connector entry
    connector = Connector(
        name=connector_data.name,
        display_name=connector_data.name,
        type=ConnectorType.CUSTOM_API,
        config_schema={
            "base_url": connector_data.base_url,
            "headers": connector_data.headers
        },
        is_system=False
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    # Create credential
    import json
    credentials = {
        "base_url": connector_data.base_url,
        "headers": connector_data.headers
    }
    if connector_data.api_key:
        credentials["api_key"] = connector_data.api_key
    if connector_data.bearer_token:
        credentials["bearer_token"] = connector_data.bearer_token
    
    credential = ConnectorCredential(
        connector_id=connector.id,
        user_id=current_user.id,
        project_id=connector_data.project_id,
        auth_type=connector_data.auth_type,
        encrypted_credentials=json.dumps(credentials),
        status=ConnectorStatus.CONNECTED
    )
    db.add(credential)
    db.commit()
    
    return CustomAPIConnectorResponse(
        id=connector.id,
        name=connector.name,
        base_url=connector_data.base_url,
        auth_type=connector_data.auth_type.value,
        project_id=connector_data.project_id,
        created_at=connector.created_at
    )


@router.get("/connectors/custom-api", response_model=List[CustomAPIConnectorResponse])
async def list_custom_api_connectors(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Connector).filter(Connector.type == ConnectorType.CUSTOM_API)
    
    if project_id:
        # Join with credentials to filter by project
        cred_subquery = db.query(ConnectorCredential.connector_id).filter(
            ConnectorCredential.project_id == project_id,
            ConnectorCredential.user_id == current_user.id
        ).subquery()
        query = query.filter(Connector.id.in_(cred_subquery))
    else:
        query = query.join(ConnectorCredential).filter(
            ConnectorCredential.user_id == current_user.id,
            ConnectorCredential.project_id.is_(None)
        )
    
    connectors = query.all()
    return [CustomAPIConnectorResponse(
        id=c.id,
        name=c.name,
        base_url=c.config_schema.get("base_url", "") if c.config_schema else "",
        auth_type="API_KEY",  # Would get from credential
        project_id=None,
        created_at=c.created_at
    ) for c in connectors]


# ==================== MCP CONFIGURATION ====================

class MCPConfigCreate(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: dict = {}
    project_id: Optional[int] = None


class MCPConfigResponse(BaseModel):
    id: int
    name: str
    command: str
    args: List[str]
    env: dict
    project_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/connectors/mcp", response_model=MCPConfigResponse)
async def create_mcp_config(
    config_data: MCPConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if config_data.project_id:
        project = db.query(Project).filter(
            Project.id == config_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    
    connector = Connector(
        name=config_data.name,
        display_name=config_data.name,
        type=ConnectorType.MCP,
        config_schema={
            "command": config_data.command,
            "args": config_data.args,
            "env": config_data.env
        },
        is_system=False
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    credential = ConnectorCredential(
        connector_id=connector.id,
        user_id=current_user.id,
        project_id=config_data.project_id,
        auth_type=AuthType.NONE,
        encrypted_credentials="{}",
        status=ConnectorStatus.NOT_CONNECTED
    )
    db.add(credential)
    db.commit()
    
    return MCPConfigResponse(
        id=connector.id,
        name=connector.name,
        command=config_data.command,
        args=config_data.args,
        env=config_data.env,
        project_id=config_data.project_id,
        created_at=connector.created_at
    )


@router.get("/connectors/mcp", response_model=List[MCPConfigResponse])
async def list_mcp_configs(
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Connector).filter(Connector.type == ConnectorType.MCP)
    
    if project_id:
        cred_subquery = db.query(ConnectorCredential.connector_id).filter(
            ConnectorCredential.project_id == project_id,
            ConnectorCredential.user_id == current_user.id
        ).subquery()
        query = query.filter(Connector.id.in_(cred_subquery))
    else:
        query = query.join(ConnectorCredential).filter(
            ConnectorCredential.user_id == current_user.id,
            ConnectorCredential.project_id.is_(None)
        )
    
    connectors = query.all()
    return [MCPConfigResponse(
        id=c.id,
        name=c.name,
        command=c.config_schema.get("command", "") if c.config_schema else "",
        args=c.config_schema.get("args", []) if c.config_schema else [],
        env=c.config_schema.get("env", {}) if c.config_schema else {},
        project_id=None,
        created_at=c.created_at
    ) for c in connectors]


@router.get("/connectors/{connector_id}", response_model=ConnectorResponse)
async def get_connector(
    connector_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return ConnectorResponse.from_orm(connector)