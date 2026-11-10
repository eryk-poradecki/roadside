"""The live path: any OpenAI-compatible chat completions endpoint (Gemini, Ollama, Groq)."""

import asyncio
import logging
from typing import Any

import httpx

from app.integrations.llm.base import (
    LLMMessage,
    LLMRequest,
    LLMResult,
    ProviderError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def _content(message: LLMMessage) -> str | list[dict[str, Any]]:
    if not message.images:
        return message.text
    parts: list[dict[str, Any]] = [{"type": "text", "text": message.text}]
    parts += [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{image.media_type};base64,{image.data_b64}"},
        }
        for image in message.images
    ]
    return parts


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after", "")
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class OpenAICompatibleProvider:
    """POST /chat/completions with a JSON-schema `response_format`; no tools (ADR 0004).

    One retry on 429 or 5xx, after `retry-after` (capped) or a short backoff. No retry on
    other 4xx. The turn budget above this caps the total time, retries included.
    """

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        connect_timeout_s: float,
        read_timeout_s: float,
        vision: bool = False,
        max_images: int = 0,
        backoff_s: float = 1.0,
        max_retry_wait_s: float = 5.0,
        reasoning_effort: str | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model = model
        self._temperature = temperature
        self._vision = vision
        self._max_images = max_images if vision else 0
        self._backoff_s = backoff_s
        self._max_retry_wait_s = max_retry_wait_s
        self._reasoning_effort = reasoning_effort
        self.timeout = httpx.Timeout(read_timeout_s, connect=connect_timeout_s)
        self._headers = {"Authorization": f"Bearer {api_key}"}
        # Opened on first use and again after `aclose`, so the app survives a lifespan restart.
        self._client: httpx.AsyncClient | None = None

    @property
    def vision(self) -> bool:
        return self._vision

    @property
    def max_images(self) -> int:
        return self._max_images

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def complete(self, request: LLMRequest) -> LLMResult:
        body: dict[str, Any] = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [{"role": m.role, "content": _content(m)} for m in request.messages],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": request.schema_name, "schema": request.schema},
            },
        }
        if self._reasoning_effort is not None:
            # Thinking models (qwen3.5 on Ollama) are much faster with it off.
            body["reasoning_effort"] = self._reasoning_effort
        response = await self._post(body)
        if response.status_code in _RETRY_STATUSES:
            wait = _retry_after(response)
            wait = self._backoff_s if wait is None else wait
            wait = min(wait, self._max_retry_wait_s)
            logger.info("llm status %d, retrying once in %.1f s", response.status_code, wait)
            await asyncio.sleep(wait)
            response = await self._post(body)
        if response.status_code != 200:
            # The body may echo request details; keep it out of the message.
            raise ProviderError(f"LLM endpoint answered HTTP {response.status_code}")
        return self._parse(response)

    async def _post(self, body: dict[str, Any]) -> httpx.Response:
        try:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self.timeout, headers=self._headers)
            return await self._client.post(self._url, json=body)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"LLM endpoint timed out ({type(exc).__name__})") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"LLM endpoint unreachable ({type(exc).__name__})") from exc

    def _parse(self, response: httpx.Response) -> LLMResult:
        try:
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("LLM endpoint sent an unexpected body") from exc
        if not isinstance(text, str) or not text:
            raise ProviderError("LLM endpoint sent no text")
        if choice.get("finish_reason") == "length":
            # Half a JSON object; a repair call would only be cut off again.
            raise ProviderError("LLM output was cut off at the token limit")
        usage = data.get("usage")
        return LLMResult(
            text=text,
            provider=self.name,
            model=str(data.get("model") or self._model),
            usage={k: v for k, v in usage.items() if isinstance(v, int)}
            if isinstance(usage, dict)
            else {},
        )
