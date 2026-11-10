"""The location context: looked up lazily at the first AI turn and cached (ADR 0004, 0005)."""

import httpx
import pytest
from fastapi import FastAPI

from app.deps import get_geocoder, get_llm_provider
from tests.fakes import FakeGeocoder, ScriptedProvider, answer_json, nominatim_result

INC = "/api/v1/incidents"
LOCATION = {"lat": 52.23, "lon": 21.01, "accuracy_m": 12}


@pytest.fixture
def provider(app: FastAPI) -> ScriptedProvider:
    fake = ScriptedProvider(answer_json(), answer_json())
    app.dependency_overrides[get_llm_provider] = lambda: fake
    return fake


def use_geocoder(app: FastAPI, geocoder: FakeGeocoder) -> FakeGeocoder:
    app.dependency_overrides[get_geocoder] = lambda: geocoder
    return geocoder


async def make_incident(client: httpx.AsyncClient, **body: object) -> int:
    r = await client.post(INC, json={"problem_type": "flat_tyre", **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def turn(client: httpx.AsyncClient, incident_id: int, locale: str = "en") -> httpx.Response:
    return await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": locale})


async def test_the_first_turn_stores_the_context_and_label(
    app: FastAPI, client: httpx.AsyncClient, provider: ScriptedProvider
) -> None:
    geocoder = use_geocoder(app, FakeGeocoder(nominatim_result()))
    incident_id = await make_incident(client, location=LOCATION)
    # Never at create.
    assert geocoder.calls == []

    r = await turn(client, incident_id, "pl")

    assert r.status_code == 201, r.text
    assert geocoder.calls == [(52.23, 21.01, "pl")]
    inputs = r.json()["inputs"]
    assert inputs["road_class"] == "motorway_expressway"
    assert inputs["settlement"] == "village"
    incident = (await client.get(f"{INC}/{incident_id}")).json()
    assert incident["location_label"] == "A2, Wola"
    prompt = provider.prompt_text()
    assert "road motorway_expressway, settlement village" in prompt
    assert "A2, Wola" not in prompt


async def test_a_failed_lookup_gives_unknown_and_the_turn_succeeds(
    app: FastAPI, client: httpx.AsyncClient, provider: ScriptedProvider
) -> None:
    use_geocoder(app, FakeGeocoder(None))
    incident_id = await make_incident(client, location=LOCATION)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["inputs"]["road_class"] == "unknown"
    assert r.json()["inputs"]["settlement"] == "unknown"
    assert (await client.get(f"{INC}/{incident_id}")).json()["location_label"] is None


async def test_no_location_makes_no_lookup(
    app: FastAPI, client: httpx.AsyncClient, provider: ScriptedProvider
) -> None:
    geocoder = use_geocoder(app, FakeGeocoder(nominatim_result()))
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201
    assert geocoder.calls == []
    assert r.json()["inputs"]["road_class"] == "unknown"


async def test_demo_mode_makes_no_lookup(app: FastAPI) -> None:
    # The conftest settings keep the default DEMO_MODE=true.
    assert app.state.geocoder is None
