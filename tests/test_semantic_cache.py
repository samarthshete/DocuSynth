import app.api.query as query_api


async def _fake_embed_query(*_args, **_kwargs):
    return [0.1] * 384


def test_semantic_cache_lookup_hit(client, monkeypatch):
    monkeypatch.setattr(query_api, "get_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(query_api, "embed_query", _fake_embed_query)
    monkeypatch.setattr(
        query_api,
        "lookup_semantic",
        lambda *_args, **_kwargs: ({"answer": "semantic", "cache_hit": False}, 0.92),
    )
    response = client.post("/api/v1/query", json={"question": "meaning", "doc_id": "doc-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "semantic"
    assert body["cache_hit"] is True
    assert body["cache_result"] == "semantic_hit"
    assert body["similarity_score"] == 0.92
    assert body["timings"]["embedding_ms"] >= 0
    assert body["timings"]["pgvector_lookup_ms"] >= 0

