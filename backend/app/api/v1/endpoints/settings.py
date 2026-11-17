import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.ai.provider import ai_provider
from app.ai.rag.qdrant_manager import qdrant_manager
from app.core.config import settings
from app.core.database import get_sync_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_sync_db)):
    """Comprehensive health check across database, Redis, Qdrant and AI provider."""
    # 1. Postgres
    db_ok = False
    try:
        db.execute(text("SELECT 1;"))
        db_ok = True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")

    # 2. Qdrant
    qdrant_info = qdrant_manager.get_stats()
    qdrant_ok = "error" not in qdrant_info

    # 3. Gemini / LLM Provider configuration state
    gemini_configured = ai_provider.is_configured()

    return {
        "status": "healthy" if (db_ok and qdrant_ok) else "degraded",
        "services": {
            "database": "online" if db_ok else "offline",
            "qdrant": "online" if qdrant_ok else "offline",
            "llm_provider": {
                "active_provider": settings.LLM_PROVIDER,
                "model": settings.GEMINI_MODEL,
                "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
                "is_configured": gemini_configured,
                "message": "Ready" if gemini_configured else "GEMINI_API_KEY pending in backend/.env",
            },
        },
    }


@router.get("/settings")
def get_application_settings(current_user: User = Depends(get_current_user)):
    """Returns application configuration without leaking secrets."""
    return {
        "app_name": settings.APP_NAME,
        "app_env": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        "gemini_configured": ai_provider.is_configured(),
        "qdrant_url": settings.QDRANT_URL,
        "sql_max_rows": settings.SQL_MAX_ROWS_RETURNED,
        "sql_query_timeout_seconds": settings.SQL_QUERY_TIMEOUT_SECONDS,
        "sql_max_corrections": settings.SQL_MAX_CORRECTION_ATTEMPTS,
    }


@router.post("/settings/test-gemini")
def test_gemini_api(current_user: User = Depends(get_current_user)):
    """Performs live connectivity test against Google Gemini API."""
    success, message, info = ai_provider.test_connectivity()
    return {
        "success": success,
        "message": message,
        "details": info,
    }
