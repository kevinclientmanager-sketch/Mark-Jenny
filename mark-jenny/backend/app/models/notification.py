from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class NotificationType(str, enum.Enum):
    TASK_STARTED = "TASK_STARTED"
    TASK_REQUIRES_APPROVAL = "TASK_REQUIRES_APPROVAL"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    SCHEDULED_TASK_RUN = "SCHEDULED_TASK_RUN"
    LONG_RUNNING_PAUSED = "LONG_RUNNING_PAUSED"
    CONNECTOR_EXPIRED = "CONNECTOR_EXPIRED"
    SECURITY_EVENT = "SECURITY_EVENT"
    SYSTEM = "SYSTEM"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text)
    data = Column(JSON)
    is_read = Column(Boolean, default=False, nullable=False)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="SET NULL"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="notifications")
    task = relationship("Task")
    schedule = relationship("Schedule")