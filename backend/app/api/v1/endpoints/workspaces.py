import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member, require_role
from app.core.database import get_sync_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_sync_db)):
    """Lists all workspaces the current user has access to."""
    memberships = (
        db.query(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .filter(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.created_at.asc())
        .all()
    )
    result = []
    for ws, role in memberships:
        result.append(
            WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                description=ws.description,
                created_by=ws.created_by,
                created_at=ws.created_at,
                role=role.value,
            )
        )
    return result


@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    ws_in: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Creates a new workspace with the creator as ADMIN."""
    ws = Workspace(
        name=ws_in.name.strip(),
        description=ws_in.description.strip() if ws_in.description else None,
        created_by=current_user.id,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=current_user.id,
        role=WorkspaceRole.ADMIN,
    )
    db.add(member)
    db.commit()

    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        created_by=ws.created_by,
        created_at=ws.created_at,
        role="ADMIN",
    )


@router.get("/{workspace_id}")
def get_workspace_details(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns workspace details and member list."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    members = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )

    member_list = [
        {
            "id": str(m.id),
            "user_id": str(u.id),
            "name": u.name,
            "email": u.email,
            "role": m.role.value,
            "joined_at": m.created_at,
        }
        for m, u in members
    ]

    return {
        "id": str(ws.id),
        "name": ws.name,
        "description": ws.description,
        "created_at": ws.created_at,
        "current_user_role": member.role.value,
        "members": member_list,
    }


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    ws_in: WorkspaceUpdate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Updates workspace settings (ADMIN only)."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    if ws_in.name is not None:
        ws.name = ws_in.name.strip()
    if ws_in.description is not None:
        ws.description = ws_in.description.strip()

    db.commit()
    db.refresh(ws)

    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        created_by=ws.created_by,
        created_at=ws.created_at,
        role=member.role.value,
    )


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Deletes workspace (ADMIN only)."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    db.delete(ws)
    db.commit()
    return {"message": "Workspace deleted successfully."}


@router.post("/{workspace_id}/members")
def add_workspace_member(
    workspace_id: uuid.UUID,
    req: WorkspaceMemberAdd,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Adds an existing user to workspace by email (ADMIN only)."""
    target_user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not registered.")

    existing_member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id,
        )
        .first()
    )
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member of this workspace.")

    new_member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=target_user.id,
        role=req.role,
    )
    db.add(new_member)
    db.commit()

    return {"message": f"Added {target_user.email} as {req.role.value} to workspace."}

