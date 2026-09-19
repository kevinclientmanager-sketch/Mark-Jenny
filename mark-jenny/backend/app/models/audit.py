from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class AuditAction(str, enum.Enum):
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    
    # Projects
    PROJECT_CREATE = "PROJECT_CREATE"
    PROJECT_UPDATE = "PROJECT_UPDATE"
    PROJECT_DELETE = "PROJECT_DELETE"
    PROJECT_ARCHIVE = "PROJECT_ARCHIVE"
    PROJECT_RESTORE = "PROJECT_RESTORE"
    PROJECT_DUPLICATE = "PROJECT_DUPLICATE"
    PROJECT_INSTRUCTIONS_UPDATE = "PROJECT_INSTRUCTIONS_UPDATE"
    
    # Tasks
    TASK_CREATE = "TASK_CREATE"
    TASK_START = "TASK_START"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    TASK_CANCEL = "TASK_CANCEL"
    TASK_APPROVE = "TASK_APPROVE"
    TASK_REJECT = "TASK_REJECT"
    TASK_UPDATE = "TASK_UPDATE"
    TASK_DELETE = "TASK_DELETE"
    TASK_PAUSE = "TASK_PAUSE"
    TASK_RESUME = "TASK_RESUME"
    TASK_RETRY = "TASK_RETRY"
    
    # Files
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"
    FILE_DELETE = "FILE_DELETE"
    FILE_SHARE = "FILE_SHARE"
    
    # Skills
    SKILL_INSTALL = "SKILL_INSTALL"
    SKILL_ENABLE = "SKILL_ENABLE"
    SKILL_DISABLE = "SKILL_DISABLE"
    SKILL_UPDATE = "SKILL_UPDATE"
    SKILL_REMOVE = "SKILL_REMOVE"
    
    # Connectors
    CONNECTOR_CONNECT = "CONNECTOR_CONNECT"
    CONNECTOR_DISCONNECT = "CONNECTOR_DISCONNECT"
    CONNECTOR_REFRESH = "CONNECTOR_REFRESH"
    CONNECTOR_EXECUTE = "CONNECTOR_EXECUTE"
    
    # Schedules
    SCHEDULE_CREATE = "SCHEDULE_CREATE"
    SCHEDULE_UPDATE = "SCHEDULE_UPDATE"
    SCHEDULE_DELETE = "SCHEDULE_DELETE"
    SCHEDULE_RUN = "SCHEDULE_RUN"
    SCHEDULE_PAUSE = "SCHEDULE_PAUSE"
    SCHEDULE_RESUME = "SCHEDULE_RESUME"
    SCHEDULE_DUPLICATE = "SCHEDULE_DUPLICATE"
    
    # Admin
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    USER_BAN = "USER_BAN"
    ROLE_CHANGE = "ROLE_CHANGE"
    SETTINGS_CHANGE = "SETTINGS_CHANGE"
    
    # Chat
    CHAT_CREATE = "CHAT_CREATE"
    CHAT_DELETE = "CHAT_DELETE"
    CHAT_MESSAGE = "CHAT_MESSAGE"
    MESSAGE_EDIT = "MESSAGE_EDIT"
    MESSAGE_DELETE = "MESSAGE_DELETE"

    # Security
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="audit_logs")