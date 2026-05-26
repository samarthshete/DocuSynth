def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics_returns_prometheus_text(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    assert "docusynth_request_count_total" in text
    for metric in (
        "docusynth_query_total",
        "docusynth_query_latency_seconds",
        "docusynth_redis_lookup_seconds",
        "docusynth_embedding_latency_seconds",
        "docusynth_pgvector_lookup_seconds",
        "docusynth_retrieval_latency_seconds",
        "docusynth_llm_calls_total",
        "docusynth_llm_call_latency_seconds",
        "docusynth_llm_calls_per_query",
        "docusynth_query_errors_total",
    ):
        assert metric in text, f"missing metric {metric}"

