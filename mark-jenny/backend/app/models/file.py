from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class FileType(str, enum.Enum):
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    SPREADSHEET = "SPREADSHEET"
    CODE = "CODE"
    ARCHIVE = "ARCHIVE"
    WEBSITE = "WEBSITE"
    OTHER = "OTHER"


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    original_name = Column(String(500), nullable=False)
    path = Column(String(1000), nullable=False)
    storage_key = Column(String(500))
    mime_type = Column(String(100))
    file_type = Column(SQLEnum(FileType), default=FileType.OTHER, nullable=False)
    size = Column(Integer, default=0)
    hash = Column(String(64))
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"))
    
    is_public = Column(Boolean, default=False)
    file_metadata = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    owner = relationship("User", back_populates="files")
    project = relationship("Project", back_populates="files")
    task = relationship("Task", back_populates="files")
    folder = relationship("Folder", back_populates="files")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(1000))
    parent_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    files = relationship("File", back_populates="folder")
    children = relationship("Folder", backref="parent", remote_side=[id])