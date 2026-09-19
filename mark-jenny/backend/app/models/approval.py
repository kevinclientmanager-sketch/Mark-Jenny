from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ApprovalType(str, enum.Enum):
    SEND_EMAIL = "SEND_EMAIL"
    PUBLISH_WEBSITE = "PUBLISH_WEBSITE"
    DELETE_FILES = "DELETE_FILES"
    EXECUTE_COMMAND = "EXECUTE_COMMAND"
    SPEND_MONEY = "SPEND_MONEY"
    POST_PUBLICLY = "POST_PUBLICLY"
    CONNECTOR_ACTION = "CONNECTOR_ACTION"
    TASK_ACTION = "TASK_ACTION"
    SKILL_INSTALL = "SKILL_INSTALL"
    MODEL_CHANGE = "MODEL_CHANGE"
    CUSTOM = "CUSTOM"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(ApprovalType), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    details = Column(JSON)
    risk_level = Column(String(20), default="medium")  # low, medium, high, critical
    
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(String(100))  # agent name or "user"
    
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    decided_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    decided_at = Column(DateTime(timezone=True))
    decision_reason = Column(Text)
    
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("Task", back_populates="approvals")
    user = relationship("User", foreign_keys=[user_id])
    decider = relationship("User", foreign_keys=[decided_by])