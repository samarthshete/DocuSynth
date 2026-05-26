"""Per-request LLM call accounting and timing helpers."""

from contextlib import contextmanager
from contextvars import ContextVar

from app.metrics.prometheus import (
    councilai_llm_call_latency_seconds,
    councilai_llm_calls_total,
)

_llm_stats: ContextVar[dict | None] = ContextVar("_llm_stats", default=None)


@contextmanager
def track_llm_calls():
    state = {"count": 0, "total_seconds": 0.0, "by_stage": {}}
    token = _llm_stats.set(state)
    try:
        yield state
    finally:
        _llm_stats.reset(token)


def record_llm_call(stage: str, seconds: float) -> None:
    state = _llm_stats.get()
    if state is not None:
        state["count"] += 1
        state["total_seconds"] += seconds
        bucket = state["by_stage"].setdefault(stage, {"count": 0, "total_seconds": 0.0})
        bucket["count"] += 1
        bucket["total_seconds"] += seconds
    councilai_llm_calls_total.labels(stage=stage).inc()
    councilai_llm_call_latency_seconds.labels(stage=stage).observe(seconds)
