import app.api.query as query_api


async def _fake_retrieve_chunks(*_args, **_kwargs):
    return [{"content": "retrieved chunk", "page_number": 3, "chunk_index": 0, "score": 0.91}]


async def _fake_embed_query(*_args, **_kwargs):
    return [0.1] * 384


async def _fake_run_council(*_args, **_kwargs):
    return {
        "final_answer": "final answer",
        "confidence": 0.9,
        "source": "chairman:mock",
        "reasoning": "reasoning",
        "candidate_answers": [{"answer": "a", "model": "m1"}],
        "peer_reviews": [{"reviewer": "m1", "review": "ok"}],
    }


def test_query_returns_structured_answer(client, monkeypatch):
    monkeypatch.setattr(query_api, "retrieve_chunks", _fake_retrieve_chunks)
    monkeypatch.setattr(query_api, "embed_query", _fake_embed_query)
    monkeypatch.setattr(query_api, "run_council", _fake_run_council)
    monkeypatch.setattr(query_api, "lookup_semantic", lambda *_args, **_kwargs: (None, None))
    monkeypatch.setattr(query_api, "store_semantic", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(query_api, "get_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(query_api, "set_json", lambda *_args, **_kwargs: None)

    response = client.post("/api/v1/query", json={"question": "What is this?", "doc_id": "doc-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "final answer"
    assert "confidence" in payload
    assert "cache_hit" in payload
    assert payload["cache_result"] == "miss"
    assert payload["llm_call_count"] == 0  # mock run_council didn't increment counters
    assert "timings" in payload
    expected_timing_keys = {
        "redis_lookup_ms", "embedding_ms", "pgvector_lookup_ms",
        "retrieval_ms", "llm_ms", "total_ms",
    }
    assert expected_timing_keys <= set(payload["timings"].keys())
    # W3 — citations / source provenance
    assert "citations" in payload
    assert payload["citations"][0]["page_number"] == 3
    assert payload["citations"][0]["score"] == 0.91
    assert payload["citations"][0]["snippet"] == "retrieved chunk"


def test_protected_endpoint_rejects_missing_jwt(client):
    client.app.dependency_overrides.clear()
    response = client.post("/api/v1/query", json={"question": "x", "doc_id": "doc-1"})
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_jwt(client):
    client.app.dependency_overrides.clear()
    response = client.post(
        "/api/v1/query",
        json={"question": "x", "doc_id": "doc-1"},
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401

