from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from app.db.base import Base


class BuilderAccess(Base):
    """Per-user gate for the self-builder. Default: no access (except master admins)."""
    __tablename__ = "builder_access"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    allowed = Column(Boolean, default=False, nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
