"""Demo mode's provider: pre-recorded real answers, looked up by the semantic key (ADR 0004).

A key miss is never answered with the nearest recording, so a demo visitor can't mistake
another scenario's advice for their own. It raises `NoRecordingError`, which the service turns
into a labelled "no recorded answer" problem. Replayed text goes through the same validation
as a live answer.
"""

from collections.abc import Mapping
from pathlib import Path

from app.assist.replay_key import made_with_vision
from app.integrations.llm.base import LLMRequest, LLMResult, ProviderError
from app.integrations.llm.recording import Recording, load_recordings


class NoRecordingError(ProviderError):
    """Demo mode has no recorded answer for this case (`no_recording`)."""


class ReplayProvider:
    """Images are never sent anywhere: a recording made with vision has `vision` in its key
    instead. `vision` and `max_images` say how the recordings to play were made, so the
    service builds the same key; the images it attaches are ignored."""

    name = "replay"

    def __init__(
        self, recordings: Mapping[str, Recording], *, vision: bool = False, max_images: int = 0
    ) -> None:
        self._recordings = dict(recordings)
        self.vision = vision
        self.max_images = max_images if vision else 0

    @classmethod
    def from_dir(cls, directory: Path, *, max_images: int = 0) -> "ReplayProvider":
        """`vision` comes from the recordings themselves (#63), so a demo needs no
        `LLM_VISION`: on when any of them was made with the photos shown to the model."""
        recordings = load_recordings(directory)
        vision = any(made_with_vision(key) for key in recordings)
        return cls(recordings, vision=vision, max_images=max_images)

    async def complete(self, request: LLMRequest) -> LLMResult:
        rec = self._recordings.get(request.replay_key) if request.replay_key else None
        if rec is None:
            raise NoRecordingError("no recorded answer for this case")
        return LLMResult(text=rec.raw_output, provider=self.name, model=rec.model)

    async def aclose(self) -> None:
        return None
