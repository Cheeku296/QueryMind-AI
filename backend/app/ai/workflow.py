import json
import logging
import time
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph import END, START, StateGraph

from app.ai.agents.schemas import (
    ResultAnalysisOutput,
    SQLCorrectionOutput,
    SQLGenerationOutput,
    SupervisorOutput,
    VisualizationOutput,
)
from app.ai.provider import ai_provider
from app.ai.rag.qdrant_manager import qdrant_manager
from app.ai.sql_safety.executor import SQLExecutor
from app.ai.sql_safety.validator import SQLValidator
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryMindAgentState(TypedDict):
    """Typed state passed through the LangGraph multi-agent pipeline."""
    user_id: str
    workspace_id: str
    connection_id: str
    conversation_id: Optional[str]
    connection_model: Any  # DatabaseConnection instance
    user_question: str
    conversation_context: List[Dict[str, str]]
    intent: str
    retrieved_schema: Dict[str, Any]
    retrieved_glossary: List[Dict[str, Any]]
    generated_sql: str
    sql_explanation: str
    validation_result: Dict[str, Any]
    execution_result: Dict[str, Any]
    execution_error: Optional[str]
    correction_attempts: int
    analysis: Dict[str, Any]
    chart_specification: Dict[str, Any]
    clarification_required: bool
    clarification_question: Optional[str]
    final_response: str
    execution_status: str  # pending, running, completed, failed, clarification_needed
    node_events: List[Dict[str, Any]]


# --- AGENT NODES ---

def supervisor_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Supervises workflow, understands intent and extracts key entities."""
    start_t = time.perf_counter()
    q = state["user_question"]
    events = list(state.get("node_events", []))

    event_start = {
        "node": "supervisor",
        "status": "running",
        "timestamp": time.time(),
        "message": "Classifying user query and routing workflow...",
    }
    events.append(event_start)

    intent = "sql_generation"
    reasoning = "Query requires data retrieval from database."
    entities = []

    # If Gemini is configured, use structured intent classification
    if ai_provider.is_configured():
        prompt = f"""You are the Supervisor Agent of QueryMind AI.
Analyze the user question and classify the primary intent:
- 'sql_generation': user wants to query, view, aggregate, calculate, or retrieve data from tables.
- 'sql_explanation': user provided SQL and wants to understand what it does.
- 'query_optimization': user wants to improve performance or index usage of a query.
- 'schema_question': user is asking about database structure, tables, columns, or relationships.
- 'general_assistance': greeting or general database question not requiring live queries.

User Question: {q}
Recent Context: {json.dumps(state.get('conversation_context', [])[-3:])}
"""
        try:
            res: SupervisorOutput = ai_provider.generate_structured(
                prompt=prompt,
                schema_class=SupervisorOutput,
                system_instruction="You are a senior database query dispatcher.",
            )
            intent = res.intent.lower()
            reasoning = res.reasoning
            entities = res.extracted_entities
        except Exception as e:
            logger.warning(f"Supervisor LLM call failed: {e}. Defaulting to sql_generation.")
    else:
        # Deterministic fallback classification
        q_lower = q.lower()
        words_set = set(q_lower.split())
        if any(w in q_lower for w in ["explain", "what does this query do", "describe query"]):
            intent = "sql_explanation"
        elif any(w in q_lower for w in ["optimize", "performance", "faster", "index suggestion"]):
            intent = "query_optimization"
        elif any(w in q_lower for w in ["show tables", "list tables", "what tables", "table schema"]):
            intent = "schema_question"
        elif words_set.intersection({"hello", "hi", "hey", "help", "greet"}):
            intent = "general_assistance"

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "supervisor",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Intent: {intent} ({reasoning})",
    })

    return {
        "intent": intent,
        "node_events": events,
    }


def schema_retrieval_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Retrieves schema definitions, column types and business terms using RAG."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "schema_retrieval",
        "status": "running",
        "timestamp": time.time(),
        "message": "Retrieving relevant tables, relationships and glossary terms from vector store...",
    })

    q = state["user_question"]
    ws_id = state["workspace_id"]
    conn_id = state["connection_id"]

    retrieved = qdrant_manager.retrieve_relevant_schema(
        workspace_id=ws_id,
        connection_id=conn_id,
        query=q,
        limit=6,
    )

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    tables_found = [t["table_name"] for t in retrieved.get("tables", [])]
    events.append({
        "node": "schema_retrieval",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Found {len(tables_found)} relevant tables: {', '.join(tables_found[:5])}",
    })

    return {
        "retrieved_schema": retrieved,
        "retrieved_glossary": retrieved.get("glossary", []),
        "node_events": events,
    }


def sql_generation_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Uses Gemini to generate dialect-specific SQL with structured output."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    conn = state.get("connection_model")
    db_type = conn.database_type.lower() if conn else "postgresql"
    dialect_name = "MySQL" if db_type == "mysql" else "PostgreSQL"
    events.append({
        "node": "sql_generation",
        "status": "running",
        "timestamp": time.time(),
        "message": f"Generating {dialect_name} query with Google Gemini...",
    })

    q = state["user_question"]
    schema_info = state.get("retrieved_schema", {})
    context_str = schema_info.get("compact_context", "")

    prompt = f"""You are the SQL Generation Agent of QueryMind AI.
