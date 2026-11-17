import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BusinessGlossary(Base):
    __tablename__ = "business_glossary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("database_connections.id", ondelete="SET NULL"), nullable=True)
    term = Column(String(255), nullable=False)
    definition = Column(Text, nullable=False)
    associated_tables = Column(ARRAY(String), default=list, nullable=False)
    associated_columns = Column(ARRAY(String), default=list, nullable=False)
    example_sql = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    workspace = relationship("Workspace", back_populates="glossary_terms")
    connection = relationship("DatabaseConnection", back_populates="glossary_terms")
