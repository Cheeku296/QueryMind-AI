import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class GlossaryCreate(BaseModel):
    connection_id: Optional[uuid.UUID] = None
    term: str
    definition: str
    associated_tables: List[str] = []
    associated_columns: List[str] = []
    example_sql: Optional[str] = None


class GlossaryUpdate(BaseModel):
    term: Optional[str] = None
    definition: Optional[str] = None
    associated_tables: Optional[List[str]] = None
    associated_columns: Optional[List[str]] = None
    example_sql: Optional[str] = None


class GlossaryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    term: str
    definition: str
    associated_tables: List[str]
    associated_columns: List[str]
    example_sql: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

