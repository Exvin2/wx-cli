"""Thin OpenRouter HTTP client used by wx forecaster."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_TIMEOUT = 30.0


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter cannot fulfil a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class OpenRouterConfig:
    """Configuration required to talk to OpenRouter."""

    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: float = DEFAULT_TIMEOUT
    retries: int = 3
    backoff_factor: float = 0.75

    @property
    def chat_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


@dataclass(slots=True)
class OpenRouterResponse:
    """Structured data returned from OpenRouter."""

    text: str
    model: str
    raw: dict[str, Any]
    usage: dict[str, Any] | None
    headers: Mapping[str, str]
    attempts: int


def chat_completion(
    messages: Iterable[Mapping[str, str]],
    *,
    config: OpenRouterConfig,
    extra_headers: Mapping[str, str] | None = None,
) -> OpenRouterResponse:
    """Call OpenRouter's chat completions endpoint and return the text payload."""

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Exvin2/claudex-cli",
        "X-Title": "wx CLI",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": config.model,
        "messages": list(messages),
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    last_error: Exception | None = None
    last_status: int | None = None
    attempts = 0
    backoff = config.backoff_factor

    for attempt in range(1, config.retries + 1):
        attempts = attempt
        try:
            response = httpx.post(
                config.chat_url,
                headers=headers,
                json=payload,
                timeout=config.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            last_status = exc.response.status_code
            if last_status in RETRYABLE_STATUS_CODES and attempt < config.retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise OpenRouterError(
                f"OpenRouter HTTP {last_status}",
                status_code=last_status,
                payload=_safe_json(exc.response),
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt < config.retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise OpenRouterError("OpenRouter request failed", status_code=None) from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt < config.retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            raise OpenRouterError(
                "OpenRouter returned invalid JSON", status_code=response.status_code
            ) from exc

        text = _extract_first_message(data)
        if not text:
            raise OpenRouterError(
                "OpenRouter response missing content",
                status_code=response.status_code,
                payload=data,
            )

        return OpenRouterResponse(
            text=text,
            model=data.get("model", config.model),
            raw=data,
            usage=data.get("usage"),
            headers=response.headers,
            attempts=attempts,
        )

    # Should not reach here; raise informative fallback error.
    raise OpenRouterError(
        "OpenRouter request exhausted retries", status_code=last_status
    ) from last_error


def _extract_first_message(data: Mapping[str, Any]) -> str | None:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
    if not isinstance(message, Mapping):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        texts = [part.get("text", "") for part in content if isinstance(part, Mapping)]
        combined = "".join(texts).strip()
        return combined or None
    return None


def _safe_json(response: httpx.Response) -> dict[str, Any] | None:
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


__all__ = [
    "OpenRouterConfig",
    "OpenRouterError",
    "OpenRouterResponse",
    "chat_completion",
]
