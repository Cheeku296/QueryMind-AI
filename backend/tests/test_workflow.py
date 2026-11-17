import pytest
from app.ai.workflow import querymind_graph
from app.models.connection import DatabaseConnection
from app.core.security import encrypt_secret


def test_langgraph_pipeline_execution():
    conn = DatabaseConnection(
        name="Workflow Test Connection",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database_name="querymind_demo",
        username="postgres",
        encrypted_credentials=encrypt_secret("postgrespassword"),
    )

    state = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "connection_id": "00000000-0000-0000-0000-000000000002",
        "conversation_id": None,
        "connection_model": conn,
        "user_question": "Which five products generated the highest revenue?",
        "conversation_context": [],
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
        "execution_status": "pending",
        "node_events": [],
    }

    final_state = querymind_graph.invoke(state)
    assert final_state["execution_status"] == "completed"
    assert "products" in final_state["generated_sql"].lower()
    assert final_state["execution_result"]["success"] is True
    assert len(final_state["execution_result"]["rows"]) > 0
    assert len(final_state["node_events"]) >= 6
