# DocuSynth — Metrics & Outcomes

> What is actually measured today, what should be, and how to generate defensible numbers. **No fabricated numbers** — every figure below is copied from a committed artifact or marked "Not measured yet." Compiled 2026-06-24.

## 1. Currently Measured Outcomes (from the codebase)

### 1a. Committed benchmark — `tests/benchmark_results.json` (authoritative artifact)
Generated 2026-05-26 by `tests/bench_semantic_cache.py`, provider Ollama, model `qwen2.5:3b`, `single_local_fast`, `mock_llm=false`, similarity threshold 0.85, 1 document.

| Metric | Value |
|---|---|
| Canonical questions | 20 |
| Rephrased queries | 102 |
| Total queries | 122 |
| Exact cache hits | 0 |
| Semantic cache hits | 23 |
| Cold misses | 99 |
| Semantic cache hit rate | 22.549% |
| Overall cache hit rate | 18.852% |
| LLM-call reduction | 18.852% |
| Cold path p50 / p95 / p99 | 6202.254 / 10377.144 / 11244.068 ms |
| Semantic cache p50 / p95 / p99 | 119.753 / 358.951 / 420.852 ms |
| Speedup p95 / p99 | 28.91× / 26.717× |
| Error rate | 0.0% |

`docs/benchmarks/benchmark_ollama_fast_final.json` is **identical** to the above (the "final" copy).

### 1b. ⚠️ README discrepancy (must reconcile)
`README.md:83-99` reports **different** numbers for the same run:

| Metric | README | Committed JSON |
|---|---|---|
| Cold p95 | 8798.772 ms | 10377.144 ms |
| Semantic cache p95 | 126.227 ms | 358.951 ms |
| p95 speedup | 69.706× | 28.91× |
| Semantic hits | 23 | 23 |
| LLM-call reduction | 18.852% | 18.852% |

The hit counts match but the latency/speedup figures do not. **Treat `benchmark_results.json` as authoritative** and regenerate the README, or re-run and update both together. Do not cite 69.7× until reproduced.

### 1c. Persisted operational signal
- `query_logs(status, latency_ms, created_at, ...)` is written on every query (`backend/app/api/query.py:_record_query`). This is the only durable product metric store — **but nothing aggregates or visualizes it** today.

### 1d. Prometheus metrics emitted (live, not persisted to a committed file)
From `backend/app/metrics/prometheus.py` (names are `docusynth_*`):
- `docusynth_request_count_total{method,path,status}`, `docusynth_request_latency_seconds`
- `docusynth_query_total{cache_result}`, `docusynth_query_latency_seconds{cache_result}` (bucketed to 120 s)
- `docusynth_redis_lookup_seconds`, `docusynth_embedding_latency_seconds`, `docusynth_pgvector_lookup_seconds`, `docusynth_retrieval_latency_seconds`
- `docusynth_llm_calls_total{stage}`, `docusynth_llm_call_latency_seconds{stage}`, `docusynth_llm_calls_per_query`
- `docusynth_cache_operations_total{result,level}`, `docusynth_council_response_seconds`, `docusynth_document_ingestion_seconds`, `docusynth_llm_failure_count_total`, `docusynth_query_errors_total{reason}`

> ⚠️ The **RAG service emits no metrics** and is **not scraped** (`monitoring/prometheus.yml` targets `backend:8080` only). OCR/embedding/ingest internals are currently unobserved in Prometheus.

## 2. Performance Metrics That Should Be Tracked

| Metric | How | Status |
|---|---|---|
| p50/p95/p99 query latency by `cache_result` | already a labeled histogram — add Grafana panel | partially (metric exists, panel may not) |
| Cache hit rate (exact vs semantic vs miss) | from `docusynth_cache_operations_total` / `docusynth_query_total` | metric exists |
| LLM calls per query distribution | `docusynth_llm_calls_per_query` | metric exists |
| Embedding / pgvector / retrieval latency | existing histograms | metric exists |
| Ingest latency & success rate | `docusynth_document_ingestion_seconds` (+ add error counter) | partial |
| Vector search latency vs corpus size | benchmark across N chunks (pre/post HNSW) | Not measured yet |
| Provider failure rate | `docusynth_llm_failure_count_total`, `docusynth_query_errors_total` | metric exists, no alert |

## 3. Product Metrics That Should Be Tracked

| Metric | Source | Status |
|---|---|---|
| Activation (sessions that ingest then ask) | needs real analytics | Not measured yet |
| Queries per document / per user | derive from `query_logs` | Not measured yet (no aggregation) |
| Semantic-cache reuse benefit (queries served without LLM) | `query_logs.status` (`semantic_cache_hit`) | computable, not surfaced |
| Answer groundedness / "not in document" rate | needs eval harness | Not measured yet |
| Explain/Questions usage | not logged separately | Not measured yet |

## 4. Engineering Metrics That Should Be Tracked

| Metric | Status |
|---|---|
| Test coverage % | Not measured yet (no coverage in CI; no CI) |
| Lines/files in repo excluding venv | Not measured yet (venv currently inflates counts) |
| Build time / image size | Not measured yet (no CI) |
| Mean time to recover / deploy frequency | Not measured yet |
| Open security findings | Not measured yet (no `security-review` run recorded) |

