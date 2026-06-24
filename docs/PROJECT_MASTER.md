# DocuSynth — Project Master Document

> Single source of truth for what DocuSynth is, why it exists, how it is built, and where it stands.
> Everything here is derived from the actual repository. Where the code does not establish a fact, it is marked **"Not found in current codebase."**
> Last compiled from source: 2026-06-24.

---

## 1. Project Name

**DocuSynth** — "Dockerized RAG Document Intelligence Platform" (per `README.md:1`).

Note: the codebase carries a previous identity, **CouncilAI**. Evidence:
- `services/go-backend/ARCHIVED.md` and `services/go-backend/go.mod` (`module github.com/regular-life/CouncilAI/go-backend`).
- All Python Prometheus metric *variable names* are still prefixed `councilai_*` even though the emitted metric names are `docusynth_*` (`backend/app/metrics/prometheus.py`).
- JWT issuer claim is still `"iss": "councilai"` (`backend/app/auth/jwt.py:22`).
- `README.md:262` explicitly says "DocuSynth supersedes the older CouncilAI branding/runtime."

## 2. One-Line Description

A multi-service, containerized Retrieval-Augmented Generation (RAG) system that ingests PDFs/images, retrieves relevant context from PostgreSQL/pgvector, answers questions with a configurable LLM backend (local Ollama, Gemini, or an OpenRouter multi-model "council"), and serves repeated/paraphrased queries from a two-tier cache (Redis exact + pgvector semantic), with Prometheus/Grafana observability.

## 3. Product Vision

Be a self-hostable, observable, benchmarked reference architecture for document-grounded question answering — one that proves measurable latency/cost wins from semantic caching and can run fully offline on local infrastructure (Ollama) or in the cloud (Gemini).

This is, in its current form, primarily a **portfolio / reference-architecture project** rather than a commercial product. `README.md:5` states it is "suitable for real engineering portfolios."

## 4. Problem Being Solved

1. **Document Q&A grounding** — answering questions strictly from the contents of uploaded documents (RAG), instead of from an LLM's parametric memory.
2. **Repeated/paraphrased query cost** — naive RAG re-runs embedding + retrieval + an expensive LLM call for every query, even when a near-identical question was already answered. DocuSynth adds an exact cache (Redis) and a semantic cache (pgvector cosine similarity) to cut LLM calls and latency.
3. **Lack of observability in RAG demos** — most demos are black boxes. DocuSynth instruments every stage (Redis lookup, embedding, pgvector lookup, retrieval, LLM) and exports it to Prometheus/Grafana.

## 5. Why This Problem Matters

- LLM inference is the dominant cost and latency contributor in a RAG pipeline. The committed benchmark (`tests/benchmark_results.json`) measures cold-path p50 ≈ 6.2 s vs semantic-cache-hit p50 ≈ 0.12 s — a large, real difference.
- Cost/latency reduction via caching is directly relevant to anyone operating RAG at scale.
- Grounding + observability are prerequisites for trustworthy enterprise document intelligence.

## 6. Target Users

Inferred from features and UI (`streamlit/app.py`), not from any stated persona doc:
- **Engineers/learners** studying or demonstrating production-style RAG architecture (primary; this is the portfolio framing).
- **Knowledge workers / students** uploading documents and asking questions, generating explanations, and auto-generating practice questions (the three Streamlit tabs: Ask / Explain / Generate Questions).
- **Self-hosters** wanting an offline RAG stack (Ollama mode).

No authentication tiers, organizations, or multi-tenant roles exist beyond a single flat `users` table.

## 7. Main User Workflows

From `streamlit/app.py` and the backend API:
1. **Login/Register** → receive JWT (`POST /api/v1/login`, `/register`).
2. **Ingest a document** → upload PDF/PNG/JPG (`POST /api/v1/ingest`) → backend proxies to the RAG service, which inspects → routes OCR → chunks → embeds → stores in pgvector.
3. **Ask** → `POST /api/v1/query` with `doc_id` + `question`; returns a grounded answer with confidence, source, cache status, and per-stage timings.
4. **Explain** → `POST /api/v1/explain` generates a leveled (beginner/intermediate/advanced) explanation of the whole document.
5. **Generate Questions** → `POST /api/v1/generate-questions` produces subjective or MCQ practice questions with answers/explanations.

