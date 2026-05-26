import json
import time

from app.config import get_settings
from app.council.instrumentation import record_llm_call
from app.council.llm_client import chat_completion, resolve_model

settings = get_settings()

def _extract_json(candidate: str) -> dict:
    raw = candidate.strip()
    if raw.startswith("```json"):
        raw = raw.removeprefix("```json").removesuffix("```").strip()
    elif raw.startswith("```"):
        raw = raw.removeprefix("```").removesuffix("```").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)

async def synthesize(question: str, chunks: list[str], candidates: list[dict], reviews: list[dict]) -> dict:
    start = time.perf_counter()
    try:
        if settings.mock_llm:
            best = max(candidates, key=lambda c: len(c.get("answer", "")))
            return {
                "answer": best["answer"],
                "reasoning": "mock-chairman synthesis",
                "source": "chairman:mock",
                "confidence": 0.99,
            }

        responses_block = "\n\n".join(
            [f"=== Response {chr(65+i)} ===\n{c['answer']}" for i, c in enumerate(candidates)]
        )
        reviews_block = "\n\n".join(
            [f"--- Reviewer {i+1} ---\n{r['review']}" for i, r in enumerate(reviews) if not r.get("error")]
        )
        context_text = "\n\n---\n\n".join(chunks)
        prompt = f"""You are the Chairman of an AI council. Multiple AI models have answered and reviewed each other.
Question: {question}
Document Excerpts:
{context_text}

Individual Responses:
{responses_block}

Peer Reviews:
{reviews_block or 'No peer reviews available'}

Respond ONLY valid JSON:
{{
  "answer":"...",
  "reasoning":"...",
  "source":"chairman-synthesis",
  "confidence":0.85
}}
"""
        text = await chat_completion(
            stage="synthesize",
            requested_model=settings.chairman_model,
            prompt=prompt,
            timeout_seconds=settings.stage_timeout,
            max_tokens=1024,
        )

        try:
            parsed = _extract_json(text)
        except Exception:
            parsed = {
                "answer": text,
                "reasoning": "chairman response not valid json",
                "source": f"chairman:{resolve_model(settings.chairman_model)}",
                "confidence": 0.7,
            }
        if not parsed.get("source"):
            parsed["source"] = f"chairman:{resolve_model(settings.chairman_model)}"
        return parsed
    finally:
        record_llm_call("synthesize", time.perf_counter() - start)
