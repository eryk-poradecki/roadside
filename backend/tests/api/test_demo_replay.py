"""Demo mode end to end: AI turns replayed from recordings, and recording a live run (ADR 0004).

The recordings in `tests/fixtures/recordings/` are hand-made; their keys are what the service
builds for an incident with no vehicle, no location context and daylight.
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.deps import get_llm_provider
from app.integrations.llm.recording import RecordingProvider, load_recordings
from app.integrations.llm.replay import ReplayProvider
from app.main import create_app
from app.services import assistant
from app.settings import Settings
from tests.fakes import ScriptedProvider, answer_json, ask_json

INC = "/api/v1/incidents"
FIXTURES = Path(__file__).parents[1] / "fixtures" / "recordings"
REPLY = {"option": "Yes, on the hard shoulder"}


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


async def make_incident(client: httpx.AsyncClient, problem_type: str = "flat_tyre") -> int:
    r = await client.post(INC, json={"problem_type": problem_type})
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
