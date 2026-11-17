import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    role: Optional[str] = "ADMIN"

    class Config:
        from_attributes = True


class WorkspaceMemberAdd(BaseModel):
    email: str
    role: WorkspaceRole = WorkspaceRole.EDITOR


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: WorkspaceRole
    created_at: datetime

    class Config:
        from_attributes = True
