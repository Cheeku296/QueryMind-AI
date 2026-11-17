import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    database_type = Column(String(50), default="postgresql", nullable=False)  # postgresql, mysql, sqlite
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=5432, nullable=False)
    database_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    encrypted_credentials = Column(Text, nullable=False)  # Encrypted password via Fernet
    ssl_configuration = Column(JSONB, nullable=True, default=dict)
    status = Column(String(50), default="disconnected", nullable=False)  # connected, disconnected, testing, failed, sync_required
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace", back_populates="connections")
    snapshots = relationship("SchemaSnapshot", back_populates="connection", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="connection", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="connection", cascade="all, delete-orphan")
    glossary_terms = relationship("BusinessGlossary", back_populates="connection", cascade="all, delete-orphan")


class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False)
    schema_version = Column(Integer, default=1, nullable=False)
    snapshot_data = Column(JSONB, nullable=False)  # Detailed tables, columns, PKs, FKs, indexes
    synchronized_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    connection = relationship("DatabaseConnection", back_populates="snapshots")
