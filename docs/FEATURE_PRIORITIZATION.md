# DocuSynth — Feature Prioritization

> Ranked, grounded feature backlog. Compiled 2026-06-24. Every feature references real files. No invented metrics.

## Scoring model

```
Priority Score = User Value + Engineering Depth + Resume Signal + Founder Value - Complexity Risk
```
Each sub-score is 1–5. Complexity Risk is subtracted. Max ≈ 20 - 1 = 19; min can go negative.

| # | Feature | UserVal | EngDepth | Resume | Founder | ComplexRisk | **Score** | Diff | Impact |
|---|---|---|---|---|---|---|---|---|---|
| F1 | Semantic-cache **faithfulness eval harness** | 4 | 5 | 5 | 5 | 2 | **17** | Med | High |
| F2 | **Cache invalidation** + content-hash keying | 5 | 4 | 4 | 5 | 2 | **16** | Med | High |
| F3 | **Citations / source provenance** in responses | 5 | 3 | 4 | 5 | 1 | **16** | Low | High |
| F4 | **CI/CD + lint/type + smoke benchmark** | 3 | 4 | 5 | 4 | 1 | **15** | Low | High |
| F5 | **HNSW index + hybrid search + reranking** | 4 | 5 | 5 | 4 | 3 | **15** | Med | High |
| F6 | **OpenTelemetry distributed tracing** | 3 | 5 | 5 | 3 | 2 | **14** | Med | High |
| F7 | **Token + USD cost tracking** (per query, saved-by-cache) | 4 | 3 | 4 | 5 | 1 | **15** | Low | High |
| F8 | **Document management API + ownership/AuthZ** | 4 | 4 | 4 | 4 | 2 | **14** | Med | High |
| F9 | **Streaming responses (SSE)** | 4 | 3 | 3 | 4 | 2 | **12** | Med | Med |
| F10 | **Alembic migrations** (single schema source) | 2 | 3 | 3 | 3 | 1 | **10** | Low | Med |
| F11 | **Async ingest via background queue** | 3 | 4 | 4 | 3 | 3 | **11** | Med | Med |
| F12 | **Terraform IaC + one verified cloud deploy** | 2 | 4 | 5 | 3 | 3 | **11** | Med | Med |
| F13 | **LangGraph refactor of the council** | 2 | 4 | 5 | 2 | 3 | **10** | Med | Med |
| F14 | Rate-limit rewrite (sliding window) | 3 | 2 | 2 | 3 | 1 | **9** | Low | Med |
| F15 | Real frontend (Next.js) replacing Streamlit | 3 | 3 | 3 | 2 | 4 | **7** | High | Med |
| F16 | Multi-tenant SaaS (orgs, billing) | 2 | 3 | 3 | 2 | 5 | **5** | High | Low |
| F17 | Fine-tuning / SageMaker pipeline | 1 | 3 | 2 | 1 | 5 | **2** | High | Low |
| F18 | Kafka event bus | 1 | 2 | 2 | 1 | 5 | **1** | High | Low |

---

## Tier 1 — Must build immediately (Score ≥ 15)

### F1 — Semantic-cache faithfulness eval harness
- **Problem:** the cache's speedup is published, its *quality cost is unknown*. A senior reviewer's first question.
- **User value:** trust that cached answers are still correct. **Eng value:** real LLM-eval skill (LLM-as-judge / overlap metrics). **Founder value:** the core sales claim becomes defensible.
- **Files:** extend `tests/bench_semantic_accuracy.py`; new `tests/eval/faithfulness.py`; read paths in `backend/app/cache/semantic_cache.py`, `backend/app/api/query.py`.
- **Backend:** add an eval mode that, for a cache hit, also computes the cold answer and scores agreement (faithfulness to retrieved chunks + answer-equivalence). **Frontend:** none. **DB:** none (or an `eval_runs` table, optional). **Infra:** add to CI as a nightly/smoke job.
- **Risks:** LLM-judge variance — mitigate with deterministic overlap metrics + a fixed judge prompt/temperature.
- **DoD:** a committed report (JSON) stating faithfulness retention % of cache hits at threshold 0.85, plus a threshold sweep; README cites it.

### F2 — Cache invalidation + content-hash keying
- **Problem:** re-ingesting a changed doc serves stale answers as "hits" (`semantic_cache.py` never invalidates).
- **Files:** `backend/app/cache/semantic_cache.py`, `backend/app/api/documents.py`, `services/python-rag/app/routers/ingest.py`, `backend/app/db/models.py`.
- **Backend:** store a `doc_content_hash` on ingest; include it in `SemanticCacheEntry`; on re-ingest, delete stale rows for that `document_id`; skip/refresh hits whose hash differs. **DB:** add column + migration. **Frontend:** none. **Infra:** none.
- **Risks:** double-write coordination between services — keep invalidation in the backend on the ingest proxy.
- **DoD:** a test proving a changed re-ingest never returns the pre-change cached answer.

### F3 — Citations / source provenance in responses
- **Problem:** chunks are fed to the council but **dropped from the response** (`query.py:228-242` returns `candidates`, not source chunks/pages). Users can't verify answers.
- **Files:** `backend/app/api/query.py`, `services/python-rag/app/routers/retrieve.py` + `app/models.py` (add a relevance score), `streamlit/app.py`.
- **Backend:** return retrieved chunks with `document_id`, `page_number`, and a similarity score in the query response. **Frontend:** render "Sources" with page numbers under each answer. **DB:** none (data exists). **Infra:** none.
- **Risks:** payload size — cap to top-k and truncate text.
- **DoD:** every answer shows the source chunks + pages it was grounded in; UI displays them.

