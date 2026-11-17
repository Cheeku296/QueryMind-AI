import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace_member
from app.ai.workflow import querymind_graph
from app.core.database import get_sync_db
from app.models.agent_run import AgentRun
from app.models.connection import DatabaseConnection
from app.models.conversation import Conversation, Message
from app.models.query import Query as QueryModel
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.chat import ChatRequest, ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for active streaming events (run_id -> list of events)
active_stream_events: Dict[str, List[Dict]] = {}


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    connection_id: Optional[uuid.UUID] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Lists conversations for the user in the current workspace."""
    q = (
        db.query(Conversation)
        .filter(
            Conversation.workspace_id == member.workspace_id,
            Conversation.user_id == current_user.id,
        )
    )
    if connection_id:
        q = q.filter(Conversation.connection_id == connection_id)
    return q.order_by(Conversation.updated_at.desc()).all()


@router.post("")
def send_chat_message(
    req: ChatRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Executes multi-agent workflow for a question and persists conversation state."""
    # 1. Verify connection
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

    # 2. Get or create conversation
    if req.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == req.conversation_id,
                Conversation.workspace_id == member.workspace_id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        # Generate initial title from first 40 chars of question
        title = req.question[:45].strip() + ("..." if len(req.question) > 45 else "")
        conv = Conversation(
            workspace_id=member.workspace_id,
            user_id=current_user.id,
            connection_id=conn.id,
            title=title,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 3. Save User message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.question.strip(),
    )
    db.add(user_msg)
    db.commit()

    # 4. Fetch recent conversation context for follow-ups
    prev_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .limit(6)
        .all()
    )
    context_list = [{"role": m.role, "content": m.content} for m in prev_messages]

    # 5. Initialize LangGraph multi-agent execution state
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    active_stream_events[run_id] = []

    initial_state = {
        "user_id": str(current_user.id),
        "workspace_id": str(member.workspace_id),
        "connection_id": str(conn.id),
        "conversation_id": str(conv.id),
        "connection_model": conn,
        "user_question": req.question.strip(),
        "conversation_context": context_list,
        "intent": "",
        "retrieved_schema": {},
        "retrieved_glossary": [],
        "generated_sql": "",
        "sql_explanation": "",
        "validation_result": {},
        "execution_result": {},
        "execution_error": None,
        "correction_attempts": 0,
        "analysis": {},
        "chart_specification": {},
        "clarification_required": False,
        "clarification_question": None,
        "final_response": "",
        "execution_status": "running",
        "node_events": [],
    }

    # Record Agent Run in database
    agent_run = AgentRun(
        workspace_id=member.workspace_id,
        user_id=current_user.id,
        conversation_id=conv.id,
        graph_execution_id=run_id,
        status="running",
        current_node="supervisor",
        execution_metadata={"question": req.question},
    )
    db.add(agent_run)
    db.commit()

    # Execute LangGraph pipeline
    try:
        final_state = querymind_graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"LangGraph execution exception: {e}")
        agent_run.status = "failed"
        agent_run.execution_metadata = {"error": str(e)}
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")

    # Update Agent Run
    agent_run.status = final_state.get("execution_status", "completed")
    agent_run.current_node = "end"
    agent_run.execution_metadata = {
        "events_count": len(final_state.get("node_events", [])),
        "sql": final_state.get("generated_sql", ""),
        "correction_attempts": final_state.get("correction_attempts", 0),
    }
    agent_run.completed_at = db.query(Conversation).filter(Conversation.id == conv.id).first().updated_at
    db.commit()

    # 6. Save Assistant response message
    response_content = final_state.get("final_response", "")
    if final_state.get("clarification_required") and final_state.get("clarification_question"):
        response_content = f"Clarification needed: {final_state['clarification_question']}"

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=response_content,
        generated_sql=final_state.get("generated_sql"),
        execution_status=final_state.get("execution_status"),
        message_metadata={
            "analysis": final_state.get("analysis", {}),
            "chart": final_state.get("chart_specification", {}),
            "execution_result": final_state.get("execution_result", {}),
            "validation_result": final_state.get("validation_result", {}),
            "node_events": final_state.get("node_events", []),
            "run_id": run_id,
        },
    )
    db.add(assistant_msg)

    # 7. Log query execution in queries table if SQL was run
    exec_res = final_state.get("execution_result", {})
    if exec_res and final_state.get("generated_sql"):
        query_log = QueryModel(
            workspace_id=member.workspace_id,
            user_id=current_user.id,
            connection_id=conn.id,
            conversation_id=conv.id,
            original_question=req.question,
            generated_sql=final_state.get("generated_sql"),
            executed_sql=exec_res.get("executed_sql") or final_state.get("generated_sql", ""),
            status="success" if exec_res.get("success") else "failed",
            execution_time_ms=exec_res.get("execution_time_ms", 0),
            row_count=exec_res.get("row_count", 0),
            error_message=exec_res.get("error"),
        )
        db.add(query_log)

    db.commit()
    db.refresh(conv)

    return {
        "conversation_id": str(conv.id),
        "run_id": run_id,
        "message": {
            "id": str(assistant_msg.id),
            "role": "assistant",
            "content": assistant_msg.content,
            "generated_sql": assistant_msg.generated_sql,
            "execution_status": assistant_msg.execution_status,
            "created_at": assistant_msg.created_at,
            "analysis": final_state.get("analysis", {}),
            "chart": final_state.get("chart_specification", {}),
            "execution_result": final_state.get("execution_result", {}),
            "validation_result": final_state.get("validation_result", {}),
            "node_events": final_state.get("node_events", []),
        },
    }


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Returns conversation and all messages."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    msg_list = []
    for m in messages:
        meta = m.message_metadata or {}
        msg_list.append({
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "generated_sql": m.generated_sql,
            "execution_status": m.execution_status,
            "created_at": m.created_at,
            "analysis": meta.get("analysis", {}),
            "chart": meta.get("chart", {}),
            "execution_result": meta.get("execution_result", {}),
            "validation_result": meta.get("validation_result", {}),
            "node_events": meta.get("node_events", []),
        })

    return {
        "id": str(conv.id),
        "title": conv.title,
        "connection_id": str(conv.connection_id) if conv.connection_id else None,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": msg_list,
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: uuid.UUID,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_sync_db),
):
    """Deletes conversation and its messages."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.workspace_id == member.workspace_id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted."}


@router.get("/{conversation_id}/stream/{run_id}")
async def stream_agent_execution(
    conversation_id: uuid.UUID,
    run_id: str,
):
    """Streams real-time Server-Sent Events (SSE) for multi-agent workflow progress."""
    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'run_id': run_id, 'status': 'connected'})}\n\n"
        events_sent = 0
        for _ in range(30):  # Stream poll loop
            if run_id in active_stream_events:
                events = active_stream_events[run_id]
                while events_sent < len(events):
                    ev = events[events_sent]
                    yield f"event: node_progress\ndata: {json.dumps(ev)}\n\n"
                    events_sent += 1
            await asyncio.sleep(0.5)

        yield f"event: complete\ndata: {json.dumps({'run_id': run_id, 'status': 'finished'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
