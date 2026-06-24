# DocuSynth — Tech Stack

> Inventory of every technology actually present, why it's used, and whether the choice is appropriate. Sources: `backend/requirements.txt`, `services/python-rag/requirements.txt`, `requirements*.txt`, Dockerfiles, `docker-compose.yml`. Compiled 2026-06-24.

## Languages

| Language | Where | Notes |
|---|---|---|
| Python 3.11 | `backend/`, `services/python-rag/`, `streamlit/`, `tests/`, `scripts/` | Primary runtime (Dockerfiles use `python:3.11-slim`). |
| Go 1.22 | `services/go-backend/` | **Archived** (`ARCHIVED.md`), not in compose. Dead code. |
| C++ | `services/go-backend/internal/cache/fastcache/semantic_cache.cpp` | Archived native cache. Dead code. |
| SQL | `backend/app/db/migrations_or_init.sql` | Postgres init script. |

## Frameworks

| Framework | Where | Why | Appropriate? |
|---|---|---|---|
| FastAPI | both services | Async REST, Pydantic validation, OpenAPI | ✅ Good fit. |
| Streamlit | `streamlit/app.py`, `streamlit_cloud_app.py` | Zero-build demo UI | ✅ For a demo. ❌ if a real product frontend is wanted. |
| SQLAlchemy 2.0 (ORM) | both services | DB access | ✅ Solid; but schema is defined 3× (ORM ×2 + init SQL) — see `DECISIONS.md`. |
| Pydantic v2 / pydantic-settings | both | Models + env config | ✅ Idiomatic. |

## Libraries (Python)

| Library | Role | Appropriate? |
|---|---|---|
| `httpx` | async HTTP to RAG service + LLM providers | ✅ |
| `redis` | exact cache + rate limit | ✅ |
| `pgvector` (sqlalchemy) | vector column + cosine distance | ✅ |
| `psycopg[binary]` 3 | Postgres driver | ✅ |
| `PyJWT` | HS256 tokens | ✅ |
| `passlib[bcrypt]` + `bcrypt<4.1` | password hashing | ✅ (pinned `<4.1` to dodge passlib/bcrypt incompatibility — a known footgun, correctly handled). |
| `prometheus-client` | metrics | ✅ |
| `transformers` + `torch` (CPU) | embeddings | ⚠️ Heavy. `sentence-transformers` is also installed but the code uses raw `transformers` + manual mean pooling (`transformer.py`). Pick one; `sentence-transformers` would be simpler and apply correct pooling/normalization for the bge model. |
| `PyPDF2` | PDF inspection/text extraction (RAG) | ❌ Deprecated. Migrate to `pypdf` (already used in the cloud app). |
| `pdfplumber` | layout/table extraction | ✅ |
| `pytesseract` + `pdf2image` + system `tesseract-ocr`/`poppler-utils` | scanned OCR | ✅ |
| `Pillow` | image handling | ✅ |
| `pypdf` | cloud demo PDF parsing | ✅ |
| `google-generativeai` | cloud demo Gemini client | ✅ (note: the *backend* calls Gemini via raw REST in `llm_client.py`, not this SDK — two different integration styles). |
| `requests` | Streamlit → backend | ✅ |

## Database

- **PostgreSQL 16 + pgvector** (`pgvector/pgvector:pg16`). Stores chunks, semantic cache, users, documents, query logs, audit logs. Embeddings are `vector(384)`.
- **No ANN index** (no IVFFlat/HNSW) → exact scan. ⚠️ Appropriate for demo, not for scale.
- **No migration tool** (Alembic absent). Schema via init SQL + `create_all`. ⚠️ Should adopt Alembic.

## Caching

- **Redis 7-alpine** — exact response cache (TTL 3600 s) + fixed-window rate-limit counters. ✅ appropriate; rate-limit math is misleading (see `IMPLEMENTATION_STATUS.md`).
- **pgvector semantic cache** — cosine-NN over cached query embeddings. ✅ novel/useful; ⚠️ no eviction, no content-aware invalidation.

## Auth

- **JWT (HS256)** + **bcrypt**. ✅ standard. ⚠️ No refresh/rotation/blacklist; `iss` set but unverified; demo user auto-seeded.

