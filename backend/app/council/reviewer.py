import asyncio
from dataclasses import dataclass

from app.council.generator import _openrouter_generate


@dataclass
class PeerReview:
    reviewer: str
    review: str
    error: str = ""


async def review_candidates(question: str, candidates: list[dict]) -> list[PeerReview]:
    answers_block = "\n\n".join(
        [f"=== Response {chr(65+i)} ===\n{candidate['answer']}" for i, candidate in enumerate(candidates)]
    )
    prompt = f"""You are reviewing multiple AI-generated answers to this question:

Question: {question}

Here are the anonymized responses:
{answers_block}

1. Evaluate each response for accuracy, completeness, and clarity
2. Rank them from best to worst
3. Explain briefly why you ranked them that way
"""
    tasks = [
        _openrouter_generate(candidate["model"], prompt, stage="review") for candidate in candidates
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    reviews: list[PeerReview] = []
    for i, result in enumerate(results):
        model = candidates[i]["model"]
        if isinstance(result, Exception):
            reviews.append(PeerReview(reviewer=model, review="", error=str(result)))
        else:
            reviews.append(PeerReview(reviewer=model, review=result.answer))
    return reviews
