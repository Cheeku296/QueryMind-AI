# QueryMind AI — Docker Deployment & Operations Guide

QueryMind AI is fully containerized using **Docker** and **Docker Compose**, providing an orchestrated local or production environment with zero manual dependency installation.

---

## 1. Services Architecture

| Service Name | Image / Build | Port Mappings | Responsibility |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | `5432:5432` | Stores core application data (`querymind`) and the isolated demo database (`querymind_demo`). |
| `redis` | `redis:7-alpine` | `6380:6379` | Message broker for Celery async tasks and real-time cache. |
| `qdrant` | `qdrant/qdrant:latest` | `6333:6333`, `6334:6334` | Vector search engine for schema embeddings and business glossary matching. |
| `backend` | `./backend/Dockerfile` | `8000:8000` | FastAPI Python 3.12 ASGI application server. |
| `celery_worker`| `./backend/Dockerfile` | (internal) | Asynchronous worker for long-running schema introspection and report generation. |
| `frontend` | `./frontend/Dockerfile` | `3000:80` | Production Nginx server hosting the compiled React 18 + Vite SPA. |

---

## 2. Quickstart Deployment

### Step 1: Clone and Configure Environment

```bash
cd QueryMind

# Copy environment template
cp backend/.env.example backend/.env
```

Edit `backend/.env` to configure your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_from_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
LLM_PROVIDER=gemini
```

### Step 2: Build and Launch Services

```bash
docker compose up -d --build
```

### Step 3: Verify Service Health

```bash
docker compose ps
```

Expected output:
```
NAME                 IMAGE                  COMMAND                  SERVICE             STATUS              PORTS
querymind-postgres   postgres:16-alpine     "docker-entrypoint.s…"   postgres            running (healthy)   0.0.0.0:5432->5432/tcp
querymind-redis      redis:7-alpine         "docker-entrypoint.s…"   redis               running (healthy)   0.0.0.0:6380->6379/tcp
querymind-qdrant     qdrant/qdrant:latest   "./qdrant"               qdrant              running (healthy)   0.0.0.0:6333-6334->6333-6334/tcp
querymind-backend    querymind-backend      "uvicorn app.main:ap…"   backend             running             0.0.0.0:8000->8000/tcp
querymind-frontend   querymind-frontend     "/docker-entrypoint.…"   frontend            running             0.0.0.0:3000->80/tcp
```

---

## 3. Database Seeding & Verification

To initialize the schema and populate the demo database with realistic synthetic data:

```bash
# Execute synthetic seeder inside backend container
docker compose exec backend python -m app.demo.seed_data
```

This creates and populates:
- 7 Departments
- 45 Employees
- 75 Customers (including edge cases with 0 orders)
- 25 Products across categories
- 320 Orders
- 801 Order Line Items
- 279 Payments
- 40 Recurring Subscriptions

---

## 4. Running Benchmarks & Tests

### Execute Unit Test Suite
```bash
docker compose exec backend pytest -v
```

### Run 50-Question NL-to-SQL Benchmark
```bash
docker compose exec backend python scripts/run_evaluations.py
```

### Test Gemini API Connectivity
```bash
docker compose exec backend python scripts/test_gemini.py
```

---

## 5. Troubleshooting & Port Conflicts

### Port 6379 / Redis In Use
If the host machine is already running a local Redis daemon on port 6379, Docker Compose maps the Redis container to host port `6380:6379`. Backend services inside Docker connect to `redis:6379` via the container bridge network.

### Inspecting Container Logs
```bash
# View backend logs in real time
docker compose logs -f backend

# View multi-agent execution events
docker compose logs -f backend | grep -i agent
```