### F4 — CI/CD + lint/type + smoke benchmark
- **Problem:** no CI, no lint config; quality is unverified per change.
- **Files:** new `.github/workflows/ci.yml`, `pyproject.toml`/`ruff.toml`, `mypy.ini`; uses existing `tests/`, `Makefile`.
- **Infra:** GitHub Actions: ruff + mypy + `pytest` + build both images + a tiny `MOCK_LLM=true` smoke of `/health` and `/query`. **Backend/Frontend/DB:** none beyond config.
- **Risks:** flaky external calls — keep CI in `MOCK_LLM=true`.
- **DoD:** green CI gate required on PRs; badge in README.

### F5 — HNSW index + hybrid search + reranking
- **Problem:** retrieval is plain cosine top-k with no ANN index (`pgvector_store.py`); quality and scale both suffer.
- **Files:** migration (HNSW on `chunks.embedding`, `semantic_cache.embedding`); `services/python-rag/app/retrieval/pgvector_store.py` (add BM25/tsvector + fusion + optional cross-encoder rerank).
- **Backend:** add `tsvector` column + GIN index; reciprocal-rank-fusion of BM25 + vector; optional `cross-encoder` rerank. **DB:** indexes + column. **Infra:** none (CPU rerank) or a small model download.
- **Risks:** rerank latency — make it optional/configurable; re-validate the 0.85 cache threshold after indexing.
- **DoD:** measured recall@k / nDCG improvement vs current cosine top-k on a labeled set (see `METRICS_AND_OUTCOMES.md`).

### F7 — Token + USD cost tracking
- **Problem:** the product pitch is cost savings, yet there is **zero token/cost tracking** (`grep` confirms). `llm_call_count` exists but not tokens or dollars.
- **Files:** `backend/app/council/llm_client.py` (parse `usage` from provider responses), `backend/app/council/instrumentation.py`, `backend/app/metrics/prometheus.py`, `backend/app/api/query.py`.
- **Backend:** capture prompt/completion tokens per call; map to per-provider USD; emit `docusynth_llm_tokens_total{stage,type}` and `docusynth_query_cost_usd`; compute "cost avoided by cache." **Frontend:** show cost/tokens in the answer meta. **DB:** optional column on `query_logs`. **Infra:** Grafana panel.
- **Risks:** Ollama returns no cost (local) — handle null pricing gracefully.
- **DoD:** Grafana shows tokens/query, cost/query, and cumulative cost saved by cache hits.

---

## Tier 2 — Build after MVP is stable (Score 10–14)

- **F6 OpenTelemetry tracing** — spans across `backend → python-rag → Postgres/LLM`; export to an OTel collector → Tempo/Jaeger. Files: both `main.py`, `rag/{embeddings,retrieval}.py`, `council/llm_client.py`. Strong platform signal.
- **F8 Document management + ownership** — list/get/delete endpoints; enforce `owner_id` everywhere; secure the RAG service with a shared secret. Files: `backend/app/api/documents.py`, `query.py`, `services/python-rag/app/main.py`.
- **F9 Streaming responses (SSE)** — stream tokens for the single-model path; `StreamingResponse` in `query.py`, `httpx` streaming in `llm_client.py`, `EventSource`/chunked read in Streamlit. (No streaming exists today.)
- **F10 Alembic** — collapse the 3-way schema definition into versioned migrations.
- **F11 Async ingest queue** — move OCR/embedding off the request path (RQ/arq + Redis, or FastAPI BackgroundTasks as a stepping stone); add a job-status endpoint.
- **F12 Terraform + one verified cloud deploy** — IaC for managed Postgres(pgvector)/Redis + the three services; reconcile the unverified Railway claim.
- **F14 Rate-limit rewrite** — sliding-window/token-bucket Lua; fix the misleading `rps*window` math.

## Tier 3 — Advanced differentiators (selective)

- **F13 LangGraph council refactor** — model generate→review→chairman as an explicit graph with retries/fallbacks/circuit-breaking. Justified *only* if the council stays a headline; otherwise skip. Nodes map 1:1 to existing functions (see `TECH_STACK_UPGRADE_ANALYSIS.md`).
- **Cache "revalidate-on-drift"** — periodically re-score a sample of cache hits against fresh cold answers; auto-evict drifted entries. Builds directly on F1.
- **Multi-document / corpus-level query** — retrieve across a user's whole library, not one `doc_id`.

## Tier 4 — Bad ideas / avoid for now

- **F15 Custom SPA frontend** — high effort, low signal for this project's positioning; Streamlit is adequate until there's a product reason.
- **F16 Multi-tenant SaaS + billing** — premature; no users yet.
- **F17 SageMaker / fine-tuning** — the system only calls external LLM APIs; nothing to train. Pure resume padding here.
- **F18 Kafka** — there is no event-stream workload; a Redis-backed job queue covers async ingest. Would look forced.

---

## Sequencing note
Tier 1 is intentionally ordered so each unblocks the next: **F4 (CI)** makes everything safe to change; **F2 (invalidation)** + **F3 (citations)** fix correctness/trust; **F1 (eval)** + **F7 (cost)** turn the cache claim into defensible, dashboarded evidence; **F5 (retrieval)** raises the quality ceiling the eval measures. See `IMMEDIATE_BUILD_PLAN.md` for the top 3 in step-by-step detail.
