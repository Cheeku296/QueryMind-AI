from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_sync_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, db: Session = Depends(get_sync_db)):
    """Registers a new user and creates their primary workspace."""
    existing = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # 1. Create user
    user = User(
        name=user_in.name.strip(),
        email=user_in.email.lower().strip(),
        password_hash=hash_password(user_in.password),
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Create default workspace
    workspace = Workspace(
        name=f"{user.name}'s Workspace",
        description="Default personal workspace for database intelligence.",
        created_by=user.id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # 3. Add user as ADMIN
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.ADMIN,
    )
    db.add(member)
    db.commit()

    # 4. Generate JWT tokens
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "name": user.name, "workspace_id": str(workspace.id)},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "role": "ADMIN",
        },
    }


@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_sync_db)):
    """Authenticates user and returns JWT tokens."""
    user = db.query(User).filter(User.email == login_in.email.lower().strip()).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    # Find primary workspace
    member = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.created_at.asc())
        .first()
    )
    ws_id = str(member.workspace_id) if member else None
    role = member.role.value if member else "VIEWER"

    ws_name = ""
    if member:
        ws = db.query(Workspace).filter(Workspace.id == member.workspace_id).first()
        ws_name = ws.name if ws else ""

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "name": user.name, "workspace_id": ws_id},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "workspace_id": ws_id,
            "workspace_name": ws_name,
            "role": role,
        },
    }


@router.post("/refresh")
def refresh_token_endpoint(refresh_token: str, db: Session = Depends(get_sync_db)):
    """Rotates refresh token and returns a new access token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found.")

    new_access = create_access_token(subject=str(user.id), extra_claims={"email": user.email, "name": user.name})
    new_refresh = create_refresh_token(subject=str(user.id))

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_sync_db)):
    """Returns profile and workspace memberships for the authenticated user."""
    memberships = (
        db.query(WorkspaceMember, Workspace)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .filter(WorkspaceMember.user_id == current_user.id)
        .all()
    )

    workspaces = []
    for m, ws in memberships:
        workspaces.append({
            "id": str(ws.id),
            "name": ws.name,
            "description": ws.description,
            "role": m.role.value,
        })

    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "status": current_user.status,
        "created_at": current_user.created_at,
        "workspaces": workspaces,
    }


@router.post("/logout")
def logout():
    """Client logout confirmation."""
    return {"message": "Logged out successfully."}


@router.post("/forgot-password")
def forgot_password(req: PasswordResetRequest, db: Session = Depends(get_sync_db)):
    """Generates password reset token if account exists."""
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if user:
        reset_token = create_access_token(
            subject=str(user.id),
            extra_claims={"purpose": "password_reset"},
            expires_delta=timedelta(minutes=15),
        )
        return {
            "message": "Password reset token generated. In production this is emailed.",
            "reset_token": reset_token,
        }
    return {"message": "If an account with that email exists, password reset instructions have been sent."}


@router.post("/reset-password")
def reset_password(req: PasswordResetConfirm, db: Session = Depends(get_sync_db)):
    """Resets user password with valid token."""
    payload = decode_token(req.token)
    if not payload or payload.get("purpose") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Password updated successfully."}
