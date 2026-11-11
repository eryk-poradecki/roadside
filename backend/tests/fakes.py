import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.integrations.llm.base import LLMRequest, LLMResult
from app.integrations.overpass import OverpassResult

Script = str | BaseException | Callable[[], Awaitable[str]]


def answer_json(**overrides: Any) -> str:
    """A valid `answer` turn as the model would send it; overrides go into the answer block."""
    urgent = overrides.pop("urgent", False)
    answer: dict[str, Any] = {
        "cause": "A puncture in the rear left tyre",
        "confidence": "likely",
        "alternatives": ["A damaged valve"],
        "steps": ["Get everyone behind the barrier first", "Call your assistance"],
        "escalate_if": ["You smell fuel"],
        "photo_observation": None,
        "extra_categories": ["repair"],
    }
    answer.update(overrides)
    return json.dumps({"kind": "answer", "urgent": urgent, "ask": None, "answer": answer})


def ask_json(
    question: str = "Is the car on the hard shoulder?",
    options: tuple[str, ...] = ("Yes, on the hard shoulder", "No, off the road"),
    now: str = "Get everyone behind the barrier",
    urgent: bool = False,
) -> str:
    """A valid `ask` turn (a clarifying question) as the model would send it."""
    ask = {"now": now, "question": question, "options": list(options)}
    return json.dumps({"kind": "ask", "urgent": urgent, "ask": ask, "answer": None})


class ScriptedProvider:
    """A provider fake that plays back scripted outputs and records every request.

    Each script item is the raw text to return, an exception to raise, or an async callable
    producing the text (to block or sleep).
    """

    name = "fake"

    def __init__(self, *script: Script, model: str = "fake-model-1") -> None:
        self.script = list(script)
        self.requests: list[LLMRequest] = []
        self.model = model
        self.vision = False
        self.max_images = 0
        # Set on every call, so a test can wait for a turn to reach the model.
        self.called = asyncio.Event()

    async def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        self.called.set()
        if not self.script:
            raise AssertionError("ScriptedProvider ran out of scripted outputs")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        text = item if isinstance(item, str) else await item()
        return LLMResult(text=text, provider=self.name, model=self.model)

    async def aclose(self) -> None:
        return None

    def prompt_text(self, call: int = 0) -> str:
        """Every message of one request, joined: what the model would read."""
        return "\n".join(m.text for m in self.requests[call].messages)


def blocking(event: asyncio.Event, text: str) -> Callable[[], Awaitable[str]]:
    async def run() -> str:
        await event.wait()
        return text

    return run


def sleeping(seconds: float, text: str) -> Callable[[], Awaitable[str]]:
    async def run() -> str:
        await asyncio.sleep(seconds)
        return text

    return run


class FakeGeocoder:
    """A scripted reverse geocoder: returns `result` (None = a failed lookup) and records calls."""

    def __init__(self, result: dict[str, Any] | None) -> None:
        self.result = result
        self.calls: list[tuple[float, float, str]] = []

    async def reverse(self, lat: float, lon: float, locale: str) -> dict[str, Any] | None:
        self.calls.append((lat, lon, locale))
        return self.result


def nominatim_result(
    highway: str = "motorway", road: str = "A2", locality: tuple[str, str] = ("village", "Wola")
) -> dict[str, Any]:
    """A jsonv2 reverse result centred on `LOCATION_POINT`."""
    return {
        "category": "highway",
        "type": highway,
        "lat": "52.2300",
        "lon": "21.0100",
        "address": {"road": road, locality[0]: locality[1]},
    }


PlaceScript = list[object] | BaseException | Callable[[], Awaitable[list[object]]]


class FakePlaceSource:
    """A scripted Overpass: each call plays the next item (elements, or an exception)."""

    def __init__(
        self, *script: "list[object] | BaseException | Callable[[], Awaitable[list[object]]]"
    ) -> None:
        self.script = list(script)
        self.calls: list[tuple[float, float, int]] = []

    async def search(self, lat: float, lon: float, radius_m: int) -> OverpassResult:
        self.calls.append((lat, lon, radius_m))
        if not self.script:
            raise AssertionError("FakePlaceSource ran out of scripted results")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        elements = item if isinstance(item, list) else await item()
        return OverpassResult(elements=elements, endpoint="https://overpass.test/api/interpreter")


def osm_node(osm_id: int, lat: float, lon: float, **tags: str) -> dict[str, Any]:
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": tags}
