import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace_member, require_role
from app.ai.rag.qdrant_manager import qdrant_manager
from app.core.database import get_sync_db
from app.models.connection import DatabaseConnection, SchemaSnapshot
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.services.schema_service import SchemaService

router = APIRouter()


def _get_connection_and_snapshot(
    connection_id: uuid.UUID,
    workspace_id: uuid.UUID,
    db: Session,
):
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.connection_id == connection_id)
        .order_by(SchemaSnapshot.schema_version.desc())
        .first()
    )
    if not snapshot:
        # Automatically trigger initial introspection
        snapshot, _ = SchemaService.sync_and_save_snapshot(db, conn)

    return conn, snapshot


@router.get("/connections/{connection_id}/schema")
def get_schema_snapshot(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns the latest schema snapshot for a database connection."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    return {
        "connection_id": str(conn.id),
        "connection_name": conn.name,
        "schema_version": snapshot.schema_version,
        "synchronized_at": snapshot.synchronized_at,
        "schema": snapshot.snapshot_data,
    }


@router.get("/connections/{connection_id}/schema/tables")
def get_tables(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns list of tables with column summaries and descriptions."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    tables = snapshot.snapshot_data.get("tables", [])
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "row_count": t.get("row_count", 0),
            "columns_count": len(t.get("columns", [])),
            "primary_key": t.get("primary_key", []),
            "foreign_keys_count": len(t.get("foreign_keys", [])),
        }
        for t in tables
    ]


@router.get("/connections/{connection_id}/schema/tables/{table_name}")
def get_table_details(
    connection_id: uuid.UUID,
    table_name: str,
    preview: bool = Query(True, description="Whether to include safe row preview"),
    preview_limit: int = Query(10, ge=1, le=50),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns comprehensive columns, constraints and live data preview for a table."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    tables = snapshot.snapshot_data.get("tables", [])
    target = next((t for t in tables if t["name"].lower() == table_name.lower()), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in schema.")

    response_data = dict(target)
    if preview:
        try:
            preview_res = SchemaService.get_table_preview(conn, target["name"], limit=preview_limit)
            response_data["preview"] = preview_res
        except Exception as e:
            response_data["preview"] = {"error": f"Preview unavailable: {str(e)}"}

    return response_data


@router.get("/connections/{connection_id}/schema/relationships")
def get_relationships(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns foreign key relationships across all tables."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    return snapshot.snapshot_data.get("relationships", [])


@router.get("/connections/{connection_id}/schema/er")
def get_er_diagram(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns ER diagram nodes and edges formatted for React Flow."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    er_data = SchemaService.generate_er_diagram_data(snapshot.snapshot_data)
    return er_data


@router.post("/connections/{connection_id}/schema/index")
def index_schema_vectors(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Manually re-indexes the schema into Qdrant."""
    conn, snapshot = _get_connection_and_snapshot(connection_id, member.workspace_id, db)
    count = qdrant_manager.index_database_schema(
        workspace_id=str(member.workspace_id),
        connection_id=str(conn.id),
        snapshot_data=snapshot.snapshot_data,
    )
    return {
        "success": True,
        "message": f"Successfully indexed {count} schema documents in Qdrant.",
        "documents_indexed": count,
    }