## 8. Initial Idea and How the Project Evolved

Reconstructed from artifacts (no design history doc exists):
1. **CouncilAI / Go era** — an earlier implementation in Go (`services/go-backend/`) with its own LLM clients (Gemini, OpenRouter), a "chairman" synthesizer, Redis cache, JWT auth, rate limiting, and a native C++ semantic cache (`internal/cache/fastcache/semantic_cache.cpp`). Now archived (`ARCHIVED.md`), not in `docker-compose.yml`.
2. **Python rewrite (DocuSynth)** — the active control plane was re-implemented in Python 3.11 + FastAPI (`backend/`), with a dedicated Python RAG microservice (`services/python-rag/`).
3. **Multi-provider LLM "council"** — the orchestrator (`backend/app/council/`) supports generating multiple candidate answers, peer review, and chairman synthesis (OpenRouter free models + Gemini chairman).
4. **Local-fast benchmark mode** — to produce reproducible, offline numbers, a `single_local_fast` path using Ollama `qwen2.5:3b` was added; the published benchmark uses this mode.
5. **Cloud demo split** — a standalone, dependency-light Streamlit app (`streamlit_cloud_app.py`) was added for free Streamlit Community Cloud hosting (keyword retrieval + optional Gemini), deliberately decoupled from the Docker stack.

## 9. Current State of the Project

**Working, locally runnable, multi-service prototype** with real benchmarks. Concretely:
- Backend control plane, RAG service, Postgres/pgvector, Redis, Prometheus, Grafana, and Streamlit all defined and wired in `docker-compose.yml`.
- Full ingest→retrieve→cache→answer path is implemented and exercised by a 908-line benchmark harness (`tests/bench_semantic_cache.py`) that produced `tests/benchmark_results.json`.
- Unit tests exist for the backend control plane (6 test files, all mock-based).

**Caveats on "current state" (evidence-based):**
- The repo ships a committed virtualenv `.venv311/` (≈4,303 tracked files; repo is 387 MB). This dwarfs the actual source.
- README headline benchmark numbers **do not match** the committed `benchmark_results.json` (see §22 and `METRICS_AND_OUTCOMES.md`).
- `docs/deployment.md` lists live Railway URLs, but `README.md:250` says the repo "does **not** claim an already-live public deployment." These contradict; live status is unverified.
- Default `MOCK_LLM=true` (`backend/app/config.py:14`, `docker-compose.yml:16`): out-of-the-box, the council returns mock answers unless explicitly disabled.

## 10. Final Intended Product

A deployable, observable RAG platform that:
- Runs identically offline (Ollama) and in cloud (Gemini), switched by env vars.
- Demonstrably reduces LLM calls and latency via semantic caching, with the savings visible in Grafana.
- Supports document Q&A, explanation, and assessment generation.

No formal PRD or roadmap file exists in the repo; this is inferred from `README.md` and `docs/deployment.md`.

## 11. Core Features

| Feature | Where | Status |
|---|---|---|
| JWT auth (login/register, bcrypt) | `backend/app/api/auth.py`, `backend/app/auth/` | Implemented |
| PDF/image ingestion pipeline | `services/python-rag/app/routers/ingest.py` | Implemented |
| Adaptive OCR routing (direct text / pdfplumber / Tesseract) | `services/python-rag/app/ocr/` | Implemented |
| Layout-aware chunking | `services/python-rag/app/chunking/layout_chunker.py` | Implemented |
| Local transformer embeddings (384-dim) | `services/python-rag/app/embedding/transformer.py` | Implemented |
| pgvector semantic retrieval | `services/python-rag/app/retrieval/pgvector_store.py` | Implemented |
| Redis exact cache | `backend/app/cache/redis_cache.py` | Implemented |
| pgvector semantic cache | `backend/app/cache/semantic_cache.py` | Implemented |
| Multi-provider LLM client (Ollama/Gemini/OpenRouter) | `backend/app/council/llm_client.py` | Implemented |
| LLM "council" (generate→review→chairman) | `backend/app/council/orchestrator.py` | Implemented |
| Query / Explain / Generate-Questions endpoints | `backend/app/api/query.py` | Implemented |
| Rate limiting | `backend/app/cache/redis_cache.py` | Implemented (misnamed; see §17) |
| Prometheus metrics + Grafana dashboard | `backend/app/metrics/prometheus.py`, `monitoring/` | Implemented |
| Audit logging (stdout + DB) | `backend/app/audit/logger.py` | Implemented |
| Streamlit UI (full platform) | `streamlit/app.py` | Implemented |
| Standalone cloud demo (keyword retrieval + Gemini) | `streamlit_cloud_app.py` | Implemented |
| Benchmark harness | `tests/bench_semantic_cache.py` | Implemented |

