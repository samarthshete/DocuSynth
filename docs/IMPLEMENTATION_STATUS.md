# DocuSynth — Implementation Status

> Brutally honest, evidence-based status of every meaningful piece. Compiled 2026-06-24 from the working tree.

## Legend
✅ Complete · 🟡 Partial · 🔴 Broken/risky · ⬜ Missing

## 1. Completed Features ✅

| Feature | Files | Evidence it works |
|---|---|---|
| JWT auth (login/register, bcrypt) | `backend/app/api/auth.py`, `backend/app/auth/{jwt,security}.py` | `tests/test_auth.py` passes login + token-claim checks |
| Exact Redis cache + key normalization | `backend/app/cache/redis_cache.py` | `tests/test_cache.py` asserts exact-hit short-circuits embedding |
| Semantic cache lookup/store (pgvector cosine) | `backend/app/cache/semantic_cache.py` | `tests/test_semantic_cache.py`; benchmark recorded 23 semantic hits |
| Query orchestration w/ per-stage timings | `backend/app/api/query.py` | `tests/test_query.py` checks structure + timings keys |
| Ingest proxy (backend→RAG) | `backend/app/api/documents.py` | `tests/test_ingest.py` |
| Full ingest pipeline (inspect→OCR→chunk→embed→store) | `services/python-rag/app/{inspection,ocr,chunking,embedding,retrieval}` | Benchmark ingested a doc and answered 122 queries, 0% error |
| Adaptive OCR routing | `services/python-rag/app/ocr/router.py` | Direct/pdfplumber/Tesseract backends implemented |
| Layout-aware chunking | `services/python-rag/app/chunking/layout_chunker.py` | Tables-as-one-chunk, heading merge, long-text split |
| Multi-provider LLM client | `backend/app/council/llm_client.py` | Ollama/Gemini/OpenRouter request+parse paths |
| Council orchestration modes | `backend/app/council/orchestrator.py` | 4 modes incl. single_local_fast (benchmarked) |
| Prometheus metrics + Grafana dashboard | `backend/app/metrics/prometheus.py`, `monitoring/` | `tests/test_metrics.py` asserts all metric names present |
| Health endpoints (deep) | `backend/app/api/health.py` | checks redis/postgres/rag |
| Streamlit UI (Ask/Explain/Questions) | `streamlit/app.py` | full flow wired |
| Standalone cloud demo | `streamlit_cloud_app.py` | keyword retrieval + optional Gemini |
| Benchmark + stress harnesses | `tests/bench_*.py`, `tests/stress_concurrency.py` | produced `benchmark_results.json` |
| Docker Compose stack | `docker-compose.yml`, Dockerfiles | healthchecks + dependencies |

## 2. Partially Completed 🟡

| Feature | Gap | Files |
|---|---|---|
| Explain / Generate-Questions | Work, but **bypass the semantic cache** (only exact-keyed Redis) and `sections` is always `[]` in `/explain` | `backend/app/api/query.py:272-413` |
| Rate limiting | Implemented but **semantics are wrong/misleading**: allows `rps*window` = 300 req/60 s, not 5 rps; **fails open** on Redis error | `backend/app/cache/redis_cache.py:56-65` |
| Document model | `documents` row created on ingest, but **no list/get/delete endpoints** and `owner_id` never enforced | `backend/app/api/documents.py`, `backend/app/db/models.py` |
| Observability coverage | Backend fully instrumented; **RAG service emits no metrics and isn't scraped** | `monitoring/prometheus.yml` |
| Embedding quality | `BAAI/bge-small-en-v1.5` loaded via generic mean pooling, no query-instruction prefix/normalization → likely suboptimal | `services/python-rag/app/embedding/transformer.py` |
| Cloud deployment | Documented + a validate script exists, but live status is **contradicted** (README vs deployment.md) and unverified | `docs/deployment.md`, `README.md:250` |
| Citations | Source chunks retrieved and returned as `candidates`, but the Streamlit UI doesn't surface document citations | `streamlit/app.py` |

## 3. Broken / Risky 🔴

| Issue | Why it's a problem | Files / evidence |
|---|---|---|
| **README benchmarks ≠ committed results** | README: cold p95 8798.772 ms, semantic p95 126.227 ms, **69.706×**. Actual JSON: 10377.144 ms, 358.951 ms, **28.91×**. Central claim is inconsistent | `README.md:83-99` vs `tests/benchmark_results.json` |
| **Stale semantic cache after re-ingest** | Cache keyed on (doc_id, query embedding), not chunk content; re-uploading a changed doc serves old answers as "hits" | `backend/app/cache/semantic_cache.py` |
| **Unbounded semantic cache** | No TTL/eviction; only inserts → DB bloat + slower exact-scan NN | `semantic_cache.py:47-62` |
| **RAG service has no auth** | If `:8001` is reachable, anyone can ingest/retrieve any doc | `services/python-rag/app/main.py` |
| **No document isolation** | Any authenticated user can query/ingest under any `doc_id` | `backend/app/api/query.py` (no ownership check) |
| **CORS `*` + `allow_credentials=True`** | Invalid/over-permissive combo on both services | `backend/app/main.py:18`, `services/python-rag/app/main.py:42` |
| **`MOCK_LLM=true` by default** | Out-of-the-box answers are mock strings; looks broken to a new user | `backend/app/config.py:14`, `docker-compose.yml:16` |
| **Forward-dated/"free" model ids** | `gemini-3-flash-preview`, OpenRouter free ids may not exist/expire → council fails silently to fallback | `backend/app/config.py:26-29` |

