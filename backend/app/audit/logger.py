import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


def log_tagged(tag: str, payload: dict, db: Session | None = None) -> None:
    enriched = {"timestamp": datetime.utcnow().isoformat(), **payload}
    logger.info("%s %s", tag, json.dumps(enriched, default=str))
    if db is None:
        return
    try:
        db.add(AuditLog(tag=tag.strip("[]"), payload=enriched))
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        logger.error("[Error] failed audit write: %s", exc)

