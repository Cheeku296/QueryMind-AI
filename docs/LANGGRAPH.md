# QueryMind AI — Multi-Agent Architecture (LangGraph)

QueryMind AI leverages **LangGraph** (built upon LangChain) to orchestrate a specialized, cyclic, multi-agent pipeline designed specifically for natural-language-to-SQL tasks. Rather than relying on a single monolithic prompt, QueryMind splits responsibilities across domain-specific agents with deterministic safety gates, self-correction loops, and structured outputs.

---

## 1. Multi-Agent Pipeline Topology

```
                  ┌───────────────────────────────┐
                  │          USER QUERY           │
                  └───────────────┬───────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │       SUPERVISOR        │
                     └────────────┬────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼ (intent: sql_query)             ▼ (intent: general)
      ┌───────────────────────────┐     ┌─────────────────────────┐
      │     SCHEMA RETRIEVAL      │     │    GENERAL ASSISTANT    │
      │         (Qdrant)          │     └────────────┬────────────┘
      └─────────────┬─────────────┘                  │
                    ▼                                │
      ┌───────────────────────────┐                  │
      │      SQL GENERATION       │                  │
      │     (Google Gemini)       │                  │
      └─────────────┬─────────────┘                  │
                    ▼                                │
      ┌───────────────────────────┐                  │
      │      SQL VALIDATION       │                  │
      │         (SQLGlot)         │                  │
      └─────────────┬─────────────┘                  │
                    │                                │
            [Is SQL Valid & Safe?]                   │
            /                   \                    │
         (yes)                  (no)                 │
          /                       \                  │
         /                  [retries < 2?]           │
        /                   /            \           │
       /                 (yes)           (no)        │
      /                    /                \        │
     │      ┌─────────────────────────┐      │       │
     │      │     SQL CORRECTION      │      │       │
     │      │     (Google Gemini)     │      │       │
     │      └──────────────┬──────────┘      │       │
     │                     │ (loop back)     │       │
     │                     ▼                 │       │
     │             (to SQL VALIDATION)       │       │
     │                                       │       │
     ▼                                       ▼       │
┌───────────────────────────┐       ┌───────────────────────┐
│       SQL EXECUTION       │       │ RETURN SAFETY ERROR   │
│     (Read-Only PG)        │       └───────────┬───────────┘
└─────────────┬─────────────┘                   │
              │                                 │
       [Query Succeeded?]                       │
       /              \                         │
    (yes)             (no)                      │
     /                  \                       │
    /               [retries < 2?]              │
   /                /            \              │
  /              (yes)           (no)           │
 /                 /                \           │
│         (to SQL CORRECTION)    (to ERROR)     │
▼                                               │
┌───────────────────────────┐                   │
│      RESULT ANALYSIS      │                   │
│     (Google Gemini)       │                   │
└─────────────┬─────────────┘                   │
              ▼                                 │
┌───────────────────────────┐                   │
│       VISUALIZATION       │                   │
│      (Chart Spec Gen)     │                   │
└─────────────┬─────────────┘                   │
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                   ┌────────────────────────┐
                   │     FINAL RESPONSE     │
                   └────────────────────────┘
```

---

## 2. Typed State Schema (`QueryMindAgentState`)

All agent nodes mutate a single shared, immutable TypedDict state throughout the lifecycle of a request:

```python
class QueryMindAgentState(TypedDict, total=False):
    # User Inputs & Context
    user_query: str
    connection_id: str
    workspace_id: str
    dialect: str
    conversation_history: List[Dict[str, str]]
    
    # Intent Routing
    intent: str               # "sql_query" | "general"
    
    # RAG Context
    retrieved_tables: List[str]
    retrieved_schema_text: str
    glossary_context: str
    
    # SQL Lifecycle
    generated_sql: str
    sql_is_valid: bool
    validation_errors: List[str]
    retry_count: int
    correction_prompt: str
    
    # Execution
    execution_results: Dict[str, Any]  # {"columns": [...], "rows": [...], "row_count": int}
    execution_error: Optional[str]
    execution_time_ms: float
    
    # Intelligence & Visualization
    explanation: str
    chart_spec: Optional[Dict[str, Any]]  # {"type": "bar|line|pie", "x_key": "...", "y_key": "..."}
    
    # Output & Diagnostics
    final_response: str
    node_trace: List[Dict[str, Any]]
```

