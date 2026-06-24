import hashlib
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit.logger import log_tagged
from app.auth.jwt import get_current_user
from app.cache.redis_cache import (
    cache_key,
    get_json,
    normalize_query,
    rate_limit_allow,
    set_json,
)
from app.cache.semantic_cache import lookup_semantic, store_semantic
from app.council.orchestrator import run_council
from app.db.models import Document, QueryLog, User
from app.db.session import get_db
from app.metrics.prometheus import (
    councilai_llm_calls_per_query,
    councilai_query_errors_total,
    councilai_query_latency_seconds,
    councilai_query_total,
    councilai_retrieval_latency_seconds,
)
from app.rag.embeddings import embed_query
from app.rag.retrieval import retrieve_all_chunks, retrieve_chunks

router = APIRouter(prefix="/api/v1")


class QueryRequest(BaseModel):
    question: str
    doc_id: str | None = None
    top_k: int = 5


class ExplainRequest(BaseModel):
    doc_id: str
    knowledge_level: str = "beginner"
    depth: str = "section-wise"
    focus_topics: list[str] = Field(default_factory=list)


class GenerateQuestionsRequest(BaseModel):
    doc_id: str
    num_questions: int = 5
    difficulty: int = 5
    question_type: str = "subjective"
    bloom_level: str | None = None


def _record_query(
    db: Session,
    user_id: str,
    doc_id: str | None,
    query_hash: str,
    status_name: str,
    latency: float,
) -> None:
    db.add(
        QueryLog(
            user_id=user_id,
            document_id=doc_id,
            query_hash=query_hash,
            status=status_name,
            latency_ms=latency * 1000,
        )
    )
    db.commit()


def _ms(seconds: float) -> float:
    return round(seconds * 1000.0, 3)