## 4. Missing Core Features ⬜

- ⬜ Document management API (list / get / delete / re-ingest).
- ⬜ Cache invalidation tied to document changes.
- ⬜ Per-user document ownership enforcement.
- ⬜ ANN vector index (HNSW/IVFFlat).
- ⬜ Database migrations (Alembic).
- ⬜ CI pipeline + linting/formatting/type-checking.
- ⬜ Tests for the python-rag service and the council orchestrator/LLM client.
- ⬜ Citations/source display in the UI.
- ⬜ Refresh tokens / logout invalidation / roles.
- ⬜ Retrieval reranking; answer-groundedness evaluation.
- ⬜ Object storage for original files (if needed).

## 5. Technical Debt

1. **`.venv311/` committed** (~4,300 tracked files; repo 387 MB). `.gitignore` ignores `.venv/` but not `.venv311/`. — `git ls-files | grep .venv311`.
2. **Archived Go/C++ backend still in-tree** (`services/go-backend/`, 24 tracked files).
3. **Dead code:** `backend/app/rag/{chunker.py,ocr.py,parser.py}` not imported on the active path; `council_responses` table has no writer.
4. **Schema defined 3×:** init SQL + backend ORM + RAG ORM, all running `create_all`. Drift risk.
5. **Branding drift:** metric variable names `councilai_*`, JWT `iss="councilai"`, Go module path `CouncilAI`, while product is DocuSynth.
6. **Two embedding integration styles** (`transformers` manual vs `sentence-transformers` installed-but-unused).
7. **Two Gemini integration styles** (backend raw REST vs cloud demo SDK).
8. **`PyPDF2` deprecated**; `.DS_Store`, `.pytest_cache`, `.pycache` present locally (mostly gitignored, but `.pycache/` contains absolute-path artifacts).
9. **Confidence scores are hardcoded** heuristics, not calibrated.

## 6. Bugs / Correctness Risks Found

- `rate_limit_allow` window math (see 🔴 table) — effectively ~300/min, not the implied 5 rps.
- `/explain` returns `sections: []` unconditionally — half-implemented field.
- Generate-questions JSON parsing is best-effort string slicing; malformed LLM JSON silently yields `[]` (`query.py:388-400`).
- `health.py` opens a raw `redis.Redis.from_url(...).ping()` each call (no reuse) — minor.
- Embedding/retrieval failures surface as 502/503 with no retry/backoff.

## 7. Files / Modules Most Involved (by area)

- **Caching & correctness:** `backend/app/cache/semantic_cache.py`, `redis_cache.py`, `backend/app/api/query.py`.
- **Auth/security:** `backend/app/auth/jwt.py`, `backend/app/api/auth.py`, both `main.py` (CORS).
- **RAG quality:** `services/python-rag/app/embedding/transformer.py`, `retrieval/pgvector_store.py`, `chunking/layout_chunker.py`.
- **Repo hygiene:** `.gitignore`, `services/go-backend/`, `.venv311/`, `backend/app/rag/`.
- **Schema:** `backend/app/db/migrations_or_init.sql`, `backend/app/db/models.py`, `services/python-rag/app/db.py`.

## 8. Priority Order for Fixing / Building

**P0 — credibility & hygiene (do first)**
1. Reconcile README benchmarks with `benchmark_results.json` (or regenerate + re-run).
2. Remove `.venv311/` from git; add `.venv*` to `.gitignore`.
3. Remove/relocate archived Go backend; delete dead `backend/app/rag/*` if confirmed unused.
4. Resolve the live-deployment contradiction (verify or remove Railway URLs).

**P1 — correctness & safety**
5. Cache invalidation on re-ingest (+ optional content-hash in cache row).
6. Enforce document ownership; lock down/secure the RAG service; restrict CORS.
7. Fix rate-limit semantics; decide fail-open vs fail-closed.
8. Verify/parameterize LLM model ids; make council opt-in.
9. Add CI + ruff/mypy; add Alembic.

**P2 — scale & quality**
10. HNSW index on both embedding columns; semantic-cache eviction.
11. RAG-service tests + council tests; RAG `/metrics` + scrape.
12. Embedding correctness (sentence-transformers or bge prefix/normalize).

**P3 — product polish**
13. Document management UI/API; citations display; export.
