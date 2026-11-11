"""Recordings of real model answers, and the decorator that makes them (ADR 0004).

One JSON file per replay key: `{key, request, raw_output, provider, model, prompt_version,
recorded_at}`. The file name comes from the key, so a repair call in the same turn overwrites
the first output and a turn leaves one recording, holding the output the turn was built from.
Images are recorded by digest, never by content: a driver's photo must not end up in the repo.
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.integrations.llm.base import LLMProvider, LLMRequest, LLMResult
from app.services.clock import utc_now

logger = logging.getLogger(__name__)

_FIELDS = ("key", "request", "raw_output", "provider", "model", "prompt_version", "recorded_at")


@dataclass(frozen=True, slots=True)
class Recording:
    key: str
    request: dict[str, Any]
    raw_output: str
    provider: str
    model: str
    prompt_version: str
    recorded_at: str

    def to_json(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in _FIELDS}

    @classmethod
    def from_json(cls, data: object) -> "Recording":
        if not isinstance(data, dict) or set(data) != set(_FIELDS):
            raise ValueError(f"a recording has exactly the fields {', '.join(_FIELDS)}")
        if not isinstance(data["request"], dict) or not all(
            isinstance(data[name], str) for name in _FIELDS if name != "request"
        ):
            raise ValueError("a recording's fields are strings, and its request an object")
        return cls(**data)


def file_name(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16] + ".json"


def load_recordings(directory: Path) -> dict[str, Recording]:
    """Every recording in `directory`, by key. A malformed file or a repeated key fails startup;
    a missing directory holds none."""
    recordings: dict[str, Recording] = {}
    if not directory.is_dir():
        return recordings
    for path in sorted(directory.glob("*.json")):
        try:
            rec = Recording.from_json(json.loads(path.read_text(encoding="utf-8")))
        except ValueError as exc:
            raise ValueError(f"recording {path.name} is not valid: {exc}") from exc
        if rec.key in recordings:
            raise ValueError(f"two recordings have the key {rec.key}")
        recordings[rec.key] = rec
    return recordings


def _request_json(request: LLMRequest) -> dict[str, Any]:
    return {
        "schema_name": request.schema_name,
        "messages": [
            {
                "role": m.role,
                "text": m.text,
                "images": [
                    {
                        "media_type": i.media_type,
                        "sha256": hashlib.sha256(i.data_b64.encode()).hexdigest(),
                    }
                    for i in m.images
                ],
            }
            for m in request.messages
        ],
    }


def _write(directory: Path, rec: Recording) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / file_name(rec.key)
    # Unique, so two turns recording the same key at once can't trip over one temp file.
    tmp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    text = json.dumps(rec.to_json(), ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class RecordingProvider:
    """Wraps a live provider and records each answer under the request's replay key.

    Only with `LLM_RECORD=true` and never in demo mode (settings refuse both together).
    """

    def __init__(
        self,
        inner: LLMProvider,
        directory: Path,
        *,
        prompt_version: str,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self._inner = inner
        self._directory = directory
        self._prompt_version = prompt_version
        self._clock = clock

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def vision(self) -> bool:
        return self._inner.vision

    @property
    def max_images(self) -> int:
        return self._inner.max_images

    async def complete(self, request: LLMRequest) -> LLMResult:
        result = await self._inner.complete(request)
        if request.replay_key is None:
            logger.warning("not recorded: the request has no replay key")
            return result
        rec = Recording(
            key=request.replay_key,
            request=_request_json(request),
            raw_output=result.text,
            provider=result.provider,
            model=result.model,
            prompt_version=self._prompt_version,
            recorded_at=self._clock(),
        )
        try:
            await asyncio.to_thread(_write, self._directory, rec)
        except OSError:
            # The driver still gets the live answer; only the recording is lost.
            logger.exception("could not write recording %s", file_name(rec.key))
        else:
            logger.info("recorded %s", file_name(rec.key))
        return result

    async def aclose(self) -> None:
        await self._inner.aclose()
