# DocuSynth — Build Roadmap

> Phased plan from cleanup to launch. Tasks reference real files. "DoD" = Definition of Done. Compiled 2026-06-24. Priorities: P0 (blocker) > P1 > P2 > P3.

---

## Phase 0 — Repo Cleanup & Setup

Goal: a clean, trustworthy, lint-able repository that matches its own claims.

| Task | Priority | Files likely affected |
|---|---|---|
| Remove committed virtualenv from git | P0 | `.venv311/` (untrack), `.gitignore` (add `.venv*`) |
| Reconcile README numbers with committed benchmark | P0 | `README.md:83-99`, `tests/benchmark_results.json`, `docs/benchmarks/*` |
| Resolve live-deployment contradiction | P0 | `docs/deployment.md:154-188`, `README.md:250` |
| Remove/relocate archived Go+C++ backend | P1 | `services/go-backend/**` |
| Delete confirmed dead code | P1 | `backend/app/rag/{chunker,ocr,parser}.py`, `council_responses` table |
| Add linting/formatting/type config | P1 | new `pyproject.toml`/`ruff.toml`, `mypy.ini` |
| Add CI (lint + unit tests + build) | P1 | new `.github/workflows/ci.yml` |
| Finish CouncilAI→DocuSynth rename (optional) | P3 | `metrics/prometheus.py` var names, `auth/jwt.py` iss |

**DoD:** `git ls-files | wc -l` drops to source-only count; repo size << 387 MB; README metrics equal the committed JSON (or are regenerated and both updated together); CI green on a clean checkout; `ruff`/`mypy` run in CI.

**Risks:** untracking `.venv311/` is history-light (just `git rm -r --cached`), but coordinate so collaborators recreate envs; changing README numbers requires deciding the authoritative run.

---

## Phase 1 — MVP Completion (correctness & safety)

Goal: the happy path is not just working but *correct* and *safe* for a shared demo.

| Task | Priority | Files |
|---|---|---|
| Cache invalidation on re-ingest | P0 | `backend/app/cache/semantic_cache.py`, `backend/app/api/documents.py`, `services/python-rag/app/routers/ingest.py` |
| Enforce document ownership | P1 | `backend/app/api/query.py`, `documents.py`, `db/models.py` |
| Secure the RAG service (network isolation + shared secret) | P1 | `services/python-rag/app/main.py`, `backend/app/rag/*`, compose |
| Restrict CORS to known origins | P1 | `backend/app/main.py:18`, `services/python-rag/app/main.py:42` |
| Fix rate-limit semantics + fail policy | P1 | `backend/app/cache/redis_cache.py:56-65` |
| Verify/parameterize LLM model ids; make council opt-in | P1 | `backend/app/config.py`, `council/orchestrator.py` |
| First RAG-service tests (chunking, OCR routing, embed dim) | P1 | new `services/python-rag/tests/` |
| Document management endpoints (list/get/delete) | P2 | `backend/app/api/documents.py` |

**DoD:** re-ingesting a changed document never serves a stale cached answer (covered by a test); a user cannot read another user's `doc_id` (test); RAG `:8001` rejects unauthenticated calls; CORS rejects unknown origins; rate-limit unit test proves the documented limit; council can be turned off per request; RAG service has ≥10 meaningful tests.

**Risks:** ownership enforcement may break existing benchmark scripts that assume the demo user owns everything — update `tests/bench_semantic_cache.py` accordingly.

---

## Phase 2 — Production Readiness

Goal: deployable to a real environment with versioned schema, observability, and resilience.

| Task | Priority | Files |
|---|---|---|
| Adopt Alembic; single schema source | P1 | new `alembic/`, `backend/app/db/models.py`, remove `create_all` from prod path |
| HNSW index on both embedding columns | P2 | migration; `chunks.embedding`, `semantic_cache.embedding` |
| Semantic-cache eviction/TTL | P2 | `semantic_cache.py` |
| RAG `/metrics` + Prometheus scrape job | P2 | `services/python-rag/app/`, `monitoring/prometheus.yml` |
| Retry/backoff for LLM + embedding/retrieval calls | P2 | `council/llm_client.py`, `rag/{embeddings,retrieval}.py` |
| Auth hardening (refresh, revoke, verify iss/aud, gate /register, disable demo seed in prod) | P2 | `auth/jwt.py`, `api/auth.py`, `main.py` |
| Verify cloud deploy end-to-end; pin model ids; secrets via platform | P2 | `docs/deployment.md`, `scripts/validate_deployment.sh` |
| Switch `PyPDF2`→`pypdf`; unify embedding lib | P2 | `services/python-rag/app/inspection/inspector.py`, `ocr/*`, `embedding/transformer.py` |

