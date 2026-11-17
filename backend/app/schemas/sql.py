import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SQLGenerateRequest(BaseModel):
    connection_id: uuid.UUID
    question: str


class SQLValidateRequest(BaseModel):
    sql: str
    connection_id: Optional[uuid.UUID] = None


class SQLExecuteRequest(BaseModel):
    connection_id: uuid.UUID
    sql: str
    conversation_id: Optional[uuid.UUID] = None
    original_question: Optional[str] = None


class SQLExplainRequest(BaseModel):
    connection_id: uuid.UUID
    sql: str


class SQLFormatRequest(BaseModel):
    sql: str
    dialect: str = "postgres"


class SavedQueryCreate(BaseModel):
    connection_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    sql: str
    tags: List[str] = []


class SavedQueryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sql: Optional[str] = None
    tags: Optional[List[str]] = None


class SavedQueryResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    sql: str
    tags: List[str]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True
