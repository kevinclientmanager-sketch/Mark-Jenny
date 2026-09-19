from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class GeneratedType(str, enum.Enum):
    WEBSITE = "WEBSITE"
    APPLICATION = "APPLICATION"
    SLIDES = "SLIDES"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    CODE = "CODE"


class GeneratedStatus(str, enum.Enum):
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEPLOYED = "DEPLOYED"


class GeneratedWebsite(Base):
    __tablename__ = "generated_websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prompt = Column(Text)
    status = Column(SQLEnum(GeneratedStatus), default=GeneratedStatus.GENERATING, nullable=False)
    files = Column(JSON)  # File structure
    preview_url = Column(String(500))
    deploy_url = Column(String(500))
    framework = Column(String(50))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deployed_at = Column(DateTime(timezone=True))

    task = relationship("Task")
    project = relationship("Project")
    owner = relationship("User")


class GeneratedApp(Base):
    __tablename__ = "generated_apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prompt = Column(Text)
    type = Column(SQLEnum(GeneratedType), nullable=False)
    status = Column(SQLEnum(GeneratedStatus), default=GeneratedStatus.GENERATING, nullable=False)
    files = Column(JSON)
    repo_url = Column(String(500))
    deploy_url = Column(String(500))
    language = Column(String(50))
    framework = Column(String(50))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deployed_at = Column(DateTime(timezone=True))

    task = relationship("Task")
    project = relationship("Project")
    owner = relationship("User")


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    browser_type = Column(String(50))  # chromium, firefox, webkit
    profile_path = Column(String(500))
    cookies = Column(JSON)
    local_storage = Column(JSON)
    session_data = Column(JSON)
    is_persistent = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))

    owner = relationship("User")
    task = relationship("Task")