# QueryMind AI — REST & SSE API Reference

QueryMind AI exposes a comprehensive, production-grade REST and Server-Sent Events (SSE) API built on **FastAPI**, with Pydantic v2 data validation, JWT authentication, and multi-tenant workspace isolation.

---

## 1. Global Specifications

- **Base URL:** `http://localhost:8000/api/v1`
- **Content-Type:** `application/json` (except streaming endpoints: `text/event-stream` and exports: `text/csv`)
- **Authentication:** Bearer token in `Authorization` header (`Authorization: Bearer <access_token>`)
- **Workspace Context:** Passed via `X-Workspace-Id: <uuid>` header for workspace-scoped endpoints.
- **Error Format:**
```json
{
  "detail": "Descriptive human-readable error message"
}
```

---

## 2. Authentication (`/api/v1/auth`)

### 2.1 User Registration
- **Endpoint:** `POST /api/v1/auth/register`
- **Request Body:**
```json
{
  "email": "user@example.com",
  "password": "Password123!",
  "full_name": "Jane Doe"
}
```
- **Response (201 Created):**
```json
{
  "id": "e8d64db4-46fb-455b-a7eb-6c483a9de010",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "created_at": "2026-11-17T10:00:00Z"
}
```
*Note: A default workspace named "Jane Doe's Workspace" is automatically created and assigned with the `OWNER` role.*

