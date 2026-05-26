import logging
import time

from app.config import get_settings
from app.council.generator import _openrouter_generate, collect_candidates
from app.council.instrumentation import track_llm_calls
from app.council.reviewer import review_candidates
from app.council.synthesizer import synthesize
from app.metrics.prometheus import councilai_council_response_seconds

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_council(
    question: str,
    chunks: list[str],
    custom_prompt: str = "",
    skip_chairman: bool = False,
) -> dict:
    start = time.perf_counter()
    context_text = "\n\n---\n\n".join(chunks)
    prompt = custom_prompt or (
        "Based on the following document excerpts, answer the question.\n\n"
        f"Document Excerpts:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Instructions:\n"
        "- Answer based ONLY on the provided excerpts\n"
        "- If the answer is not in the excerpts, say so clearly\n"
        "- Be concise but thorough"
    )

    with track_llm_calls() as stats:
        if settings.llm_provider == "ollama" and settings.local_llm_fast_mode:
            single = await _openrouter_generate(
                settings.ollama_model,
                prompt,
                stage="generate",
                max_tokens=128,
                temperature=0.0,
            )
            if single.error:
                raise RuntimeError(single.error)
            elapsed = time.perf_counter() - start
            councilai_council_response_seconds.observe(elapsed)
            return {
                "final_answer": single.answer,
                "reasoning": "",
                "confidence": 0.6,
                "source": f"{single.model} (single-local-fast)",
                "candidate_answers": [single.__dict__],
                "peer_reviews": [],
                "latency": elapsed,
                "llm_call_count": 1,
                "llm_total_seconds": stats["total_seconds"],
                "llm_by_stage": dict(stats["by_stage"]),
                "council_mode": "single_local_fast",
            }

        candidates = [candidate.__dict__ for candidate in await collect_candidates(prompt)]
        valid_candidates = [candidate for candidate in candidates if not candidate.get("error")]
        if not valid_candidates:
            raise RuntimeError("all council members failed to respond")
        if len(valid_candidates) == 1:
            elapsed = time.perf_counter() - start
            councilai_council_response_seconds.observe(elapsed)
            return {
                "final_answer": valid_candidates[0]["answer"],
                "reasoning": "",
                "confidence": 0.5,
                "source": f"{valid_candidates[0]['model']} (single-response)",
                "candidate_answers": candidates,
                "peer_reviews": [],
                "latency": elapsed,
                "llm_call_count": stats["count"],
                "llm_total_seconds": stats["total_seconds"],
                "llm_by_stage": dict(stats["by_stage"]),
                "council_mode": "single_response",
            }

        reviews = [review.__dict__ for review in await review_candidates(question, valid_candidates)]
        if skip_chairman:
            best = max(valid_candidates, key=lambda c: len(c["answer"]))
            elapsed = time.perf_counter() - start
            councilai_council_response_seconds.observe(elapsed)
            return {
                "final_answer": best["answer"],
                "reasoning": "",
                "confidence": 0.75,
                "source": f"{best['model']} (peer-reviewed, no chairman)",
                "candidate_answers": candidates,
                "peer_reviews": reviews,
                "latency": elapsed,
                "llm_call_count": stats["count"],
                "llm_total_seconds": stats["total_seconds"],
                "llm_by_stage": dict(stats["by_stage"]),
                "council_mode": "peer_review_no_chairman",
            }

        try:
            chairman = await synthesize(question, chunks, valid_candidates, reviews)
            chairman_error: str | None = None
        except Exception as exc:
            logger.warning(
                "[Council] chairman synthesis failed exc_type=%s exc=%s; "
                "falling back to best valid candidate",
                type(exc).__name__,
                exc,
            )
            best = max(valid_candidates, key=lambda c: len(c["answer"]))
            chairman = {
                "answer": best["answer"],
                "reasoning": "",
                "confidence": 0.65,
                "source": f"{best['model']} (chairman-fallback)",
            }
            chairman_error = f"{type(exc).__name__}: {exc}"

        elapsed = time.perf_counter() - start
        councilai_council_response_seconds.observe(elapsed)
        result = {
            "final_answer": chairman["answer"],
            "reasoning": chairman.get("reasoning", ""),
            "confidence": chairman.get("confidence", 0.7),
            "source": chairman.get("source", "chairman-synthesis"),
            "candidate_answers": candidates,
            "peer_reviews": reviews,
            "latency": elapsed,
            "llm_call_count": stats["count"],
            "llm_total_seconds": stats["total_seconds"],
            "llm_by_stage": dict(stats["by_stage"]),
            "council_mode": "full_council",
        }
        if chairman_error is not None:
            result["chairman_error"] = chairman_error
        return result
