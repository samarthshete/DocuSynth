# DocuSynth — Resume Bullet Bank

> Single source of truth for resume bullets, role positioning, and defensible wording.
> Compiled 2026-06-24 from the actual repo + `/docs`. Re-validate metrics against `tests/benchmark_results.json` before every use.

---

## ⚠️ Honesty Guardrails (read before using anything here)

1. **Use the committed benchmark, not the README.** `README.md` claims a **69.7×** speedup; the committed artifact `tests/benchmark_results.json` says **28.91× (p95)**. **Use ~29×. Never use 69.7×** until a re-run proves it.
2. **Authoritative measured numbers** (from `tests/benchmark_results.json`, single-document, `single_local_fast`, Ollama `qwen2.5:3b`, `mock_llm=false`, 122 queries):
   - Semantic cache **p95 speedup: 28.91×** (cold p95 ≈ 10,377 ms → cached p95 ≈ 359 ms)
   - **LLM-call reduction: 18.852%**
   - **Semantic cache hit rate: 22.549%** (23 hits of 102 rephrased queries; 0 exact hits)
   - **Error rate: 0.0%** across 122 queries (20 canonical + 102 paraphrases)
3. **Scale honesty:** this is a **single-document, 122-query local benchmark on a 3B model**, not a production-traffic result. Phrase as "in a 122-query local benchmark," never "in production" or "at scale."
4. **Do not claim:** CI/CD, IaC/Terraform, AWS, horizontal-scaling results, cost-in-dollars savings, document-level access control, distributed tracing, faithfulness/accuracy of the cache. **None are built or measured.** They live in the PLANNED section.
5. **No invented metrics.** Where a number isn't measured, use `N`, `X`, `Y`, or write `Not measured yet`.

---

## 0. Rules for Using This File

- **Layout choice:** use **2 projects × 3 bullets** when résumé space is tight; use **3 projects × 2 bullets** when the projects themselves are your main proof.
- **Only use bullets marked `READY`.** Never use bullets marked `PLANNED — DO NOT USE YET`.
- **Select by role fit, not preference.** Match the Role-to-Project Matrix (§1) and the role packages (§4).
- **Never claim a tool or metric** unless it is implemented in the repo **and** measured in a committed artifact.
- **Keep bullets defensible in an interview:** if asked "how did you measure that?", the answer must be `tests/benchmark_results.json` or specific source files.
- **One project ≠ a whole résumé.** This repo contains exactly **one** project (DocuSynth). Secondary/third "projects" in the matrix are **placeholders you must fill** with your own other work — I will not fabricate projects or their bullets.

---

## 1. Role-to-Project Matrix

> DocuSynth is the only project evidenced in this repo, so it is the Primary for most roles. `[Supply: …]` = a project of yours that I cannot see; the bracket says what it should demonstrate. Be honest about the **Avoid/Downplay** column.

| Role Target | Primary Project | Secondary Project | Optional Third | Why This Set Works | Avoid / Downplay |
|---|---|---|---|---|---|
| **Backend Engineer** | DocuSynth | `[Supply: a CRUD/API service with a real datastore + tests]` | `[Supply: a perf/concurrency project]` | DocuSynth shows API design, caching, datastore, observability; secondary proves breadth beyond AI | Don't lead with the LLM "council"; downplay Streamlit |
| **Software Developer / SDE** | DocuSynth | `[Supply: a clean algorithms/systems project]` | `[Supply: anything with tests + docs]` | Shows end-to-end ownership, testing, clean structure | Downplay unverified deploy/scale claims |
| **Full-stack Engineer** | DocuSynth | `[Supply: a project with a real JS/TS frontend]` | — | DocuSynth covers backend+UI+DB; secondary covers real frontend (Streamlit is weak FE signal) | Downplay "frontend engineering" — it's Streamlit, not React |
| **AI Engineer / Applied AI** | DocuSynth | `[Supply: an LLM/ML eval or fine-tune project]` | `[Supply: data/RAG project]` | RAG pipeline + semantic caching + provider abstraction is a strong AI-infra story | Don't claim retrieval quality/accuracy (Not measured yet) |
| **AWS / Cloud SDE** | `[Supply: a real AWS project]` | DocuSynth (as secondary) | — | **DocuSynth is weak here** — Docker Compose only, no AWS/IaC/CI. Use it for containerization/observability, not "cloud" | Avoid implying AWS, EKS, Lambda, or IaC — none exist |
| **Founding / Startup Engineer** | DocuSynth | `[Supply: anything you shipped end-to-end fast]` | — | Solo-built multi-service system with measured optimization + benchmark rigor = founder signal | Downplay the breadth of half-features; show focus |
| **AI Security / Agent Infrastructure** | DocuSynth | `[Supply: a security/eval/guardrails project]` | — | **Stretch fit.** Use the multi-model orchestration + (PLANNED) eval harness; honestly this role needs more than the repo has today | Don't claim "secure" — RAG service is unauthenticated, CORS `*` |
| **Platform Engineer** | DocuSynth | `[Supply: an infra/observability/CI project]` | — | Multi-service Compose, Prometheus/Grafana, health checks, benchmark harness | Avoid claiming CI/CD, tracing, or autoscaling (PLANNED) |

