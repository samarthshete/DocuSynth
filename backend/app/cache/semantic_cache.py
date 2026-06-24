import time
from typing import Optional

from app.config import get_settings
from app.db.models import SemanticCacheEntry
from app.metrics.prometheus import (
    councilai_cache_operations_total,
    councilai_pgvector_lookup_seconds,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

settings = get_settings()


def lookup_semantic(
    db: Session,
    doc_id: str | None,
    normalized_query: str,
    query_embedding: list[float],
) -> tuple[Optional[dict], Optional[float]]:
    """Return (response_json, similarity) if a match passes the threshold, else (None, similarity_or_None)."""
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
    councilai_cache_operations_total.labels(result="hit", level="l1").inc()
    return _entry.response_json, similarity


def store_semantic(
    db: Session,
    doc_id: str | None,
    normalized_query: str,
    query_embedding: list[float],
    response_json: dict,
) -> None:
    db.add(
        SemanticCacheEntry(
            document_id=doc_id,
            normalized_query=normalized_query,
            response_json=response_json,
            embedding=query_embedding,
        )
    )
    db.commit()


def clear_semantic_cache(db: Session) -> int:
    deleted = db.query(SemanticCacheEntry).delete()
    db.commit()
    return int(deleted or 0)
