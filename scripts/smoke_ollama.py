"""Ollama chat-completions smoke test.

Sends one OpenAI-compatible chat completion request to Ollama and prints
status plus response text.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _fallback_urls(url: str) -> list[str]:
    urls = [url]
    if "host.docker.internal" in url:
        urls.append(url.replace("host.docker.internal", "localhost"))
    return urls


def main() -> int:
    env_values = _read_env_file(Path(__file__).resolve().parents[1] / ".env")
    base_url = os.getenv("OLLAMA_BASE_URL") or env_values.get(
        "OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1/chat/completions"
    )
    model = os.getenv("OLLAMA_MODEL") or env_values.get("OLLAMA_MODEL", "qwen2.5:3b")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with only: ok"}],
        "max_tokens": 32,
    }
    headers = {"Content-Type": "application/json"}

    print(f"[smoke-ollama] model={model}")
    for url in _fallback_urls(base_url):
        print(f"[smoke-ollama] url={url}")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
        except requests.RequestException as exc:
            print(f"[smoke-ollama] request_error={type(exc).__name__}: {exc}")
            continue

        print(f"[smoke-ollama] status={response.status_code}")
        body = response.text
        print(f"[smoke-ollama] body={body[:1200]}")
        if response.status_code != 200:
            return 1
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            print(f"[smoke-ollama] parse_error={type(exc).__name__}: {exc}")
            return 1
        print(f"[smoke-ollama] response={content!r}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
