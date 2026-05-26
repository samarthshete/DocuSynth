import hashlib
import logging
from typing import Optional

from sqlalchemy import select

from app.db import ChunkRecord, SessionLocal
from app.embedding.transformer import TransformerEmbeddings
from app.models import Chunk, ChunkType
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PgVectorStore:
    def __init__(self):
        self.embeddings = TransformerEmbeddings(settings.embedding_model)

    def ingest(self, chunks: list[Chunk], doc_id: str) -> int:
        if not chunks:
            return 0
        vectors = self.embeddings.embed_documents([chunk.content for chunk in chunks])
        with SessionLocal() as session:
            for chunk, vector in zip(chunks, vectors):
                session.add(
                    ChunkRecord(
                        document_id=doc_id,
                        chunk_text=chunk.content,
                        page_number=chunk.page_number or None,
                        metadata_json={
                            "chunk_type": chunk.chunk_type.value,
                            "chunk_index": chunk.chunk_index,
                            **chunk.metadata,
                            "chunk_hash": hashlib.md5(chunk.content[:100].encode("utf-8")).hexdigest()[:8],
                        },
                        embedding=vector,
                    )
                )
            session.commit()
        logger.info("Ingested %s chunks for doc_id=%s", len(chunks), doc_id)
        return len(chunks)

    def retrieve(self, query: str, doc_id: Optional[str], top_k: int = 5) -> list[Chunk]:
        query_vector = self.embeddings.embed_query(query)
        with SessionLocal() as session:
            stmt = select(ChunkRecord)
            if doc_id:
                stmt = stmt.where(ChunkRecord.document_id == doc_id)
            stmt = stmt.order_by(ChunkRecord.embedding.cosine_distance(query_vector)).limit(top_k)
            records = session.execute(stmt).scalars().all()
        result: list[Chunk] = []
        for idx, record in enumerate(records):
            metadata = record.metadata_json or {}
            result.append(
                Chunk(
                    content=record.chunk_text,
                    chunk_type=ChunkType(metadata.get("chunk_type", "paragraph")),
                    page_number=record.page_number or 0,
                    chunk_index=int(metadata.get("chunk_index", idx)),
                    metadata=metadata,
                )
            )
        return result

    def retrieve_all(self, doc_id: str) -> list[Chunk]:
        with SessionLocal() as session:
            stmt = (
                select(ChunkRecord)
                .where(ChunkRecord.document_id == doc_id)
                .order_by(ChunkRecord.page_number.asc(), ChunkRecord.id.asc())
            )
            records = session.execute(stmt).scalars().all()
        result: list[Chunk] = []
        for idx, record in enumerate(records):
            metadata = record.metadata_json or {}
            result.append(
                Chunk(
                    content=record.chunk_text,
                    chunk_type=ChunkType(metadata.get("chunk_type", "paragraph")),
                    page_number=record.page_number or 0,
                    chunk_index=int(metadata.get("chunk_index", idx)),
                    metadata=metadata,
                )
            )
        return result

