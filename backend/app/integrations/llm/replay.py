"""Demo mode's provider: pre-recorded real answers, looked up by the semantic key (ADR 0004).

A key miss is never answered with the nearest recording, so a demo visitor can't mistake
another scenario's advice for their own. It raises `NoRecordingError`, which the service turns
into a labelled "no recorded answer" problem. Replayed text goes through the same validation
as a live answer.

A replayed AI turn arrives after a simulated thinking time (#143), as a live one would, so the
safety checklist is read first: `thinking_s` before a first turn, `reply_thinking_s` before
the answer to a clarifying question. A damage report draft and a key miss come at once.
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path

from app.assist.replay_key import key_stage, made_with_vision
from app.integrations.llm.base import LLMRequest, LLMResult, ProviderError
from app.integrations.llm.recording import Recording, load_recordings

Sleep = Callable[[float], Awaitable[None]]


class NoRecordingError(ProviderError):
    """Demo mode has no recorded answer for this case (`no_recording`)."""


class ReplayProvider:
    """Images are never sent anywhere: a recording made with vision has `vision` in its key
    instead. `vision` and `max_images` say how the recordings to play were made, so the
    service builds the same key; the images it attaches are ignored."""

    name = "replay"

    def __init__(
        self,
        recordings: Mapping[str, Recording],
        *,
        vision: bool = False,
        max_images: int = 0,
        thinking_s: float = 0,
        reply_thinking_s: float = 0,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._recordings = dict(recordings)
        self.vision = vision
        self.max_images = max_images if vision else 0
        self._thinking_s = {"first_turn": thinking_s, "after_reply": reply_thinking_s}
        self._sleep = sleep

    @classmethod
    def from_dir(
        cls,
        directory: Path,
        *,
        max_images: int = 0,
        thinking_s: float = 0,
        reply_thinking_s: float = 0,
        sleep: Sleep = asyncio.sleep,
    ) -> "ReplayProvider":
        """`vision` comes from the recordings themselves (#63), so a demo needs no
        `LLM_VISION`: on when any of them was made with the photos shown to the model."""
        recordings = load_recordings(directory)
        vision = any(made_with_vision(key) for key in recordings)
        return cls(
            recordings,
            vision=vision,
            max_images=max_images,
            thinking_s=thinking_s,
            reply_thinking_s=reply_thinking_s,
            sleep=sleep,
        )

    def has_recording(self, key: str) -> bool:
        """Whether a request under `key` would replay rather than miss."""
        return key in self._recordings

    async def complete(self, request: LLMRequest) -> LLMResult:
        rec = self._recordings.get(request.replay_key) if request.replay_key else None
        if rec is None:
            raise NoRecordingError("no recorded answer for this case")
        wait = self._thinking_s.get(key_stage(rec.key), 0)
        if wait > 0:
            await self._sleep(wait)
        return LLMResult(text=rec.raw_output, provider=self.name, model=rec.model)

    async def aclose(self) -> None:
        return None