### 2.2 User Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Request Body:**
```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```
- **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "e8d64db4-46fb-455b-a7eb-6c483a9de010",
    "email": "user@example.com",
    "full_name": "Jane Doe"
  }
}
```

### 2.3 Token Refresh
- **Endpoint:** `POST /api/v1/auth/refresh`
- **Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2.4 Get Current User Profile
- **Endpoint:** `GET /api/v1/auth/me`
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):**
```json
{
  "id": "e8d64db4-46fb-455b-a7eb-6c483a9de010",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "created_at": "2026-11-17T10:00:00Z"
}
```

---

## 3. Workspaces (`/api/v1/workspaces`)

### 3.1 List User Workspaces
- **Endpoint:** `GET /api/v1/workspaces`
- **Response (200 OK):**
```json
[
  {
    "id": "7ac15fc1-ca74-4b47-be51-e3be6cf94cb0",
    "name": "Production Workspace",
    "slug": "production-workspace",
    "role": "owner",
    "created_at": "2026-11-17T10:00:00Z"
  }
]
```

### 3.2 Create Workspace
- **Endpoint:** `POST /api/v1/workspaces`
- **Request Body:**
```json
{
  "name": "Analytics & BI",
  "description": "Workspace for data analysts"
}
```

---

## 4. Database Connections (`/api/v1/connections`)

External database connection credentials (password, SSL certs) are encrypted at rest using AES-128-CBC / HMAC Fernet symmetric encryption before insertion into PostgreSQL.

### 4.1 Test Unsaved Connection Parameters
- **Endpoint:** `POST /api/v1/connections/test`
- **Request Body:**
```json
{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "querymind_demo",
  "username": "querymind_app",
  "password": "AppPassword123!",
  "ssl_mode": "prefer"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Connection successful! PostgreSQL version: 16.2",
  "latency_ms": 14.8
}
```

### 4.2 Create & Register Connection
- **Endpoint:** `POST /api/v1/connections`
- **Request Body:**
```json
{
  "name": "E-Commerce Demo DB",
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "querymind_demo",
  "username": "querymind_app",
  "password": "AppPassword123!",
  "ssl_mode": "prefer",
  "is_read_only": true
}
```
- **Response (201 Created):**
```json
{
  "id": "c1f7a4df-128a-4467-9382-7f28bb019483",
  "name": "E-Commerce Demo DB",
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "querymind_demo",
  "username": "querymind_app",
  "is_read_only": true,
  "status": "connected",
  "created_at": "2026-11-17T10:05:00Z"
}
```

### 4.3 Trigger Schema Sync & Introspection
- **Endpoint:** `POST /api/v1/connections/{id}/sync-schema`
- **Description:** Performs full catalog reflection, stores snapshot in `schema_snapshots`, and vectorizes/indexes all tables and columns into Qdrant (`querymind_schemas` collection).
- **Response (200 OK):**
```json
{
  "status": "synced",
  "tables_count": 8,
  "columns_count": 66,
  "snapshot_id": "8f3e2b9c-5a2d-4530-bc56-d8431e67fa12",
  "qdrant_indexed_count": 74
}
```

---

## 5. Schema & ER Diagram (`/api/v1/schema`)

### 5.1 Get Latest Schema Snapshot
- **Endpoint:** `GET /api/v1/schema/connections/{id}/snapshot`
- **Response (200 OK):**
```json
{
  "id": "8f3e2b9c-5a2d-4530-bc56-d8431e67fa12",
  "version": 1,
  "tables": [
    {
      "name": "orders",
      "type": "table",
      "row_count_estimate": 320,
      "columns": [
        {"name": "id", "data_type": "UUID", "is_primary_key": true, "nullable": false},
        {"name": "customer_id", "data_type": "UUID", "is_foreign_key": true, "fk_target": "customers.id", "nullable": false},
        {"name": "total_amount", "data_type": "NUMERIC(10,2)", "nullable": false},
        {"name": "status", "data_type": "VARCHAR(50)", "nullable": false},
        {"name": "created_at", "data_type": "TIMESTAMP", "nullable": false}
      ]
    }
  ]
}
```

### 5.2 Get ER Diagram Data for React Flow
- **Endpoint:** `GET /api/v1/schema/connections/{id}/er-diagram`
- **Response (200 OK):** Returns formatted nodes and edges ready for `@xyflow/react` rendering.
```json
{
  "nodes": [
    {
      "id": "orders",
      "type": "tableNode",
      "position": {"x": 250, "y": 100},
      "data": {
        "label": "orders",
        "columns": [
          {"name": "id", "type": "UUID", "isPk": true, "isFk": false},
          {"name": "customer_id", "type": "UUID", "isPk": false, "isFk": true}
        ]
      }
    }
  ],
  "edges": [
    {
      "id": "fk_orders_customers",
      "source": "customers",
      "target": "orders",
      "animated": true,
      "label": "1:N"
    }
  ]
}
```

---

## 6. AI Chat & Multi-Agent Execution (`/api/v1/chat`)

### 6.1 Create or Fetch Conversation
- **Endpoint:** `POST /api/v1/chat/conversations`
- **Request Body:**
```json
{
  "title": "Revenue Analysis Q4",
  "connection_id": "c1f7a4df-128a-4467-9382-7f28bb019483"
}
```

### 6.2 SSE Streaming Chat & Agent Pipeline
- **Endpoint:** `POST /api/v1/chat/stream`
- **Content-Type:** `text/event-stream`
- **Request Body:**
```json
{
  "conversation_id": "a90b4d18-f29e-4a6c-9c98-e7912bc3fa91",
  "connection_id": "c1f7a4df-128a-4467-9382-7f28bb019483",
  "content": "Which 5 customers have generated the most revenue, and what is their total spend?"
}
```
- **Server-Sent Event Stream Format:**
```
event: node_start
data: {"node": "supervisor", "status": "running", "timestamp": "2026-11-17T10:15:00.100Z"}

event: node_complete
data: {"node": "supervisor", "intent": "sql_query", "tables": ["customers", "orders"]}

event: node_start
data: {"node": "schema_retrieval", "status": "running"}

event: node_complete
data: {"node": "schema_retrieval", "retrieved_tables": ["customers", "orders"]}

event: node_start
data: {"node": "sql_generation", "status": "running"}

event: node_complete
data: {"node": "sql_generation", "generated_sql": "SELECT c.id, c.first_name, c.last_name, SUM(o.total_amount) AS total_spent FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.first_name, c.last_name ORDER BY total_spent DESC LIMIT 5;"}

event: node_start
data: {"node": "sql_validation", "status": "running"}

event: node_complete
data: {"node": "sql_validation", "is_valid": true, "safety": "PASSED"}

event: node_start
data: {"node": "sql_execution", "status": "running"}

event: node_complete
data: {"node": "sql_execution", "row_count": 5, "duration_ms": 11.4}

event: node_start
data: {"node": "result_analysis", "status": "running"}

event: node_complete
data: {"node": "result_analysis", "explanation": "The top 5 revenue-generating customers are listed in order of total historical spend."}