## 12. MVP Scope

The MVP is effectively already met locally: ingest a PDF, ask a question, get a grounded answer, observe cache hits and metrics. The end-to-end happy path is implemented and benchmarked.

## 13. Non-MVP / Future Scope

Not present in the repo; proposed in `ROADMAP.md`. Includes: cloud deployment hardening, document/user ownership enforcement, cache invalidation on re-ingest, CI, RAG-service tests, embedding normalization, real persona/PRD, and removal of dead code (Go backend, committed venv).

## 14. Full Technical Architecture

Two FastAPI services share one PostgreSQL/pgvector database and a Redis instance.

```
Streamlit UI ──HTTP──▶ backend (FastAPI, :8080)
                          │  auth, rate limit, cache decisions, council orchestration, metrics
            ┌─────────────┼───────────────────────────┐
            ▼             ▼                            ▼
        Redis        python-rag (FastAPI, :8000)     LLM provider
       (exact          ingest / retrieve / embed     (Ollama | Gemini | OpenRouter)
        cache +              │
        rate limit)          ▼
                       PostgreSQL + pgvector  ◀── also read directly by backend
                       (chunks, semantic_cache, users, query_logs, audit_logs, ...)
                          ▲
        Prometheus ──────scrape backend:8080/metrics──────▶ Grafana
```

See `ARCHITECTURE.md` for the detailed Mermaid diagram, request lifecycle, and failure analysis.

## 15. Frontend Architecture

- **Full UI:** `streamlit/app.py` — a single-file Streamlit app. Session state holds the JWT, `doc_id`, and chat/explain/questions history. It talks to the backend via `requests` against `API_BASE_URL` (default `http://localhost:8080`). Three tabs: Ask, Explain, Generate Questions. No build step, no SPA framework.
- **Cloud demo UI:** `streamlit_cloud_app.py` — fully standalone; does PDF text extraction (`pypdf`), fixed-size overlapping chunking, **keyword (token-overlap) retrieval — not embeddings**, and optional Gemini answering. This is a deliberately simplified, separate codepath (`README.md:124-137`).

There is no React/Next.js/Vue frontend. "Frontend architecture" = Streamlit.

## 16. Backend Architecture

Two services:

**A) `backend/` — control plane (FastAPI, port 8080)**
- `app/main.py` — app factory, CORS (`*`), HTTP logging+metrics middleware, global exception handler, startup that calls `init_db()` and seeds a `demo/demo123` user.
- `app/api/` — routers: `auth`, `documents` (ingest proxy), `query` (query/explain/generate-questions), `admin` (clear-cache), `health`, `metrics`.
- `app/auth/` — `jwt.py` (HS256, HTTPBearer), `security.py` (bcrypt via passlib).
- `app/cache/` — `redis_cache.py` (exact cache, rate limit), `semantic_cache.py` (pgvector cosine).
- `app/council/` — `orchestrator.py`, `generator.py`, `reviewer.py`, `synthesizer.py`, `llm_client.py`, `instrumentation.py`.
- `app/rag/` — `embeddings.py`, `retrieval.py` (HTTP clients to the RAG service). **Note:** `app/rag/` also contains `chunker.py`, `ocr.py`, `parser.py` which are *not imported anywhere in the active path* (likely legacy; the real OCR/chunking lives in the RAG service).
- `app/db/` — `models.py` (ORM), `session.py` (engine/init), `migrations_or_init.sql` (mounted into Postgres on first boot).
- `app/metrics/prometheus.py` — all counters/histograms.
- `app/audit/logger.py` — tagged JSON logging, optional DB write.

