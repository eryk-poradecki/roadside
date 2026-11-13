"""Demo mode end to end: AI turns, nearby places and the location context replayed from
recordings, and recording a live run (ADR 0004, #58).

The recordings in `tests/fixtures/recordings/` are hand-made; their keys are what the service
builds for an incident with no vehicle and daylight. The place recordings in `places/` hold
the location context and nearby places of a flat tyre and of running out of fuel.
"""

import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.deps import get_geocoder, get_llm_provider, get_place_source
from app.integrations.llm.recording import RecordingProvider, load_recordings
from app.integrations.llm.replay import ReplayProvider
from app.integrations.place_recording import load_place_recordings
from app.main import create_app
from app.services import assistant
from app.settings import Settings
from tests.fakes import (
    FakeGeocoder,
    FakePlaceSource,
    ScriptedProvider,
    answer_json,
    ask_json,
    nominatim_result,
    osm_node,
)
from tests.running import running

INC = "/api/v1/incidents"
FIXTURES = Path(__file__).parents[1] / "fixtures" / "recordings"
REPLY = {"option": "Yes, on the hard shoulder"}
# The visitor's own point: demo mode never sends it anywhere.
LOCATION = {"lat": 52.23, "lon": 21.01, "accuracy_m": 12}


@pytest.fixture(autouse=True)
def _daylight(monkeypatch: pytest.MonkeyPatch) -> None:
    """`dark` is in the replay key; pin it so the recordings match at any hour."""
    monkeypatch.setattr(assistant, "is_dark", lambda *_: False)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Demo mode never calls a model: any outgoing HTTP request fails the test."""

    async def refuse(*_: object, **__: object) -> httpx.Response:
        raise AssertionError("demo mode made a network call")

    # The test client's ASGITransport stays in-process; only real network transports refuse.
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", refuse)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=True,
        llm_recordings_dir=FIXTURES,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    migrate(settings.database_path)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_incident(
    client: httpx.AsyncClient, problem_type: str = "flat_tyre", **body: object
) -> int:
    r = await client.post(INC, json={"problem_type": problem_type, **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def turn(
    client: httpx.AsyncClient,
    incident_id: int,
    reply: dict[str, Any] | None = None,
    locale: str = "en",
) -> httpx.Response:
    body: dict[str, Any] = {"locale": locale}
    if reply is not None:
        body["reply"] = reply
    return await client.post(f"{INC}/{incident_id}/ai-turns", json=body)


async def nearby(client: httpx.AsyncClient, incident_id: int, radius_km: int = 5) -> httpx.Response:
    return await client.post(f"{INC}/{incident_id}/nearby", json={"radius_km": radius_km})


async def stored_kinds(client: httpx.AsyncClient, incident_id: int) -> list[str]:
    r = await client.get(f"{INC}/{incident_id}")
    return [t["kind"] for t in r.json()["ai_turns"]]


def test_demo_mode_builds_the_replay_provider(app: FastAPI) -> None:
    assert isinstance(app.state.llm_provider, ReplayProvider)


async def test_a_help_request_with_a_question_completes_from_recordings(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client)

    first = await turn(client, incident_id)
    assert first.status_code == 201, first.text
    assert first.json()["kind"] == "question"
    assert first.json()["question"]["options"][0] == REPLY["option"]

    second = await turn(client, incident_id, reply=REPLY)
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["kind"] == "advice"
    assert body["advice"]["cause"] == "A puncture in the rear left tyre"
    assert await stored_kinds(client, incident_id) == ["question", "reply", "advice"]


async def test_replayed_turns_name_the_recorded_model(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await client.get(f"{INC}/{incident_id}")

    [question] = r.json()["ai_turns"]
    assert (question["provider"], question["model"]) == ("replay", "fixture-model")


async def test_the_attached_sample_photos_pick_the_recording(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client)
    r = await client.post(f"{INC}/{incident_id}/photos", json={"sample_id": "screw_in_tread"})
    assert r.status_code == 201, r.text

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["advice"]["cause"] == "A screw in the tread"


async def test_a_key_miss_is_a_labelled_fallback_that_stores_nothing(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, problem_type="out_of_fuel")

    r = await turn(client, incident_id)

    assert r.status_code == 503
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["reason"] == "no_recording"
    assert await stored_kinds(client, incident_id) == []


async def test_another_locale_is_a_key_miss(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client)

    r = await turn(client, incident_id, locale="pl")

    assert r.json()["reason"] == "no_recording"


async def test_an_unrecorded_reply_is_a_key_miss_and_the_reply_stays(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, reply={"text": "somewhere else"})

    assert r.json()["reason"] == "no_recording"
    assert await stored_kinds(client, incident_id) == ["question", "reply"]


async def test_replayed_output_is_validated_like_live_output(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, problem_type="flat_battery")

    r = await turn(client, incident_id)

    assert r.status_code == 502
    assert r.json()["reason"] == "invalid_output"
    assert await stored_kinds(client, incident_id) == []


# --- recorded nearby places and location context (#58) ----------------------------------------


def test_demo_mode_builds_no_nominatim_or_overpass_client(app: FastAPI) -> None:
    assert app.state.geocoder is None
    assert app.state.place_source is None


async def test_a_help_request_shows_recorded_places_and_uses_the_recorded_context(
    client: httpx.AsyncClient,
) -> None:
    # `_no_network` fails the test on any outgoing request: no Overpass, no Nominatim.
    incident_id = await make_incident(client, location=LOCATION)

    places = await nearby(client, incident_id)
    advice = await turn(client, incident_id)

    assert places.status_code == 200, places.text
    assert places.json()["status"] == "found"
    assert places.json()["radius_km"] == 5
    assert [p["name"] for p in places.json()["places"]] == ["Wulkanizacja A2", "Orlen MOP Wola"]
    assert advice.status_code == 201, advice.text
    # The recorded motorway context picked the motorway recording.
    assert advice.json()["inputs"]["road_class"] == "motorway_expressway"
    assert advice.json()["advice"]["cause"] == "A blowout on the motorway"
    incident = (await client.get(f"{INC}/{incident_id}")).json()
    assert incident["location_label"] == "A2, Wola"
    assert incident["nearby"] == places.json()


async def test_the_wide_radius_returns_the_recorded_wide_result(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)

    r = await nearby(client, incident_id, radius_km=25)

    assert r.status_code == 200, r.text
    assert r.json()["radius_km"] == 25
    assert len(r.json()["places"]) == 3


async def test_a_recorded_none_is_a_none(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, "out_of_fuel", location=LOCATION)

    r = await nearby(client, incident_id)

    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["radius_km"]) == ("none", 5)


async def test_an_unrecorded_radius_is_labelled_and_keeps_the_places_found(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, "out_of_fuel", location=LOCATION)
    first = await nearby(client, incident_id)

    r = await nearby(client, incident_id, radius_km=25)

    assert r.status_code == 503
    assert r.headers["content-type"] == "application/problem+json"
    assert r.json()["reason"] == "nearby_not_recorded"
    incident = (await client.get(f"{INC}/{incident_id}")).json()
    assert incident["nearby"] == first.json()


async def test_an_unrecorded_scenario_has_no_places_and_an_unknown_context(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, "flat_tyre", location=LOCATION, situation="parked")

    places = await nearby(client, incident_id)
    advice = await turn(client, incident_id)

    assert places.status_code == 503
    assert places.json()["reason"] == "nearby_not_recorded"
    # No recorded context: unknown, as when a live lookup fails, and no label.
    assert advice.json()["reason"] == "no_recording"
    incident = (await client.get(f"{INC}/{incident_id}")).json()
    assert incident["location_label"] is None
    assert incident["nearby"] is None


async def test_a_new_scenario_drops_the_places_and_context_of_the_old_one(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)
    await turn(client, incident_id)

    r = await client.patch(f"{INC}/{incident_id}", json={"problem_type": "out_of_fuel"})

    assert r.status_code == 200, r.text
    # The out-of-fuel recording has a context with no label, and no places looked up yet.
    assert (r.json()["location_label"], r.json()["nearby"]) == (None, None)
    places = await nearby(client, incident_id)
    assert places.json()["status"] == "none"


async def test_a_change_outside_the_scenario_keeps_the_places_and_context(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)
    await turn(client, incident_id)

    r = await client.patch(f"{INC}/{incident_id}", json={"note": "Loud bang"})

    assert r.json()["location_label"] == "A2, Wola"
    assert r.json()["nearby"]["status"] == "found"


# --- the recorded light (#63) ------------------------------------------------------------------


async def test_the_recorded_light_beats_the_visitors_clock(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A visitor at night still replays the scenario recorded in daylight."""
    monkeypatch.setattr(assistant, "is_dark", lambda *_: True)
    incident_id = await make_incident(client, location=LOCATION)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["inputs"]["dark"] is False
    assert r.json()["advice"]["cause"] == "A blowout on the motorway"


