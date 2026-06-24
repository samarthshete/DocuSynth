# DocuSynth — Onboarding for AI Agents

> Read this first if you are a future Claude/Cursor/Codex agent working on DocuSynth. It is the fast path to being productive without breaking things. Compiled 2026-06-24. Verify any file/flag still exists before acting on it.

## 1. Project Summary (30 seconds)

DocuSynth is a **two-service FastAPI RAG system**: a control plane (`backend/`, port 8080) and a RAG service (`services/python-rag/`, port 8000→8001), sharing one **PostgreSQL+pgvector** DB and **Redis**. It ingests PDFs/images, embeds + stores chunks, retrieves by cosine similarity, answers with a configurable LLM (Ollama / Gemini / OpenRouter "council"), and serves repeated/paraphrased queries from a **two-tier cache** (Redis exact + pgvector semantic). UI is **Streamlit**. Observability via **Prometheus + Grafana**. A separate `streamlit_cloud_app.py` is a standalone, dependency-light public demo.

Read `PROJECT_MASTER.md` and `ARCHITECTURE.md` for depth; `IMPLEMENTATION_STATUS.md` for what's broken.

## 2. Important Files (the 20% that matters)

| Path | What |
|---|---|
| `backend/app/api/query.py` | **The core.** Cache cascade → retrieval → council → response + timings. Start here. |
| `backend/app/council/orchestrator.py` | LLM mode selection (single_local_fast / single_response / peer_review / full_council). |
| `backend/app/council/llm_client.py` | Provider abstraction (Ollama/Gemini/OpenRouter). |
| `backend/app/cache/semantic_cache.py` | pgvector semantic cache (note: no invalidation/eviction). |
| `backend/app/cache/redis_cache.py` | Exact cache + rate limit (note: rate-limit math is misleading). |
| `backend/app/config.py` | All backend settings + env mapping. |
| `backend/app/db/models.py` + `migrations_or_init.sql` | Schema (defined in 3 places — careful). |
| `services/python-rag/app/routers/ingest.py` | Ingest pipeline orchestration. |
| `services/python-rag/app/ocr/router.py` | Adaptive OCR routing. |
| `services/python-rag/app/chunking/layout_chunker.py` | Chunking logic. |
| `services/python-rag/app/embedding/transformer.py` | Embeddings (384-dim, mean pooling). |
| `services/python-rag/app/retrieval/pgvector_store.py` | Vector ingest/retrieve. |
| `streamlit/app.py` | Full UI. |
| `docker-compose.yml`, `Makefile` | How everything runs locally. |
| `tests/bench_semantic_cache.py` | Authoritative benchmark harness. |
| `docs/IMPLEMENTATION_STATUS.md` | Read before changing anything. |

## 3. How to Run Locally

```bash
ollama pull qwen2.5:3b          # local LLM (validated mode)
cp .env.example .env            # then set JWT_SECRET, POSTGRES_* etc.
make up                         # postgres, redis, python-rag, backend, prometheus, grafana
make health                     # backend :8080, rag :8001, prometheus :9091
make streamlit                  # UI on :8501
```
- Default login: `demo / demo123` (auto-seeded at startup).
- Run tests: `make test` (dockerized) or `pytest -q tests` with `PYTHONPATH` including `backend/`.
- Benchmark: `make benchmark`.
- ⚠️ **`MOCK_LLM` defaults to `true`** — set `MOCK_LLM=false` (and a real provider) for genuine answers.

URLs: backend `:8080`, rag `:8001`, prometheus `:9091`, grafana `:3000`, streamlit `:8501`, ollama `:11434`.

## 4. How the App Works (data flow)

- **Ingest:** Streamlit → `backend /api/v1/ingest` → `python-rag /ingest` (inspect → OCR route → chunk → embed → store in `chunks`) → backend writes a `documents` row.
- **Query:** Streamlit → `backend /api/v1/query` → Redis exact cache → (miss) embed via `python-rag /embed` → pgvector semantic cache → (miss) `python-rag /retrieve` → `run_council()` LLM → cache + persist → response with `timings`, `cache_result`, `similarity_score`, `llm_call_count`.

## 5. Current Status (honest)