**B) `services/python-rag/` — RAG service (FastAPI, port 8000→8001)**
- `app/main.py` — lifespan preloads the embedding model.
- `app/routers/` — `ingest`, `retrieve`, `retrieve_all`, `embed`.
- `app/inspection/inspector.py` — PDF/image heuristics (text layer, scanned, tables, multicolumn).
- `app/ocr/` — `router.py` (adaptive routing), `tesseract.py`, `layout_aware.py` (pdfplumber), `interface.py`, plus a `DirectTextExtractor`.
- `app/chunking/layout_chunker.py` — structure-preserving chunking.
- `app/embedding/transformer.py` — HF transformers + mean pooling, class-level model cache.
- `app/retrieval/pgvector_store.py` — ingest/retrieve/retrieve_all against pgvector.
- `app/db.py` — its own engine + `ChunkRecord` ORM (same `chunks` table the backend also defines).

## 17. Database / Data Model

PostgreSQL 16 with the `pgvector` extension (`pgvector/pgvector:pg16`). Schema is created **two ways** (a known smell): (a) `backend/app/db/migrations_or_init.sql` mounted as a Docker init script, and (b) `Base.metadata.create_all()` in both services. Tables (`backend/app/db/models.py`, init SQL):

- `users(id, username unique, password_hash, created_at)`
- `documents(id PK str, filename, owner_id, metadata_json, created_at)`
- `chunks(id, document_id, chunk_text, page_number, metadata_json, embedding vector(384), created_at)` — written by the RAG service (`ChunkRecord`), also modeled by the backend (`Chunk`).
- `query_logs(id, user_id, document_id, query_hash, status, latency_ms, created_at)`
- `council_responses(id, query_log_id FK, model_name, response_text, stage, created_at)` — **table exists but no code writes to it** (dead schema).
- `audit_logs(id, tag, payload jsonb, created_at)`
- `semantic_cache(id, document_id, normalized_query, response_json jsonb, embedding vector(384), created_at)`

Indexes: `chunks(document_id)`, `semantic_cache(document_id)`. **No ANN/IVFFlat/HNSW index on either `embedding` column** — vector search is exact (sequential) scan. Fine at demo scale, a scalability cliff at volume (see `IMPLEMENTATION_STATUS.md`).

## 18. API Design

REST/JSON under `/api/v1` (control plane):
- `POST /login`, `POST /register` → `{token, user_id}`
- `POST /ingest` (multipart) → `{doc_id, chunk_count, metadata, message}`
- `POST /query` → answer + `{confidence, source, cache_result, similarity_score, llm_call_count, timings, ...}`
- `POST /explain` → `{explanation, confidence, source, ...}`
- `POST /generate-questions` → `{questions[], raw_output, ...}`
- `POST /admin/clear-cache` (JWT) → flushes Redis + clears semantic cache
- `GET /health`, `GET /metrics`

RAG service: `POST /ingest`, `POST /retrieve`, `POST /retrieve-all`, `POST /embed`, `GET /health`. No OpenAPI version negotiation; no pagination; no list/delete document endpoints.

## 19. Auth / Session Flow

- `POST /login` verifies bcrypt password, returns HS256 JWT (`create_token`, `backend/app/auth/jwt.py`) with `user_id`, `iat`, `exp` (default 3600 s), `iss="councilai"`.
- Protected routes use `HTTPBearer` → `decode_token` → DB lookup of the user (`get_current_user`).
- No refresh tokens, no logout/blacklist (logout is client-side only in Streamlit), no roles/scopes, no token rotation. `iss` is set but never verified.
- A `demo/demo123` user is auto-seeded at backend startup (`backend/app/main.py:32-36`).

## 20. Agent / AI / LLM Flow

`run_council()` (`backend/app/council/orchestrator.py`) chooses a mode:
1. **`single_local_fast`** — if `LLM_PROVIDER=ollama` and `LOCAL_LLM_FAST_MODE=true`: one Ollama call, `max_tokens=128`, `temperature=0`. (This is the benchmarked mode.)
2. Otherwise **generate candidates** from `COUNCIL_MODEL_1..3` in parallel (`collect_candidates`). If only one valid → `single_response`.
3. **Peer review** — each candidate model reviews the anonymized answers (`reviewer.py`). If `skip_chairman` (used by generate-questions) → return longest candidate (`peer_review_no_chairman`).
4. **Chairman synthesis** — `CHAIRMAN_MODEL` (default `gemini-3-flash-preview`) merges responses+reviews into JSON (`synthesizer.py`); on failure, falls back to the longest candidate (`full_council`).