@router.post("/query")
async def query_endpoint(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start = time.perf_counter()
    timings = {
        "redis_lookup_ms": 0.0,
        "embedding_ms": 0.0,
        "pgvector_lookup_ms": 0.0,
        "retrieval_ms": 0.0,
        "llm_ms": 0.0,
        "total_ms": 0.0,
    }
    cache_result = "miss"
    similarity_score: float | None = None
    llm_call_count = 0

    if not rate_limit_allow(user.username):
        councilai_query_errors_total.labels(reason="rate_limited").inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded"
        )
    if not request.question.strip():
        councilai_query_errors_total.labels(reason="invalid_input").inc()
        raise HTTPException(status_code=400, detail="question is required")

    normalized = normalize_query(request.question)
    query_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    redis_key = cache_key(request.doc_id, normalized)

    # 1) Redis exact cache
    redis_t0 = time.perf_counter()
    cached = get_json(redis_key)
    timings["redis_lookup_ms"] = _ms(time.perf_counter() - redis_t0)
    if cached:
        cache_result = "exact_hit"
        timings["total_ms"] = _ms(time.perf_counter() - start)
        cached["cache_hit"] = True
        cached["cache_result"] = cache_result
        cached["similarity_score"] = None
        cached["llm_call_count"] = 0
        cached["timings"] = timings
        cached["latency"] = f"{(time.perf_counter() - start):.6f}s"
        councilai_query_total.labels(cache_result=cache_result).inc()
        councilai_query_latency_seconds.labels(cache_result=cache_result).observe(
            time.perf_counter() - start
        )
        councilai_llm_calls_per_query.observe(0)
        _record_query(
            db,
            user.username,
            request.doc_id,
            query_hash,
            "redis_cache_hit",
            time.perf_counter() - start,
        )
        log_tagged(
            "[Cache]",
            {"event": "exact_hit", "doc_id": request.doc_id, "query_hash": query_hash},
        )
        return cached

    # 2) Embedding + pgvector semantic cache
    embed_t0 = time.perf_counter()
    vector = await embed_query(normalized)
    timings["embedding_ms"] = _ms(time.perf_counter() - embed_t0)

    # Content hash gates the semantic cache so a re-ingested (changed) document
    # never serves a stale cached answer.
    doc_content_hash: str | None = None
    if request.doc_id:
        doc_row = db.query(Document).filter(Document.id == request.doc_id).first()
        doc_content_hash = doc_row.content_hash if doc_row else None

    pg_t0 = time.perf_counter()
    semantic_cached, similarity_score = lookup_semantic(
        db, request.doc_id, normalized, vector, doc_content_hash
    )
    timings["pgvector_lookup_ms"] = _ms(time.perf_counter() - pg_t0)

    if semantic_cached:
        cache_result = "semantic_hit"
        timings["total_ms"] = _ms(time.perf_counter() - start)
        semantic_cached["cache_hit"] = True
        semantic_cached["cache_result"] = cache_result
        semantic_cached["similarity_score"] = similarity_score
        semantic_cached["llm_call_count"] = 0
        semantic_cached["timings"] = timings
        semantic_cached["latency"] = f"{(time.perf_counter() - start):.6f}s"
        councilai_query_total.labels(cache_result=cache_result).inc()
        councilai_query_latency_seconds.labels(cache_result=cache_result).observe(
            time.perf_counter() - start
        )
        councilai_llm_calls_per_query.observe(0)
        _record_query(
            db,
            user.username,
            request.doc_id,
            query_hash,
            "semantic_cache_hit",
            time.perf_counter() - start,
        )
        log_tagged(
            "[Cache]",
            {
                "event": "semantic_hit",
                "doc_id": request.doc_id,
                "query_hash": query_hash,
                "similarity": similarity_score,
            },
        )
        return semantic_cached

    # 3) Retrieval
    retrieval_t0 = time.perf_counter()
    try:
        chunks_payload = await retrieve_chunks(
            request.question, request.doc_id, request.top_k or 5
        )
    except Exception as exc:
        councilai_query_errors_total.labels(reason="retrieval_failed").inc()
        log_tagged(
            "[Error]",
            {"event": "retrieval_failed", "doc_id": request.doc_id, "error": str(exc)},
        )
        raise HTTPException(status_code=503, detail="retrieval service unavailable") from exc
    timings["retrieval_ms"] = _ms(time.perf_counter() - retrieval_t0)
    councilai_retrieval_latency_seconds.observe(timings["retrieval_ms"] / 1000.0)

    chunk_texts = [chunk["content"] for chunk in chunks_payload if chunk.get("content")]
    if not chunk_texts:
        councilai_query_errors_total.labels(reason="no_chunks").inc()
        raise HTTPException(status_code=404, detail="no relevant chunks found for this question")

    # 4) Council
    llm_t0 = time.perf_counter()
    try:
        council_result = await run_council(
            request.question, chunk_texts, custom_prompt="", skip_chairman=False
        )
    except Exception as exc:
        councilai_query_errors_total.labels(reason="council_failed").inc()
        log_tagged(
            "[Error]",
            {"event": "council_failed", "doc_id": request.doc_id, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail="LLM council failed") from exc
    timings["llm_ms"] = _ms(time.perf_counter() - llm_t0)
    llm_call_count = int(council_result.get("llm_call_count", 0))
    councilai_llm_calls_per_query.observe(llm_call_count)

    timings["total_ms"] = _ms(time.perf_counter() - start)
    response = {
        "answer": council_result["final_answer"],
        "confidence": council_result["confidence"],
        "source": council_result["source"],
        "reasoning": council_result.get("reasoning", ""),
        "council_mode": council_result.get("council_mode", "full_council"),
        "peer_reviewed": len(council_result.get("peer_reviews", [])) > 0,
        "candidates": council_result.get("candidate_answers", []),
        "latency": f"{(time.perf_counter() - start):.6f}s",
        "cache_hit": False,
        "cache_result": cache_result,
        "similarity_score": similarity_score,
        "llm_call_count": llm_call_count,
        "timings": timings,
    }

    set_json(redis_key, response)
    store_semantic(db, request.doc_id, normalized, vector, response, doc_content_hash)

    councilai_query_total.labels(cache_result=cache_result).inc()
    councilai_query_latency_seconds.labels(cache_result=cache_result).observe(
        time.perf_counter() - start
    )
    _record_query(
        db,
        user.username,
        request.doc_id,
        query_hash,
        "success",
        time.perf_counter() - start,
    )
    log_tagged(
        "[Council]",
        {
            "event": "miss",
            "doc_id": request.doc_id,
            "query_hash": query_hash,
            "llm_call_count": llm_call_count,
        },
        db=db,
    )
    return response


@router.post("/explain")
async def explain_endpoint(
    request: ExplainRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start = time.perf_counter()
    if not rate_limit_allow(user.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded"
        )
    explain_cache_key = (
        f"explain:{request.doc_id}:{request.knowledge_level}:{request.depth}"
    )
    cached = get_json(explain_cache_key)
    if cached:
        cached["cache_hit"] = True
        cached["latency"] = f"{(time.perf_counter() - start):.6f}s"
        return cached
    chunks_payload = await retrieve_all_chunks(request.doc_id)
    chunk_texts = [chunk["content"] for chunk in chunks_payload if chunk.get("content")]
    if not chunk_texts:
        raise HTTPException(status_code=404, detail="document not found or empty")

    focus_clause = ""
    if request.focus_topics:
        focus_clause = (
            f"\n\nFocus especially on these topics: {', '.join(request.focus_topics)}"
        )
    depth_instruction = {
        "brief": "Provide a concise summary (2-3 paragraphs max).",
        "section-wise": "Organize the explanation into clear sections with headings.",
        "detailed": "Provide a thorough, detailed explanation covering all major points.",
    }.get(request.depth, "Organize the explanation into clear sections with headings.")
    level_instruction = {
        "beginner": "Explain as if to someone completely new to the subject.",
        "intermediate": "Explain at an intermediate level.",
        "advanced": "Explain at an expert level.",
    }.get(
        request.knowledge_level,
        "Explain as if to someone completely new to the subject.",
    )
    context_text = "\n\n---\n\n".join(chunk_texts)
    prompt = (
        "You are an expert educator. Based ONLY on the following document excerpts, generate an explanation.\n\n"
        f"Document Excerpts:\n{context_text}\n\n"
        f"Instructions:\n- {level_instruction}\n- {depth_instruction}\n"
        "- Ground every claim in the provided excerpts\n- Use clear formatting with headings and structure"
        f"{focus_clause}\n\nRespond with a well-structured explanation."
    )
    result = await run_council(
        f"explain:{request.doc_id}", chunk_texts, custom_prompt=prompt, skip_chairman=False
    )
    response = {
        "explanation": result["final_answer"],
        "sections": [],
        "confidence": result["confidence"],
        "source": result["source"],
        "latency": f"{(time.perf_counter() - start):.6f}s",
        "cache_hit": False,
        "llm_call_count": int(result.get("llm_call_count", 0)),
    }
    set_json(explain_cache_key, response)
    return response


@router.post("/generate-questions")
async def generate_questions_endpoint(
    request: GenerateQuestionsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _ = db
    start = time.perf_counter()
    if not rate_limit_allow(user.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded"
        )
    questions_cache_key = (
        f"questions:{request.doc_id}:{request.num_questions}:{request.difficulty}:{request.question_type}"
    )
    cached = get_json(questions_cache_key)
    if cached:
        cached["cache_hit"] = True
        cached["latency"] = f"{(time.perf_counter() - start):.6f}s"
        return cached
    chunks_payload = await retrieve_all_chunks(request.doc_id)
    chunk_texts = [chunk["content"] for chunk in chunks_payload if chunk.get("content")]
    if not chunk_texts:
        raise HTTPException(status_code=404, detail="document not found or empty")

    question_type_instruction = "open-ended subjective questions requiring evidence-based reasoning"
    options_fragment = ""
    if request.question_type == "mcq":
        question_type_instruction = "multiple-choice questions (MCQ) with exactly 4 options each"
        options_fragment = ', "options": ["A) ...", "B) ...", "C) ...", "D) ..."]'
    bloom_clause = (
        f"\n- Target Bloom's taxonomy level: {request.bloom_level}"
        if request.bloom_level
        else ""
    )
    context_text = "\n\n---\n\n".join(chunk_texts)
    prompt = (
        "You are an expert assessment designer. Based ONLY on the following document excerpts, "
        "generate practice questions.\n\n"
        f"Document Excerpts:\n{context_text}\n\n"
        f"Generate exactly {max(1, min(request.num_questions, 20))} {question_type_instruction}.\n"
        f"Requirements:\n- Difficulty level: {max(1, min(request.difficulty, 10))}/10{bloom_clause}\n"
        "- Ground every question in the provided document content\n"
        "- Provide an answer and brief explanation for each question\n\n"
        "Respond ONLY with a JSON array where each item is:\n"
        '{"question":"...","answer":"...","explanation":"..."'
        f"{options_fragment}" + "}"
    )
    result = await run_council(
        f"questions:{request.doc_id}", chunk_texts, custom_prompt=prompt, skip_chairman=True
    )
    raw_output = result["final_answer"]
    questions: list[dict] = []
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    left = cleaned.find("[")
    right = cleaned.rfind("]")
    if left >= 0 and right > left:
        cleaned = cleaned[left : right + 1]
    try:
        questions = json.loads(cleaned)
    except Exception:
        questions = []
    if len(questions) > request.num_questions:
        questions = questions[: request.num_questions]
    response = {
        "questions": questions,
        "raw_output": raw_output,
        "confidence": result["confidence"],
        "source": result["source"],
        "latency": f"{(time.perf_counter() - start):.6f}s",
        "cache_hit": False,
        "llm_call_count": int(result.get("llm_call_count", 0)),
    }
    set_json(questions_cache_key, response)
    return response
