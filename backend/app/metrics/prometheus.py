from prometheus_client import Counter, Histogram

councilai_request_count_total = Counter(
    "docusynth_request_count_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

councilai_request_latency_seconds = Histogram(
    "docusynth_request_latency_seconds",
    "Request latency in seconds",
    ["method", "path"],
)

councilai_council_response_seconds = Histogram(
    "docusynth_council_response_seconds",
    "Council orchestration response latency in seconds",
)

councilai_llm_failure_count_total = Counter(
    "docusynth_llm_failure_count_total",
    "Total LLM call failures",
)

councilai_cache_operations_total = Counter(
    "docusynth_cache_operations_total",
    "Cache operations by result and level",
    ["result", "level"],
)

councilai_retrieval_latency_seconds = Histogram(
    "docusynth_retrieval_latency_seconds",
    "RAG retrieval latency in seconds",
)

councilai_document_ingestion_seconds = Histogram(
    "docusynth_document_ingestion_seconds",
    "Document ingestion latency in seconds",
)

councilai_query_total = Counter(
    "docusynth_query_total",
    "Total /api/v1/query requests by cache_result",
    ["cache_result"],
)

councilai_query_latency_seconds = Histogram(
    "docusynth_query_latency_seconds",
    "End-to-end /api/v1/query latency in seconds, labelled by cache_result",
    ["cache_result"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

councilai_redis_lookup_seconds = Histogram(
    "docusynth_redis_lookup_seconds",
    "Redis exact-cache lookup latency in seconds",
    buckets=(0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)

councilai_embedding_latency_seconds = Histogram(
    "docusynth_embedding_latency_seconds",
    "Query embedding latency in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

councilai_pgvector_lookup_seconds = Histogram(
    "docusynth_pgvector_lookup_seconds",
    "pgvector semantic cache lookup latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2),
)

councilai_llm_calls_total = Counter(
    "docusynth_llm_calls_total",
    "Total LLM calls by stage",
    ["stage"],
)

councilai_llm_call_latency_seconds = Histogram(
    "docusynth_llm_call_latency_seconds",
    "Latency per individual LLM call in seconds",
    ["stage"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

councilai_llm_calls_per_query = Histogram(
    "docusynth_llm_calls_per_query",
    "Number of LLM calls per /api/v1/query request",
    buckets=(0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20),
)

councilai_query_errors_total = Counter(
    "docusynth_query_errors_total",
    "Total /api/v1/query errors by reason",
    ["reason"],
)

councilai_semantic_cache_stale_total = Counter(
    "docusynth_semantic_cache_stale_total",
    "Semantic cache entries skipped on lookup or invalidated on re-ingest due to a "
    "changed document content hash",
    ["event"],  # event=lookup_skip | invalidate
)
