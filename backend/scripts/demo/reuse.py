"""Reuse what is already recorded during a recording run (#63).

A branch's reply has to be recorded against the exact question and options a visitor will
replay. Asking the model again for the first turn would word them differently and orphan every
reply recorded so far. So a key that is already recorded is answered from its recording, and
only what is missing goes to the live model (wrapped in `RecordingProvider`, which writes it).

A repair call has the same key as the call it repairs. So the second call for a key within one
step always goes live: a reused output that fails validation is replaced by a live one.
"""

from collections.abc import Mapping
from typing import Literal

from app.integrations.llm.base import LLMProvider, LLMRequest, LLMResult
from app.integrations.llm.recording import Recording

Outcome = Literal["reused", "recorded"]


class ReuseProvider:
    def __init__(
        self, inner: LLMProvider, recordings: Mapping[str, Recording], *, fresh: bool = False
    ) -> None:
        self._inner = inner
        self._known: dict[str, LLMResult] = (
            {}
            if fresh
            else {
                k: LLMResult(text=r.raw_output, provider=r.provider, model=r.model)
                for k, r in recordings.items()
            }
        )
        self._seen_this_step: set[str] = set()
        # Every key this run asked for, and what happened to it last.
        self.touched: dict[str, Outcome] = {}
        self.step_log: list[tuple[str, Outcome]] = []

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def vision(self) -> bool:
        return self._inner.vision

    @property
    def max_images(self) -> int:
        return self._inner.max_images

    def begin_step(self) -> None:
        """One request to the API: a turn or a damage report, with its repair call."""
        self._seen_this_step = set()
        self.step_log = []

    async def complete(self, request: LLMRequest) -> LLMResult:
        key = request.replay_key
        if key is None:
            return await self._inner.complete(request)
        known = self._known.get(key)
        if known is not None and key not in self._seen_this_step:
            outcome: Outcome = "reused"
            result = known
        else:
            outcome = "recorded"
            result = await self._inner.complete(request)
            self._known[key] = result
        self._seen_this_step.add(key)
        # Recorded earlier in this run stays recorded: the report says what is new.
        if self.touched.get(key) != "recorded":
            self.touched[key] = outcome
        self.step_log.append((key, outcome))
        return result

    async def aclose(self) -> None:
        await self._inner.aclose()
