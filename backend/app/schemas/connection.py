import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ConnectionTestRequest(BaseModel):
    database_type: str = "postgresql"
    host: str
    port: int = 5432
    database_name: str
    username: str
    password: str
    ssl_mode: Optional[str] = None


class ConnectionCreate(BaseModel):
    name: str
    database_type: str = "postgresql"
    host: str
    port: int = 5432
    database_name: str
    username: str
    password: str
    ssl_configuration: Optional[Dict[str, Any]] = None


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_configuration: Optional[Dict[str, Any]] = None


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    database_type: str
    host: str
    port: int
    database_name: str
    username: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
