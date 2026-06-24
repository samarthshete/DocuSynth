# DocuSynth — Immediate Build Plan (Top 3 Features)

> The three features to build next, in build order, with exact technical steps, files, tests, metrics, and the resume/interview payoff each unlocks. Grounded in the current code. No code is implemented here (per instruction) — this is the spec. Compiled 2026-06-24.

**Day-0 enabler (do alongside #1):** stand up **GitHub Actions CI** (`.github/workflows/ci.yml`: ruff + mypy + `pytest` + build both images + a `MOCK_LLM=true` smoke of `/health` and `/query`) so every change below is safe. It's ~half a day and gates everything. Also `git rm -r --cached .venv311` and add `.venv*` to `.gitignore`.

Build order rationale: **correctness (F2) → trust (F3) → proof (F1)**. You can't credibly publish a faithfulness number until the cache is correct and answers are inspectable.

---

## Feature 1 (build now): Semantic-cache invalidation + content-hash keying

### Why now
The product's headline is the semantic cache. Today it **never invalidates** — `backend/app/cache/semantic_cache.py` keys only on `(document_id, query embedding)` and `store_semantic()` only inserts. Re-ingesting a changed document serves the *old* answer as a "hit." This is a correctness bug that would blow up in a live demo and undermines every benchmark claim.

### Exact technical work
1. **Compute a document content hash on ingest.** In `backend/app/api/documents.py` (the ingest proxy), after reading `content`, compute `content_hash = sha256(content).hexdigest()`. Persist it on the `Document` row.
2. **Add columns.** `documents.content_hash` and `semantic_cache.doc_content_hash` in `backend/app/db/models.py` + `backend/app/db/migrations_or_init.sql` (and the future Alembic migration).
3. **Stamp the cache row.** In `backend/app/cache/semantic_cache.py::store_semantic`, write the current `doc_content_hash`.
4. **Validate on lookup.** In `lookup_semantic`, after the cosine match, require `entry.doc_content_hash == current_doc_content_hash`; if it differs, treat as a miss (and optionally delete the stale row).
5. **Invalidate on re-ingest.** In the ingest proxy, when an existing `doc_id` is re-ingested with a new `content_hash`, `DELETE FROM semantic_cache WHERE document_id = :doc_id` (and let it repopulate).

### Files
- Edit: `backend/app/api/documents.py`, `backend/app/cache/semantic_cache.py`, `backend/app/db/models.py`, `backend/app/db/migrations_or_init.sql`, `backend/app/api/query.py` (pass the hash through).
- (Schema also touched in `services/python-rag/app/db.py` if you add the column there.)

### Tests to add (`tests/`)
- `test_semantic_cache_invalidation.py`: ingest → query (miss, stores) → re-ingest changed content (new hash) → same query must be a **miss**, not the stale hit. Use the existing `FakeDB`/monkeypatch pattern from `tests/conftest.py` and `tests/test_semantic_cache.py`.
- Unit test: `lookup_semantic` returns `(None, similarity)` when hashes differ even if cosine ≥ threshold.

### Metrics to track
- New label on `docusynth_cache_operations_total`: `reason="stale_hash"` for invalidated would-be hits.
- Track invalidations/day in Grafana.

### Resume bullet (eventual)
> "Designed content-hash–keyed cache invalidation for a semantic LLM cache, eliminating stale-answer serving on document updates; verified with regression tests."

### Interview story
A clean **cache-coherence** problem: "We had a semantic cache that keyed on the question, not the document state. I added a content hash so cache validity tracks the underlying data, and wrote tests proving stale answers can't be served." Demonstrates systems thinking beyond CRUD.

---

## Feature 2 (build next): Citations / source provenance in responses

### Why now
Answers currently return `candidates` but **not the source chunks** — `backend/app/api/query.py:228-242` drops the retrieved chunk metadata. The RAG `RetrieveResponse` (`services/python-rag/app/models.py`) returns `Chunk`s but with **no similarity score**. Users can't verify groundedness, which is the #1 trust objection for any "chat with your docs" tool. This is low effort (data already flows through) and high trust impact.

### Exact technical work
1. **Return a score from retrieval.** In `services/python-rag/app/retrieval/pgvector_store.py::retrieve`, compute and attach `score = 1 - cosine_distance` per chunk; add a `score: float | None` field to `Chunk` (or a `RetrievedChunk`) in `services/python-rag/app/models.py`; include it in `RetrieveResponse`.
2. **Carry citations through the backend.** In `backend/app/api/query.py`, build a `citations` list from `chunks_payload` (each: `document_id`, `page_number`, `score`, truncated `content`, `chunk_index`) and add it to the response dict. Cap at `top_k`; truncate text (e.g. 300 chars).
3. **Persist citations in the cached payload** so exact/semantic hits also return them (they already cache the full response JSON via `set_json`/`store_semantic`).
4. **Render in UI.** In `streamlit/app.py`, under each assistant answer, add a "📎 Sources" expander listing page numbers + snippets + score.

### Files
- Edit: `services/python-rag/app/retrieval/pgvector_store.py`, `services/python-rag/app/models.py`, `services/python-rag/app/routers/retrieve.py`, `backend/app/api/query.py`, `streamlit/app.py`.

### Tests to add
- Extend `tests/test_query.py`: assert the response contains `citations` with `page_number` and `score` keys (the fake `retrieve_chunks` in that test returns `{"content": ...}`; extend the fake to include page/score and assert passthrough).
- RAG-side unit test (new `services/python-rag/tests/`): `retrieve` returns chunks with a numeric `score` in `[0,1]`.

### Metrics to track
- `docusynth_citations_per_answer` (histogram) — sanity that answers are grounded.
- Average top-1 similarity score by `cache_result` — a retrieval-health signal.

### Resume bullet (eventual)
> "Added end-to-end source attribution to a RAG pipeline (page-level citations with similarity scores) surfaced in the UI, improving answer verifiability."

### Interview story
"Grounded answers are worthless if users can't trust them, so I plumbed chunk provenance (page + score) from pgvector through the API to the UI, including through the cache layer so cached answers stay attributable." Shows product empathy + full-stack data flow.

---

## Feature 3 (the differentiator): Semantic-cache faithfulness eval harness

### Why now
This is the **highest-scoring feature** (`FEATURE_PRIORITIZATION.md`) and the project's unique proof: it turns "the cache is 28.9× faster" into "the cache is 28.9× faster **and answers stay within X% faithfulness of the cold path.**" Without it, a senior reviewer assumes the speedup costs accuracy. `tests/bench_semantic_accuracy.py` already exists as a starting point. Build this **after** F1/F2 so you're measuring a correct cache and can use citations for groundedness.

### Exact technical work
1. **Define the eval set.** Reuse the benchmark's 20 canonical questions + 102 rephrasings (already in `tests/bench_semantic_cache.py`). Label expected-answer references once (or use the cold answer as reference).
2. **Dual-path scoring.** New `tests/eval/faithfulness.py`: for each query that the cache would serve as a hit (similarity ≥ threshold), also compute the **cold** answer (force `cache_result=miss`), then score:
   - **Answer agreement:** LLM-as-judge ("are these two answers equivalent for this question?", fixed prompt, temperature 0) **and** a deterministic lexical overlap (ROUGE-L / token-F1) as a non-LLM backstop.
   - **Groundedness:** does the cached answer's content appear in the retrieved chunks (uses F3's citations)?
