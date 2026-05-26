"""Retrieve-All Router — returns all stored chunks for a document."""

import logging
from fastapi import APIRouter, HTTPException

from app.models import RetrieveAllRequest, RetrieveAllResponse
from app.retrieval.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/retrieve-all", response_model=RetrieveAllResponse)
async def retrieve_all_chunks(request: RetrieveAllRequest):
    """Retrieve all chunks for a document, ordered by page and chunk index."""
    try:
        store = PgVectorStore()
        chunks = store.retrieve_all(request.doc_id)
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Document {request.doc_id} not found or has no content",
            )

        logger.info(f"Retrieved all {len(chunks)} chunks for doc_id={request.doc_id}")

        return RetrieveAllResponse(
            chunks=chunks,
            doc_id=request.doc_id,
            total_chunks=len(chunks),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Retrieve-all failed for doc_id={request.doc_id}")
        raise HTTPException(status_code=500, detail=f"Retrieve-all failed: {str(e)}")
