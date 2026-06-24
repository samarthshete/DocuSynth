import hashlib
import json
import logging
import re
import time
from typing import Any

import redis
from app.config import get_settings
from app.metrics.prometheus import (
    councilai_cache_operations_total,
    councilai_redis_lookup_seconds,
)
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
settings = get_settings()
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


def cache_key(doc_id: str | None, question: str) -> str:
    normalized = normalize_query(question)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"query:{doc_id or 'global'}:{digest}"


def get_json(key: str) -> dict[str, Any] | None:
    start = time.perf_counter()
    try:
        raw = redis_client.get(key)
    except RedisError as exc:
        logger.warning("[Cache] redis get failed: %s", exc)
        councilai_cache_operations_total.labels(result="error", level="l2").inc()
        return None
    finally:
        councilai_redis_lookup_seconds.observe(time.perf_counter() - start)
    if raw is None:
        councilai_cache_operations_total.labels(result="miss", level="l2").inc()
        return None
    councilai_cache_operations_total.labels(result="hit", level="l2").inc()
    return json.loads(raw)


def set_json(key: str, value: dict[str, Any]) -> None:
    try:
        redis_client.setex(key, settings.redis_cache_ttl_seconds, json.dumps(value))
    except RedisError as exc:
        logger.warning("[Cache] redis setex failed: %s", exc)


def rate_limit_allow(user_id: str) -> bool:
    key = f"ratelimit:{user_id}"
    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, settings.rate_limit_window_seconds)
    except RedisError as exc:
        logger.warning("[Cache] rate-limit fail-open due to redis error: %s", exc)
        return True
    return count <= settings.rate_limit_rps * settings.rate_limit_window_seconds


def flush_all() -> None:
    try:
        redis_client.flushdb()
    except RedisError as exc:
        logger.warning("[Cache] redis flushdb failed: %s", exc)
