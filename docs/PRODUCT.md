# DocuSynth — Product Document

> Product-level view inferred from the codebase and UI. There is **no PRD, persona doc, or analytics in the repo**; everything below is reconstructed from `streamlit/app.py`, the API surface, and `README.md`, and is labeled as inferred. Compiled 2026-06-24.

## 1. Product Idea

Upload a document, then **ask it questions, have it explained at your level, and auto-generate practice questions from it** — with answers grounded strictly in the document, served fast and cheaply by reusing prior answers via semantic caching, and fully observable.

## 2. User Pain Points (inferred)

1. "I have a long PDF and need specific answers without reading all of it."
2. "Generic chatbots hallucinate or answer from general knowledge, not *my* document."
3. "Re-asking slightly different versions of the same question is slow and (in hosted LLMs) expensive."
4. "I want to study a document — I need it explained simply and need practice questions."
5. (Operator) "I can't see where time/cost goes in my RAG pipeline."

## 3. User Personas (inferred — not in repo)

> ⚠️ No persona definitions exist in the codebase. These are reasonable inferences from features.

- **Persona A — "The Engineer/Evaluator" (primary).** Reviewing DocuSynth as a reference RAG architecture or portfolio piece. Cares about correctness, metrics, caching design, observability, and deployability.
- **Persona B — "The Student/Self-learner."** Uses Ask/Explain/Generate-Questions to study material. Cares about clarity, leveled explanations, and quiz generation.
- **Persona C — "The Self-hoster."** Wants offline document Q&A (Ollama). Cares about running everything locally without paying for an LLM API.

There are **no roles, orgs, or tiers** in the data model — all users are equal (`users` table).

## 4. User Stories

- As a user, I can register/log in so my session is authenticated. *(implemented)*
- As a user, I can upload a PDF/image and have it ingested into searchable chunks. *(implemented)*
- As a user, I can ask a question about my document and get a grounded answer with a confidence and source. *(implemented)*
- As a user, I can see whether my answer came from cache and how fast each stage was. *(implemented — `timings`, `cache_result` in response)*
- As a user, I can request a beginner/intermediate/advanced explanation of the document. *(implemented — `/explain`)*
- As a user, I can generate N subjective or MCQ questions at a difficulty/Bloom level. *(implemented — `/generate-questions`)*
- As an operator, I can watch query rate, latency, cache distribution, and LLM calls in Grafana. *(implemented)*
- As a user, I can only access *my own* documents. ❌ **NOT implemented** (`owner_id` stored but never enforced).
- As a user, I can list/delete my documents. ❌ **NOT implemented** (no such endpoints).
- As a user, my answers refresh when I re-upload a changed document. ❌ **NOT implemented** (stale cache).

## 5. Jobs To Be Done

1. **When** I have a dense document **I want to** extract specific answers **so I can** avoid reading the whole thing.
2. **When** I'm learning **I want to** get a leveled explanation and practice questions **so I can** study efficiently.
3. **When** I repeatedly query similar things **I want to** get instant answers **so I can** save time/cost.
4. **When** I run this system **I want to** see its internal performance **so I can** trust and tune it.

## 6. MVP Features (status)

| MVP feature | Status |
|---|---|
| Auth (login/register, JWT) | ✅ |
| Document ingest (PDF/image) | ✅ |
| Grounded Q&A | ✅ |
| Two-tier caching (exact + semantic) | ✅ |
| Explanation generation | ✅ |
| Question generation | ✅ |
| Observability (Prometheus/Grafana) | ✅ |
| Document ownership/isolation | ❌ missing |
| Document management (list/delete) | ❌ missing |

The functional MVP (ingest → ask → grounded answer, locally) **is met**.

## 7. Feature Priority

> Recommended priority given the project's portfolio/reference intent and the gaps found.

**P0 (credibility & correctness):**
- Reconcile README benchmarks with `benchmark_results.json`.
- Cache invalidation on re-ingest (correctness).
- Document ownership enforcement (or explicit "single-tenant demo" disclaimer).

**P1 (usability/product):**
- Document list/delete endpoints + Streamlit management UI.
- Surface citations/source chunks in answers (data exists; UI doesn't show them).

**P2 (depth):**
- ANN index for scale; cache eviction.
- MCQ rendering polish; export of questions/explanations.

## 8. Product Workflows

1. **Onboarding:** open Streamlit → log in (`demo/demo123`) → upload PDF → "Ingest".
2. **Ask loop:** type question → see answer + meta (confidence/source/latency/cache/peer-review) → repeat (paraphrases hit semantic cache).
3. **Explain:** pick level + depth (+ optional focus topics) → generate → expandable history.
4. **Questions:** pick count/difficulty/type(+Bloom) → generate → reveal answers per question.

## 9. Success Metrics

> None are tracked in-product today. `query_logs` (status, latency_ms) is the only persistent product-signal table, and there is **no dashboard or analytics over it**. Recommended (see `METRICS_AND_OUTCOMES.md`):
- **Cache hit rate** (semantic + exact) — already computed in benchmarks; should be a live Grafana panel.
- **LLM-call reduction %** — proxy for cost savings.
- **p50/p95 query latency by cache_result** — already a labeled histogram.
- **Answer groundedness / "I don't know" rate** — not measured; needs eval harness.
- **Ingest success rate & time** — `docusynth_document_ingestion_seconds` exists.
- **Activation:** % of sessions that ingest then ask. (Requires real user analytics — not present.)

## 10. Product Risks

1. **Trust/credibility:** published numbers don't match the committed artifact (`README.md` vs `benchmark_results.json`).
2. **Correctness/safety:** stale-cache answers after document changes can silently mislead.
3. **Privacy:** no document isolation between users; RAG service unauthenticated.
4. **Expectation gap:** default `MOCK_LLM=true` yields mock answers on first run, which looks broken.
5. **Cost (cloud mode):** full council = up to 7 LLM calls/query; can be expensive on paid providers.

## 11. Differentiation from Existing Products

Honest framing: DocuSynth competes conceptually with hosted "chat with your PDF" tools and RAG frameworks (LangChain/LlamaIndex demos, commercial doc-QA SaaS).

**Genuine differentiators (as built):**
- **Two-tier caching with a measured semantic-cache layer** — most demos cache exact matches at best; the paraphrase-aware pgvector cache with a published speedup is a real, somewhat uncommon emphasis.
- **First-class observability** — per-stage timings in every response + Prometheus/Grafana out of the box.
- **Provider portability** — same code runs fully offline (Ollama) or on Gemini/OpenRouter via env flags.
- **Optional multi-model "council"** (generate→peer-review→chairman) — a distinctive, if costly, answer-quality mechanism.

**Where it is NOT differentiated / weaker than incumbents:**
- No multi-tenancy, no doc management, no citations UI, no eval/quality guarantees.
- Retrieval quality is standard pgvector cosine with no reranking; the cloud demo even falls back to keyword overlap.
- It is a reference/portfolio architecture, not a polished product.