**Role-fit ranking for DocuSynth (strongest → weakest):** AI Engineer ≈ Backend ≈ Platform > Full-stack > Founding > SDE > AI Security > AWS/Cloud.

---

## 2. DocuSynth — Fact Sheet (what's actually true)

**One-liner (résumé header):**
> *DocuSynth — a provider-portable RAG platform with a two-tier (exact + semantic) LLM cache and full request-path observability.*

**READY / proven in code:**
- 6-service Dockerized stack: FastAPI control plane (`backend/`), Python RAG microservice (`services/python-rag/`), PostgreSQL/pgvector, Redis, Prometheus, Grafana (+ Streamlit UI). — `docker-compose.yml`
- Two-tier cache: Redis exact-match (`backend/app/cache/redis_cache.py`) + pgvector semantic cache (`backend/app/cache/semantic_cache.py`).
- Provider-portable LLM client: Ollama / Gemini / OpenRouter behind one interface. — `backend/app/council/llm_client.py`
- Multi-model "council": parallel candidate generation → peer review → chairman synthesis, with fallbacks. — `backend/app/council/orchestrator.py`
- Adaptive ingestion: text-layer detection → pdfplumber/Tesseract OCR routing → layout-aware chunking → 384-d transformer embeddings → pgvector. — `services/python-rag/app/`
- JWT (HS256) + bcrypt auth; Redis fixed-window rate limiting. — `backend/app/auth/`, `redis_cache.py`
- Prometheus metrics with per-stage latency timings; Grafana dashboards. — `backend/app/metrics/prometheus.py`, `monitoring/`
- Reproducible benchmark harness emitting committed JSON. — `tests/bench_semantic_cache.py`, `tests/benchmark_results.json`
- Dependency-injected pytest suites (mocked DB/LLM). — `tests/`

**NOT true yet (do not claim):** CI/CD, Terraform/IaC, AWS, document ownership/AuthZ, cache invalidation, citations, OpenTelemetry tracing, token/USD cost tracking, HNSW/hybrid retrieval, faithfulness/accuracy of cache, async ingest queue. → see §5 PLANNED.

---

## 3. READY Bullet Bank (atomic, reusable)

> All `< 28 words`, strong verb first, specific contribution + outcome. Tags show best-fit roles. Mix and match into role packages (§4).

**B1 — Caching headline (AI / Backend / Platform)** `READY`
> Designed a two-tier cache (Redis exact-match + pgvector semantic) that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.

**B2 — Semantic caching mechanism (AI / Backend)** `READY`
> Built paraphrase-aware semantic caching over sentence-embedding cosine similarity (pgvector, 0.85 threshold), reaching a 22.5% hit rate on rephrased queries with 0% errors.

**B3 — Multi-service architecture (Backend / Platform / Founding)** `READY`
> Architected a 6-service Dockerized RAG platform (FastAPI control plane + Python RAG microservice, PostgreSQL/pgvector, Redis, Prometheus, Grafana) with health-checked Compose orchestration.

**B4 — Provider-portable LLM layer (AI / Backend)** `READY`
> Built a provider-portable LLM client (Ollama, Gemini, OpenRouter) behind one interface, enabling fully offline or cloud inference switched by environment config.

**B5 — RAG ingestion pipeline (AI / Backend)** `READY`
> Implemented an adaptive ingestion pipeline: text-layer detection routing PDFs to pdfplumber/Tesseract OCR, layout-aware chunking, transformer embeddings, and pgvector storage.

