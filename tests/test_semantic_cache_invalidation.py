"""W2 — semantic cache invalidation / content-hash gating.

Proves that a vector-similar cache entry is NOT served once the underlying document
content changes (different ``doc_content_hash``), and that re-ingest invalidation works.
These are unit tests over ``app.cache.semantic_cache`` with lightweight fakes — no DB needed.
"""

import pytest
from app.cache.semantic_cache import (
    invalidate_semantic_cache,
    lookup_semantic,
    store_semantic,
)
from app.db.models import SemanticCacheEntry


class _ExecResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _LookupDB:
    """Fake Session whose vector query returns a fixed (entry, distance) row."""

    def __init__(self, row):
        self._row = row
        self.deleted = []
        self.committed = False

    def execute(self, *_args, **_kwargs):
        return _ExecResult(self._row)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed = True


def _entry(doc_hash):
    return SemanticCacheEntry(
        document_id="doc-1",
        normalized_query="what is this",
        response_json={"answer": "cached"},
        embedding=[0.1] * 384,
        doc_content_hash=doc_hash,
    )


def test_matching_hash_is_served():
    db = _LookupDB((_entry("hashA"), 0.05))  # similarity 0.95 >= 0.85
    response, similarity = lookup_semantic(db, "doc-1", "what is this", [0.1] * 384, "hashA")
    assert response == {"answer": "cached"}
    assert similarity == pytest.approx(0.95)
    assert db.deleted == []


def test_stale_hash_is_not_served_and_is_deleted():
    entry = _entry("hashA")
    db = _LookupDB((entry, 0.05))  # vector-similar but document changed -> hashB
    response, similarity = lookup_semantic(db, "doc-1", "what is this", [0.1] * 384, "hashB")
    assert response is None  # stale answer must NOT be served
    assert similarity == pytest.approx(0.95)
    assert db.deleted == [entry]  # stale entry evicted so it repopulates cold
    assert db.committed is True


def test_no_hash_provided_preserves_legacy_behavior():
    db = _LookupDB((_entry("hashA"), 0.05))
    response, _ = lookup_semantic(db, "doc-1", "what is this", [0.1] * 384)  # no hash gate
    assert response == {"answer": "cached"}


class _CaptureDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def test_store_semantic_persists_content_hash():
    db = _CaptureDB()
    store_semantic(db, "doc-1", "q", [0.1] * 384, {"answer": "x"}, doc_content_hash="hashA")
    assert db.added and db.added[0].doc_content_hash == "hashA"


class _DeleteQuery:
    def __init__(self, count):
        self._count = count

    def filter(self, *_args, **_kwargs):
        return self

    def delete(self):
        return self._count


class _InvalidateDB:
    def __init__(self, count):
        self._count = count
        self.committed = False

    def query(self, _model):
        return _DeleteQuery(self._count)

    def commit(self):
        self.committed = True


def test_invalidate_semantic_cache_deletes_by_doc_id():
    db = _InvalidateDB(3)
    assert invalidate_semantic_cache(db, "doc-1") == 3
    assert db.committed is True
