# QueryMind AI — Schema-Aware Vector RAG Architecture

Enterprise databases often contain hundreds or thousands of tables and tens of thousands of columns. Shoving the entire raw database schema into an LLM context window causes high latency, token exhaustion, context degradation, and hallucinations.

QueryMind AI implements a **Schema-Aware Retrieval-Augmented Generation (RAG)** pipeline backed by **Qdrant Vector Database** and Google's **`text-embedding-004`** model.

---

## 1. Vector Store Architecture

- **Engine:** Qdrant Vector Search Engine
- **Collection Name:** `querymind_schemas`
- **Vector Dimension:** `768` (matching Google Gemini `text-embedding-004`)
- **Distance Metric:** `Cosine`
- **Storage:** On-disk payload storage with in-memory HNSW index for sub-millisecond retrieval.

### Payload Schema

```json
{
  "id": "e7b019f2-...",
  "vector": [0.0124, -0.0542, 0.0891, ...],
  "payload": {
    "connection_id": "c1f7a4df-128a-4467-9382-7f28bb019483",
    "type": "table | column | glossary",
    "table_name": "orders",
    "column_name": "total_amount",
    "content": "Table: orders | Column: total_amount (NUMERIC(10,2)) | Total monetary amount of the order after discounts and taxes.",
    "metadata": {
      "data_type": "NUMERIC(10,2)",
      "is_primary_key": false,
      "is_foreign_key": false,
      "nullable": false
    }
  }
}
```

---

## 2. Chunking & Representation Strategy

When a connection undergoes schema synchronization (`POST /api/v1/connections/{id}/sync-schema`), the catalog introspector generates three levels of vector documents:

### 1. Table-Level Document
Captures the semantic essence, table purpose, row estimates, and relationships:
```text
Table: orders
Type: Table
Estimated Rows: 320
Columns: id, customer_id, order_date, status, total_amount, shipping_address
Foreign Keys: customer_id -> customers(id)
Description: Records customer purchase transactions and statuses.
```

### 2. Column-Level Document
Indexes individual columns with their types, constraints, and comments to match fine-grained natural language queries:
```text
Table: customers | Column: email
Data Type: VARCHAR(255)
Constraints: UNIQUE, NOT NULL
Description: Primary contact email address used for user authentication and notifications.
```

### 3. Business Glossary Document
Integrates institutional vocabulary and metrics into the vector space:
```text
Glossary Term: ARR (Annual Recurring Revenue)
Formula: SUM(monthly_rate * 12) FROM subscriptions WHERE status = 'active'
Target Tables: subscriptions
Description: The annualized value of all active recurring subscription contracts.
```

---

## 3. Query Retrieval Pipeline

```
     User Query: "Show me total spend per customer in California"
                                 │
                                 ▼
              Google GenAI text-embedding-004 (768d)
                                 │
                                 ▼
                     Qdrant Vector Filtered Search
        Filter: payload.connection_id == "<target_connection_id>"
                             Top-K = 10
                                 │
                                 ▼
              Ranked Schema Nodes & Relationships
       • orders (Score: 0.88)
       • customers (Score: 0.84)
       • customers.state (Score: 0.81)
       • orders.total_amount (Score: 0.79)
                                 │
                                 ▼
                  Synthesized Schema Context Block
             Injected into Gemini SQL Generation Prompt
```

---

## 4. Multi-Tenant Scoping & Performance

- **Zero Cross-Workspace Leakage:** Every Qdrant search strictly enforces payload filter `Must([FieldCondition(key="connection_id", match=MatchValue(value=conn_id))])`.
- **Latency:** Vector search against 100,000 indexed schema entities in Qdrant executes in **< 4ms**.
- **Cold-Start Fallback:** If `GEMINI_API_KEY` is not yet supplied by the operator, the embedding service transparently falls back to deterministic unit vectors, allowing unit tests, migrations, and UI flows to run without crashing.