`MOCK_LLM=true` short-circuits generation/synthesis with canned strings (`generator.py:30`, `synthesizer.py:25`). Per-request LLM call counting/timing via `instrumentation.py` (contextvar). Provider selection and request shaping (Ollama/OpenAI-compat, Gemini, OpenRouter) live in `llm_client.py`.

**Confidence values are hardcoded heuristics** (e.g., 0.6 for single_local_fast, 0.99 for mock chairman) — they are not calibrated.

## 21. External Services Used

- **Ollama** (local LLM, `qwen2.5:3b`) — runs on the host, reached via `host.docker.internal:11434`.
- **Google Gemini** (`gemini-2.5-flash`, chairman `gemini-3-flash-preview`) — requires `GEMINI_API_KEY`.
- **OpenRouter** (free council models) — requires `OPENROUTER_API_KEY`.
- **Hugging Face** model download for embeddings (`BAAI/bge-small-en-v1.5`) at RAG startup.
- **Docker images:** `pgvector/pgvector:pg16`, `redis:7-alpine`, `prom/prometheus:latest`, `grafana/grafana:latest`.

## 22. Deployment Architecture

- **Local (validated):** `docker-compose.yml` brings up backend, python-rag, postgres, redis, prometheus, grafana (+ a `test` profile, + Streamlit run separately via `make streamlit`). Ollama runs on the host.
- **Cloud:** `docs/deployment.md` documents Railway (primary) and Render (secondary): deploy backend/python-rag/streamlit as Docker services, provision managed Postgres (pgvector) + Redis, switch to Gemini mode. `.env.railway.example` provided. `scripts/validate_deployment.sh` smoke-tests health/login/ingest/query.
- **Free demo:** `streamlit_cloud_app.py` on Streamlit Community Cloud (`requirements-streamlit-cloud.txt`).

**Contradiction to resolve:** `docs/deployment.md:154-188` lists specific live Railway URLs and "validation result … passed," while `README.md:250` states no live deployment is claimed. Treat live status as **unverified** until reconfirmed.

## 23. Security Considerations

Honest assessment (details in `IMPLEMENTATION_STATUS.md`/`DECISIONS.md`):
- ✅ Passwords bcrypt-hashed; secrets via env; `.env` gitignored and **never committed** (verified via git history).
- ⚠️ **CORS `allow_origins=["*"]` with `allow_credentials=True`** on both services (`backend/app/main.py:18`, `services/python-rag/app/main.py:42`) — invalid/over-permissive combination.
- ⚠️ **No document ownership enforcement** — `documents.owner_id` is stored but never checked; any authenticated user can query/ingest under any `doc_id`. The RAG service has **no auth at all** (port 8001 must not be public).
- ⚠️ **Auto-seeded `demo/demo123`** must be disabled in production.
- ⚠️ **Rate limit is misleading**: `count <= rate_limit_rps * rate_limit_window_seconds` = 5×60 = **300 requests per 60 s fixed window per user**, not 5 rps; it also fails open on Redis errors.
- ⚠️ Self-registration is open (`/register`) with no password policy.
- ⚠️ Admin `clear-cache` is gated only by any valid JWT (`backend/app/api/admin.py` notes "restrict via network policy").
- ⚠️ Working-tree `.env` contains real `GEMINI_API_KEY`/`OPENROUTER_API_KEY` values — keep local; rotate if ever shared.

## 24. Performance Considerations

- Two-tier cache is the core perf feature; committed numbers (`tests/benchmark_results.json`): cold p50 ≈ 6202 ms / p95 ≈ 10377 ms; semantic-hit p50 ≈ 120 ms / p95 ≈ 359 ms; p95 speedup ≈ 28.9×; semantic hit rate 22.5%.
- Embeddings computed on CPU (`torch … cpu` wheel) — fine for demo, slow at scale; embedding is synchronous per text in a Python loop (`transformer.py`).
- Vector search has no ANN index → exact scan over `chunks`/`semantic_cache`.
- Backend↔RAG is HTTP per request (embedding and retrieval are separate round-trips).