**B6 — Multi-model orchestration (AI / AI-Security)** `READY`
> Engineered a multi-model "council" orchestrator running parallel candidate generation, peer review, and chairman synthesis, with per-stage timeouts and graceful fallback on provider failure.

**B7 — Observability (Platform / Backend)** `READY`
> Instrumented the query path with Prometheus metrics and per-stage latency breakdown (Redis, embedding, pgvector, retrieval, LLM), surfaced in Grafana dashboards.

**B8 — Benchmark rigor (AI / SDE / Founding)** `READY`
> Built a reproducible benchmark harness (20 canonical + 102 paraphrased queries) emitting committed JSON for latency percentiles, cache-hit rate, and LLM-call reduction.

**B9 — Auth + API (Backend / SDE)** `READY`
> Implemented JWT (HS256) authentication with bcrypt hashing, Redis fixed-window rate limiting, and a versioned FastAPI surface for ingest, query, and admin operations.

**B10 — Testing (SDE / Backend)** `READY`
> Wrote dependency-injected pytest suites with FastAPI TestClient and mocked DB/LLM dependencies, covering auth, the cache cascade, and the query pipeline.

**B11 — Vector retrieval (AI)** `READY`
> Implemented semantic retrieval over PostgreSQL/pgvector using 384-dimension embeddings and cosine distance, with top-k chunk selection feeding the generation stage.

**B12 — Pragmatic deployment story (Founding / SDE)** `READY`
> Containerized and orchestrated the full stack with Docker Compose, dependency health gating, and a one-command local bring-up plus an automated smoke-validation script.

---

## 4. Role Packages — 3-bullet and 2-bullet versions

> For each role: a **3-bullet** version (project as main proof) and a **2-bullet** version (when running 3 projects). Pull from §3; wording is pre-tuned. All `READY`.

### Backend Engineer
**3-bullet:**
- B3 — Architected a 6-service Dockerized RAG platform (FastAPI control plane + Python RAG microservice, PostgreSQL/pgvector, Redis, Prometheus, Grafana) with health-checked Compose orchestration.
- B1 — Designed a two-tier cache (Redis exact-match + pgvector semantic) that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B9 — Implemented JWT (HS256) auth with bcrypt hashing, Redis fixed-window rate limiting, and a versioned FastAPI surface for ingest, query, and admin operations.

**2-bullet:**
- B1 — Designed a two-tier cache (Redis exact-match + pgvector semantic) that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B3 — Architected a 6-service Dockerized RAG platform (FastAPI + Python RAG microservice, PostgreSQL/pgvector, Redis, Prometheus, Grafana) with health-checked Compose orchestration.

### Software Developer / SDE
**3-bullet:**
- B3 — Architected a 6-service Dockerized RAG platform with a FastAPI control plane, a Python microservice, PostgreSQL/pgvector, and Redis.
- B8 — Built a reproducible benchmark harness (20 canonical + 102 paraphrased queries) emitting committed JSON for latency percentiles, cache-hit rate, and LLM-call reduction.
- B10 — Wrote dependency-injected pytest suites with FastAPI TestClient and mocked DB/LLM dependencies, covering auth, the cache cascade, and the query pipeline.

**2-bullet:**
- B1 — Designed a two-tier cache that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B10 — Wrote dependency-injected pytest suites (FastAPI TestClient, mocked DB/LLM) covering auth, the cache cascade, and the query pipeline.

### Full-stack Engineer
**3-bullet:**
- B3 — Architected a 6-service Dockerized RAG platform (FastAPI, Python RAG microservice, PostgreSQL/pgvector, Redis, Prometheus, Grafana) plus a Streamlit UI.
- B1 — Designed a two-tier cache that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B9 — Implemented JWT auth with bcrypt and rate limiting, and a versioned FastAPI surface consumed by a Streamlit client for ingest and query.

**2-bullet:**
- B3 — Architected a 6-service Dockerized RAG platform (FastAPI + Python microservice, PostgreSQL/pgvector, Redis) with a Streamlit UI over a versioned API.
- B1 — Designed a two-tier cache that cut p95 query latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.

### AI Engineer / Applied AI Engineer
**3-bullet:**
- B1 — Designed a two-tier cache (Redis exact + pgvector semantic) that cut p95 latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B5 — Implemented an adaptive RAG ingestion pipeline: OCR routing (pdfplumber/Tesseract), layout-aware chunking, transformer embeddings, and pgvector retrieval.
- B6 — Engineered a multi-model "council" orchestrator (parallel generation, peer review, chairman synthesis) across Ollama, Gemini, and OpenRouter with fallbacks.