Generate a precise, safe, read-only {dialect_name} query to answer the user question.

DATABASE SCHEMA CONTEXT:
{context_str}

USER QUESTION:
{q}

PREVIOUS CONVERSATION CONTEXT:
{json.dumps(state.get('conversation_context', [])[-3:])}

REQUIREMENTS:
1. Generate valid {dialect_name} SQL only.
2. Never perform SELECT * unless strictly necessary; select explicit, relevant columns.
3. Use proper JOIN conditions based on the foreign key relationships shown above.
4. Use standard aggregation (SUM, COUNT, AVG) and GROUP BY where appropriate.
5. If sorting by date or numerical value, use explicit ORDER BY.
6. Return structured output with SQL, explanation, tables used, and assumptions.
"""
    sql = ""
    explanation = ""
    tables_used = []
    columns_used = []
    requires_clarification = False
    clarification_question = None

    if ai_provider.is_configured():
        try:
            res: SQLGenerationOutput = ai_provider.generate_structured(
                prompt=prompt,
                schema_class=SQLGenerationOutput,
                system_instruction=f"You are an expert {dialect_name} database engineer.",
            )
            sql = res.sql.strip().rstrip(";")
            explanation = res.explanation
            tables_used = res.tables_used
            columns_used = res.columns_used
            requires_clarification = res.requires_clarification
            clarification_question = res.clarification_question
        except Exception as e:
            logger.warning(f"Gemini SQL generation error: {e}")
            sql = f"-- Error generating SQL with Gemini: {str(e)}"
            explanation = "Failed to generate SQL via Gemini API."
    else:
        # Fallback heuristic generator for demo tables when Gemini key is pending
        q_lower = q.lower()
        if "employee" in q_lower and "department" in q_lower:
            sql = "SELECT d.name AS department_name, COUNT(e.id) AS total_employees, AVG(e.salary)::numeric(12,2) AS avg_salary FROM departments d LEFT JOIN employees e ON d.id = e.department_id GROUP BY d.name ORDER BY total_employees DESC"
            explanation = "Calculates employee count and average salary per department."
            tables_used = ["departments", "employees"]
        elif "product" in q_lower and "revenue" in q_lower:
            sql = "SELECT p.name AS product_name, p.category, SUM(oi.subtotal) AS total_revenue FROM order_items oi JOIN products p ON p.id = oi.product_id GROUP BY p.name, p.category ORDER BY total_revenue DESC LIMIT 5"
            explanation = "Aggregates revenue across order items grouped by product."
            tables_used = ["order_items", "products"]
        elif "order" in q_lower and "month" in q_lower:
            sql = "SELECT DATE_TRUNC('month', order_date)::date AS order_month, COUNT(id) AS total_orders, SUM(total_amount) AS total_revenue FROM orders WHERE status = 'completed' GROUP BY order_month ORDER BY order_month DESC LIMIT 6"
            explanation = "Aggregates completed orders and monthly revenue for recent months."
            tables_used = ["orders"]
        elif "customer" in q_lower and ("not" in q_lower or "zero" in q_lower):
            sql = "SELECT c.id, c.first_name, c.last_name, c.email, c.city, c.country FROM customers c LEFT JOIN orders o ON c.id = o.customer_id WHERE o.id IS NULL"
            explanation = "Identifies customers who have never placed an order."
            tables_used = ["customers", "orders"]
        else:
            # General fallback query
            sql = "SELECT * FROM products ORDER BY price DESC LIMIT 10"
            explanation = "Default product catalog listing."
            tables_used = ["products"]

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "sql_generation",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Generated SQL query: {sql[:100]}...",
    })

    return {
        "generated_sql": sql,
        "sql_explanation": explanation,
        "clarification_required": requires_clarification,
        "clarification_question": clarification_question,
        "node_events": events,
    }


def sql_validation_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Deterministically validates SQL syntax, dialect and security policies with SQLGlot."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "sql_validation",
        "status": "running",
        "timestamp": time.time(),
        "message": "Validating SQL safety and syntax deterministically with SQLGlot...",
    })

    raw_sql = state.get("generated_sql", "")
    conn = state.get("connection_model")
    dialect = "mysql" if conn and conn.database_type.lower() == "mysql" else "postgres"
    val_res = SQLValidator.validate_sql(
        sql=raw_sql,
        dialect=dialect,
        max_rows=settings.SQL_MAX_ROWS_RETURNED,
    )

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    status_str = "Passed" if val_res.is_valid else f"Failed ({', '.join(val_res.errors)})"
    events.append({
        "node": "sql_validation",
        "status": "completed" if val_res.is_valid else "warning",
        "duration_ms": dur_ms,
        "output": f"Validation {status_str}",
    })

    return {
        "validation_result": val_res.to_dict(),
        "generated_sql": val_res.sanitized_sql if val_res.is_valid else raw_sql,
        "node_events": events,
    }


def sql_execution_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Executes validated query safely against external database."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "sql_execution",
        "status": "running",
        "timestamp": time.time(),
        "message": "Executing query against database with read-only transaction and timeout...",
    })

    sql = state["generated_sql"]
    conn = state["connection_model"]

    exec_res = SQLExecutor.execute_query(
        conn=conn,
        validated_sql=sql,
        timeout_seconds=settings.SQL_QUERY_TIMEOUT_SECONDS,
        max_rows=settings.SQL_MAX_ROWS_RETURNED,
    )

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "sql_execution",
        "status": "completed" if exec_res.success else "failed",
        "duration_ms": dur_ms,
        "output": f"Execution {'succeeded' if exec_res.success else 'failed'}: {exec_res.row_count} rows in {exec_res.execution_time_ms}ms",
    })

    return {
        "execution_result": exec_res.to_dict(),
        "execution_error": exec_res.error,
        "node_events": events,
    }


def sql_correction_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Analyzes execution or validation errors using Gemini and proposes corrected SQL."""
    start_t = time.perf_counter()
    attempts = state.get("correction_attempts", 0) + 1
    events = list(state.get("node_events", []))
    events.append({
        "node": "sql_correction",
        "status": "running",
        "timestamp": time.time(),
        "message": f"Self-correcting SQL query (Attempt {attempts}/{settings.SQL_MAX_CORRECTION_ATTEMPTS})...",
    })

    failed_sql = state.get("generated_sql", "")
    error_msg = state.get("execution_error") or str(state.get("validation_result", {}).get("errors", []))
    schema_info = state.get("retrieved_schema", {})
    context_str = schema_info.get("compact_context", "")

    corrected_sql = failed_sql

    if ai_provider.is_configured():
        prompt = f"""You are the SQL Correction Agent of QueryMind AI.
The previous SQL query failed during execution or validation.

SCHEMA:
{context_str}

FAILED SQL:
{failed_sql}

ERROR MESSAGE:
{error_msg}

USER QUESTION:
{state['user_question']}

Fix the syntax, table, column name, or group by clause error. Return only valid PostgreSQL.
"""
        try:
            res: SQLCorrectionOutput = ai_provider.generate_structured(
                prompt=prompt,
                schema_class=SQLCorrectionOutput,
                system_instruction="You are a SQL debugging and correction specialist.",
            )
            corrected_sql = res.corrected_sql.strip().rstrip(";")
        except Exception as e:
            logger.warning(f"Gemini SQL correction failed: {e}")

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "sql_correction",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Proposed corrected SQL: {corrected_sql[:80]}...",
    })

    return {
        "generated_sql": corrected_sql,
        "correction_attempts": attempts,
        "node_events": events,
    }


