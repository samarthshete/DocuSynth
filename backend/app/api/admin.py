"""Admin endpoints used by benchmarks/operations.

Authenticated by JWT. Designed for local benchmarking and integration runs;
restrict via network policy in production deployments.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.audit.logger import log_tagged
from app.auth.jwt import get_current_user
from app.cache.redis_cache import flush_all
from app.cache.semantic_cache import clear_semantic_cache
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/admin")


@router.post("/clear-cache")
def clear_cache(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    flush_all()
    deleted = clear_semantic_cache(db)
    log_tagged(
        "[Audit]",
        {"action": "clear_cache", "user_id": user.username, "semantic_deleted": deleted},
    )
    return {"status": "ok", "redis": "flushed", "semantic_cache_deleted": deleted}