**2-bullet:**
- B1 — Designed a two-tier cache that cut p95 latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B5 — Built an adaptive RAG pipeline (OCR routing, layout-aware chunking, transformer embeddings, pgvector retrieval) behind a provider-portable LLM client (Ollama/Gemini/OpenRouter).

### AWS / Cloud SDE
> ⚠️ **DocuSynth is your weakest fit here — no AWS, IaC, or CI exist.** Use it only as a *secondary* containerization/observability story, and lead with a real AWS project. These bullets stay strictly within what's true.

**3-bullet (use as secondary project only):**
- B3 — Architected a 6-service Dockerized platform with health-checked Compose orchestration and clean service boundaries.
- B7 — Instrumented services with Prometheus metrics and Grafana dashboards, exposing per-stage latency across the request path.
- B12 — Containerized the full stack with dependency health gating, one-command bring-up, and an automated smoke-validation script.

**2-bullet (secondary only):**
- B3 — Architected a 6-service Dockerized platform (FastAPI, PostgreSQL/pgvector, Redis, Prometheus, Grafana) with health-checked orchestration.
- B7 — Instrumented the request path with Prometheus + Grafana, exposing per-stage latency (Redis, embedding, pgvector, retrieval, LLM).

### Founding Engineer / Startup Engineer
**3-bullet:**
- B3 — Solo-built a 6-service Dockerized RAG platform end-to-end (FastAPI, Python microservice, PostgreSQL/pgvector, Redis, Prometheus, Grafana, Streamlit).
- B1 — Designed a two-tier cache that cut p95 latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark — the product's core optimization.
- B8 — Built a reproducible benchmark harness emitting committed JSON, turning a performance claim into a defensible, repeatable measurement.

**2-bullet:**
- B1 — Solo-designed a two-tier LLM cache that cut p95 latency ~29× on cache hits and ~19% of LLM calls in a 122-query local benchmark.
- B3 — Built and orchestrated a 6-service Dockerized RAG platform end-to-end with observability and a reproducible benchmark.

### AI Security / Agent Infrastructure
> ⚠️ **Stretch fit.** Honest framing: the multi-model orchestration is the closest signal; the project is **not** a security system (RAG service is unauthenticated, CORS `*`). Do not claim "secure." Pair with a real security/eval project.

**3-bullet:**
- B6 — Engineered a multi-model orchestrator (parallel generation, peer review, chairman synthesis) with per-stage timeouts and graceful fallback on provider failure.
- B4 — Built a provider-portable LLM client (Ollama/Gemini/OpenRouter) isolating provider failures behind one interface.
- B7 — Instrumented the LLM call path with Prometheus metrics (calls per query, per-stage latency, error counters by reason).

**2-bullet:**
- B6 — Engineered a multi-model orchestrator with peer review, chairman synthesis, per-stage timeouts, and fallback handling across three LLM providers.
- B7 — Instrumented the LLM path with Prometheus (calls/query, per-stage latency, error-by-reason counters) for failure visibility.

### Platform Engineer
**3-bullet:**
- B3 — Architected a 6-service Dockerized platform with health-checked Compose orchestration, named volumes, and clean service boundaries.
- B7 — Instrumented the full request path with Prometheus metrics and per-stage latency, surfaced in provisioned Grafana dashboards.
- B8 — Built a reproducible benchmark harness emitting committed JSON for latency percentiles, cache-hit rate, and LLM-call reduction.

**2-bullet:**
- B3 — Architected a 6-service Dockerized platform (FastAPI, PostgreSQL/pgvector, Redis, Prometheus, Grafana) with health-checked orchestration.
- B7 — Instrumented the request path with Prometheus + Grafana, exposing per-stage latency and error metrics across services.

---

## 5. PLANNED Bullets — DO NOT USE YET

> These describe work in `FEATURE_PRIORITIZATION.md` / `IMMEDIATE_BUILD_PLAN.md` that is **not built or not measured**. Each lists its **activation condition**: the commit/artifact that makes it `READY`. Move a bullet up to §3 only when its condition is met and metrics replace placeholders.

