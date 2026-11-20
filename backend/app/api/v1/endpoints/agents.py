import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_workspace_member
from app.core.database import get_sync_db
from app.models.agent_run import AgentRun
from app.models.workspace import WorkspaceMember

router = APIRouter()


@router.get("/runs")
def list_agent_runs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Lists LangGraph multi-agent execution runs for the workspace."""
    q = db.query(AgentRun).filter(AgentRun.workspace_id == member.workspace_id)
    if status_filter:
        q = q.filter(AgentRun.status == status_filter)

    runs = q.order_by(AgentRun.started_at.desc()).limit(limit).all()

    return [
        {
            "id": str(r.id),
            "run_id": r.graph_execution_id,
            "conversation_id": str(r.conversation_id) if r.conversation_id else None,
            "status": r.status,
            "current_node": r.current_node,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "metadata": r.execution_metadata,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_agent_run(
    run_id: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Retrieves full details and events of an agent run."""
    run = (
        db.query(AgentRun)
        .filter(
            AgentRun.graph_execution_id == run_id,
            AgentRun.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {
        "id": str(run.id),
        "run_id": run.graph_execution_id,
        "conversation_id": str(run.conversation_id) if run.conversation_id else None,
        "status": run.status,
        "current_node": run.current_node,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "metadata": run.execution_metadata,
    }

