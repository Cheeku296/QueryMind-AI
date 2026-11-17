import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member, require_role
from app.core.database import get_sync_db
from app.models.query import SavedQuery
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.sql import SavedQueryCreate, SavedQueryResponse, SavedQueryUpdate

router = APIRouter()


@router.get("", response_model=List[SavedQueryResponse])
def list_saved_queries(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Lists saved queries in the workspace."""
    q = db.query(SavedQuery).filter(SavedQuery.workspace_id == member.workspace_id)
    if search:
        search_fmt = f"%{search.strip()}%"
        q = q.filter(SavedQuery.title.ilike(search_fmt) | SavedQuery.description.ilike(search_fmt))
    if tag:
        q = q.filter(SavedQuery.tags.contains([tag.strip()]))

    return q.order_by(SavedQuery.updated_at.desc()).all()


@router.post("", response_model=SavedQueryResponse)
def create_saved_query(
    req: SavedQueryCreate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Saves a SQL query in the library."""
    saved = SavedQuery(
        workspace_id=member.workspace_id,
        user_id=current_user.id,
        title=req.title.strip(),
        description=req.description.strip() if req.description else None,
        sql=req.sql.strip(),
        tags=req.tags,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.get("/{query_id}", response_model=SavedQueryResponse)
def get_saved_query(
    query_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves a single saved query."""
    saved = (
        db.query(SavedQuery)
        .filter(SavedQuery.id == query_id, SavedQuery.workspace_id == member.workspace_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Saved query not found.")
    return saved


@router.patch("/{query_id}", response_model=SavedQueryResponse)
def update_saved_query(
    query_id: uuid.UUID,
    req: SavedQueryUpdate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Updates a saved query."""
    saved = (
        db.query(SavedQuery)
        .filter(SavedQuery.id == query_id, SavedQuery.workspace_id == member.workspace_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Saved query not found.")

    if req.title is not None:
        saved.title = req.title.strip()
    if req.description is not None:
        saved.description = req.description.strip()
    if req.sql is not None:
        saved.sql = req.sql.strip()
    if req.tags is not None:
        saved.tags = req.tags

    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/{query_id}")
def delete_saved_query(
    query_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Deletes a saved query."""
    saved = (
        db.query(SavedQuery)
        .filter(SavedQuery.id == query_id, SavedQuery.workspace_id == member.workspace_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Saved query not found.")

    db.delete(saved)
    db.commit()
    return {"message": "Saved query deleted."}
