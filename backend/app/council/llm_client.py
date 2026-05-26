import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def truncate(text: str, limit: int = 500) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"... <truncated {len(text) - limit} chars>"


def provider_name() -> str:
    return (settings.llm_provider or "openrouter").strip().lower()


def resolve_model(requested_model: str) -> str:
    if provider_name() == "ollama":
        return settings.ollama_model
    return requested_model


async def chat_completion(
    *,
    stage: str,
    requested_model: str,
    prompt: str,
    timeout_seconds: float,
    max_tokens: int = 1024,
    temperature: float | None = None,
) -> str:
    provider = provider_name()
    model = resolve_model(requested_model)
    if provider == "ollama":
        url = settings.ollama_base_url
        headers = {"Content-Type": "application/json"}
    elif provider == "openrouter":
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        url = settings.openrouter_url
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/regular-life/DocuSynth",
            "X-Title": "DocuSynth",
        }
    else:
        raise RuntimeError(f"unsupported LLM_PROVIDER={settings.llm_provider!r}")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.warning(
            "[LLM] provider=%s stage=%s model=%s exception_type=%s latency=%.3fs message=%s",
            provider,
            stage,
            model,
            type(exc).__name__,
            elapsed,
            truncate(str(exc)),
        )
        raise

    elapsed = time.perf_counter() - start
    if response.status_code != 200:
        body = truncate(response.text or "")
        logger.warning(
            "[LLM] provider=%s stage=%s model=%s status_code=%s latency=%.3fs body=%s",
            provider,
            stage,
            model,
            response.status_code,
            elapsed,
            body,
        )
        raise RuntimeError(
            f"{provider} status {response.status_code} for {model}: {body}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        body = truncate(response.text or "")
        logger.warning(
            "[LLM] provider=%s stage=%s model=%s status_code=%s latency=%.3fs parse_error=%s body=%s",
            provider,
            stage,
            model,
            response.status_code,
            elapsed,
            type(exc).__name__,
            body,
        )
        raise RuntimeError(f"{provider} response parse failed for {model}: {exc}") from exc
