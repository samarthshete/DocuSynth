"""DocuSynth semantic-cache benchmark.

Measures end-to-end /api/v1/query latency, cache hit composition, and LLM call
reduction for the FastAPI + PostgreSQL/pgvector + Redis stack. Numbers are
generated locally from real runs against a running stack.

Usage:
    docker compose up --build
    python tests/bench_semantic_cache.py
        [--api http://localhost:8080]
        [--pdf path/to/file.pdf]
        [--mock-llm]
        [--threshold 0.85]

Outputs:
    tests/benchmark_results_raw.json
    tests/benchmark_results.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests

DEFAULT_API = os.getenv("API_BASE", "http://localhost:8080")
DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.85"))
RESULTS_DIR = Path(__file__).resolve().parent
RAW_RESULTS_FILE = RESULTS_DIR / "benchmark_results_raw.json"
SUMMARY_RESULTS_FILE = RESULTS_DIR / "benchmark_results.json"

USERNAME = os.getenv("BENCH_USERNAME", "bench_user")
PASSWORD = os.getenv("BENCH_PASSWORD", "bench-password-123")


# Canonical questions and paraphrases. The doc content does not need to match;
# what matters is that paraphrases of the same canonical produce semantically
# similar embeddings so the pgvector cache can resolve them to the canonical.
QUERY_CLUSTERS: list[dict[str, Any]] = [
    {
        "id": 1,
        "canonical": "What is the main topic of this document?",
        "paraphrases": [
            "Summarize the principal subject of this document.",
            "Describe the central theme covered in this document.",
            "What is the document primarily about?",
            "Give me the high-level topic of this document.",
            "What overall subject does this document address?",
            "Identify the main subject discussed in this document.",
        ],
    },
    {
        "id": 2,
        "canonical": "List the key concepts introduced in this document.",
        "paraphrases": [
            "What are the most important ideas in this document?",
            "Enumerate the core concepts covered in this document.",
            "Which key terms or concepts does the document introduce?",
            "Provide a list of the central ideas presented here.",
            "Outline the main concepts of this document.",
        ],
    },
    {
        "id": 3,
        "canonical": "Explain the methodology described in this document.",
        "paraphrases": [
            "Describe the approach this document presents.",
            "How does the methodology in the document work?",
            "What method is outlined in this document?",
            "Walk through the procedure presented in the document.",
            "Explain how the technique discussed in the document operates.",
            "What approach does this document follow?",
        ],
    },
    {
        "id": 4,
        "canonical": "What problem does this document solve?",
        "paraphrases": [
            "Which problem is addressed by this document?",
            "What issue is the document trying to resolve?",
            "Describe the problem this document targets.",
            "What is the motivating problem in this document?",
            "Which challenge does this document tackle?",
        ],
    },
    {
        "id": 5,
        "canonical": "Who are the intended readers of this document?",
        "paraphrases": [
            "Which audience is this document written for?",
            "What kind of reader benefits from this document?",
            "Who would find this document most useful?",
            "Who is the target reader of this document?",
            "Identify the audience for this document.",
        ],
    },
    {
        "id": 6,
        "canonical": "What are the most important results or conclusions?",
        "paraphrases": [
            "Summarize the main findings of this document.",
            "What does the document conclude?",
            "What outcomes does the document highlight?",
            "List the headline results of this document.",
            "What are the critical conclusions of this document?",
        ],
    },
    {
        "id": 7,
        "canonical": "Explain the architecture diagrammed in the document.",
        "paraphrases": [
            "Walk me through the architecture presented in this document.",
            "How does the system architecture in the document work?",
            "Describe the overall structure of the system described here.",
            "Explain the components and connections shown in the document.",
            "What architecture is documented here?",
        ],
    },
    {
        "id": 8,
        "canonical": "How is data stored and retrieved in this system?",
        "paraphrases": [
            "Describe the data storage and retrieval flow in the document.",
            "How does this system persist and look up data?",
            "Explain how data is saved and queried in the system.",
            "What persistence mechanism is described in the document?",
            "How are records stored and accessed in this system?",
        ],
    },
    {
        "id": 9,
        "canonical": "What role does caching play in this system?",
        "paraphrases": [
            "How is caching used in the system?",
            "Describe the caching strategy in this document.",
            "What is the purpose of the cache in this design?",
            "How does the system leverage caching?",
            "Explain the caching layer described here.",
        ],
    },
    {
        "id": 10,
        "canonical": "Describe how authentication is handled in the system.",
        "paraphrases": [
            "How does this system authenticate users?",
            "Explain the authentication mechanism in this document.",
            "What auth approach does the document describe?",
            "How is identity verified in this system?",
            "Describe the login and authentication flow here.",
        ],
    },
    {
        "id": 11,
        "canonical": "How is observability implemented in this system?",
        "paraphrases": [
            "What observability tools does this document describe?",
            "Explain monitoring and metrics for this system.",
            "How is this system instrumented for observability?",
            "Describe the metrics, logs, and traces in this design.",
            "How does the system expose telemetry?",
        ],
    },
    {
        "id": 12,
        "canonical": "What are the trade-offs of the approach described?",
        "paraphrases": [
            "Discuss the trade-offs of the methodology in this document.",
            "What compromises does the documented approach involve?",
            "Explain the pros and cons of the described approach.",
            "What are the costs and benefits of this design?",
            "Outline the trade-offs documented here.",
        ],
    },
    {
        "id": 13,
        "canonical": "How does the system handle failures and errors?",
        "paraphrases": [
            "Describe error handling in this system.",
            "What is the failure-handling strategy of this design?",
            "How is the system resilient to failures?",
            "Explain how errors are managed and recovered from here.",
            "Outline the document's failure recovery approach.",
        ],
    },
    {
        "id": 14,
        "canonical": "What configuration options does this system expose?",
        "paraphrases": [
            "List the configurable parameters of this system.",
            "Which settings can be adjusted in this design?",
            "Describe the configuration surface area of this system.",
            "What knobs does the documented system provide?",
            "Enumerate the runtime configuration options here.",
        ],
    },
    {
        "id": 15,
        "canonical": "How does this system scale under load?",
        "paraphrases": [
            "What scaling strategy does this system use?",
            "Explain how the design handles increased load.",
            "Describe horizontal and vertical scaling for this system.",
            "How does this architecture remain performant at scale?",
            "What scalability properties does the document describe?",
        ],
    },
    {
        "id": 16,
        "canonical": "What security guarantees does the system provide?",
        "paraphrases": [
            "Describe the security model of this system.",
            "What security controls does this document outline?",
            "How does the documented design protect data?",
            "Explain the threat model and mitigations in this document.",
            "List the security guarantees of this design.",
        ],
    },
    {
        "id": 17,
        "canonical": "How is testing performed for this system?",
        "paraphrases": [
            "Describe the testing strategy of this design.",
            "What test types does the document cover?",
            "How is correctness validated in this system?",
            "Explain how the system is verified through testing.",
            "Outline the documented test approach.",
        ],
    },
    {
        "id": 18,
        "canonical": "What dependencies does this system rely on?",
        "paraphrases": [
            "List the external dependencies of this system.",
            "Which third-party services are required by this system?",
            "Describe the runtime dependencies of this system.",
            "What software components must be present for this system?",
            "Enumerate the dependencies described in the document.",
        ],
    },
    {
        "id": 19,
        "canonical": "How is the documented system deployed?",
        "paraphrases": [
            "Describe the deployment workflow for this system.",
            "How do operators ship this system to production?",
            "Explain the deployment model in this document.",
            "What are the deployment steps for this design?",
            "Outline how the system is rolled out.",
        ],
    },
    {
        "id": 20,
        "canonical": "What future improvements are suggested in the document?",
        "paraphrases": [
            "Which future work does this document propose?",
            "List the improvements outlined for future iterations.",
            "What enhancements does the document recommend next?",
            "Describe the roadmap or future plans in the document.",
            "What follow-up work is suggested?",
        ],
    },
]


@dataclass
class QueryRecord:
    canonical_question_id: int
    is_canonical: bool
    question: str
    cache_result: str
    similarity_score: float | None
    total_latency_ms: float
    embedding_latency_ms: float
    redis_lookup_ms: float
    pgvector_lookup_ms: float
    retrieval_latency_ms: float
    llm_latency_ms: float
    llm_call_count: int
    council_mode: str
    status_code: int
    error: str | None = None


@dataclass
class BenchmarkConfig:
    api_base: str = DEFAULT_API
    pdf_path: Path | None = None
    mock_llm: bool = False
    similarity_threshold: float = DEFAULT_THRESHOLD
    delay_seconds: float = 0.0
    max_canonicals: int | None = None
    max_paraphrases: int | None = None
    provider: str = "openrouter"
    model: str = ""
    local_fast_mode: bool = False


@dataclass
class Summary:
    timestamp: str
    api_base: str
    provider: str
    model: str
    local_fast_mode: bool
    council_mode: str
    mock_llm: bool
    similarity_threshold: float
    number_of_documents: int
    canonical_questions: int
    rephrased_queries: int
    exact_cache_hits: int
    semantic_cache_hits: int
    cold_misses: int
    semantic_cache_hit_rate: float
    overall_cache_hit_rate: float
    llm_call_reduction_percent: float
    cold_path_p50_ms: float
    cold_path_p95_ms: float
    cold_path_p99_ms: float
    semantic_cache_p50_ms: float | None
    semantic_cache_p95_ms: float | None
    semantic_cache_p99_ms: float | None
    speedup_p95: float | None
    speedup_p99: float | None
    error_rate_percent: float
    delay_seconds: float
    llm_calls_per_miss: float
    resume_publishable: bool
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    weight = rank - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def _print(line: str = "") -> None:
    print(line, flush=True)


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _ensure_pdf(cfg: BenchmarkConfig) -> Path:
    if cfg.pdf_path and cfg.pdf_path.exists():
        return cfg.pdf_path

    env_path = os.getenv("BENCH_PDF")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    fallback = Path(__file__).resolve().parent.parent / "data" / "11 - WGAN.pdf"
    if fallback.exists():
        return fallback

    generated = RESULTS_DIR / "_generated_bench_doc.pdf"
    if generated.exists():
        return generated

    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise SystemExit(
            "No PDF available. Provide one via --pdf path/to/file.pdf or set BENCH_PDF env var. "
            "Optionally install reportlab to auto-generate one: pip install reportlab"
        ) from exc

    _print(f"  → No PDF supplied; generating a synthetic one at {generated}")
    pdf = canvas.Canvas(str(generated), pagesize=LETTER)
    width, height = LETTER
    pages = [
        [
            "DocuSynth Reference Document (Synthetic)",
            "",
            "This document describes a Dockerized document intelligence platform.",
            "It uses FastAPI for the control plane and Python for retrieval-augmented",
            "generation. PostgreSQL with the pgvector extension stores both document",
            "chunks and a semantic cache of normalized queries with their embeddings.",
            "Redis provides exact-match query caching and per-user rate limiting.",
            "JWT tokens authenticate requests against protected endpoints.",
        ],
        [
            "Architecture overview:",
            "Clients send authenticated requests to /api/v1/query. The control plane",
            "first checks Redis for an exact match using a normalized hash of the",
            "question. On a miss it embeds the question via the RAG service, then",
            "performs a cosine-distance lookup in the pgvector semantic_cache table.",
            "If similarity exceeds the configured threshold (default 0.85) the cached",
            "answer is returned. Otherwise retrieval, council generation, peer review,",
            "and chairman synthesis run sequentially before storing results in both caches.",
        ],
        [
            "Observability and operations:",
            "Prometheus scrapes /metrics on the backend and Grafana visualizes",
            "request rate, latency percentiles, cache hit rate, retrieval and embedding",
            "latency, LLM call counts, and error counts. Structured tagged logs",
            "([HTTP], [Council], [Cache], [Audit], [Error], [RAG]) carry user_id,",
            "doc_id, query hashes, and per-stage timings for forensic analysis.",
            "Deployment is orchestrated through Docker Compose for local development",
            "with parity to a future Kubernetes deployment.",
        ],
        [
            "Failure handling and trade-offs:",
            "If retrieval fails the request returns 503 and increments a labelled",
            "error counter. If all council members fail synthesis falls back to the",
            "single best candidate with reduced confidence. Trade-offs include",
            "additional latency from peer review in exchange for higher answer",
            "robustness, and embedding overhead in exchange for paraphrase-tolerant",
            "caching. Future improvements include async ingestion via a Redis worker",
            "and fine-grained per-document semantic-cache namespacing.",
        ],
    ]
    for page_text in pages:
        text_obj = pdf.beginText(72, height - 72)
        text_obj.setFont("Helvetica", 11)
        for line in page_text:
            text_obj.textLine(line)
        pdf.drawText(text_obj)
        pdf.showPage()
    pdf.save()
    return generated


# ---------------------------------------------------------------------------
# HTTP steps
# ---------------------------------------------------------------------------


def _api(cfg: BenchmarkConfig, path: str) -> str:
    return f"{cfg.api_base.rstrip('/')}{path}"


def _login(cfg: BenchmarkConfig, session: requests.Session) -> dict[str, str]:
    _print("[1/5] Authenticating")
    try:
        response = session.post(
            _api(cfg, "/api/v1/login"),
            json={"username": USERNAME, "password": PASSWORD},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SystemExit(f"  ✗ auth request failed: {exc}") from exc
    if response.status_code == 200:
        return {"Authorization": f"Bearer {response.json()['token']}"}
    try:
        response = session.post(
            _api(cfg, "/api/v1/register"),
            json={"username": USERNAME, "password": PASSWORD},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise SystemExit(f"  ✗ register request failed: {exc}") from exc
    if response.status_code in (200, 201):
        return {"Authorization": f"Bearer {response.json()['token']}"}
    raise SystemExit(f"  ✗ auth failed: {response.status_code} {response.text}")


def _ingest(cfg: BenchmarkConfig, session: requests.Session, headers: dict[str, str]) -> str:
    _print("[2/5] Ingesting test document")
    pdf_path = _ensure_pdf(cfg)
    with pdf_path.open("rb") as fp:
        try:
            response = session.post(
                _api(cfg, "/api/v1/ingest"),
                headers=headers,
                files={"file": (pdf_path.name, fp, "application/pdf")},
                timeout=600,
            )
        except requests.RequestException as exc:
            raise SystemExit(f"  ✗ ingest request failed: {exc}") from exc
    if response.status_code != 200:
        raise SystemExit(f"  ✗ ingest failed ({response.status_code}): {response.text[:300]}")
    body = response.json()
    doc_id = body.get("doc_id")
    if not doc_id:
        raise SystemExit(f"  ✗ ingest response missing doc_id: {body}")
    _print(f"  ✓ ingested {pdf_path.name} → doc_id={doc_id}, chunks={body.get('chunk_count')}")
    return doc_id


def _clear_caches(cfg: BenchmarkConfig, session: requests.Session, headers: dict[str, str]) -> None:
    _print("[3/5] Clearing Redis + pgvector semantic_cache")
    try:
        response = session.post(_api(cfg, "/api/v1/admin/clear-cache"), headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise SystemExit(f"  ✗ clear-cache request failed: {exc}") from exc
    if response.status_code != 200:
        raise SystemExit(f"  ✗ clear-cache failed ({response.status_code}): {response.text}")
    body = response.json()
    _print(f"  ✓ {body}")


def _do_query(
    cfg: BenchmarkConfig,
    session: requests.Session,
    headers: dict[str, str],
    doc_id: str,
    canonical_id: int,
    is_canonical: bool,
    question: str,
) -> QueryRecord:
    t0 = time.perf_counter()
    try:
        response = session.post(
            _api(cfg, "/api/v1/query"),
            headers=headers,
            json={"question": question, "doc_id": doc_id, "top_k": 5},
            timeout=600,
        )
    except requests.RequestException as exc:
        return QueryRecord(
            canonical_question_id=canonical_id,
            is_canonical=is_canonical,
            question=question,
            cache_result="error",
            similarity_score=None,
            total_latency_ms=(time.perf_counter() - t0) * 1000.0,
            embedding_latency_ms=0.0,
            redis_lookup_ms=0.0,
            pgvector_lookup_ms=0.0,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            llm_call_count=0,
            council_mode="error",
            status_code=-1,
            error=str(exc),
        )

    measured_total_ms = (time.perf_counter() - t0) * 1000.0
    if response.status_code != 200:
        return QueryRecord(
            canonical_question_id=canonical_id,
            is_canonical=is_canonical,
            question=question,
            cache_result="error",
            similarity_score=None,
            total_latency_ms=measured_total_ms,
            embedding_latency_ms=0.0,
            redis_lookup_ms=0.0,
            pgvector_lookup_ms=0.0,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            llm_call_count=0,
            council_mode="error",
            status_code=response.status_code,
            error=response.text[:500],
        )

    payload = response.json()
    timings = payload.get("timings") or {}
    return QueryRecord(
        canonical_question_id=canonical_id,
        is_canonical=is_canonical,
        question=question,
        cache_result=str(payload.get("cache_result") or ("exact_hit" if payload.get("cache_hit") else "miss")),
        similarity_score=payload.get("similarity_score"),
        total_latency_ms=float(timings.get("total_ms") or measured_total_ms),
        embedding_latency_ms=float(timings.get("embedding_ms") or 0.0),
        redis_lookup_ms=float(timings.get("redis_lookup_ms") or 0.0),
        pgvector_lookup_ms=float(timings.get("pgvector_lookup_ms") or 0.0),
        retrieval_latency_ms=float(timings.get("retrieval_ms") or 0.0),
        llm_latency_ms=float(timings.get("llm_ms") or 0.0),
        llm_call_count=int(payload.get("llm_call_count") or 0),
        council_mode=str(payload.get("council_mode") or ""),
        status_code=response.status_code,
        error=None,
    )


def _run_phase(
    label: str,
    cfg: BenchmarkConfig,
    session: requests.Session,
    headers: dict[str, str],
    doc_id: str,
    items: list[tuple[int, bool, str]],
) -> list[QueryRecord]:
    _print(f"  ▶ {label}: {len(items)} requests")
    records: list[QueryRecord] = []
    for index, (canonical_id, is_canonical, question) in enumerate(items, start=1):
        record = _do_query(cfg, session, headers, doc_id, canonical_id, is_canonical, question)
        records.append(record)
        marker = "miss" if record.cache_result == "miss" else record.cache_result
        line = (
            f"    [{index:>3}/{len(items)}] cluster={canonical_id:<2} "
            f"cache={marker:<12} total={record.total_latency_ms:8.1f}ms "
            f"llm_calls={record.llm_call_count}"
        )
        if record.similarity_score is not None:
            line += f" sim={record.similarity_score:.3f}"
        if record.error:
            line += f" err={record.error[:80]}"
        _print(line)
        if cfg.delay_seconds and cfg.delay_seconds > 0 and index < len(items):
            time.sleep(cfg.delay_seconds)
    return records


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _summarize(cfg: BenchmarkConfig, records: list[QueryRecord]) -> Summary:
    successful = [record for record in records if record.status_code == 200]
    errors = [record for record in records if record.status_code != 200]

    cold_misses = [record for record in successful if record.cache_result == "miss"]
    exact_hits = [record for record in successful if record.cache_result == "exact_hit"]
    semantic_hits = [record for record in successful if record.cache_result == "semantic_hit"]

    rephrased = [record for record in records if not record.is_canonical]
    rephrased_successful = [record for record in rephrased if record.status_code == 200]
    semantic_hits_in_rephrased = [
        record for record in rephrased_successful if record.cache_result == "semantic_hit"
    ]

    canonical_count = sum(1 for record in records if record.is_canonical)
    rephrased_count = len(rephrased)

    total_records = len(records) or 1

    semantic_hit_rate = (
        (len(semantic_hits_in_rephrased) / len(rephrased_successful)) * 100.0
        if rephrased_successful
        else 0.0
    )
    overall_hit_rate = (
        ((len(exact_hits) + len(semantic_hits)) / len(successful)) * 100.0
        if successful
        else 0.0
    )

    cold_total_latency = [record.total_latency_ms for record in cold_misses]
    semantic_total_latency = [record.total_latency_ms for record in semantic_hits]

    cold_p50 = _percentile(cold_total_latency, 50) or 0.0
    cold_p95 = _percentile(cold_total_latency, 95) or 0.0
    cold_p99 = _percentile(cold_total_latency, 99) or 0.0
    sem_p50 = _percentile(semantic_total_latency, 50)
    sem_p95 = _percentile(semantic_total_latency, 95)
    sem_p99 = _percentile(semantic_total_latency, 99)

    speedup_p95 = (cold_p95 / sem_p95) if (sem_p95 and sem_p95 > 0) else None
    speedup_p99 = (cold_p99 / sem_p99) if (sem_p99 and sem_p99 > 0) else None

    total_llm_calls = sum(record.llm_call_count for record in successful)
    no_cache_baseline_calls = sum(
        max(record.llm_call_count, 1) if record.cache_result == "miss" else 0
        for record in successful
    )
    # Baseline if every successful query had to run the cold path: assume the
    # average cold-path call count (or 1 when none was observed).
    avg_cold_calls = (
        statistics.mean([r.llm_call_count for r in cold_misses]) if cold_misses else 0.0
    )
    if avg_cold_calls <= 0:
        avg_cold_calls = 1.0
    baseline_calls = avg_cold_calls * len(successful)
    if baseline_calls > 0:
        llm_call_reduction_percent = max(
            0.0, (1.0 - total_llm_calls / baseline_calls) * 100.0
        )
    else:
        llm_call_reduction_percent = 0.0

    error_rate_percent = (len(errors) / total_records) * 100.0
    llm_calls_per_miss = (
        float(statistics.mean([record.llm_call_count for record in cold_misses]))
        if cold_misses
        else 0.0
    )
    enough_samples = canonical_count >= 20 and rephrased_count >= 100
    full_default_shape = cfg.max_canonicals is None and cfg.max_paraphrases is None
    full_benchmark_complete = full_default_shape and enough_samples
    council_mode = "single_local_fast" if cfg.local_fast_mode and cfg.provider == "ollama" else "full_council"
    resume_publishable = (
        (not cfg.mock_llm)
        and cfg.provider == "ollama"
        and full_benchmark_complete
        and error_rate_percent <= 1.0
    )

    notes: list[str] = []
    if cfg.mock_llm:
        notes.append("mock-llm mode active: LLM responses are local stubs, do NOT publish as real benchmarks")
    if not semantic_hits:
        notes.append("no semantic cache hits observed; consider lowering similarity_threshold or seeding more canonicals")
    if not cold_misses:
        notes.append("no cold misses recorded; cold-path percentiles will be zero")
    _ = no_cache_baseline_calls  # kept for potential future use

    return Summary(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        api_base=cfg.api_base,
        provider=cfg.provider,
        model=cfg.model,
        local_fast_mode=cfg.local_fast_mode,
        council_mode=council_mode,
        mock_llm=cfg.mock_llm,
        similarity_threshold=cfg.similarity_threshold,
        number_of_documents=1,
        canonical_questions=canonical_count,
        rephrased_queries=rephrased_count,
        exact_cache_hits=len(exact_hits),
        semantic_cache_hits=len(semantic_hits),
        cold_misses=len(cold_misses),
        semantic_cache_hit_rate=round(semantic_hit_rate, 3),
        overall_cache_hit_rate=round(overall_hit_rate, 3),
        llm_call_reduction_percent=round(llm_call_reduction_percent, 3),
        cold_path_p50_ms=round(cold_p50, 3),
        cold_path_p95_ms=round(cold_p95, 3),
        cold_path_p99_ms=round(cold_p99, 3),
        semantic_cache_p50_ms=round(sem_p50, 3) if sem_p50 is not None else None,
        semantic_cache_p95_ms=round(sem_p95, 3) if sem_p95 is not None else None,
        semantic_cache_p99_ms=round(sem_p99, 3) if sem_p99 is not None else None,
        speedup_p95=round(speedup_p95, 3) if speedup_p95 is not None else None,
        speedup_p99=round(speedup_p99, 3) if speedup_p99 is not None else None,
        error_rate_percent=round(error_rate_percent, 3),
        delay_seconds=round(cfg.delay_seconds, 3),
        llm_calls_per_miss=round(llm_calls_per_miss, 3),
        resume_publishable=resume_publishable,
        notes=notes,
    )


def _save(records: list[QueryRecord], summary: Summary) -> None:
    raw_payload = {
        "timestamp": summary.timestamp,
        "summary": asdict(summary),
        "records": [asdict(record) for record in records],
    }
    RAW_RESULTS_FILE.write_text(json.dumps(raw_payload, indent=2))
    SUMMARY_RESULTS_FILE.write_text(json.dumps(asdict(summary), indent=2))
    _print(f"  ✓ raw results → {RAW_RESULTS_FILE}")
    _print(f"  ✓ summary    → {SUMMARY_RESULTS_FILE}")


def _print_summary(summary: Summary) -> None:
    _print("")
    _print("─── Benchmark summary (locally measured) ───")
    for key, value in asdict(summary).items():
        if isinstance(value, list):
            for item in value:
                _print(f"  note: {item}")
        else:
            _print(f"  {key}: {value}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DocuSynth semantic-cache benchmark")
    parser.add_argument("--api", default=DEFAULT_API, help="Backend base URL (default: %(default)s)")
    parser.add_argument("--pdf", type=Path, default=None, help="Path to a test PDF")
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Label results as mock (set MOCK_LLM=true on the backend separately)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Similarity threshold the backend uses (default: %(default)s)",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=None,
        help=(
            "Sleep this many seconds between benchmark requests. "
            "Defaults to 0.0 in --mock-llm mode and 1.0 in real mode."
        ),
    )
    parser.add_argument("--max-canonicals", type=int, default=None)
    parser.add_argument("--max-paraphrases", type=int, default=None)
    args = parser.parse_args(argv)

    if args.delay_seconds is None:
        delay_seconds = 0.0 if args.mock_llm else 1.0
    else:
        delay_seconds = max(0.0, float(args.delay_seconds))

    cfg = BenchmarkConfig(
        api_base=args.api,
        pdf_path=args.pdf,
        mock_llm=args.mock_llm,
        similarity_threshold=args.threshold,
        delay_seconds=delay_seconds,
        max_canonicals=(
            max(0, int(args.max_canonicals)) if args.max_canonicals is not None else None
        ),
        max_paraphrases=(
            max(0, int(args.max_paraphrases)) if args.max_paraphrases is not None else None
        ),
    )

    env_values = _read_env_file(Path(__file__).resolve().parents[1] / ".env")
    provider = env_values.get("LLM_PROVIDER", "openrouter").strip().lower() or "openrouter"
    local_fast_mode = env_values.get("LOCAL_LLM_FAST_MODE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if provider == "ollama":
        model = env_values.get("OLLAMA_MODEL", "qwen2.5:3b")
    else:
        model = env_values.get("COUNCIL_MODEL_1", "unknown")
    cfg.provider = provider
    cfg.model = model
    cfg.local_fast_mode = local_fast_mode

    if not cfg.mock_llm:
        mock_env = env_values.get("MOCK_LLM", "").strip().lower()
        if mock_env in {"", "true", "1", "yes", "on"}:
            raise SystemExit(
                "Real benchmark mode requires backend environment MOCK_LLM=false. "
                "Update .env and restart backend before running without --mock-llm."
            )
        if provider == "openrouter":
            openrouter_key = env_values.get("OPENROUTER_API_KEY", "")
            if not openrouter_key or "your_" in openrouter_key.lower():
                raise SystemExit(
                    "Real benchmark mode with LLM_PROVIDER=openrouter requires valid OPENROUTER_API_KEY in .env."
                )

    _print(
        f"DocuSynth benchmark → {cfg.api_base}  threshold={cfg.similarity_threshold}  "
        f"mock_llm={cfg.mock_llm}  provider={cfg.provider}  model={cfg.model}  "
        f"local_fast_mode={cfg.local_fast_mode}  delay_seconds={cfg.delay_seconds}"
    )

    session = requests.Session()
    headers = _login(cfg, session)
    doc_id = _ingest(cfg, session, headers)
    _clear_caches(cfg, session, headers)

    selected_clusters = QUERY_CLUSTERS
    if cfg.max_canonicals is not None:
        selected_clusters = QUERY_CLUSTERS[: cfg.max_canonicals]

    canonical_phase: list[tuple[int, bool, str]] = [
        (cluster["id"], True, cluster["canonical"]) for cluster in selected_clusters
    ]
    paraphrase_phase_full: list[tuple[int, bool, str]] = [
        (cluster["id"], False, paraphrase)
        for cluster in selected_clusters
        for paraphrase in cluster["paraphrases"]
    ]
    if cfg.max_paraphrases is None:
        paraphrase_phase = paraphrase_phase_full
    else:
        paraphrase_phase = paraphrase_phase_full[: cfg.max_paraphrases]

    _print("[4/5] Cold canonical phase (populates Redis + pgvector caches)")
    cold_records = _run_phase("cold canonical", cfg, session, headers, doc_id, canonical_phase)

    _print("[5/5] Paraphrase phase (exercises pgvector semantic cache)")
    paraphrase_records = _run_phase(
        "paraphrases", cfg, session, headers, doc_id, paraphrase_phase
    )

    all_records = cold_records + paraphrase_records
    summary = _summarize(cfg, all_records)
    _save(all_records, summary)
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