def result_analysis_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Explains actual query results using Gemini."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "result_analysis",
        "status": "running",
        "timestamp": time.time(),
        "message": "Analyzing query results and extracting business insights...",
    })

    exec_res = state.get("execution_result", {})
    rows = exec_res.get("rows", [])
    cols = exec_res.get("columns", [])

    analysis = {
        "summary": f"Query executed successfully, returning {len(rows)} records.",
        "key_findings": [f"Columns retrieved: {', '.join(cols)}"],
        "trends": [],
        "anomalies": [],
        "limitations": [],
    }

    if ai_provider.is_configured() and rows:
        sample_rows = rows[:15]  # Send bounded sample to avoid large context
        prompt = f"""You are the Result Analysis Agent of QueryMind AI.
Analyze the following query results and provide a structured summary.

USER QUESTION:
{state['user_question']}

COLUMNS:
{cols}

SAMPLE ROWS:
{sample_rows}

TOTAL ROWS: {len(rows)}

Provide factual takeaways directly supported by the data. Do not hallucinate numbers.
"""
        try:
            res: ResultAnalysisOutput = ai_provider.generate_structured(
                prompt=prompt,
                schema_class=ResultAnalysisOutput,
                system_instruction="You are a senior data analyst.",
            )
            analysis = res.model_dump()
        except Exception as e:
            logger.warning(f"Result analysis LLM call failed: {e}")

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "result_analysis",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Analysis complete: {analysis.get('summary', '')[:80]}...",
    })

    return {
        "analysis": analysis,
        "final_response": analysis.get("summary", ""),
        "execution_status": "completed",
        "node_events": events,
    }


