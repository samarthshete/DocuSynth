import httpx
import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine

settings = get_settings()
router = APIRouter()


@router.get("/health")
async def health() -> dict:
    payload = {"status": "healthy", "service": "python-backend", "version": "1.0.0"}
    try:
        redis.Redis.from_url(settings.redis_url).ping()
        payload["redis"] = "healthy"
    except Exception:
        payload["redis"] = "unhealthy"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        payload["postgres"] = "healthy"
    except Exception:
        payload["postgres"] = "unhealthy"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.rag_service_url}/health")
            payload["rag_service"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        payload["rag_service"] = "unhealthy"
    return payload

