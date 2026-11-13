"""The recording run and the demo check end to end (#63), with a fake model, Nominatim and
Overpass: what the run records, a demo-mode app replays with no miss, at any hour.

Three real scenarios: a one-shot urgent answer, a question with branches that waits for a
reviewer's choice, and the pothole with its damage report draft.
"""

import json
import sqlite3
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.deps import get_geocoder, get_place_source
from app.integrations.llm.base import LLMRequest, LLMResult
from app.integrations.llm.recording import RecordingProvider, load_recordings
from app.integrations.place_recording import load_place_recordings
from app.main import create_app
from app.services import assistant
from app.settings import Settings
from scripts.demo.check import DemoCheckFailed, NoDemoVehicle, NotDemoMode, check
from scripts.demo.record import RecordRun, record
from scripts.demo.scenarios import Scenario, load_scenarios
from tests.fakes import FakePlaceSource, answer_json, ask_json, osm_node, report_json
from tests.running import running

IDS = ("smoke_engine_bay", "unknown_knocking_warning", "pothole_damaged_wheel")
QUESTION = "Jakiego koloru jest kontrolka?"
OPTIONS = ("Czerwona", "Żółta lub pomarańczowa", "Kilka kontrolek naraz")
CHOICES = {
    "unknown_knocking_warning": {
        "pl": {"warning_light_red": OPTIONS[0], "warning_light_yellow": OPTIONS[1]}
    }
}
# A run at 03:00 UTC: night, though every scenario here happens in daylight.
NIGHT = datetime(2026, 11, 12, 3, 0, tzinfo=UTC)


class Model:
    """Answers like the live model did: the Polish knocking note asks first, then answers."""

    name = "fake"
    vision = True
    max_images = 3

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResult:
        self.calls += 1
        prompt = "\n".join(m.text for m in request.messages)
        if request.schema_name == "damage_report":
            text = report_json()
        elif "bonnet" in prompt or "maski" in prompt:
            text = answer_json(urgent=True, steps=["Call 112 now", "Keep away from the car"])
        elif "stuka" in prompt and QUESTION not in prompt:
            text = ask_json(question=QUESTION, options=OPTIONS)
        else:
            text = answer_json()
        return LLMResult(text=text, provider=self.name, model="fake-live")

    async def aclose(self) -> None:
        return None


class Geocoder:
    """A main road right under whatever point is asked about."""

    async def reverse(self, lat: float, lon: float, locale: str) -> dict[str, Any]:
        return {
            "category": "highway",
            "type": "primary",
            "lat": str(lat),
            "lon": str(lon),
            "address": {"road": "DK92", "village": "Wola"},
        }


def scenarios() -> list[Scenario]:
    return [s for s in load_scenarios() if s.id in IDS]


def recording_app(tmp_path: Path, recordings: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "record.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=False,
        llm_base_url="http://llm.test/v1",
        llm_api_key="k",
        llm_model="m",
        llm_record=True,
        llm_recordings_dir=recordings,
    )
    migrate(settings.database_path)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app = create_app(settings)
    places: list[list[object]] = [
        [osm_node(i, 52.0, 21.0, amenity="fuel", name=f"Station {i}")] for i in range(20)
    ]
    app.dependency_overrides[get_geocoder] = lambda: Geocoder()
    app.dependency_overrides[get_place_source] = lambda: FakePlaceSource(*places)
    return app


async def record_with(
    tmp_path: Path, recordings: Path, model: Model, choices: dict[str, Any]
) -> RecordRun:
    app = recording_app(tmp_path, recordings)
    live = RecordingProvider(model, recordings, prompt_version="v3")
    return await record(app, live, recordings, scenarios(), choices, full_run=True, today=NIGHT)


