from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class SkillSource(str, enum.Enum):
    OFFICIAL = "OFFICIAL"
    UPLOADED = "UPLOADED"
    GITHUB = "GITHUB"
    CREATED_BY_MARK = "CREATED_BY_MARK"


class SkillStatus(str, enum.Enum):
    INSTALLED = "INSTALLED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"
    UPDATING = "UPDATING"


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    version = Column(String(50), nullable=False)
    source = Column(SQLEnum(SkillSource), default=SkillSource.UPLOADED, nullable=False)
    source_url = Column(String(500))
    status = Column(SQLEnum(SkillStatus), default=SkillStatus.INSTALLED, nullable=False)
    
    manifest = Column(JSON)
    instructions = Column(Text)
    tools = Column(JSON)
    permissions = Column(JSON)
    config_schema = Column(JSON)
    default_config = Column(JSON)
    dependencies = Column(JSON)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", back_populates="skills")
    versions = relationship("SkillVersion", back_populates="skill")
    projects = relationship("ProjectSkill", back_populates="skill")


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    manifest = Column(JSON)
    instructions = Column(Text)
    tools = Column(JSON)
    permissions = Column(JSON)
    config_schema = Column(JSON)
    default_config = Column(JSON)
    dependencies = Column(JSON)
    changelog = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    skill = relationship("Skill", back_populates="versions")