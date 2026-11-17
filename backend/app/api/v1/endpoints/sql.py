import logging
import uuid
import sqlglot
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member, require_role
from app.ai.agents.schemas import SQLGenerationOutput
from app.ai.provider import ai_provider
from app.ai.rag.qdrant_manager import qdrant_manager
from app.ai.sql_safety.executor import SQLExecutor
from app.ai.sql_safety.validator import SQLValidator
from app.core.config import settings
from app.core.database import get_sync_db
from app.models.connection import DatabaseConnection
from app.models.query import Query as QueryModel
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.sql import (
    SQLExecuteRequest,
    SQLExplainRequest,
    SQLFormatRequest,
    SQLGenerateRequest,
    SQLValidateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
def generate_sql(
    req: SQLGenerateRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Generates schema-aware PostgreSQL SQL from natural language."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == req.connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    # 1. Retrieve relevant schema from Qdrant
    retrieved = qdrant_manager.retrieve_relevant_schema(
        workspace_id=str(member.workspace_id),
        connection_id=str(conn.id),
        query=req.question,
        limit=6,
    )
    context_str = retrieved.get("compact_context", "")

    # 2. Invoke Gemini if configured
    if ai_provider.is_configured():
        prompt = f"""Generate a valid, read-only PostgreSQL query.
SCHEMA:
{context_str}

QUESTION:
{req.question}
"""
        try:
            res: SQLGenerationOutput = ai_provider.generate_structured(
                prompt=prompt,
                schema_class=SQLGenerationOutput,
                system_instruction="You are a senior PostgreSQL data architect.",
            )
            return {
                "sql": res.sql.strip().rstrip(";"),
                "explanation": res.explanation,
                "tables_used": res.tables_used,
                "assumptions": res.assumptions,
                "requires_clarification": res.requires_clarification,
            }
        except Exception as e:
            logger.warning(f"Gemini SQL generation error: {e}")
            raise HTTPException(status_code=500, detail=f"LLM SQL generation failed: {str(e)}")

    # Heuristic fallback if Gemini API key is not yet configured
    return {
        "sql": "SELECT p.name, p.category, p.price FROM products p ORDER BY p.price DESC LIMIT 10",
        "explanation": "Default demonstration query. Please configure GEMINI_API_KEY in backend/.env for AI SQL generation.",
        "tables_used": ["products"],
        "assumptions": ["Using default product table preview"],
        "requires_clarification": False,
    }


@router.post("/validate")
def validate_sql(
    req: SQLValidateRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Deterministically validates SQL syntax, dialect and security policies using SQLGlot."""
    result = SQLValidator.validate_sql(
        sql=req.sql,
        dialect="postgres",
        max_rows=settings.SQL_MAX_ROWS_RETURNED,
    )
    return result.to_dict()


@router.post("/execute")
def execute_sql(
    req: SQLExecuteRequest,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Validates and executes SQL query safely with read-only transaction and timeout."""
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == req.connection_id,
            DatabaseConnection.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    # 1. Deterministic SQLGlot validation
    val_res = SQLValidator.validate_sql(
        sql=req.sql,
        dialect="postgres",
        max_rows=settings.SQL_MAX_ROWS_RETURNED,
    )
    if not val_res.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security/Syntax Validation Failed: {'; '.join(val_res.errors)}",
        )

    # 2. Execute validated query
    exec_res = SQLExecutor.execute_query(
        conn=conn,
        validated_sql=val_res.sanitized_sql,
        timeout_seconds=settings.SQL_QUERY_TIMEOUT_SECONDS,
        max_rows=settings.SQL_MAX_ROWS_RETURNED,
    )

    # 3. Log query execution in history
    query_log = QueryModel(
        workspace_id=member.workspace_id,
        user_id=current_user.id,
        connection_id=conn.id,
        conversation_id=req.conversation_id,
        original_question=req.original_question,
        generated_sql=req.sql,
        executed_sql=val_res.sanitized_sql,
        status="success" if exec_res.success else "failed",
        execution_time_ms=exec_res.execution_time_ms,
        row_count=exec_res.row_count,
        error_message=exec_res.error,
    )
    db.add(query_log)
    db.commit()

    return {
        **exec_res.to_dict(),
        "warnings": val_res.warnings,
        "query_id": str(query_log.id),
    }


@router.post("/explain")
def explain_sql(
    req: SQLExplainRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Explains a SQL query in plain English."""
    val_res = SQLValidator.validate_sql(req.sql, dialect="postgres")
    if not val_res.is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid SQL: {'; '.join(val_res.errors)}")

    if ai_provider.is_configured():
        prompt = f"""Explain this PostgreSQL query in plain English for technical and business users.
Break down what each JOIN, WHERE condition, and aggregation computes:

SQL:
{req.sql}
"""
        try:
            explanation = ai_provider.generate_text(prompt=prompt)
            return {"sql": req.sql, "explanation": explanation}
        except Exception as e:
            logger.warning(f"Explain query LLM error: {e}")

    return {
        "sql": req.sql,
        "explanation": f"This query accesses tables: {', '.join(val_res.tables_used)}. It selects and filters rows in read-only mode.",
    }


@router.post("/format")
def format_sql(req: SQLFormatRequest):
    """Formats SQL syntax cleanly using SQLGlot."""
    try:
        formatted = sqlglot.transpile(req.sql, read=req.dialect, write=req.dialect, pretty=True)
        return {"formatted_sql": formatted[0] if formatted else req.sql}
    except Exception as e:
        return {"formatted_sql": req.sql, "error": str(e)}
