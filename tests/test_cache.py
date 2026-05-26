import app.api.query as query_api


async def _fake_embed_query(*_args, **_kwargs):
    raise AssertionError("embed_query should not run on exact cache hit")


def test_redis_exact_cache_checked_before_llm(client, monkeypatch):
    monkeypatch.setattr(query_api, "get_json", lambda *_args, **_kwargs: {"answer": "cached", "cache_hit": False})
    monkeypatch.setattr(query_api, "embed_query", _fake_embed_query)
    response = client.post("/api/v1/query", json={"question": "cached?", "doc_id": "doc-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "cached"
    assert body["cache_hit"] is True
    assert body["cache_result"] == "exact_hit"
    assert body["llm_call_count"] == 0
    assert body["timings"]["total_ms"] >= 0

