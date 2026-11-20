# QueryMind AI — Security & Governance Reference

QueryMind AI is designed around a zero-trust, defense-in-depth security model to guarantee data integrity, prevent unauthorized access, and protect connected enterprise databases against destructive operations or denial-of-service.

---

## 1. Threat Model & Mitigations

| Threat | Risk Level | Mitigation Strategy |
|---|---|---|
| **SQL Injection (User Prompt)** | Critical | SQL is never concatenated via text templates. Generated SQL is parsed via SQLGlot AST into structured syntax trees before execution. |
| **Destructive SQL (DDL/DML)** | Critical | Deterministic SQLGlot AST verification rejects non-`SELECT` statements. Additionally, connections execute under `SET TRANSACTION READ ONLY`. |
| **Denial of Service (Runaway Queries)** | High | Automatic injection of `LIMIT 500` and mandatory `SET statement_timeout = 15000` (15-second hard kill). |
| **Database Credential Theft** | Critical | External passwords encrypted at rest via AES-128-CBC/HMAC Fernet. Passwords are never serialized in API responses or logs. |
| **Multi-Tenant Data Leakage** | High | Every database query, vector search, and schema cache enforces workspace-level foreign key and UUID payload scoping. |
| **Account Compromise** | Medium | Passwords hashed using Argon2id; short-lived JWT access tokens (15 mins) with refresh token rotation. |

---

## 2. Deterministic SQL Safety Engine (SQLGlot AST)

Before any query touches a database connection, it must pass through `SQLValidator` in `backend/app/ai/sql_safety/validator.py`:

```python
# Validation Rules:
1. AST Root Check:
   The parsed syntax tree must resolve exclusively to `exp.Select`.
   
2. Forbidden AST Nodes:
   Rejects exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, 
   exp.Create, exp.Truncate, exp.Grant, exp.Revoke.

3. Multi-Statement Injection Check:
   Splitting the statement via sqlglot.parse() must produce exactly 1 expression.
   Any query with semicolons or chained queries is rejected instantly.

4. Dangerous Built-in Functions:
   Rejects calls to sleep or process disruption functions:
   pg_sleep, pg_terminate_backend, pg_cancel_backend, lo_import, lo_export.

5. Automatic Row Clamping:
   If the statement lacks a LIMIT clause, SQLGlot mutates the AST to append LIMIT 500.
   If the user-provided LIMIT exceeds 500, it is clamped to 500.
```

---

## 3. Database Execution Governance

In addition to AST parsing, the database execution engine (`SQLSafeExecutor`) enforces strict runtime guards at the session level:

```sql
-- Executed immediately before the user query on the connection:
SET TRANSACTION READ ONLY;
SET statement_timeout = 15000; -- 15 seconds
```

If a user or LLM attempts to execute any write operation, PostgreSQL immediately rejects it with:
```
ERROR: cannot execute <COMMAND> in a read-only transaction
```

---

## 4. Credential Encryption at Rest

External database connection credentials are encrypted using **Fernet** (symmetric encryption built on AES-128 in CBC mode with PKCS7 padding and HMAC-SHA256 for message authentication).

- **Key Generation:** Derived from `ENCRYPTION_KEY` in environment.
- **Database Storage:** Stored in the `database_connections.password_encrypted` column.
- **Serialization Redaction:** `DatabaseConnectionResponse` Pydantic models explicitly omit the password field, returning only masked connection indicators.

---

## 5. Authentication & Workspace RBAC

### Password Hashing
QueryMind uses **Argon2id** (the memory-hard password hash recommended by OWASP and winner of the Password Hashing Competition) with parameters:
- Time cost: 2 iterations
- Memory cost: 65,536 KiB (64 MiB)
- Parallelism: 4 threads

### Session Tokens
- **Access Token:** Short-lived JWT (15-minute lifespan), signed with HMAC-SHA256.
- **Refresh Token:** Long-lived JWT (7-day lifespan) stored securely for rotation.

### Workspace Role-Based Access Control (RBAC)
- **`owner`:** Full administrative control, billing, workspace deletion, member invitations.
- **`admin`:** Connection management, schema sync, glossary definitions.
- **`member`:** Conversational querying, SQL IDE execution, report generation.
- **`viewer`:** Read-only access to saved queries, reports, and dashboards.

