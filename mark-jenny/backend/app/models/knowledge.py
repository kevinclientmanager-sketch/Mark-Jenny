from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class MemoryType(str, enum.Enum):
    WORKING = "WORKING"
    SHORT_TERM = "SHORT_TERM"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    PROJECT = "PROJECT"
    USER_PREFERENCE = "USER_PREFERENCE"
    TASK = "TASK"
    FAILURE = "FAILURE"


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    use_when = Column(Text)
    content = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    source = Column(String(100))
    confidence = Column(Integer, default=100)
    importance = Column(Integer, default=50)
    tags = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="knowledge")
    owner = relationship("User")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(MemoryType), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100))
    confidence = Column(Integer, default=100)
    importance = Column(Integer, default=50)
    enabled = Column(Boolean, default=True, nullable=False)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    
    memory_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="memories")
    project = relationship("Project", back_populates="memories")
    task = relationship("Task", back_populates="memories")