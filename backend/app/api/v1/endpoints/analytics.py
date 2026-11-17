import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace_member
from app.core.database import get_sync_db
from app.models.agent_run import AgentRun
from app.models.connection import DatabaseConnection, SchemaSnapshot
from app.models.conversation import Conversation
from app.models.query import Query as QueryModel, SavedQuery
from app.models.report import Report
from app.models.workspace import WorkspaceMember

router = APIRouter()


@router.get("/overview")
def get_analytics_overview(
    days: int = Query(30, ge=1, le=365),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Calculates comprehensive dashboard and analytics overview metrics from persisted data."""
    ws_id = member.workspace_id
    since_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Database connections
    db_count = db.query(DatabaseConnection).filter(DatabaseConnection.workspace_id == ws_id).count()

    # Table count from latest snapshots
    snapshots = (
        db.query(SchemaSnapshot)
        .join(DatabaseConnection, DatabaseConnection.id == SchemaSnapshot.connection_id)
        .filter(DatabaseConnection.workspace_id == ws_id)
        .all()
    )
    total_tables = 0
    seen_conns = set()
    for s in snapshots:
        if s.connection_id not in seen_conns:
            seen_conns.add(s.connection_id)
            total_tables += len(s.snapshot_data.get("tables", []))

    # Query metrics
    queries_q = db.query(QueryModel).filter(
        QueryModel.workspace_id == ws_id,
        QueryModel.created_at >= since_date,
    )
    total_queries = queries_q.count()
    successful_queries = queries_q.filter(QueryModel.status == "success").count()
    failed_queries = queries_q.filter(QueryModel.status == "failed").count()

    avg_duration = (
        db.query(func.avg(QueryModel.execution_time_ms))
        .filter(QueryModel.workspace_id == ws_id, QueryModel.created_at >= since_date)
        .scalar()
        or 0
    )

    # Conversations & Reports & Saved Queries
    conversations_count = db.query(Conversation).filter(Conversation.workspace_id == ws_id).count()
    saved_queries_count = db.query(SavedQuery).filter(SavedQuery.workspace_id == ws_id).count()
    reports_count = db.query(Report).filter(Report.workspace_id == ws_id).count()

    return {
        "connected_databases": db_count,
        "available_tables": total_tables,
        "total_queries": total_queries,
        "successful_queries": successful_queries,
        "failed_queries": failed_queries,
        "success_rate": round((successful_queries / total_queries * 100), 1) if total_queries > 0 else 100.0,
        "average_query_duration_ms": round(float(avg_duration), 1),
        "total_conversations": conversations_count,
        "total_saved_queries": saved_queries_count,
        "total_reports": reports_count,
        "period_days": days,
    }


@router.get("/query-trends")
def get_query_trends(
    days: int = Query(7, ge=1, le=90),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns query volume and latency trends over time."""
    ws_id = member.workspace_id
    since_date = datetime.now(timezone.utc) - timedelta(days=days)

    queries = (
        db.query(
            func.date_trunc("day", QueryModel.created_at).label("day"),
            func.count(QueryModel.id).label("count"),
            func.avg(QueryModel.execution_time_ms).label("avg_duration"),
        )
        .filter(QueryModel.workspace_id == ws_id, QueryModel.created_at >= since_date)
        .group_by("day")
        .order_by("day")
        .all()
    )

    trends = [
        {
            "date": row.day.strftime("%Y-%m-%d") if row.day else "",
            "queries": row.count,
            "avg_duration_ms": round(float(row.avg_duration or 0), 1),
        }
        for row in queries
    ]

    return {"trends": trends}


@router.get("/database-usage")
def get_database_usage(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns breakdown of query volume per database connection."""
    ws_id = member.workspace_id
    usage = (
        db.query(
            DatabaseConnection.name,
            func.count(QueryModel.id).label("queries_count"),
        )
        .join(QueryModel, QueryModel.connection_id == DatabaseConnection.id)
        .filter(DatabaseConnection.workspace_id == ws_id)
        .group_by(DatabaseConnection.name)
        .order_by(func.count(QueryModel.id).desc())
        .all()
    )

    return [{"database": name, "query_count": cnt} for name, cnt in usage]


@router.get("/agent-performance")
def get_agent_performance(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns multi-agent workflow performance metrics."""
    ws_id = member.workspace_id
    runs = db.query(AgentRun).filter(AgentRun.workspace_id == ws_id).all()

    total_runs = len(runs)
    completed_runs = sum(1 for r in runs if r.status == "completed")
    failed_runs = sum(1 for r in runs if r.status == "failed")

    return {
        "total_agent_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs,
        "workflow_success_rate": round((completed_runs / total_runs * 100), 1) if total_runs > 0 else 100.0,
    }
