import time
from typing import Optional

from app.config import get_settings
from app.db.models import SemanticCacheEntry
from app.metrics.prometheus import (
    councilai_cache_operations_total,
    councilai_pgvector_lookup_seconds,
    councilai_semantic_cache_stale_total,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

settings = get_settings()


def lookup_semantic(
    db: Session,
    doc_id: str | None,
    normalized_query: str,
    query_embedding: list[float],
    doc_content_hash: str | None = None,
) -> tuple[Optional[dict], Optional[float]]:
    """Return (response_json, similarity) if a match passes the threshold, else (None, similarity_or_None).

    When ``doc_content_hash`` is provided, a vector match whose stored ``doc_content_hash``
    differs is treated as a miss (the document changed since the answer was cached), so stale
    answers are never served. The stale entry is deleted so it repopulates on the cold path.
    """
    distance_expr = SemanticCacheEntry.embedding.cosine_distance(query_embedding).label("distance")
    stmt = select(SemanticCacheEntry, distance_expr).order_by(distance_expr).limit(1)
    if doc_id is None:
        stmt = stmt.where(SemanticCacheEntry.document_id.is_(None))
    else:
        stmt = stmt.where(SemanticCacheEntry.document_id == doc_id)
    start = time.perf_counter()
    try:
        row = db.execute(stmt).first()
    finally:
        councilai_pgvector_lookup_seconds.observe(time.perf_counter() - start)
    if row is None:
        councilai_cache_operations_total.labels(result="miss", level="l1").inc()
        return None, None
    _entry, distance = row
    similarity = 1.0 - float(distance)
    if similarity < settings.semantic_threshold:
        councilai_cache_operations_total.labels(result="miss", level="l1").inc()
        return None, similarity
    if doc_content_hash is not None and _entry.doc_content_hash != doc_content_hash:
        # Vector-similar but the underlying document changed -> stale, do not serve.
        councilai_semantic_cache_stale_total.labels(event="lookup_skip").inc()
        councilai_cache_operations_total.labels(result="miss", level="l1").inc()
        db.delete(_entry)
        db.commit()
        return None, similarity
    councilai_cache_operations_total.labels(result="hit", level="l1").inc()
    return _entry.response_json, similarity


def store_semantic(
    db: Session,
    doc_id: str | None,
    normalized_query: str,
    query_embedding: list[float],
    response_json: dict,
    doc_content_hash: str | None = None,
) -> None:
    db.add(
        SemanticCacheEntry(
            document_id=doc_id,
            normalized_query=normalized_query,
            response_json=response_json,
            embedding=query_embedding,
            doc_content_hash=doc_content_hash,
        )
    )
    db.commit()


def invalidate_semantic_cache(db: Session, doc_id: str) -> int:
    """Delete all semantic-cache entries for a document. Called when a document is
    re-ingested with changed content so stale answers cannot be served."""
    deleted = (
        db.query(SemanticCacheEntry)
        .filter(SemanticCacheEntry.document_id == doc_id)
        .delete()
    )
    db.commit()
    count = int(deleted or 0)
    if count:
        councilai_semantic_cache_stale_total.labels(event="invalidate").inc(count)
    return count


def clear_semantic_cache(db: Session) -> int:
    deleted = db.query(SemanticCacheEntry).delete()
    db.commit()
    return int(deleted or 0)
