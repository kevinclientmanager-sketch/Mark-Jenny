from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ScheduleFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ONCE = "ONCE"
    CRON = "CRON"


class ScheduleRunOption(str, enum.Enum):
    SAME_TASK = "SAME_TASK"
    SEPARATE_TASK = "SEPARATE_TASK"


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    prompt = Column(Text, nullable=False)
    frequency = Column(SQLEnum(ScheduleFrequency), default=ScheduleFrequency.DAILY, nullable=False)
    cron_expression = Column(String(100))
    time_of_day = Column(String(10))  # HH:MM format
    timezone = Column(String(50), default="UTC")
    
    run_option = Column(SQLEnum(ScheduleRunOption), default=ScheduleRunOption.SAME_TASK)
    skip_confirmations = Column(Boolean, default=False)
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    connectors = Column(JSON)  # List of connector IDs
    config = Column(JSON)
    
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    run_count = Column(Integer, default=0)
    max_runs = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="schedules")
    agent = relationship("Agent")
    owner = relationship("User")
    runs = relationship("ScheduleRun", back_populates="schedule")


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED, SKIPPED
    error = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    schedule = relationship("Schedule", back_populates="runs")
    task = relationship("Task")