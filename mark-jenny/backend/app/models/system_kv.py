from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from app.db.base import Base


class SystemKV(Base):
    """Persisted system-wide key/value state.

    Replaces the module-level dicts that admin feature flags, the blacklist,
    subscriptions and credits lived in - those were lost on every restart.
    Created automatically by init_db, so no migration is needed.
    """

    __tablename__ = "system_kv"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