def visualization_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Recommends chart type and formats dataset for Recharts."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "visualization",
        "status": "running",
        "timestamp": time.time(),
        "message": "Generating visualization recommendation with Recharts formatting...",
    })

    exec_res = state.get("execution_result", {})
    rows = exec_res.get("rows", [])
    cols = exec_res.get("columns", [])

    chart_spec = {
        "chart_type": "bar",
        "title": "Query Results",
        "x_axis": cols[0] if cols else "x",
        "y_axis": cols[1] if len(cols) > 1 else (cols[0] if cols else "y"),
        "data": [],
    }

    if len(cols) >= 2 and len(rows) > 0:
        # Determine appropriate chart type based on column types and question
        q_lower = state["user_question"].lower()
        if any(w in q_lower for w in ["trend", "over time", "month", "timeline", "date"]):
            chart_type = "line"
        elif any(w in q_lower for w in ["distribution", "proportion", "percentage", "share"]):
            chart_type = "pie"
        else:
            chart_type = "bar"

        # Format rows into list of dicts for Recharts
        chart_data = []
        for r in rows[:50]:  # Limit chart points
            entry = {}
            for i, c in enumerate(cols):
                val = r[i]
                if isinstance(val, (int, float)):
                    entry[c] = val
                else:
                    try:
                        entry[c] = float(val)
                    except (ValueError, TypeError):
                        entry[c] = str(val)
            chart_data.append(entry)

        chart_spec = {
            "chart_type": chart_type,
            "title": f"{cols[1]} by {cols[0]}" if len(cols) > 1 else "Metric Distribution",
            "x_axis": cols[0],
            "y_axis": cols[1] if len(cols) > 1 else cols[0],
            "data": chart_data,
        }

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "visualization",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": f"Chart generated: {chart_spec['chart_type']} ({chart_spec['title']})",
    })

    return {
        "chart_specification": chart_spec,
        "node_events": events,
    }


