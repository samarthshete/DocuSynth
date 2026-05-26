# DocuSynth Deployment Guide

This guide prepares DocuSynth for cloud demo deployment while preserving the validated local Docker + Ollama setup.

## Deployment Targets

- Primary: Railway
- Secondary: Render

## Runtime Modes

Use exactly one runtime mode per environment.

### A) Local validated mode (default for local benchmarks)

```env
LLM_PROVIDER=ollama
LOCAL_LLM_FAST_MODE=true
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1/chat/completions
OLLAMA_MODEL=qwen2.5:3b
```

Notes:
- Keeps the validated local benchmark path unchanged.
- Use this mode with local Docker Compose and local Ollama.

### B) Cloud demo mode

```env
LLM_PROVIDER=gemini
LOCAL_LLM_FAST_MODE=false
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=<set-as-secret-env-var>
MOCK_LLM=false
```

Notes:
- `GEMINI_API_KEY` must come from the platform secret environment variable.
- Do not commit API keys or real credentials.

## Health Endpoints

DocuSynth services expose:

- Backend: `GET /health`
- Python RAG: `GET /health`

These are required for platform health checks and validation scripts.

## Railway Deployment (Recommended)

### Deployment plan (must review before deploy)

Services to deploy:

- `backend` from `backend/Dockerfile`
- `python-rag` from `services/python-rag/Dockerfile`
- `streamlit` from `streamlit/Dockerfile`
- managed `Postgres` service
- managed `Redis` service

Environment variables needed:

- Shared app/runtime:
  - `LLM_PROVIDER=gemini`
  - `LOCAL_LLM_FAST_MODE=false`
  - `GEMINI_MODEL=gemini-2.5-flash`
  - `GEMINI_API_KEY` (secret)
  - `MOCK_LLM=false`
- Backend:
  - `DATABASE_URL`
  - `REDIS_URL`
  - `RAG_SERVICE_URL`
  - `JWT_SECRET` (secret)
  - `JWT_EXPIRATION_SECONDS=3600`
- Python RAG:
  - `DATABASE_URL`
  - `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`
  - `PORT=8000`
- Streamlit:
  - `API_BASE_URL`

Database/Redis setup:

- Railway managed Postgres service (ensure pgvector extension is enabled by app init)
- Railway managed Redis service

Expected public URLs:

- Backend: `https://<backend-domain>/`
- Python RAG: `https://<python-rag-domain>/`
- Streamlit: `https://<streamlit-domain>/`

### 1) Preflight checks (do this before any deploy)

Do not deploy blindly. Confirm CLI install and login state:

```bash
railway --version
railway whoami
```

If either command fails, install/login first and stop deployment until resolved.

### 2) Services to deploy

Create one service each:

- `backend` (Dockerfile: `backend/Dockerfile`)
- `python-rag` (Dockerfile: `services/python-rag/Dockerfile`)
- `streamlit` (optional separate service, Dockerfile: `streamlit/Dockerfile`)

Provision dependencies:

- PostgreSQL with pgvector support
- Redis

### 3) Environment variables

Start from `.env.railway.example`, then add real secret values in Railway:

- `DATABASE_URL` from Railway Postgres
- `REDIS_URL` from Railway Redis
- `JWT_SECRET` generated secret
- `GEMINI_API_KEY` as secret
- `LLM_PROVIDER=gemini`
- `LOCAL_LLM_FAST_MODE=false`
- `GEMINI_MODEL=gemini-2.5-flash`
- `MOCK_LLM=false`

Backend-specific:

- `RAG_SERVICE_URL=https://<python-rag-public-url>`

Streamlit-specific:

- `API_BASE_URL=https://<backend-public-url>`

### 4) Public URL routing

Railway services are independently routable:

- Backend public URL serves API endpoints (`/api/v1/*`, `/health`, `/metrics`)
- Python RAG public URL serves `/health`, `/ingest`, `/retrieve`, `/retrieve-all`
- Streamlit public URL is the demo UI

Ensure backend can reach python-rag via `RAG_SERVICE_URL`.

### 5) Observability in cloud

Prometheus/Grafana are optional in cloud unless you explicitly deploy them as services.
Local Prometheus/Grafana remains unchanged in Docker Compose.

### Live deployment notes (Railway)

Project:

- `DocuSynth Cloud Demo`

Deployed services:

- `backend`
- `python-rag`
- `streamlit`
- `Postgres`
- `Redis`

Public URLs:

- Backend: `https://backend-production-7d0a.up.railway.app`
- Python RAG: `https://python-rag-production-00f8.up.railway.app`
- Streamlit: `https://streamlit-production-4103.up.railway.app`

Validation command used:

```bash
BACKEND_URL='https://backend-production-7d0a.up.railway.app' \
RAG_URL='https://python-rag-production-00f8.up.railway.app' \
scripts/validate_deployment.sh
```

Validation result:

- backend `/health` OK
- python-rag `/health` OK
- login OK
- sample PDF ingest OK
- sample PDF query OK

## Render Deployment (Secondary Option)

Render supports Docker web services for:

- backend
- python-rag
- streamlit

Data services:

- Use Render managed Postgres/Redis, or external providers
- Confirm pgvector extension availability if using managed Postgres

Persistence:

- If any file-system persistence is required beyond DB/Redis, use persistent disks

Use the same cloud demo runtime mode variables (`LLM_PROVIDER=gemini`, `LOCAL_LLM_FAST_MODE=false`, secrets from env vars).

## Local Compose Compatibility

No changes are required to keep local Docker Compose working. Continue using:

- `.env.example` as base
- local Ollama runtime mode for validated local performance runs

## Post-Deploy Validation

Run:

```bash
scripts/validate_deployment.sh
```

By default it checks:

- backend `/health`
- python-rag `/health`
- login flow
- sample PDF ingest
- sample PDF query

Override URLs or credentials with environment variables if needed (see script header).
