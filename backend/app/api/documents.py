import hashlib
import time

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.audit.logger import log_tagged
from app.auth.jwt import get_current_user
from app.cache.redis_cache import rate_limit_allow
from app.config import get_settings
from app.db.models import Document, User
from app.db.session import get_db
from app.metrics.prometheus import councilai_document_ingestion_seconds

settings = get_settings()
router = APIRouter(prefix="/api/v1")


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    doc_id: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    if not rate_limit_allow(user.username):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limit exceeded")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="file is required")
    if not doc_id:
        digest = hashlib.md5(content[:4096]).hexdigest()[:12]
        doc_id = f"{file.filename}_{digest}"

    files = {"file": (file.filename, content, file.content_type or "application/pdf")}
    data = {"doc_id": doc_id}
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(f"{settings.rag_service_url}/ingest", files=files, data=data)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RAG service unavailable: {exc}") from exc

    metadata = payload.get("metadata", {})
    existing = db.query(Document).filter(Document.id == doc_id).first()
    if existing is None:
        db.add(
            Document(
                id=doc_id,
                filename=file.filename or "uploaded.pdf",
                owner_id=user.username,
                metadata_json=metadata,
            )
        )
        db.commit()

    councilai_document_ingestion_seconds.observe(time.perf_counter() - start)
    log_tagged("[Audit]", {"action": "ingest", "user_id": user.username, "doc_id": doc_id, "status": "success"}, db=db)
    return payload