## Storage

- Documents are **not** persisted as files — only extracted chunks + embeddings are stored in Postgres. No object store (S3/GCS). Uploaded bytes are processed in-memory then discarded. ✅ fine for Q&A; ❌ if re-processing/originals are ever needed.

## LLM / AI Tooling

| Provider | How | Why | Appropriate? |
|---|---|---|---|
| Ollama (`qwen2.5:3b`) | OpenAI-compatible REST via `host.docker.internal` | Free, offline, reproducible benchmarks | ✅ for local/benchmark. |
| Google Gemini | raw REST (`generativelanguage`) | Cloud demo answering + chairman | ✅; model ids (`gemini-2.5-flash`, `gemini-3-flash-preview`) should be verified against the live Gemini API before relying on them. |
| OpenRouter (free council models) | OpenAI-compatible REST | Multi-model council | ⚠️ "free" model ids drift/expire frequently; brittle. |
| HF `BAAI/bge-small-en-v1.5` | local embeddings | Free 384-dim embeddings | ⚠️ Used via generic mean pooling without bge's recommended query-instruction prefix/normalization — likely suboptimal retrieval quality. |

> When configuring or extending the LLM layer, consult the project's `claude-api` skill / current provider docs for valid model ids and parameters before hardcoding new ones — several ids here look forward-dated and should be confirmed.

## Deployment

- **Docker Compose** (local, 6 services + test profile). ✅ well-structured (healthchecks, `depends_on: service_healthy`, named volumes, bind-mounted init SQL/monitoring config).
- **Railway / Render** (cloud, documented in `docs/deployment.md`). ⚠️ Live status unverified/contradicted.
- **Streamlit Community Cloud** (standalone demo). ✅ clean separation.
- Dockerfiles: backend slim + OCR deps; RAG installs CPU torch first (smart for build size). ✅

## DevOps / CI

- **None.** No `.github/workflows`, no GitLab CI, no pre-commit, no linter/formatter config (no `ruff`/`black`/`flake8`/`mypy` config files found). ❌ First gap to close.
- `Makefile` provides `up/down/restart/logs/health/test/smoke/benchmark/streamlit/clean-benchmark`. ✅ handy local DX.

## Monitoring / Logging

- **Prometheus** scrapes `backend:8080/metrics` only (RAG service is **not** scraped). ⚠️
- **Grafana** with provisioned datasource + dashboard (`monitoring/grafana/`). ✅
- **Logging:** stdlib `logging` to stdout (structured-ish tagged JSON via `audit/logger.py`), plus optional `audit_logs` DB writes. ⚠️ No centralized log aggregation, no request IDs/trace correlation.

## Testing Tools

- **pytest** + FastAPI `TestClient`. 6 backend unit test files, all mock-based (`tests/conftest.py` provides a `FakeDB` and dependency overrides). ✅ for control-plane logic.
- **Benchmark/stress harnesses:** `tests/bench_semantic_cache.py` (active), `bench_semantic_accuracy.py`, `bench_document_chunking.py`, `stress_concurrency.py`. ✅ a real strength.
- **No tests** for the python-rag service (OCR, chunking, embeddings, retrieval) or the council orchestrator/LLM client. ❌ See `IMPLEMENTATION_STATUS.md`.

## Should any choice change?

| Change | Recommendation | Priority |
|---|---|---|
| `PyPDF2` → `pypdf` | Yes; PyPDF2 is deprecated and `pypdf` already in repo | P1 |
| `transformers`+manual pooling → `sentence-transformers` | Yes; correct pooling/normalization for bge, less code | P2 |
| Add Alembic | Yes; eliminate 3-way schema definition | P1 |
| Add ANN index (HNSW) | Yes before any scale | P2 |
| Add CI + ruff + mypy | Yes; cheapest big win for quality | P1 |
| Scrape RAG `/metrics` | Yes; add `/metrics` to RAG | P2 |
| Remove Go backend + committed `.venv311/` | Yes; repo hygiene | P0 |
| Streamlit → real frontend | Only if pursuing a product, not portfolio | P3 |
| Pin/verify LLM model ids | Yes; OpenRouter "free" ids + forward-dated Gemini ids are brittle | P1 |