| ID | PLANNED bullet (draft) | Activation condition |
|---|---|---|
| P1 | "Built an evaluation harness measuring faithfulness retention of a semantic LLM cache vs the cold path, retaining X% faithfulness while keeping the ~29× speedup." | `tests/eval/faithfulness.py` exists + committed report with a real `X` (F1) |
| P2 | "Designed content-hash–keyed cache invalidation eliminating stale-answer serving on document updates, verified by regression tests." | Invalidation in `semantic_cache.py` + passing `test_semantic_cache_invalidation.py` (F2) |
| P3 | "Added end-to-end page-level source citations to a RAG pipeline, surfaced in the UI through the cache layer." | Citations returned by `query.py` + rendered in `streamlit/app.py` (F3) |
| P4 | "Set up GitHub Actions CI (ruff, mypy, pytest, image build, smoke test) gating every PR." | `.github/workflows/ci.yml` merged and green (F4) |
| P5 | "Improved retrieval recall@k/nDCG by X% with HNSW indexing plus hybrid BM25+vector search and cross-encoder reranking." | HNSW + hybrid + rerank in `pgvector_store.py` + measured `X` (F5) |
| P6 | "Added OpenTelemetry distributed tracing across two FastAPI services, pgvector, and LLM providers." | OTel spans propagated backend→rag + exported (F6) |
| P7 | "Instrumented per-query token and USD cost, quantifying $Y saved by cache hits." | Token/cost parsing in `llm_client.py` + Grafana panel + real `Y` (F7) |
| P8 | "Enforced per-user document ownership (AuthZ) and authenticated the internal RAG service." | Ownership checks in `query.py`/`documents.py` + RAG auth (F8) |
| P9 | "Provisioned managed Postgres/Redis and the service tier with Terraform; deployed via CI/CD." | `terraform/` applied + one verified deploy (F12) |
| P10 | "Moved OCR/embedding off the request path with a Redis-backed job queue and object storage, returning 202 + job status." | Async ingest worker + `ingest_jobs` + object store (F11) |
| P11 | "Modeled the multi-agent LLM council as a typed LangGraph state machine with retries, timeouts, and circuit-breaking." | LangGraph refactor of `orchestrator.py` (F13) |

**Metric placeholders to keep honest:** `X` = measured improvement %, `Y` = measured $ saved, `N` = count. Until measured, the bullet stays in this table.

---

## 6. Bullet Quality Rules (apply to every edit)

- **Strong action verb first:** Architected, Designed, Engineered, Implemented, Built, Instrumented, Reduced. Avoid "Worked on," "Helped," "Responsible for."
- **< 28 words.** If longer, cut adjectives, not the metric.
- **One specific technical contribution per bullet** — name the actual tech (pgvector, Redis, FastAPI), not "modern technologies."
- **Prefer architecture + outcome:** "Designed X → measured result." A bullet with no outcome is weak; a bullet with an unmeasured outcome is dishonest.
- **No vague wording:** ban "scalable," "robust," "seamless," "cutting-edge," "production-grade," "enterprise" unless proven in the repo.
- **No overclaiming:** don't imply AWS/CI/scale/security that isn't there; don't use the README's 69.7×.
- **Interview-test every bullet:** you must be able to point to a file or a committed artifact when asked "show me."

### Rejected / rewritten examples (do not reuse the ❌ forms)
- ❌ "Built a production-grade, scalable AI platform serving millions of requests." → **Reject** (no scale data, not production). ✅ Use **B1/B3**.
- ❌ "Achieved 69.7× latency improvement with semantic caching." → **Reject** (README number contradicts committed JSON). ✅ "~29× p95 on cache hits in a 122-query local benchmark" (B1).
- ❌ "Deployed on AWS with CI/CD and Terraform." → **Reject** (none exist). ✅ Keep PLANNED (P4/P9).
- ❌ "Secured the platform with enterprise-grade auth." → **Reject** (RAG service unauthenticated, CORS `*`). ✅ "Implemented JWT + bcrypt auth and Redis rate limiting" (B9), no "enterprise."
- ❌ "Improved answer accuracy with a multi-model council." → **Reject** (accuracy Not measured yet). ✅ Describe the mechanism only (B6), no accuracy claim.

---

## 7. Maintenance

- When a PLANNED feature ships, replace its placeholder metric with the **committed** number, move the bullet to §3 with a `READY` tag, and add its role to the packages in §4.
- Re-verify §2 numbers against `tests/benchmark_results.json` after any change to caching, embeddings, retrieval, or model/provider — and regenerate the README from that JSON so the two never diverge again.