3. **Threshold sweep.** Run the eval at thresholds e.g. `[0.80, 0.85, 0.90, 0.95]`; record hit-rate vs faithfulness at each → pick/justify the operating point (currently hardcoded 0.85 in `config.py`).
4. **Wire into CI/nightly.** Add a job (small sample in PR CI with `MOCK_LLM` off only on a manual/nightly trigger to avoid cost/flakiness).
5. **Publish.** Commit the JSON report under `docs/benchmarks/`; cite it in README and `METRICS_AND_OUTCOMES.md`.

### Files
- New: `tests/eval/faithfulness.py`, `tests/eval/__init__.py`; report under `docs/benchmarks/`.
- Edit/extend: `tests/bench_semantic_accuracy.py`, `tests/bench_semantic_cache.py` (expose a "force cold" flag), `backend/app/api/query.py` (optional `?force_cold=true`/header for eval), `README.md`, `docs/METRICS_AND_OUTCOMES.md`.

### Tests / validation
- The harness itself is the test artifact; add a small unit test that the scorer returns deterministic results for identical inputs (faithfulness == 1.0 for identical answers).

### Metrics to track (all currently **Not measured yet**)
- **Faithfulness retention** = mean agreement(cached, cold) over cache hits.
- **Groundedness rate** of cached answers.
- **Hit-rate vs faithfulness curve** across thresholds.
- Emit `docusynth_cache_faithfulness` to Prometheus for a live (sampled) panel.

### Resume bullet (eventual)
> "Built an evaluation harness measuring faithfulness retention of a semantic LLM cache vs the cold RAG path; used a hit-rate/faithfulness threshold sweep to set the cache similarity cutoff, quantifying the latency/quality tradeoff."

### Interview story
The strongest one in the project: "Caching LLM answers by semantic similarity trades correctness for speed. I built an eval harness — LLM-as-judge plus a deterministic overlap backstop — to measure how much faithfulness we lose at each similarity threshold, then chose the operating point from data instead of guessing. That's how I'd justify shipping a cache that changes user-visible answers." This is exactly the rigor AI-engineering interviews probe for.

---

## How the three connect
F1 makes the cache **correct**; F2 makes answers **verifiable** (and supplies the groundedness signal); F3 **proves** the cache preserves quality and tunes its threshold. Together they convert DocuSynth's positioning from "chat with PDF" into **"a measured, trustworthy semantic-caching layer for RAG"** — the defensible thing in `FUTURE_IMPLEMENTATION_STRATEGY.md`. Add F7 (token/cost tracking) immediately after to complete the "saves money, proven not to hurt quality" story.