**DoD:** fresh DB built solely via Alembic; vector queries use the HNSW index (verified via `EXPLAIN`); semantic cache stays bounded under load; Grafana shows RAG-service panels; transient provider errors auto-retry; `scripts/validate_deployment.sh` passes against a real deployment; demo seed disabled when `ENV=prod`.

**Risks:** HNSW changes recall characteristics — re-validate semantic threshold (0.85) after indexing; Alembic adoption must migrate existing data, not drop it.

---

## Phase 3 — Scaling & Advanced Features

Goal: handle volume and improve answer quality.

| Task | Priority | Files |
|---|---|---|
| Externalize Postgres/Redis; tune pools / PgBouncer | P2 | compose/infra, `db/session.py` |
| Horizontal scale backend/RAG (stateless) + load test | P2 | compose/infra, `tests/stress_concurrency.py` |
| Retrieval reranking (cross-encoder) | P3 | `services/python-rag/app/retrieval/` |
| Async/batched ingest pipeline (queue) | P3 | `services/python-rag/app/routers/ingest.py` |
| Citations in responses + UI | P3 | `backend/app/api/query.py`, `streamlit/app.py` |
| Answer-groundedness eval harness | P3 | extend `tests/bench_semantic_accuracy.py` |

**DoD:** documented throughput target met under `stress_concurrency.py`; reranking improves a measured retrieval metric; ingest of large/scanned PDFs doesn't block the request thread; answers show source chunks; an eval harness reports groundedness over a fixed set.

**Risks:** reranking adds latency — keep it optional; queue introduces eventual consistency for "is my doc ready?" UX.

---

## Phase 4 — Polish, Launch, Analytics, Monitoring

Goal: a credible public release.

| Task | Priority | Files |
|---|---|---|
| Product analytics over `query_logs` (activation, hit-rate, latency) | P2 | new Grafana panels / queries |
| Alerting (error rate, latency SLO, provider failures) | P2 | `monitoring/` (Prometheus rules/Alertmanager) |
| Accessibility pass on UI | P3 | `streamlit/app.py` |
| Docs: API reference (export OpenAPI), runbook, SECURITY.md | P2 | `docs/` |
| Public demo polish + onboarding copy | P3 | `streamlit/app.py`, `streamlit_cloud_app.py` |
| Cost dashboard for cloud LLM usage | P3 | metrics + Grafana |

**DoD:** Grafana shows live product + reliability metrics with alerts; an exported OpenAPI spec and a runbook exist; demo has clear first-run guidance; no `MOCK_LLM` surprise on the hosted demo.

**Risks:** analytics require a real user base; alert thresholds need tuning against real traffic to avoid noise.

---

## Cross-cutting acceptance gates
- Every phase ends with: CI green, README/docs updated, no new committed binaries/venvs, and benchmark numbers regenerated if behavior changed.

---

# Strategy-Aligned Roadmap (v2) — added 2026-06-24

