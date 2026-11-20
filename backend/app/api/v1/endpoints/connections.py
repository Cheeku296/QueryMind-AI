import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace_member, require_role
from app.ai.rag.qdrant_manager import qdrant_manager
from app.core.database import get_sync_db
from app.core.security import decrypt_secret, encrypt_secret
from app.models.connection import DatabaseConnection, SchemaSnapshot
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionUpdate,
)
from app.services.connection_service import ConnectionService
from app.services.schema_service import SchemaService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/test")
def test_connection_params(req: ConnectionTestRequest):
    """Tests connection parameters without saving."""
    success, message, server_info = ConnectionService.test_connection_params(
        database_type=req.database_type,
        host=req.host,
        port=req.port,
        database_name=req.database_name,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"success": True, "message": message, "server_info": server_info}


@router.get("", response_model=List[ConnectionResponse])
def list_connections(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Lists all database connections for the current workspace."""
    conns = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.workspace_id == member.workspace_id)
        .order_by(DatabaseConnection.created_at.desc())
        .all()
    )
    return conns


@router.post("", response_model=ConnectionResponse)
def create_connection(
    req: ConnectionCreate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Tests, persists, and automatically introspects a new database connection."""
    # 1. Test connection
    success, message, _ = ConnectionService.test_connection_params(
        database_type=req.database_type,
        host=req.host,
        port=req.port,
        database_name=req.database_name,
        username=req.username,
        password=req.password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection verification failed: {message}",
        )

    # 2. Persist connection with encrypted credentials
    conn = ConnectionService.create_connection(
        db=db,
        workspace_id=member.workspace_id,
        name=req.name.strip(),
        database_type=req.database_type,
        host=req.host.strip(),
        port=req.port,
        database_name=req.database_name.strip(),
        username=req.username.strip(),
        password=req.password,
        ssl_configuration=req.ssl_configuration,
    )

    # 3. Synchronize schema & index in Qdrant
    try:
        snapshot, snapshot_data = SchemaService.sync_and_save_snapshot(db, conn)
        qdrant_manager.index_database_schema(
            workspace_id=str(member.workspace_id),
            connection_id=str(conn.id),
            snapshot_data=snapshot_data,
        )
    except Exception as e:
        logger.warning(f"Initial schema synchronization failed: {e}")
        conn.status = "sync_required"
        db.commit()

    return conn


@router.get("/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves connection details (credentials are never exposed)."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")
    return conn


@router.patch("/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: uuid.UUID,
    req: ConnectionUpdate,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Updates database connection details (ADMIN only)."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    if req.name is not None:
        conn.name = req.name.strip()
    if req.host is not None:
        conn.host = req.host.strip()
    if req.port is not None:
        conn.port = req.port
    if req.database_name is not None:
        conn.database_name = req.database_name.strip()
    if req.username is not None:
        conn.username = req.username.strip()
    if req.password is not None and req.password.strip():
        conn.encrypted_credentials = encrypt_secret(req.password.strip())
    if req.ssl_configuration is not None:
        conn.ssl_configuration = req.ssl_configuration

    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/{connection_id}")
def delete_connection(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN])),
    db: Session = Depends(get_sync_db),
):
    """Deletes database connection and removes its indexed vectors from Qdrant."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    # Remove vector index
    try:
        qdrant_manager.delete_connection_index(
            workspace_id=str(member.workspace_id),
            connection_id=str(conn.id),
        )
    except Exception as e:
        logger.warning(f"Error deleting connection index from Qdrant: {e}")

    db.delete(conn)
    db.commit()
    return {"message": "Database connection and associated vector indices deleted."}


@router.post("/{connection_id}/sync")
def sync_connection_schema(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Performs full schema discovery and re-indexes into Qdrant."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    snapshot, snapshot_data = SchemaService.sync_and_save_snapshot(db, conn)
    indexed_count = qdrant_manager.index_database_schema(
        workspace_id=str(member.workspace_id),
        connection_id=str(conn.id),
        snapshot_data=snapshot_data,
    )

    return {
        "success": True,
        "message": f"Schema synchronized. {snapshot_data.get('total_tables', 0)} tables found. Indexed {indexed_count} schema vectors.",
        "schema_version": snapshot.schema_version,
        "tables_count": snapshot_data.get("total_tables", 0),
    }


@router.get("/{connection_id}/status")
def test_connection_status(
    connection_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Tests live connectivity to the saved database connection."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    success, message, server_info = ConnectionService.test_existing_connection(conn)
    conn.status = "connected" if success else "failed"
    db.commit()

    return {
        "status": conn.status,
        "connected": success,
        "message": message,
        "server_info": server_info,
    }

