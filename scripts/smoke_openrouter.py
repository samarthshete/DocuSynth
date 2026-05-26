"""Direct OpenRouter chat-completions smoke test.

Sends a single request to OpenRouter using the same credentials and headers
DocuSynth uses in production. Logs model, URL, HTTP status, truncated body, and
exception type so we can confirm provider connectivity in isolation from the
council orchestration code.

Usage:
    python3 scripts/smoke_openrouter.py
    python3 scripts/smoke_openrouter.py --model google/gemini-2.5-flash
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import httpx


DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"
DEFAULT_PROMPT = "Reply with only: ok"
TRUNCATE = 1200


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


def _truncate(text: str, limit: int = TRUNCATE) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... <truncated {len(text) - limit} chars>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenRouter chat-completions smoke test")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    env_values = _read_env_file(Path(__file__).resolve().parents[1] / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY") or env_values.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set in environment or .env")
        return 2

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/regular-life/DocuSynth",
        "X-Title": "DocuSynth",
    }

    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "<short>"
    print(f"[smoke] model       = {args.model}")
    print(f"[smoke] provider    = {args.url}")
    print(f"[smoke] api_key     = {masked}")
    print(f"[smoke] prompt      = {args.prompt!r}")
    print(f"[smoke] max_tokens  = {args.max_tokens}")
    print(f"[smoke] timeout_sec = {args.timeout}")

    try:
        with httpx.Client(timeout=args.timeout) as client:
            response = client.post(args.url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        print(f"[smoke] exception_type = {type(exc).__name__}")
        print(f"[smoke] exception_msg  = {exc}")
        traceback.print_exc()
        return 1

    body_text = response.text or ""
    print(f"[smoke] http_status = {response.status_code}")
    print(f"[smoke] body_len    = {len(body_text)}")
    print("[smoke] body_preview ↓")
    print(_truncate(body_text))

    if response.status_code != 200:
        return 1

    try:
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        print(f"[smoke] message_content = {message!r}")
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"[smoke] parse_exception = {type(exc).__name__}: {exc}")
        return 1

    print("[smoke] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
