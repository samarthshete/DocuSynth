import time

import httpx

from app.config import get_settings
from app.metrics.prometheus import councilai_embedding_latency_seconds

settings = get_settings()


async def embed_query(text: str) -> list[float]:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(f"{settings.rag_service_url}/embed", json={"text": text})
            response.raise_for_status()
            return response.json()["embedding"]
    finally:
        councilai_embedding_latency_seconds.observe(time.perf_counter() - start)
