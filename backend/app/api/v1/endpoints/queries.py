import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member, require_role
from app.core.database import get_sync_db
from app.models.connection import DatabaseConnection
from app.models.query import Query as QueryModel, SavedQuery
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.sql import SavedQueryCreate, SavedQueryResponse

router = APIRouter()


@router.get("/history")
def get_query_history(
    connection_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves paginated query execution history for the workspace."""
    q = (
        db.query(QueryModel, DatabaseConnection.name.label("connection_name"), User.name.label("user_name"))
        .join(DatabaseConnection, DatabaseConnection.id == QueryModel.connection_id)
        .join(User, User.id == QueryModel.user_id)
        .filter(QueryModel.workspace_id == member.workspace_id)
    )

    if connection_id:
        q = q.filter(QueryModel.connection_id == connection_id)
    if status_filter:
        q = q.filter(QueryModel.status == status_filter.lower())
    if search:
        search_fmt = f"%{search.strip()}%"
        q = q.filter(
            QueryModel.executed_sql.ilike(search_fmt) | QueryModel.original_question.ilike(search_fmt)
        )

    total_count = q.count()
    items = q.order_by(QueryModel.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for q_item, conn_name, u_name in items:
        result.append({
            "id": str(q_item.id),
            "connection_id": str(q_item.connection_id),
            "connection_name": conn_name,
            "user_id": str(q_item.user_id),
            "user_name": u_name,
            "conversation_id": str(q_item.conversation_id) if q_item.conversation_id else None,
            "original_question": q_item.original_question,
            "generated_sql": q_item.generated_sql,
            "executed_sql": q_item.executed_sql,
            "status": q_item.status,
            "execution_time_ms": q_item.execution_time_ms,
            "row_count": q_item.row_count,
            "error_message": q_item.error_message,
            "created_at": q_item.created_at,
        })

    return {"total": total_count, "items": result, "limit": limit, "offset": offset}


@router.get("/{query_id}")
def get_query_details(
    query_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves details of a single historical query execution."""
    q_item = (
        db.query(QueryModel)
        .filter(
            QueryModel.id == query_id,
            QueryModel.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not q_item:
        raise HTTPException(status_code=404, detail="Query record not found.")

    return {
        "id": str(q_item.id),
        "connection_id": str(q_item.connection_id),
        "user_id": str(q_item.user_id),
        "original_question": q_item.original_question,
        "generated_sql": q_item.generated_sql,
        "executed_sql": q_item.executed_sql,
        "status": q_item.status,
        "execution_time_ms": q_item.execution_time_ms,
        "row_count": q_item.row_count,
        "error_message": q_item.error_message,
        "created_at": q_item.created_at,
    }


@router.post("/{query_id}/save")
def save_historical_query(
    query_id: uuid.UUID,
    title: str = Query(..., description="Title for the saved query"),
    description: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Saves a past executed query into the workspace's saved queries library."""
    q_item = (
        db.query(QueryModel)
        .filter(
            QueryModel.id == query_id,
            QueryModel.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not q_item:
        raise HTTPException(status_code=404, detail="Query record not found.")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    saved = SavedQuery(
        workspace_id=member.workspace_id,
        user_id=current_user.id,
        title=title.strip(),
        description=description.strip() if description else q_item.original_question,
        sql=q_item.executed_sql,
        tags=tag_list,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return {"message": "Query saved successfully.", "saved_query_id": str(saved.id)}


@router.delete("/{query_id}")
def delete_query_history(
    query_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Deletes a historical query log entry (ADMIN only)."""
    q_item = (
        db.query(QueryModel)
        .filter(
            QueryModel.id == query_id,
            QueryModel.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not q_item:
        raise HTTPException(status_code=404, detail="Query record not found.")

    db.delete(q_item)
    db.commit()
    return {"message": "Query log entry deleted."}