## 5. Realistic Benchmark Tests to Generate Defensible Metrics

All harnesses already exist or are small extensions:

1. **Cache speedup (authoritative re-run).** `make benchmark` → `tests/bench_semantic_cache.py`. Record hardware, provider/model, threshold, and commit the JSON. Then regenerate README from the JSON so they can never diverge.
2. **Council vs single-model.** Run the benchmark with `LOCAL_LLM_FAST_MODE=false` (full council) and compare latency/cost/quality to `single_local_fast`. Currently the headline numbers are single-path only — measure the council explicitly.
3. **Retrieval/semantic accuracy.** `tests/bench_semantic_accuracy.py` — report precision of semantic-cache hits (are "hits" actually the same intent?) and tune the 0.85 threshold with a precision/recall curve.
4. **Chunking quality.** `tests/bench_document_chunking.py` — measure chunk size distribution, table preservation, and retrieval hit quality across document types.
5. **Concurrency/throughput.** `tests/stress_concurrency.py` — find max sustained RPS and p95 under load; use to validate the rate-limit fix and horizontal scaling.
6. **Vector index scaling (new).** Load 10k/100k/1M synthetic chunks; measure `pgvector_lookup` latency before/after an HNSW index. This produces the most credible "scalability" evidence and justifies Phase 2.
7. **Embedding quality A/B (new).** Compare current mean-pooling vs `sentence-transformers`/bge-prefixed embeddings on a labeled retrieval set.

## 6. Reporting Rules (to keep numbers defensible)
- Always state: provider, model, mode (single vs council), `mock_llm`, threshold, hardware, date, document count.
- Commit the raw + summary JSON; generate prose from JSON, never hand-type figures.
- Never present the single-path speedup as if it were the council's.
- Re-run after any change to caching, embeddings, retrieval, or indexing.

---

## 7. Strategy-Aligned Metrics & Benchmarks (added 2026-06-24)

> Tied to the features in `FEATURE_PRIORITIZATION.md` / `IMMEDIATE_BUILD_PLAN.md`. Every new metric below is **Not measured yet** — listed with exactly how to generate it. No values are invented.

### 7a. The metric that changes the project's story
- **Cache faithfulness retention** — *Not measured yet.* For every query the semantic cache would serve as a hit (similarity ≥ threshold), also compute the cold answer and score agreement (LLM-as-judge at temperature 0 **+** a deterministic ROUGE-L/token-F1 backstop). Report mean retention and the **hit-rate vs faithfulness curve** across thresholds `[0.80, 0.85, 0.90, 0.95]`. Harness: new `tests/eval/faithfulness.py` extending `tests/bench_semantic_accuracy.py`. This is the single most valuable number to produce; it converts "28.9× faster" into a defensible quality-vs-latency tradeoff.

### 7b. New benchmark tests to add
| Benchmark | Produces | Harness | Status |
|---|---|---|---|
| Faithfulness/threshold sweep | retention % per threshold + hit-rate curve | `tests/eval/faithfulness.py` (+ `--force-cold` on the query path) | Not measured yet |
| Retrieval quality (recall@k, nDCG) | quality of cosine top-k vs hybrid+rerank (F5) | extend `tests/bench_semantic_accuracy.py` with a labeled relevance set | Not measured yet |
| Cost per query + cost saved by cache | tokens (prompt/completion) + USD per query; cumulative $ avoided by hits (F7) | parse `usage` in `council/llm_client.py`; aggregate from `query_logs`/Prometheus | Not measured yet (no token tracking today) |
| Vector lookup vs corpus size (pre/post HNSW) | `pgvector_lookup` latency at 10k/100k/1M chunks (F5) | seed synthetic chunks; time `python-rag /retrieve` | Not measured yet |
| Council vs single-model | latency, cost, and faithfulness of full council vs `single_local_fast` | run `tests/bench_semantic_cache.py` with `LOCAL_LLM_FAST_MODE=false` | Not measured yet |
| Ingest throughput + failure rate (async) | docs/min, retry/failure counts (F11) | drive `tests/stress_concurrency.py` against the ingest path | Not measured yet |
| Max sustained RPS + p95 under load | capacity for the rate-limit fix + scaling claims | `tests/stress_concurrency.py` | Not measured yet |

### 7c. New live metrics to emit (Prometheus)
- `docusynth_llm_tokens_total{stage,type}`, `docusynth_query_cost_usd`, `docusynth_cost_saved_usd_total` (F7).
- `docusynth_cache_faithfulness` (sampled, from the eval pipeline) (F1).
- `docusynth_citations_per_answer`, plus top-1 similarity by `cache_result` (F3).
- New `reason="stale_hash"` on `docusynth_cache_operations_total` (F2 invalidations).
- **Scrape the RAG service** (currently unscraped) to capture embed/retrieve/ingest latencies.

### 7d. Engineering metrics to start tracking (via CI — F4)
- Test coverage %; build time + image size; lint/type pass rate; security findings (`security-review`). All **Not measured yet** (no CI today).

### 7e. Defensibility checklist before publishing any new number
1. Generated by a committed harness, not hand-typed.
2. Raw + summary JSON committed under `docs/benchmarks/`.
3. Run conditions recorded (provider/model/mode/threshold/hardware/date).
4. Prose (README) generated from the JSON so the two cannot diverge again.
