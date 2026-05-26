import asyncio
import logging
import time
from dataclasses import dataclass

from app.config import get_settings
from app.council.instrumentation import record_llm_call
from app.council.llm_client import chat_completion, resolve_model, truncate
from app.metrics.prometheus import councilai_llm_failure_count_total

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CandidateAnswer:
    answer: str
    model: str
    error: str = ""

async def _openrouter_generate(
    model: str,
    prompt: str,
    stage: str = "generate",
    max_tokens: int = 1024,
    temperature: float | None = None,
) -> CandidateAnswer:
    start = time.perf_counter()
    try:
        if settings.mock_llm:
            effective_model = resolve_model(model)
            return CandidateAnswer(
                answer=f"MOCK RESPONSE ({effective_model}): {prompt[:140]}",
                model=effective_model,
            )
        content = await chat_completion(
            stage=stage,
            requested_model=model,
            prompt=prompt,
            timeout_seconds=settings.llm_timeout,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return CandidateAnswer(answer=content, model=resolve_model(model))
    finally:
        record_llm_call(stage, time.perf_counter() - start)


async def collect_candidates(prompt: str) -> list[CandidateAnswer]:
    tasks = [_openrouter_generate(model, prompt, stage="generate") for model in settings.council_models]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    candidates: list[CandidateAnswer] = []
    for i, result in enumerate(results):
        model = settings.council_models[i]
        if isinstance(result, Exception):
            councilai_llm_failure_count_total.inc()
            logger.warning(
                "[Council] generate failed model=%s exc_type=%s exc=%s",
                model,
                type(result).__name__,
                truncate(str(result)),
            )
            candidates.append(CandidateAnswer(answer="", model=model, error=str(result)))
        else:
            candidates.append(result)
    return candidates
