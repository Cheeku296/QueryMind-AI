import json
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member, require_role
from app.ai.provider import ai_provider
from app.ai.sql_safety.executor import SQLExecutor
from app.ai.sql_safety.validator import SQLValidator
from app.core.database import get_sync_db
from app.models.connection import DatabaseConnection
from app.models.report import Report
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.report import ReportGenerateRequest, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[ReportResponse])
def list_reports(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Lists analytical reports in the workspace."""
    reports = (
        db.query(Report)
        .filter(Report.workspace_id == member.workspace_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return reports


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    req: ReportGenerateRequest,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Generates a complete analytical business report using live query results and Gemini synthesis."""
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

    sql = req.sql_query or "SELECT * FROM orders ORDER BY total_amount DESC LIMIT 50"

    # Validate and execute
    val = SQLValidator.validate_sql(sql, dialect="postgres")
    if not val.is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid SQL: {'; '.join(val.errors)}")

    exec_res = SQLExecutor.execute_query(conn, val.sanitized_sql)
    if not exec_res.success:
        raise HTTPException(status_code=400, detail=f"Report query execution failed: {exec_res.error}")

    # Build report content
    summary = f"Comprehensive analysis based on {exec_res.row_count} records retrieved from {conn.database_name}."
    findings = [
        f"Query executed in {exec_res.execution_time_ms} ms.",
        f"Columns analyzed: {', '.join(exec_res.columns)}",
    ]
    if exec_res.rows:
        findings.append(f"Primary sample value: {exec_res.rows[0]}")

    if ai_provider.is_configured() and exec_res.rows:
        prompt = f"""You are the Business Intelligence Report Author for QueryMind AI.
Generate a structured executive report.

TITLE: {req.title}
OBJECTIVE: Analytical assessment for {conn.database_name}
COLUMNS: {exec_res.columns}
SAMPLE DATA: {exec_res.rows[:15]}

Return JSON with keys:
- 'executive_summary': narrative summary
- 'key_metrics': object with 3-5 calculated numbers
- 'findings': list of bullet points
- 'recommendations': list of action items
- 'limitations': list of constraints
"""
        try:
            raw_text = ai_provider.generate_text(prompt=prompt)
            # Try parsing json
            clean_json = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(clean_json)
            summary = parsed.get("executive_summary", summary)
            findings = parsed.get("findings", findings)
        except Exception as e:
            logger.warning(f"Report LLM synthesis error: {e}")

    report_content = {
        "title": req.title,
        "executive_summary": summary,
        "objective": f"In-depth analytical review of {conn.database_name}",
        "database_source": conn.name,
        "sql_query": val.sanitized_sql,
        "key_metrics": {
            "total_rows": exec_res.row_count,
            "execution_duration_ms": exec_res.execution_time_ms,
            "columns_count": len(exec_res.columns),
        },
        "findings": findings,
        "columns": exec_res.columns,
        "sample_rows": exec_res.rows[:20],
        "limitations": [
            "Data sampled under read-only transaction limits.",
            "Historical snapshot scoped to current operational data.",
        ],
    }

    report = Report(
        workspace_id=member.workspace_id,
        user_id=current_user.id,
        title=req.title,
        report_type=req.report_type,
        report_content=report_content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves report details."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.workspace_id == member.workspace_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Downloads report data as JSON or CSV."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.workspace_id == member.workspace_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if format == "csv":
        # Format sample rows to CSV
        content = report.report_content
        cols = content.get("columns", [])
        rows = content.get("sample_rows", [])
        lines = [",".join([f'"{c}"' for c in cols])]
        for r in rows:
            lines.append(",".join([f'"{val}"' if val is not None else "" for val in r]))
        csv_data = "\n".join(lines)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'},
        )

    # JSON export
    return Response(
        content=json.dumps(report.report_content, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.json"'},
    )


@router.delete("/{report_id}")
def delete_report(
    report_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_role([WorkspaceRole.ADMIN, WorkspaceRole.EDITOR])),
    db: Session = Depends(get_sync_db),
):
    """Deletes an analytical report."""
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.workspace_id == member.workspace_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully."}