Working local prototype with real benchmarks. Key problems to be aware of (full list in `IMPLEMENTATION_STATUS.md`):
- README benchmark numbers **don't match** `tests/benchmark_results.json` (trust the JSON).
- `.venv311/` is **committed** (≈4,300 files, 387 MB repo) — do not add more.
- Semantic cache never invalidates on re-ingest and never evicts.
- No document ownership enforcement; RAG service is unauthenticated; CORS is `*`.
- No ANN index (exact vector scans); no Alembic; no CI; no RAG-service tests.
- Archived Go backend (`services/go-backend/`) and dead `backend/app/rag/{chunker,ocr,parser}.py`.

## 6. Coding Conventions (match the existing code)

- Python 3.11, FastAPI + Pydantic v2 + SQLAlchemy 2.0 (typed `Mapped[...]`).
- `pydantic-settings` `Settings` + `@lru_cache get_settings()` for config; read env, never hardcode secrets.
- Tagged structured logging via `app.audit.logger.log_tagged("[Tag]", {...})`.
- Prometheus: metric **names** are `docusynth_*` even though Python **variables** are `councilai_*` — keep that pattern if editing `metrics/prometheus.py`.
- Async route handlers; `httpx.AsyncClient` for outbound HTTP with explicit timeouts.
- Errors → `HTTPException` with specific status codes (404 no chunks, 502 council, 503 retrieval).
- Tests use the `client` fixture + `monkeypatch` to stub `query_api.*` (see `tests/conftest.py`, `tests/test_query.py`).

## 7. Where to Add New Features

| You want to… | Put it in… |
|---|---|
| New API endpoint (control plane) | `backend/app/api/` + register router in `backend/app/main.py` |
| New LLM provider or council behavior | `backend/app/council/llm_client.py` / `orchestrator.py` |
| New caching behavior | `backend/app/cache/` |
| New OCR/chunking/embedding/retrieval logic | `services/python-rag/app/{ocr,chunking,embedding,retrieval}/` |
| New metric | `backend/app/metrics/prometheus.py` (and emit it where relevant) |
| New DB table/column | ORM model **and** `migrations_or_init.sql` (until Alembic exists) — keep them in sync |
| UI change | `streamlit/app.py` (full) or `streamlit_cloud_app.py` (standalone demo) |

## 8. What NOT to Touch Without Review

- `tests/benchmark_results.json` and `docs/benchmarks/*` — these are published evidence; regenerate via `make benchmark`, don't hand-edit.
- The semantic-cache key/threshold logic (`semantic_cache.py`, `SEMANTIC_CACHE_THRESHOLD=0.85`) — changing it invalidates published numbers; re-benchmark if you do.
- Embedding dimension (384) — it's hardcoded in two `vector(384)` columns and the init SQL; changing the model/dim requires a coordinated migration.
- `docker-compose.yml` ports/healthchecks — other docs and scripts assume these exact ports.
- The schema's three definitions — if you edit one, edit all three (or introduce Alembic first).
- Anything in `services/go-backend/` — archived; don't revive it.

## 9. Common Mistakes to Avoid

1. Assuming real answers on first run — `MOCK_LLM=true` by default returns mock strings.
2. Quoting README's 69.7× speedup — it contradicts the committed JSON (28.91×).
3. Committing files into `.venv311/` or adding new venvs — the repo is already bloated.
4. Editing the ORM but not `migrations_or_init.sql` (or vice versa) → schema drift.
5. Adding a feature that reads the DB from the backend instead of via the RAG API — the boundary is already leaky; don't make it worse.
6. Expecting the RAG service in Prometheus — it isn't scraped.
7. Trusting the LLM model id defaults (`gemini-3-flash-preview`, OpenRouter "free" ids) — verify they exist before relying on them; consult the `claude-api` skill / provider docs for Anthropic/LLM specifics.
8. Inventing benchmark numbers — only report what a committed JSON contains (see `METRICS_AND_OUTCOMES.md`).

## 10. Next Best Tasks (ranked)

1. **P0** Untrack `.venv311/`; add `.venv*` to `.gitignore`.
2. **P0** Reconcile README ↔ `benchmark_results.json` (regenerate prose from JSON).
3. **P0** Verify or remove the live Railway URLs in `docs/deployment.md`.
4. **P1** Cache invalidation on re-ingest (correctness) — `semantic_cache.py` + ingest path.
5. **P1** Enforce document ownership + secure the RAG service + restrict CORS.
6. **P1** Fix rate-limit semantics; add CI + ruff/mypy; add first RAG-service tests.
7. **P2** HNSW index + semantic-cache eviction; scrape RAG `/metrics`; adopt Alembic.

See `ROADMAP.md` for the full phased plan and Definitions of Done.
