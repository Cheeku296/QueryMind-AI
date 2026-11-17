import logging
from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "querymind_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
)


@celery_app.task(name="tasks.sync_schema_background")
def sync_schema_background(workspace_id: str, connection_id: str):
    """Background task to discover schema and update vector embeddings."""
    logger.info(f"Starting background schema sync for connection: {connection_id}")
    from app.core.database import SessionLocal
    from app.models.connection import DatabaseConnection
    from app.services.schema_service import SchemaService
    from app.ai.rag.qdrant_manager import qdrant_manager

    db = SessionLocal()
    try:
        conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
        if not conn:
            return {"status": "error", "message": "Connection not found"}

        snapshot, snapshot_data = SchemaService.sync_and_save_snapshot(db, conn)
        qdrant_manager.index_database_schema(
            workspace_id=workspace_id,
            connection_id=connection_id,
            snapshot_data=snapshot_data,
        )
        return {"status": "success", "tables": len(snapshot_data.get("tables", []))}
    except Exception as e:
        logger.error(f"Background schema sync failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