def general_assistant_node(state: QueryMindAgentState) -> Dict[str, Any]:
    """Handles general conversational and database questions."""
    start_t = time.perf_counter()
    events = list(state.get("node_events", []))
    events.append({
        "node": "general_assistant",
        "status": "running",
        "timestamp": time.time(),
        "message": "Generating conversational response...",
    })

    q = state["user_question"]
    response_text = ""

    if ai_provider.is_configured():
        prompt = f"User Question: {q}\nProvide an informative, helpful response about databases, SQL, or QueryMind AI capabilities."
        try:
            response_text = ai_provider.generate_text(prompt=prompt)
        except Exception as e:
            response_text = f"I am QueryMind AI. I can assist you with database schema discovery, natural language to SQL generation, and analytics."
    else:
        response_text = (
            "Welcome to QueryMind AI! I can explore your database schema, generate SQL queries from natural language, "
            "safely execute them against your databases, and create interactive visualizations. "
            "To activate full Gemini AI features, please configure your GEMINI_API_KEY in backend/.env."
        )

    dur_ms = int((time.perf_counter() - start_t) * 1000)
    events.append({
        "node": "general_assistant",
        "status": "completed",
        "duration_ms": dur_ms,
        "output": response_text[:100],
    })

    return {
        "final_response": response_text,
        "execution_status": "completed",
        "node_events": events,
    }


# --- ROUTERS / CONDITIONAL EDGES ---

def route_intent(state: QueryMindAgentState) -> str:
    intent = state.get("intent", "sql_generation")
    if intent in ("sql_generation", "query_optimization"):
        return "schema_retrieval"
    elif intent == "sql_explanation":
        return "schema_retrieval"
    else:
        return "general_assistant"


def route_validation(state: QueryMindAgentState) -> str:
    if state.get("clarification_required"):
        return END

    val_res = state.get("validation_result", {})
    if val_res.get("is_valid", False):
        return "sql_execution"

    attempts = state.get("correction_attempts", 0)
    if attempts < settings.SQL_MAX_CORRECTION_ATTEMPTS:
        return "sql_correction"
    return END


def route_execution(state: QueryMindAgentState) -> str:
    exec_res = state.get("execution_result", {})
    if exec_res.get("success", False):
        return "result_analysis"

    attempts = state.get("correction_attempts", 0)
    if attempts < settings.SQL_MAX_CORRECTION_ATTEMPTS:
        return "sql_correction"
    return END


# --- GRAPH BUILDER ---

def build_querymind_graph() -> StateGraph:
    """Builds and compiles the QueryMind LangGraph multi-agent workflow."""
    workflow = StateGraph(QueryMindAgentState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("schema_retrieval", schema_retrieval_node)
    workflow.add_node("sql_generation", sql_generation_node)
    workflow.add_node("sql_validation", sql_validation_node)
    workflow.add_node("sql_execution", sql_execution_node)
    workflow.add_node("sql_correction", sql_correction_node)
    workflow.add_node("result_analysis", result_analysis_node)
    workflow.add_node("visualization", visualization_node)
    workflow.add_node("general_assistant", general_assistant_node)

    # Add Edges
    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_intent,
        {
            "schema_retrieval": "schema_retrieval",
            "general_assistant": "general_assistant",
        },
    )

    workflow.add_edge("schema_retrieval", "sql_generation")
    workflow.add_edge("sql_generation", "sql_validation")

    workflow.add_conditional_edges(
        "sql_validation",
        route_validation,
        {
            "sql_execution": "sql_execution",
            "sql_correction": "sql_correction",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "sql_execution",
        route_execution,
        {
            "result_analysis": "result_analysis",
            "sql_correction": "sql_correction",
            END: END,
        },
    )

    workflow.add_edge("sql_correction", "sql_validation")
    workflow.add_edge("result_analysis", "visualization")
    workflow.add_edge("visualization", END)
    workflow.add_edge("general_assistant", END)

    return workflow.compile()


querymind_graph = build_querymind_graph()