event: node_start
data: {"node": "visualization", "status": "running"}

event: node_complete
data: {"node": "visualization", "chart_spec": {"type": "bar", "x_key": "last_name", "y_key": "total_spent", "title": "Top 5 Customers by Revenue"}}

event: final_message
data: {
  "message_id": "f8a123bc-1111-2222-3333-444455556666",
  "content": "Here are the top 5 customers by revenue...",
  "generated_sql": "SELECT c.id, c.first_name, c.last_name, SUM(o.total_amount) AS total_spent ...",
  "query_results": {"columns": ["id", "first_name", "last_name", "total_spent"], "rows": [...]},
  "chart_spec": {"type": "bar", "x_key": "last_name", "y_key": "total_spent"},
  "execution_metrics": {"duration_ms": 11.4, "rows": 5, "cached": false}
}
```

---

## 7. SQL IDE & Execution (`/api/v1/sql`)

### 7.1 Deterministic SQL Validation
- **Endpoint:** `POST /api/v1/sql/validate`
- **Request Body:**
```json
{
  "sql": "SELECT * FROM customers WHERE status = 'active';"
}
```
- **Response (200 OK):**
```json
{
  "is_valid": true,
  "statement_type": "SELECT",
  "tables": ["customers"],
  "columns": ["*"],
  "has_limit": false,
  "injected_limit": "SELECT * FROM customers WHERE status = 'active' LIMIT 500",
  "errors": []
}
```

### 7.2 Safe SQL Execution
- **Endpoint:** `POST /api/v1/sql/execute`
- **Request Body:**
```json
{
  "connection_id": "c1f7a4df-128a-4467-9382-7f28bb019483",
  "sql": "SELECT id, email, created_at FROM customers ORDER BY created_at DESC LIMIT 10;",
  "explain": false
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "columns": ["id", "email", "created_at"],
  "rows": [
    {"id": "550e8400-e29b-41d4-a716-446655440000", "email": "customer@example.com", "created_at": "2026-01-15T08:30:00Z"}
  ],
  "row_count": 10,
  "duration_ms": 12.3,
  "query_id": "33481234-bcde-4f5a-8b12-111122223333"
}
```

---

## 8. Saved Queries & History (`/api/v1/queries`, `/api/v1/saved-queries`)

- `GET /api/v1/queries` — Fetch execution audit log with latency, rows, and status.
- `POST /api/v1/saved-queries` — Bookmark query with custom tags and descriptions.
- `GET /api/v1/saved-queries` — Filter saved queries by tag or name.
- `DELETE /api/v1/saved-queries/{id}` — Delete a saved query.

---

## 9. Business Glossary (`/api/v1/glossary`)

- `GET /api/v1/glossary` — List all semantic business definitions.
- `POST /api/v1/glossary` — Create glossary term (e.g. `ARR = Annual Recurring Revenue`). Automatically embeds definition into Qdrant for RAG grounding.
- `PUT /api/v1/glossary/{id}` — Update term.
- `DELETE /api/v1/glossary/{id}` — Remove term and delete vector from Qdrant.

---

## 10. Analytical Reports (`/api/v1/reports`)

- `GET /api/v1/reports` — List generated reports.
- `POST /api/v1/reports` — Generate comprehensive markdown analytical summary with embedded charts.
- `GET /api/v1/reports/{id}` — Fetch report details.
- `GET /api/v1/reports/{id}/export?format=json|csv` — Export report datasets as JSON or CSV.

---

## 11. Settings & Health Checks (`/api/v1/settings`)

### 11.1 Test Gemini API Connectivity
- **Endpoint:** `POST /api/v1/settings/gemini/test`
- **Response (200 OK):**
```json
{
  "configured": true,
  "status": "ready",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "embedding_model": "text-embedding-004",
  "message": "Gemini API key is configured and responsive."
}
```
*If not yet configured:*
```json
{
  "configured": false,
  "status": "setup_required",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "message": "GEMINI_API_KEY is not set or contains the default placeholder. Please edit backend/.env."
}
```

### 11.2 System Health & Dependency Status
- **Endpoint:** `GET /api/v1/settings/system-status`
- **Response (200 OK):**
```json
{
  "app_version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "qdrant": "connected",
  "gemini": "ready"
}
```
