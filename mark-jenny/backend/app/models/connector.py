from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ConnectorType(str, enum.Enum):
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    GMAIL = "GMAIL"
    GITHUB = "GITHUB"
    SLACK = "SLACK"
    NOTION = "NOTION"
    OUTLOOK = "OUTLOOK"
    OUTLOOK_CALENDAR = "OUTLOOK_CALENDAR"
    OUTLOOK_MAIL = "OUTLOOK_MAIL"
    SHOPIFY = "SHOPIFY"
    APIFY = "APIFY"
    INSTAGRAM = "INSTAGRAM"
    META_ADS = "META_ADS"
    CUSTOM_API = "CUSTOM_API"
    MCP = "MCP"


class ConnectorStatus(str, enum.Enum):
    NOT_CONNECTED = "NOT_CONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class AuthType(str, enum.Enum):
    OAUTH2 = "OAUTH2"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    BASIC_AUTH = "BASIC_AUTH"
    NONE = "NONE"


class Connector(Base):
    __tablename__ = "connectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    type = Column(SQLEnum(ConnectorType), nullable=False)
    description = Column(Text)
    icon = Column(String(100))
    config_schema = Column(JSON)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    credentials = relationship("ConnectorCredential", back_populates="connector")


class ConnectorCredential(Base):
    __tablename__ = "connector_credentials"

    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    
    auth_type = Column(SQLEnum(AuthType), nullable=False)
    encrypted_credentials = Column(Text, nullable=False)  # Encrypted JSON
    status = Column(SQLEnum(ConnectorStatus), default=ConnectorStatus.NOT_CONNECTED, nullable=False)
    error_message = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    last_sync_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    connector = relationship("Connector", back_populates="credentials")
    user = relationship("User")
    project = relationship("Project")