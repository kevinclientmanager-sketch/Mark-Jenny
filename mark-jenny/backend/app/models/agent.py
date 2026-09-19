from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ModelProvider(str, enum.Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OLLAMA = "OLLAMA"
    AZURE = "AZURE"
    CUSTOM = "CUSTOM"


class ModelCapability(str, enum.Enum):
    CHAT = "CHAT"
    REASONING = "REASONING"
    CODING = "CODING"
    VISION = "VISION"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    EMBEDDINGS = "EMBEDDINGS"


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    provider = Column(SQLEnum(ModelProvider), nullable=False)
    model_id = Column(String(255), nullable=False)  # e.g., "gpt-4", "claude-3-opus"
    capabilities = Column(JSON)  # List of ModelCapability
    context_window = Column(Integer)
    max_output_tokens = Column(Integer)
    cost_per_1k_input = Column(Integer)  # In cents
    cost_per_1k_output = Column(Integer)  # In cents
    is_local = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    config = Column(JSON)  # Additional provider-specific config
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ModelProviderConfig(Base):
    __tablename__ = "model_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(SQLEnum(ModelProvider), nullable=False)
    api_key_encrypted = Column(Text)
    base_url = Column(String(500))
    config = Column(JSON)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


class AgentType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    RESEARCH = "RESEARCH"
    CODING = "CODING"
    BROWSER = "BROWSER"
    DOCUMENT = "DOCUMENT"
    SPREADSHEET = "SPREADSHEET"
    DESIGN = "DESIGN"
    DATA = "DATA"
    SECURITY = "SECURITY"
    QA = "QA"
    SUPERVISOR = "SUPERVISOR"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(AgentType), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="SET NULL"))
    available_tools = Column(JSON)
    available_skills = Column(JSON)
    config = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    model = relationship("Model")