## 25. Scalability Considerations

- Single Postgres shared by both services; no read replicas; no connection pool tuning beyond `pool_pre_ping`.
- Semantic cache **grows unbounded** (no TTL/eviction; `store_semantic` only inserts).
- Embedding model loaded per-process; `PgVectorStore()` is instantiated per request (cheap, since the model is class-cached, but still allocates).
- Stateless backend/RAG containers can scale horizontally if Postgres/Redis are externalized.
- No ANN index is the first hard scaling limit.

## 26. Accessibility Considerations

Not addressed in the codebase. Streamlit provides baseline semantics, but there is no a11y testing, ARIA work, contrast checking, or keyboard-nav validation. **Not found in current codebase.**

## 27. SEO / Agent-Readability Considerations

- No web SEO surface (Streamlit app, not a marketed website). **Not applicable.**
- Agent-readability: this `/docs` set (including `ONBOARDING_FOR_AI_AGENTS.md`) is the agent-facing surface. API has no published OpenAPI export file, though FastAPI serves `/docs` (Swagger) at runtime.

## 28. Known Limitations

1. README benchmark figures contradict the committed benchmark JSON.
2. `.venv311/` committed → 387 MB repo, ~4,300 tracked files.
3. No cache invalidation: re-ingesting a changed document leaves stale semantic-cache answers (cache keyed on query embedding + doc_id, **not** on retrieved content).
4. No vector ANN index; exact scan only.
5. No document ownership checks; RAG service unauthenticated.
6. Duplicate schema definitions (init SQL + two ORM layers) can drift.
7. `council_responses` table and `backend/app/rag/{chunker,ocr,parser}.py` appear to be dead code.
8. Default `MOCK_LLM=true` confuses first-run expectations.
9. No CI, no linting config, no RAG-service tests.
10. `PyPDF2` (deprecated) used in the RAG service.

## 29. Risks

- **Credibility risk:** mismatched benchmark numbers undermine the project's central selling point.
- **Correctness risk:** stale semantic-cache answers after document changes.
- **Security risk:** unauthenticated RAG service + no ownership checks if any of this is exposed publicly.
- **Operational risk:** unverified cloud deployment claims; unbounded cache growth.
- **Maintainability risk:** committed venv, dead code, branding drift (councilai/docusynth).

## 30. Open Questions

1. Is there a live Railway deployment right now, or should those URLs be removed from `docs/deployment.md`?
2. Which benchmark run is authoritative — and should `README.md` be regenerated from `benchmark_results.json`?
3. Is the multi-model "council" the intended production path, or is `single_local_fast`/Gemini the real target? (The council adds 5–7 LLM calls/query.)
4. Should the project remain a portfolio piece or be hardened toward a real product? (Drives `ROADMAP.md` priorities.)
5. Is `BAAI/bge-small-en-v1.5` actually being loaded, given `transformer.py` uses generic mean pooling without bge's recommended query prefix/normalization?

## 31. Final Outcome and Expected Impact

As-is, DocuSynth is a credible, runnable demonstration that **semantic caching delivers an order-of-magnitude latency reduction on repeated/paraphrased RAG queries**, with the savings visible in Grafana — a strong portfolio/reference artifact. With the cleanup and hardening in `ROADMAP.md` (honest benchmarks, repo slimming, cache invalidation, auth/ownership, ANN index, CI), it could become a genuinely deployable small-scale RAG service.

---

### Companion documents
- `ARCHITECTURE.md` — diagrams, request lifecycle, failure analysis
- `PRODUCT.md` — personas, stories, JTBD, metrics
- `TECH_STACK.md` — technology inventory + appropriateness review
- `IMPLEMENTATION_STATUS.md` — what's done/partial/broken/missing
- `DECISIONS.md` — decision log + alternatives
- `ROADMAP.md` — phased build plan
- `METRICS_AND_OUTCOMES.md` — measured vs. to-measure
- `ONBOARDING_FOR_AI_AGENTS.md` — fast-start for future AI agents
