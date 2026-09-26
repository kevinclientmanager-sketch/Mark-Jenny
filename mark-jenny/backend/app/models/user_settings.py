from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.sql import func

from app.db.base import Base


class UserSettings(Base):
    """Real per-user settings.

    Replaces the previous in-process dict that lost every toggle on restart.
    Created automatically by init_db (create_all checkfirst=True), so no
    migration is required on an existing deployment.
    """

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # AI Studio
    default_model = Column(String(200))          # model_id, e.g. gpt-4o-mini
    default_provider = Column(String(50))         # ModelProvider value
    routing_strategy = Column(String(50), default="balanced")   # balanced|cost|speed|quality
    temperature = Column(Float, default=0.3)
    max_tokens = Column(Integer, default=4096)
    fast_answer = Column(Boolean, default=True)

    # Feature / behaviour toggles previously stored in memory
    prefs = Column(JSON, default=dict)
    feature_flags = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
