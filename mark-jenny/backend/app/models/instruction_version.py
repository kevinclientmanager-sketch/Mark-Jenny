from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from app.db.base import Base


class InstructionVersion(Base):
    """Versioned project instructions.

    The instructions endpoint previously hardcoded `versions = []`, so the
    version history shown in the UI was always empty. Every update now writes
    a row here, giving real history.
    """

    __tablename__ = "instruction_versions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
