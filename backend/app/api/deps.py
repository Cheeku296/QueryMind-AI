import uuid
from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_sync_db
from app.core.security import decode_token
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_sync_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject invalid.",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    return user


def get_current_workspace_member(
    current_user: User = Depends(get_current_user),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    db: Session = Depends(get_sync_db),
) -> WorkspaceMember:
    if not x_workspace_id:
        # Fall back to user's first workspace
        member = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.user_id == current_user.id)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no workspace memberships. Please create a workspace first.",
            )
        return member

    try:
        ws_uuid = uuid.UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid workspace ID format.")

    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == ws_uuid,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an authorized member of this workspace.",
        )
    return member


def require_role(allowed_roles: list[WorkspaceRole]):
    def role_checker(member: WorkspaceMember = Depends(get_current_workspace_member)) -> WorkspaceMember:
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required role: {[r.value for r in allowed_roles]}",
            )
        return member
    return role_checker
