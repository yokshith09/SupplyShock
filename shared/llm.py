"""Async ASI1 client (OpenAI-compatible chat completions). Owner: D2.

Env:
    ASI1_API_KEY   required for real calls
    ASI1_MODEL     default "asi1-mini"
    ASI1_BASE_URL  default "https://api.asi1.ai/v1"

Usage:
    from shared.llm import complete, complete_json, LLMError
    text = await complete([{"role": "user", "content": "hi"}])
    data = await complete_json(messages, schema_hint='{"intent": "SCAN|EVENT_IMPACT|..."}')
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("supplyshock.llm")

DEFAULT_BASE_URL = "https://api.asi1.ai/v1"
DEFAULT_MODEL = "asi1-mini"
MAX_ATTEMPTS = 3  # first try + 2 retries


class LLMError(Exception):
    """The LLM call failed after retries, or returned unusable output."""


class _RetryableHTTPError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"ASI1 returned HTTP {status_code}")
        self.status_code = status_code


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TransportError, _RetryableHTTPError))


def _settings() -> tuple[str, str, str]:
    api_key = os.getenv("ASI1_API_KEY", "")
    if not api_key:
        raise LLMError("ASI1_API_KEY is not set")
    model = os.getenv("ASI1_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("ASI1_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return api_key, model, base_url


async def _post_chat(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    api_key, model, base_url = _settings()
    payload = {"model": model, **payload}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=1, min=1, max=3),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        ):
            with attempt:
                resp = await client.post(
                    f"{base_url}/chat/completions", json=payload, headers=headers
                )
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise _RetryableHTTPError(resp.status_code)
                if resp.status_code >= 400:
                    raise LLMError(f"ASI1 returned HTTP {resp.status_code}: {resp.text[:200]}")
                return resp.json()
    raise LLMError("unreachable")  # pragma: no cover


async def complete(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    timeout_s: float = 15,
) -> str:
    """Return the assistant's text reply. Raises LLMError on failure."""
    try:
        data = await _post_chat({"messages": messages, "temperature": temperature}, timeout_s)
    except LLMError:
        raise
    except (httpx.HTTPError, _RetryableHTTPError) as exc:
        logger.warning("asi1 call failed: %s", exc)
        raise LLMError(f"ASI1 call failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("ASI1 response had no message content") from exc


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _parse_json(text: str) -> Any:
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first {...} or [...] block in the text.
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        if start == -1:
            raise
        end = max(text.rfind("}"), text.rfind("]"))
        return json.loads(text[start : end + 1])


async def complete_json(
    messages: list[dict[str, str]],
    schema_hint: str,
    timeout_s: float = 15,
) -> Any:
    """Ask for JSON only and return it parsed. Retries once on invalid JSON."""
    instruction = f"Reply with valid JSON only, no prose and no code fences. Shape: {schema_hint}"
    # Some providers reject more than one system message, so merge into the caller's one.
    if messages and messages[0].get("role") == "system":
        convo = [
            {"role": "system", "content": f"{messages[0]['content']}\n\n{instruction}"},
            *messages[1:],
        ]
    else:
        convo = [{"role": "system", "content": instruction}, *messages]
    text = await complete(convo, temperature=0, timeout_s=timeout_s)
    try:
        return _parse_json(text)
    except (json.JSONDecodeError, ValueError):
        logger.info("asi1 returned invalid JSON, asking again")

    convo += [
        {"role": "assistant", "content": text},
        {"role": "user", "content": "That was not valid JSON. Return valid JSON only."},
    ]
    text = await complete(convo, temperature=0, timeout_s=timeout_s)
    try:
        return _parse_json(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMError("ASI1 did not return valid JSON after a retry") from exc