async def test_the_recorded_light_picks_the_damage_report_draft(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant, "is_dark", lambda *_: True)
    incident_id = await make_incident(client, "pothole_damage", location=LOCATION)

    r = await client.post(f"{INC}/{incident_id}/damage-report", json={"locale": "pl"})

    assert r.status_code == 201, r.text


async def test_the_recorded_light_needs_no_location(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It belongs to the scenario, not to a point: a visitor who shares none replays it too."""
    monkeypatch.setattr(assistant, "is_dark", lambda *_: True)
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["inputs"]["dark"] is False


# --- recording a live run --------------------------------------------------------------------


async def test_recording_writes_one_recording_per_turn_that_replays(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    live = Settings(
        database_path=tmp_path / "live.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=False,
        llm_base_url="http://llm.test/v1",
        llm_api_key="k",
        llm_model="m",
        llm_record=True,
        llm_recordings_dir=recordings,
    )
    migrate(live.database_path)
    app = create_app(live)
    assert isinstance(app.state.llm_provider, RecordingProvider)
    # The live model is scripted: one question, then (after a repair) the advice.
    fake = ScriptedProvider(ask_json(), "not json", answer_json(), model="live-model")
    provider = RecordingProvider(fake, recordings, prompt_version="v1")
    app.dependency_overrides[get_llm_provider] = lambda: provider

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        incident_id = await make_incident(c)
        assert (await turn(c, incident_id)).status_code == 201
        assert (await turn(c, incident_id, reply=REPLY)).status_code == 201

    saved = load_recordings(recordings)
    assert len(saved) == 2
    by_replies = {len(json.loads(k)["replies"]): rec for k, rec in saved.items()}
    assert by_replies[0].raw_output == ask_json()
    assert by_replies[1].raw_output == answer_json()
    for rec in saved.values():
        assert (rec.provider, rec.model, rec.prompt_version) == ("fake", "live-model", "v1")
        assert rec.request["messages"][0]["role"] == "system"

    # The same help request in demo mode replays what was recorded.
    demo = Settings(
        database_path=tmp_path / "demo.db",
        upload_dir=tmp_path / "uploads",
        llm_recordings_dir=recordings,
    )
    migrate(demo.database_path)
    transport = httpx.ASGITransport(app=create_app(demo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        incident_id = await make_incident(c)
        assert (await turn(c, incident_id)).json()["kind"] == "question"
        assert (await turn(c, incident_id, reply=REPLY)).json()["kind"] == "advice"


async def test_recording_captures_the_places_and_the_context_that_replay(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    live = Settings(
        database_path=tmp_path / "live.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=False,
        llm_base_url="http://llm.test/v1",
        llm_api_key="k",
        llm_model="m",
        llm_record=True,
        llm_recordings_dir=recordings,
    )
    migrate(live.database_path)
    app = create_app(live)
    fake = ScriptedProvider(answer_json(cause="A blowout"), model="live-model")
    provider = RecordingProvider(fake, recordings, prompt_version="v1")
    tyres = osm_node(1, 52.2300, 21.0122, shop="tyres", name="Wulkanizacja")
    garage = osm_node(2, 52.3000, 21.0122, shop="car_repair", name="Garage")
    source = FakePlaceSource([tyres], [tyres, garage])
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder(nominatim_result())
    app.dependency_overrides[get_place_source] = lambda: source

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        incident_id = await make_incident(c, location=LOCATION)
        live_5 = (await nearby(c, incident_id)).json()
        live_25 = (await nearby(c, incident_id, radius_km=25)).json()
        assert (await turn(c, incident_id)).json()["inputs"]["road_class"] == "motorway_expressway"

    [saved] = load_place_recordings(recordings / "places").values()
    assert json.loads(saved.key)["problem_type"] == "flat_tyre"
    assert saved.location is not None
    assert saved.location.label == "A2, Wola"
    assert sorted(saved.nearby) == [5, 25]
    # The light the turn was given, which demo mode replays in place of the clock (#63).
    assert saved.dark is False

    # The same help request in demo mode, from another point, replays all of it.
    demo = Settings(
        database_path=tmp_path / "demo.db",
        upload_dir=tmp_path / "uploads",
        llm_recordings_dir=recordings,
    )
    migrate(demo.database_path)
    transport = httpx.ASGITransport(app=create_app(demo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        incident_id = await make_incident(c, location={"lat": 50.06, "lon": 19.94})
        assert (await nearby(c, incident_id)).json() == live_5
        assert (await nearby(c, incident_id, radius_km=25)).json() == live_25
        replayed = (await turn(c, incident_id)).json()
        assert replayed["advice"]["cause"] == "A blowout"
        incident = (await c.get(f"{INC}/{incident_id}")).json()
        assert incident["location_label"] == "A2, Wola"


# --- the damage report draft (ADR 0009, #59) ---------------------------------------------------


async def test_a_damage_report_draft_is_replayed(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, problem_type="pothole_damage")

    r = await client.post(f"{INC}/{incident_id}/damage-report", json={"locale": "pl"})

    assert r.status_code == 201, r.text
    assert "głęboką wyrwę w jezdni" in r.json()["body"]
    assert "Przecięta przednia prawa opona" in r.json()["body"]


async def test_an_unrecorded_damage_report_is_a_labelled_fallback(
    client: httpx.AsyncClient,
) -> None:
    incident_id = await make_incident(client, problem_type="pothole_damage")

    r = await client.post(f"{INC}/{incident_id}/damage-report", json={"locale": "en"})

    assert r.status_code == 503
    assert r.json()["reason"] == "no_recording"
    assert (await client.get(f"{INC}/{incident_id}/damage-report")).status_code == 404


async def test_a_failed_damage_report_keeps_the_places(settings: Settings, tmp_path: Path) -> None:
    """#143: a draft with no recording stores nothing, the incident's places included."""
    recordings = tmp_path / "with-places"
    shutil.copytree(FIXTURES, recordings)
    places_dir = recordings / "places"
    pothole = json.loads((places_dir / "pothole_on_road.json").read_text())
    tyre = json.loads((places_dir / "flat_tyre_on_road.json").read_text())
    pothole["nearby"] = tyre["nearby"]
    (places_dir / "pothole_on_road.json").write_text(json.dumps(pothole))
    settings.llm_recordings_dir = recordings

    async with running(settings) as c:
        incident_id = await make_incident(c, problem_type="pothole_damage", location=LOCATION)
        places = await nearby(c, incident_id)
        assert places.status_code == 200, places.text

        r = await c.post(f"{INC}/{incident_id}/damage-report", json={"locale": "en"})

        assert r.json()["reason"] == "no_recording"
        incident = (await c.get(f"{INC}/{incident_id}")).json()
        assert incident["nearby"] == places.json()


async def test_only_recorded_letter_languages_are_offered(client: httpx.AsyncClient) -> None:
    """#143: demo mode offers a draft only where one is recorded (here: Polish)."""
    incident_id = await make_incident(client, problem_type="pothole_damage", location=LOCATION)

    r = await client.get(f"{INC}/{incident_id}/damage-report/locales")

    assert r.status_code == 200, r.text
    assert r.json() == {"locales": ["pl"]}
    # Asking writes nothing: the context is still looked up by the first turn or draft.
    incident = (await client.get(f"{INC}/{incident_id}")).json()
    assert incident["location_label"] is None


async def test_a_scenario_with_no_recorded_report_offers_none(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, problem_type="pothole_damage", situation="parked")

    r = await client.get(f"{INC}/{incident_id}/damage-report/locales")

    assert r.json() == {"locales": []}