> This supersedes nothing above; it re-frames the work around the positioning in `FUTURE_IMPLEMENTATION_STRATEGY.md` ("a measured, trustworthy semantic-caching layer for RAG"). Features (F#) are defined in `FEATURE_PRIORITIZATION.md`; the top 3 are spec'd in `IMMEDIATE_BUILD_PLAN.md`; the target system is `V2_ARCHITECTURE_PROPOSAL.md`. Difficulty: Low/Med/High.

## Phase 1 — Immediate high-impact improvements
**Goal:** make the project correct, credible, and differentiated, fast.

| Task | Priority | Difficulty | Files | Dependencies |
|---|---|---|---|---|
| CI/CD + ruff + mypy + smoke (F4) | P0 | Low | `.github/workflows/ci.yml`, `pyproject.toml`, `mypy.ini` | none |
| Untrack `.venv311/`; reconcile README↔benchmark | P0 | Low | `.gitignore`, `README.md`, `tests/benchmark_results.json` | none |
| Cache invalidation + content-hash (F2) | P0 | Med | `cache/semantic_cache.py`, `api/documents.py`, `db/models.py`, `migrations_or_init.sql` | CI |
| Citations / provenance (F3) | P1 | Low | `python-rag/.../pgvector_store.py`, `models.py`, `api/query.py`, `streamlit/app.py` | none |
| Faithfulness eval harness (F1) | P1 | Med | `tests/eval/faithfulness.py`, `bench_semantic_accuracy.py`, `README.md`, `METRICS_AND_OUTCOMES.md` | F2, F3 |
| Token + USD cost tracking (F7) | P1 | Low | `council/llm_client.py`, `instrumentation.py`, `metrics/prometheus.py`, `api/query.py` | CI |

**DoD:** CI green on clean checkout; repo source-only; README numbers == committed JSON; a test proves re-ingest invalidates stale hits; answers show page-level citations; a committed faithfulness report + threshold sweep exists; Grafana shows tokens/cost and $ saved by cache.
**Metrics to prove success:** faithfulness retention % (was *Not measured yet*); citations/answer; cost/query + cost saved; CI pass rate.

## Phase 2 — Production readiness
**Goal:** safe, observable, deployable.

| Task | Priority | Difficulty | Files | Dependencies |
|---|---|---|---|---|
| Document ownership + AuthZ; secure RAG service; pin CORS (F8) | P1 | Med | `api/{query,documents}.py`, `python-rag/app/main.py`, both `main.py` | CI |
| OpenTelemetry tracing across services (F6) | P1 | Med | both `main.py`, `rag/{embeddings,retrieval}.py`, `council/llm_client.py` | metrics |
| Alembic migrations, single schema source (F10) | P1 | Low | new `alembic/`, `db/models.py` | none |
| HNSW index + hybrid search + rerank (F5) | P2 | Med | migration, `python-rag/.../pgvector_store.py` | Alembic |
| Scrape RAG `/metrics`; cost + cache-quality dashboards | P2 | Low | `python-rag/app`, `monitoring/prometheus.yml`, Grafana | F6/F7 |
| Rate-limit rewrite (sliding window) (F14) | P2 | Low | `cache/redis_cache.py` | none |
| Terraform + one verified cloud deploy (F12) | P2 | Med | new `terraform/`, `docs/deployment.md` | CI |

**DoD:** users can't access others' docs (test); RAG service rejects unauthenticated calls; traces visible in Tempo/Jaeger; fresh DB built via Alembic only; vector queries use HNSW (`EXPLAIN`); one reproducible cloud deploy passes `scripts/validate_deployment.sh`.
**Metrics:** retrieval recall@k/nDCG improvement vs cosine top-k (*Not measured yet*); p95 by `cache_result` (live); trace coverage of the query path.

## Phase 3 — Advanced differentiated features
**Goal:** unique, defensible depth.

| Task | Priority | Difficulty | Files | Dependencies |
|---|---|---|---|---|
| Async ingest via Redis queue + object store (F11 + S3/R2) | P2 | Med | `api/documents.py`, new worker, `python-rag/.../ingest.py` | Phase 2 |
| Cache "revalidate-on-drift" (auto-evict drifted hits) | P2 | Med | `cache/semantic_cache.py`, eval harness, scheduler | F1 |
| Hybrid retrieval tuning + measured nDCG | P3 | Med | `python-rag/.../pgvector_store.py`, eval | F5 |
| LangGraph council refactor (only if council kept) (F13) | P3 | Med | `council/orchestrator.py` (+ nodes) | decision |

**DoD:** uploads return `202 + job_id`, processed async with retries; drifted cache entries auto-evicted with evidence; (if done) council is a typed, circuit-broken graph.
**Metrics:** ingest throughput + failure rate; cache drift rate over time; council latency/cost vs single-model (*Not measured yet*).

## Phase 4 — Cloud/AI infrastructure upgrade (only where justified)
**Goal:** production-grade infra — added deliberately, not decoratively.

| Task | Priority | Difficulty | Files | Dependencies |
|---|---|---|---|---|
| EKS + Helm + HPA (deliberate K8s story) | P3 | High | `deploy/helm/`, manifests | Terraform, multi-replica need |
| Lambda for event-driven ingest/eval (paired with F11) | P3 | Med | worker packaging, queue triggers | F11 |
| Alerting + SLOs (Prometheus rules/Alertmanager) | P2 | Med | `monitoring/` | F6 |

**DoD:** autoscaling under load test; alerts fire on error-rate/latency SLO breaches.
**Metrics:** sustained RPS + p95 under `tests/stress_concurrency.py`; MTTR; deploy frequency.
**Guardrail:** do not start Phase 4 until the **MVP column** in `V2_ARCHITECTURE_PROPOSAL.md` §13 is fully green. Skip SageMaker/DynamoDB/Kafka entirely (see `TECH_STACK_UPGRADE_ANALYSIS.md`).