---

## 3. Detailed Node Specifications

### Node 1: Supervisor (`supervisor`)
- **Model:** `gemini-2.5-flash`
- **Goal:** Classifies user intent (`sql_query` vs `general`), extracts table candidates, and determines if external database interaction is required.
- **Safety Fallback:** If the Gemini API key is missing or invalid, an intent keyword classifier ensures standard greetings bypass SQL workflows safely without raising exceptions.

### Node 2: Schema Retrieval (`schema_retrieval`)
- **Engine:** Qdrant Vector DB & Cosine Similarity
- **Goal:** Vectorizes the user's natural language query using `text-embedding-004` (768 dimensions), queries Qdrant with `connection_id` filter, and extracts relevant table schemas, column data types, foreign keys, and matching glossary definitions.

### Node 3: SQL Generation (`sql_generation`)
- **Model:** `gemini-2.5-flash`
- **Output:** Pydantic Structured Output `SQLGenerationOutput` (`sql`, `explanation`, `tables_used`).
- **Prompt Guardrails:**
  - Enforces explicit dialect syntax (PostgreSQL `NOW()`, `DATE_TRUNC()`, `ILIKE`).
  - Never invents tables or columns outside the retrieved schema.
  - Automatically targets only `SELECT` expressions.

### Node 4: SQL Validation (`sql_validation`)
- **Engine:** SQLGlot AST Parser
- **Rules Enforced Deterministically:**
  1. Statement type MUST be `SELECT`.
  2. Forbids `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`.
  3. Rejects multiple statements (semicolon chaining).
  4. Checks for missing `LIMIT` and automatically clamps queries to `LIMIT 500`.

### Node 5: Self-Correction Loop (`sql_correction`)
- **Model:** `gemini-2.5-flash`
- **Trigger:** Either `sql_validation` failure (syntax error / AST reject) or `sql_execution` failure (PostgreSQL runtime error).
- **Behavior:** Passes the failed SQL statement, the exact database or validator error message, and the original schema back to Gemini with instructions to repair the query.
- **Guardrail:** Caps correction iterations to **2 retries max** to prevent infinite execution loops and token exhaustion.

### Node 6: SQL Execution (`sql_execution`)
- **Engine:** PostgreSQL Async Connection (`psycopg` / `asyncpg`)
- **Enforcement:**
  - `SET TRANSACTION READ ONLY` precedes execution.
  - `SET statement_timeout = 15000` enforces a 15-second cutoff.
  - Timed in milliseconds.

### Node 7: Result Analysis (`result_analysis`)
- **Model:** `gemini-2.5-flash`
- **Goal:** Summarizes query results into natural language business answers, highlights trends, caveats, and business implications.

### Node 8: Visualization Planner (`visualization`)
- **Model:** `gemini-2.5-flash`
- **Output:** `ChartSpec` JSON object containing `type` (`bar`, `line`, `pie`, `area`), `x_key`, `y_key`, and chart options. The frontend dynamically renders this via Recharts.

### Node 9: General Assistant (`general_assistant`)
- **Goal:** Responds to conversational greetings, questions about QueryMind's capabilities, or conceptual SQL tutorials without hitting external databases.

---

## 4. Real-Time Streaming via Server-Sent Events (SSE)

The execution graph emits state transitions in real time to the frontend via the `/api/v1/chat/stream` endpoint.

Each event includes:
- `event: node_start` — Node name and timestamp.
- `event: node_complete` — Node results and metrics.
- `event: final_message` — Complete payload with formatted markdown, SQL, dataset, and chart specifications.

