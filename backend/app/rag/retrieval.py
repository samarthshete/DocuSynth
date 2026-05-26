import httpx

from app.config import get_settings

settings = get_settings()


async def retrieve_chunks(question: str, doc_id: str | None, top_k: int) -> list[dict]:
    payload = {"question": question, "doc_id": doc_id, "top_k": top_k}
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(f"{settings.rag_service_url}/retrieve", json=payload)
        response.raise_for_status()
        return response.json().get("chunks", [])


async def retrieve_all_chunks(doc_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(f"{settings.rag_service_url}/retrieve-all", json={"doc_id": doc_id})
        response.raise_for_status()
        return response.json().get("chunks", [])

