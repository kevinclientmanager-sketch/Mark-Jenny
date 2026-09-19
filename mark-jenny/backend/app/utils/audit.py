from sqlalchemy.orm import Session
from app.models.audit import AuditLog, AuditAction
from app.models.user import User
from typing import Optional
import json


async def log_audit(
    db: Session,
    action: AuditAction,
    resource_type: str,
    resource_id: str,
    user_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> AuditLog:
    """Log an audit event."""
    audit_log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def get_client_info(request) -> tuple:
    """Extract client IP and user agent from request."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent