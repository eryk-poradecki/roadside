"""Demo mode's provider: pre-recorded real answers, looked up by the semantic key (ADR 0004).

A key miss is never answered with the nearest recording, so a demo visitor can't mistake
another scenario's advice for their own. It raises `NoRecordingError`, which the service turns
into a labelled "no recorded answer" problem. Replayed text goes through the same validation
as a live answer.
"""

from collections.abc import Mapping
from pathlib import Path

from app.integrations.llm.base import LLMRequest, LLMResult, ProviderError
from app.integrations.llm.recording import Recording, load_recordings


class NoRecordingError(ProviderError):
    """Demo mode has no recorded answer for this case (`no_recording`)."""


class ReplayProvider:
    name = "replay"
    # Images are never sent: a recording made with vision has `vision` in its key instead.
    vision = False
    max_images = 0

    def __init__(self, recordings: Mapping[str, Recording]) -> None:
        self._recordings = dict(recordings)

    @classmethod
    def from_dir(cls, directory: Path) -> "ReplayProvider":
        return cls(load_recordings(directory))

    async def complete(self, request: LLMRequest) -> LLMResult:
        rec = self._recordings.get(request.replay_key) if request.replay_key else None
        if rec is None:
            raise NoRecordingError("no recorded answer for this case")
        return LLMResult(text=rec.raw_output, provider=self.name, model=rec.model)

    async def aclose(self) -> None:
        return None