@pytest.fixture
async def demo(tmp_path: Path) -> AsyncIterator[Callable[[Path], Awaitable[httpx.AsyncClient]]]:
    """A started demo-mode app: its lifespan has seeded the demo vehicles (#122)."""
    async with AsyncExitStack() as stack:

        async def open_demo(recordings: Path) -> httpx.AsyncClient:
            settings = Settings(
                database_path=tmp_path / "demo.db",
                upload_dir=tmp_path / "demo-uploads",
                llm_recordings_dir=recordings,
            )
            return await stack.enter_async_context(running(settings))

        yield open_demo


@pytest.fixture
async def recorded(tmp_path: Path) -> tuple[Path, Model, RecordRun, RecordRun]:
    recordings = tmp_path / "recordings"
    model = Model()
    first = await record_with(tmp_path / "a", recordings, model, {})
    second = await record_with(tmp_path / "b", recordings, model, CHOICES)
    return recordings, model, first, second


@pytest.fixture(autouse=True)
def _dirs(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()


async def test_a_question_waits_for_a_choice_then_its_replies_are_recorded(
    recorded: tuple[Path, Model, RecordRun, RecordRun],
) -> None:
    _, _, first, second = recorded

    waiting = [w for w in first.walks if w.needs_choice]
    assert {w.branch.id for w in waiting} == {"warning_red", "warning_yellow"}
    assert all(w.needs_choice and w.needs_choice[1] == QUESTION for w in waiting)
    assert not first.ok
    assert second.ok, [(w.name, w.problems) for w in second.walks]


async def test_a_rerun_reuses_the_recorded_question(
    recorded: tuple[Path, Model, RecordRun, RecordRun],
) -> None:
    _, _, _, second = recorded

    steps = [step for steps in second.steps.values() for step in steps]
    first_turns = [outcome for label, _, outcome in steps if label == "first turn"]
    replies = [outcome for label, _, outcome in steps if label.startswith("reply")]
    assert set(first_turns) == {"reused"}
    assert "recorded" in replies


async def test_the_run_records_turns_places_light_and_report(
    recorded: tuple[Path, Model, RecordRun, RecordRun],
) -> None:
    recordings, _, _, second = recorded

    saved = load_recordings(recordings)
    keys = [json.loads(k) for k in saved]
    # 3 scenarios x 2 locales, + red, yellow and skip replies in Polish, + 2 report drafts.
    assert len(saved) == 6 + 3 + 2
    assert sum(k.get("artifact") == "damage_report" for k in keys) == 2
    # Recorded at night, but in each scenario's own daylight.
    assert all(k["dark"] is False for k in keys)
    assert {(r.provider, r.model, r.prompt_version) for r in saved.values()} == {
        ("fake", "fake-live", "v3")
    }
    places = load_place_recordings(recordings / "places")
    assert len(places) == 3
    assert all(p.dark is False and sorted(p.nearby) == [5, 25] for p in places.values())
    assert second.findings == []
    assert second.orphans == []


async def test_the_demo_check_replays_every_walk_with_no_miss(
    recorded: tuple[Path, Model, RecordRun, RecordRun],
    demo: Callable[[Path], Awaitable[httpx.AsyncClient]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recordings, model, _, _ = recorded
    calls = model.calls
    # The visitor's clock says night: the recorded light must win.
    monkeypatch.setattr(assistant, "is_dark", lambda *_: True)

    walks = await check(await demo(recordings), scenarios(), CHOICES)

    assert [(w.name, w.problems) for w in walks if not w.ok] == []
    assert len(walks) == 2 + 4 + 2
    [pothole_en, _] = [w for w in walks if w.scenario.id == "pothole_damaged_wheel"]
    assert set(pothole_en.reports) == {"en", "pl"}
    assert model.calls == calls


async def test_the_demo_check_reports_a_miss(
    tmp_path: Path, demo: Callable[[Path], Awaitable[httpx.AsyncClient]]
) -> None:
    with pytest.raises(DemoCheckFailed, match="/config is missing scenario pothole_damaged_wheel"):
        await check(await demo(tmp_path / "empty"), scenarios(), CHOICES)


async def test_the_demo_check_cleans_up_after_itself(
    recorded: tuple[Path, Model, RecordRun, RecordRun],
    demo: Callable[[Path], Awaitable[httpx.AsyncClient]],
) -> None:
    client = await demo(recorded[0])
    seeded = (await client.get("/api/v1/vehicles")).json()

    await check(client, scenarios(), CHOICES)

    assert (await client.get("/api/v1/incidents")).json()["total"] == 0
    # It walked the seeded vehicles, as a visitor picks them, and left them be.
    after = (await client.get("/api/v1/vehicles")).json()
    assert [{k: v for k, v in row.items() if k != "updated_at"} for row in after] == [
        {k: v for k, v in row.items() if k != "updated_at"} for row in seeded
    ]


async def test_the_demo_check_refuses_an_app_without_a_seeded_demo_vehicle(
    tmp_path: Path, demo: Callable[[Path], Awaitable[httpx.AsyncClient]]
) -> None:
    """A visitor can't pick a deleted demo vehicle, so the check doesn't make its own."""
    client = await demo(tmp_path / "empty")
    [octavia] = [v for v in (await client.get("/api/v1/vehicles")).json() if v["name"] == "Octavia"]
    # Simulate damaged storage: demo-mode API calls now protect these rows.
    with closing(sqlite3.connect(tmp_path / "demo.db")) as conn:
        conn.execute("DELETE FROM vehicles WHERE id = ?", (octavia["id"],))
        conn.commit()

    with pytest.raises(NoDemoVehicle, match="Octavia"):
        await check(client, scenarios(), CHOICES)


async def test_the_demo_check_refuses_an_edited_demo_vehicle(
    tmp_path: Path, demo: Callable[[Path], Awaitable[httpx.AsyncClient]]
) -> None:
    """An edited demo vehicle no longer hits its recordings: say so, not a row of misses."""
    client = await demo(tmp_path / "empty")
    [octavia] = [v for v in (await client.get("/api/v1/vehicles")).json() if v["name"] == "Octavia"]
    # Simulate a row changed outside demo mode.
    with closing(sqlite3.connect(tmp_path / "demo.db")) as conn:
        conn.execute("UPDATE vehicles SET fuel_type = NULL WHERE id = ?", (octavia["id"],))
        conn.commit()

    with pytest.raises(NoDemoVehicle, match="Octavia"):
        await check(client, scenarios(), CHOICES)


async def test_the_demo_check_refuses_a_live_app(tmp_path: Path) -> None:
    app = recording_app(tmp_path, tmp_path / "recordings")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://live") as client:
        with pytest.raises(NotDemoMode):
            await check(client, scenarios(), CHOICES)


async def test_an_orphan_is_found_on_a_full_run(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    stale = recordings / "0000000000000000.json"
    stale.write_text(
        json.dumps(
            {
                "key": '{"stale":true}',
                "request": {},
                "raw_output": "{}",
                "provider": "p",
                "model": "m",
                "prompt_version": "v1",
                "recorded_at": "t",
            }
        )
    )

    run = await record_with(tmp_path / "a", recordings, Model(), CHOICES)

    assert run.orphans == [stale]


async def test_a_failed_places_lookup_is_retried(tmp_path: Path) -> None:
    """Public Overpass fails often: a recording run retries before giving up on a radius."""
    from app.integrations.overpass import NearbyUnavailable

    recordings = tmp_path / "recordings"
    app = recording_app(tmp_path / "a", recordings)
    flaky = FakePlaceSource(NearbyUnavailable("busy"), [], NearbyUnavailable("busy"), [])
    app.dependency_overrides[get_place_source] = lambda: flaky
    smoke = [s for s in scenarios() if s.id == "smoke_engine_bay"]
    live = RecordingProvider(Model(), recordings, prompt_version="v3")

    run = await record(app, live, recordings, smoke, {}, today=NIGHT, retry_wait_s=0)

    assert run.walks[0].nearby == {5: "none", 25: "none"}
    assert run.ok
