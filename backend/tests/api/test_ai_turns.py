import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.deps import get_llm_provider
from app.integrations.llm.base import ProviderError, ProviderTimeoutError
from app.main import create_app
from app.settings import Settings
from tests.conftest import ORIGIN
from tests.fakes import Script, ScriptedProvider, answer_json, blocking, sleeping

INC = "/api/v1/incidents"
V = "/api/v1/vehicles"

Install = Callable[..., ScriptedProvider]


@pytest.fixture
def install(app: FastAPI) -> Install:
    """Swap the LLM provider for a scripted fake through a dependency override."""

    def run(*script: Script) -> ScriptedProvider:
        fake = ScriptedProvider(*script)
        app.dependency_overrides[get_llm_provider] = lambda: fake
        return fake

    return run


async def make_incident(client: httpx.AsyncClient, **body: object) -> int:
    r = await client.post(INC, json={"problem_type": "flat_tyre", **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def turn(client: httpx.AsyncClient, incident_id: int, locale: str = "en") -> httpx.Response:
    return await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": locale})


async def stored_turns(client: httpx.AsyncClient, incident_id: int) -> list[dict[str, object]]:
    r = await client.get(f"{INC}/{incident_id}")
    assert r.status_code == 200
    turns: list[dict[str, object]] = r.json()["ai_turns"]
    return turns


# --- the advice --------------------------------------------------------------------------


async def test_a_turn_returns_the_advice_and_stores_it(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client)

    r = await turn(client, incident_id, "pl")

    assert r.status_code == 201, r.text
    assert "location" not in r.headers
    body = r.json()
    assert body["seq"] == 1
    assert body["kind"] == "advice"
    assert body["urgent"] is False
    assert body["locale"] == "pl"
    assert body["advice"] == {
        "cause": "A puncture in the rear left tyre",
        "confidence": "likely",
        "alternatives": ["A damaged valve"],
        "steps": ["Get everyone behind the barrier first", "Call your assistance"],
        "escalate_if": ["You smell fuel"],
        "photo_observation": None,
        "extra_categories": ["repair"],
    }
    assert body["prompt_version"] == "v3"
    assert body["provider"] == "fake"
    assert body["model"] == "fake-model-1"
    assert body["created_at"].endswith("Z")
    assert await stored_turns(client, incident_id) == [body]
    assert len(fake.requests) == 1


async def test_the_schema_sent_is_flat(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client)

    await turn(client, incident_id)

    schema = fake.requests[0].schema
    assert schema["properties"]["kind"]["enum"] == ["ask", "answer"]
    assert schema["properties"]["ask"]["type"] == ["object", "null"]
    text = json.dumps(schema)
    for keyword in ("oneOf", "anyOf", "minItems", "maxItems", "maxLength", "minLength"):
        assert keyword not in text
    assert schema["properties"]["answer"]["type"] == ["object", "null"]


async def test_the_answer_language_is_the_ui_locale(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(), answer_json())
    a = await make_incident(client, note="Złapałem gumę")
    b = await make_incident(client, note="Got a flat")

    await turn(client, a, "en")
    await turn(client, b, "pl")

    assert "Answer language: English" in fake.prompt_text(0)
    assert "Answer language: Polish" in fake.prompt_text(1)


@pytest.mark.parametrize("body", [{}, {"locale": "de"}, {"locale": "pl", "extra": 1}])
async def test_a_bad_body_is_422(
    client: httpx.AsyncClient, install: Install, body: dict[str, object]
) -> None:
    fake = install()
    incident_id = await make_incident(client)

    r = await client.post(f"{INC}/{incident_id}/ai-turns", json=body)

    assert r.status_code == 422
    assert r.json()["reason"] == "validation_error"
    assert fake.requests == []


async def test_unknown_incident_is_404(client: httpx.AsyncClient, install: Install) -> None:
    fake = install()
    r = await turn(client, 999)
    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"
    assert fake.requests == []


async def test_photo_observation_is_dropped_when_no_photo_was_shown(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(answer_json(photo_observation="A nail in the tread"))
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.json()["advice"]["photo_observation"] is None


async def test_an_urgent_answer_with_112_first_is_accepted(
    client: httpx.AsyncClient, install: Install
) -> None:
    steps = ["Call 112 now", "Get everyone behind the barrier"]
    install(answer_json(urgent=True, steps=steps))
    incident_id = await make_incident(client, note="Smoke from the bonnet")

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["urgent"] is True
    assert r.json()["advice"]["steps"] == steps


# --- validation and the repair call ----------------------------------------------------------


INVALID_OUTPUTS = {
    "not json": "Sure! Here are some steps.",
    "one step": answer_json(steps=["Only one"]),
    "seven steps": answer_json(steps=[f"Step {n}" for n in range(7)]),
    "three alternatives": answer_json(alternatives=["a", "b", "c"]),
    "no escalate": answer_json(escalate_if=[]),
    "bad confidence": answer_json(confidence="certain"),
    "towing category": answer_json(extra_categories=["towing"]),
    "a place field": json.dumps({**json.loads(answer_json()), "places": [{"name": "Jan's Tyres"}]}),
    "a place inside the answer": answer_json(nearest_shop="Jan's Tyres, ul. Polna 1"),
    "urgent without 112 first": answer_json(urgent=True),
    "both blocks": json.dumps(
        {
            **json.loads(answer_json()),
            "ask": {"now": "x", "question": "y", "options": ["a", "b"]},
        }
    ),
    "a step too long": answer_json(steps=["x" * 281, "ok"]),
}


@pytest.mark.parametrize("raw", INVALID_OUTPUTS.values(), ids=INVALID_OUTPUTS.keys())
async def test_invalid_output_gets_one_repair_call(
    client: httpx.AsyncClient, install: Install, raw: str
) -> None:
    fake = install(raw, answer_json())
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert len(fake.requests) == 2
    repair = fake.requests[1].messages
    # The repair call replays the conversation, the bad output and what was wrong with it.
    assert repair[: len(fake.requests[0].messages)] == fake.requests[0].messages
    assert repair[-2].role == "assistant"
    assert repair[-2].text == raw
    assert repair[-1].role == "user"
    assert "invalid" in repair[-1].text.lower()
    assert fake.requests[1].schema == fake.requests[0].schema


async def test_a_second_invalid_output_fails_the_turn_and_stores_nothing(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install("nope", answer_json(steps=["one"]))
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 502
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["reason"] == "invalid_output"
    assert len(fake.requests) == 2
    assert await stored_turns(client, incident_id) == []


@pytest.mark.parametrize("opener", ["```json", "```JSON", "```"])
async def test_a_fenced_json_output_is_accepted(
    client: httpx.AsyncClient, install: Install, opener: str
) -> None:
    fake = install(f"{opener}\n{answer_json()}\n```")
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert len(fake.requests) == 1


# --- provider failures and the budget ------------------------------------------------------


async def test_a_provider_error_is_502_and_stores_nothing(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(ProviderError("HTTP 500"))
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 502
    assert r.json()["reason"] == "provider_error"
    assert await stored_turns(client, incident_id) == []


async def test_a_provider_timeout_is_504(client: httpx.AsyncClient, install: Install) -> None:
    install(ProviderTimeoutError("read timeout"))
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 504
    assert r.json()["reason"] == "timeout"


@pytest.fixture
def tight_budget_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_path=tmp_path / "budget.db",
        upload_dir=tmp_path / "uploads",
        frontend_origins=[ORIGIN],
        llm_turn_budget_s=0.2,
    )
    migrate(settings.database_path)
    return create_app(settings)


async def test_the_turn_budget_covers_the_repair_call(tight_budget_app: FastAPI) -> None:
    # Each call fits the budget alone; the first plus the repair call does not.
    fake = ScriptedProvider(sleeping(0.12, "not json"), sleeping(0.12, answer_json()))
    tight_budget_app.dependency_overrides[get_llm_provider] = lambda: fake
    transport = httpx.ASGITransport(app=tight_budget_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        incident_id = await make_incident(client)

        r = await turn(client, incident_id)

        assert r.status_code == 504
        assert r.json()["reason"] == "timeout"
        assert len(fake.requests) == 2
        assert await stored_turns(client, incident_id) == []

        # The lock was released: "Try again" works.
        fake.script.append(answer_json())
        assert (await turn(client, incident_id)).status_code == 201


# --- conflicts -----------------------------------------------------------------------------


async def test_advice_closes_the_answer(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client)
    assert (await turn(client, incident_id)).status_code == 201

    r = await turn(client, incident_id)

    assert r.status_code == 409
    assert r.json()["reason"] == "advice_exists"
    assert len(fake.requests) == 1
    assert len(await stored_turns(client, incident_id)) == 1


async def test_one_turn_at_a_time_per_incident(client: httpx.AsyncClient, install: Install) -> None:
    release = asyncio.Event()
    fake = install(blocking(release, answer_json()), answer_json())
    busy = await make_incident(client)
    other = await make_incident(client)

    first = asyncio.create_task(turn(client, busy))
    await fake.called.wait()

    second = await turn(client, busy)
    assert second.status_code == 409
    assert second.json()["reason"] == "turn_in_progress"
    # Another incident is not blocked.
    assert (await turn(client, other)).status_code == 201

    release.set()
    assert (await first).status_code == 201
    assert len(fake.requests) == 2


async def test_a_failed_turn_releases_the_lock(client: httpx.AsyncClient, install: Install) -> None:
    install(ProviderError("down"), answer_json())
    incident_id = await make_incident(client)

    assert (await turn(client, incident_id)).status_code == 502
    assert (await turn(client, incident_id)).status_code == 201


async def test_an_incident_deleted_during_the_turn_is_404(
    client: httpx.AsyncClient, install: Install
) -> None:
    release = asyncio.Event()
    fake = install(blocking(release, answer_json()))
    incident_id = await make_incident(client)

    pending = asyncio.create_task(turn(client, incident_id))
    await fake.called.wait()
    assert (await client.delete(f"{INC}/{incident_id}")).status_code == 204
    release.set()

    r = await pending
    assert r.status_code == 404


# --- what the model is told ----------------------------------------------------------------

PRIVATE_VEHICLE = {
    "name": "Family Golf",
    "make_model": "VW Golf VII",
    "year": 2016,
    "fuel_type": "diesel",
    "transmission": "manual",
    "tyre_size": "205/55 R16",
    "spare_wheel": "space_saver",
    "wheel_locks": True,
    "lock_key_location": "glovebox",
    "registration": "WX 1234K",
    "assistance_insurer": "PZU",
    "assistance_phone": "+48 600 700 800",
    "policy_number": "POL-998877",
}
LOCATION = {"lat": 52.231234, "lon": 21.016789, "accuracy_m": 9.5}


async def test_private_data_never_reaches_the_model(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    vehicle = (await client.post(V, json=PRIVATE_VEHICLE)).json()
    incident_id = await make_incident(
        client, vehicle_id=vehicle["id"], note="Rear left", location=LOCATION
    )

    assert (await turn(client, incident_id)).status_code == 201

    prompt = fake.prompt_text()
    for secret in ("WX 1234K", "WX1234K", "600 700 800", "600700800", "POL-998877"):
        assert secret not in prompt
    for coordinate in ("52.23", "21.01", "52,23", "21,01"):
        assert coordinate not in prompt
    # What the model may see, it does see.
    for fact in ("Family Golf", "VW Golf VII", "2016", "diesel", "manual", "205/55 R16"):
        assert fact in prompt
    assert "space_saver" in prompt
    assert "glovebox" in prompt
    assert "has assistance, insurer PZU" in prompt
    assert "Rear left" in prompt


async def test_an_insurer_without_a_phone_is_not_assistance(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    vehicle = (await client.post(V, json={"name": "Golf", "assistance_insurer": "Warta"})).json()
    incident_id = await make_incident(client, vehicle_id=vehicle["id"])

    await turn(client, incident_id)

    user = fake.requests[0].messages[1].text
    assert "- Assistance insurance: unknown" in user
    assert "Warta" not in fake.prompt_text()


async def test_empty_vehicle_facts_are_unknown_never_none(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    vehicle = (await client.post(V, json={"name": "Golf"})).json()
    incident_id = await make_incident(client, vehicle_id=vehicle["id"])

    await turn(client, incident_id)

    block = fake.requests[0].messages[-1].text
    assert "- Spare wheel: unknown" in block
    assert "- Fuel type: unknown" in block
    assert "- Wheel locks: unknown" in block
    assert "- Spare wheel: none" not in block


async def test_lpg_reads_as_a_petrol_engine_with_an_lpg_installation(
    client: httpx.AsyncClient, install: Install
) -> None:
    """#107: LPG is fitted to petrol engines; a bare "lpg" reads as if it were the only fuel."""
    fake = install(answer_json())
    vehicle = (await client.post(V, json={"name": "Astra", "fuel_type": "lpg"})).json()
    incident_id = await make_incident(client, vehicle_id=vehicle["id"])

    await turn(client, incident_id)

    block = fake.requests[0].messages[-1].text
    assert "- Fuel type: petrol engine with an LPG installation" in block


async def test_no_vehicle_says_so(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client)

    await turn(client, incident_id)

    assert "No vehicle details were given." in fake.prompt_text()


async def test_the_prompt_carries_the_safety_rules(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client)

    await turn(client, incident_id)

    system = fake.requests[0].messages[0]
    assert system.role == "system"
    text = system.text
    invariants = [
        "Hazard lights on as soon as the car stops.",
        "A reflective vest on, if the driver has one.",
        "Everyone gets out and stands behind the barrier",
        "The warning triangle goes behind the car",
        "Never change a tyre, jump-start, repair or push the car next to moving traffic",
        "An electric car is never towed on its wheels.",
        "Injury, smoke, fire, a fuel leak or a car standing in a live lane: call 112.",
    ]
    for invariant in invariants:
        assert invariant in text
    assert "Always lead with the single most important safety action" in text
    assert "never repeat the checklist as a list" in text
    assert "Poland" in text
    assert "112" in text
    assert "Never name a business" in text
    assert "Nearby panel" in text
    assert "Ask only when the driver's reply would change the first steps" in text
    assert "When the situation is parked" in text


async def test_the_prompt_points_to_nearby_only_for_its_four_categories(
    client: httpx.AsyncClient, install: Install
) -> None:
    """Nearby has no towing (ADR 0004, #106): a step must not promise a tow truck there."""
    fake = install(answer_json())
    incident_id = await make_incident(client)

    await turn(client, incident_id)

    text = fake.requests[0].messages[0].text
    assert (
        "exactly four categories: tyre shops, fuel stations, charging stations and car repair"
        in text
    )
    assert "wulkanizacja, stacja paliw, stacja ładowania, warsztat samochodowy" in text
    assert (
        "Never point to Nearby for towing, roadside assistance, police, hospitals"
        " or anything else" in text
    )
    assert "For a tow, tell the driver to call roadside assistance" in text


async def test_the_situation_is_in_the_fact_block_and_on_the_road_by_default(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(), answer_json())
    on_road = await make_incident(client)
    parked = await make_incident(client, situation="parked")

    first = (await turn(client, on_road)).json()
    second = (await turn(client, parked)).json()

    assert "Situation: on the road" in fake.requests[0].messages[1].text
    assert "Situation: parked off the road" in fake.requests[1].messages[1].text
    assert first["inputs"]["situation"] == "on_road"
    assert second["inputs"]["situation"] == "parked"


# --- the inputs snapshot -------------------------------------------------------------------


async def test_the_inputs_snapshot_is_stored_and_survives_later_edits(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(answer_json())
    vehicle = (await client.post(V, json=PRIVATE_VEHICLE)).json()
    incident_id = await make_incident(
        client, vehicle_id=vehicle["id"], note="Rear left", location=LOCATION
    )
    advice = (await turn(client, incident_id)).json()

    inputs = advice["inputs"]
    assert inputs["problem_type"] == "flat_tyre"
    assert inputs["note"] == "Rear left"
    assert inputs["vehicle"]["name"] == "Family Golf"
    assert inputs["vehicle"]["spare_wheel"] == "space_saver"
    assert inputs["vehicle"]["has_assistance"] is True
    assert inputs["vehicle"]["assistance_insurer"] == "PZU"
    assert inputs["road_class"] == "unknown"
    assert inputs["settlement"] == "unknown"
    assert inputs["situation"] == "on_road"
    assert inputs["photo_ids_seen"] == []
    assert inputs["photos_not_sent"] == 0
    assert isinstance(inputs["dark"], bool)
    assert inputs["local_time"][:4] == advice["created_at"][:4]
    # The snapshot never holds what the model may not see.
    dumped = json.dumps(inputs)
    for secret in ("WX 1234K", "600 700 800", "POL-998877", "52.23", "21.01"):
        assert secret not in dumped

    edited_vehicle = {**PRIVATE_VEHICLE, "name": "Renamed", "spare_wheel": "none"}
    assert (await client.put(f"{V}/{vehicle['id']}", json=edited_vehicle)).status_code == 200
    patch = {"problem_type": "other", "note": "Changed my mind", "vehicle_id": None}
    assert (await client.patch(f"{INC}/{incident_id}", json=patch)).status_code == 200
    assert (await client.delete(f"{V}/{vehicle['id']}")).status_code == 204

    assert await stored_turns(client, incident_id) == [advice]


async def test_local_time_is_polish_time(client: httpx.AsyncClient, install: Install) -> None:
    install(answer_json())
    incident_id = await make_incident(client)

    inputs = (await turn(client, incident_id)).json()["inputs"]

    # Europe/Warsaw is UTC+1 in winter and UTC+2 in summer.
    assert inputs["local_time"][-6:] in {"+01:00", "+02:00"}


# --- logging -------------------------------------------------------------------------------


async def test_nothing_sensitive_is_logged_at_info(
    client: httpx.AsyncClient, install: Install, caplog: pytest.LogCaptureFixture
) -> None:
    install("not json", answer_json())
    vehicle = (await client.post(V, json=PRIVATE_VEHICLE)).json()
    incident_id = await make_incident(
        client, vehicle_id=vehicle["id"], note="Secret note text", location=LOCATION
    )

    with caplog.at_level(logging.INFO):
        assert (await turn(client, incident_id)).status_code == 201

    logged = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "fake-model-1" in logged  # a turn logs provider, model and outcome
    for secret in ("Secret note text", "52.23", "21.01", "WX 1234K", "Hazard lights", "PZU"):
        assert secret not in logged


def _returning(fake: ScriptedProvider) -> Callable[[], ScriptedProvider]:
    # A closure with no parameters: FastAPI would read a default argument as a query param.
    return lambda: fake


async def test_another_worker_cannot_start_a_turn_for_the_same_incident(settings: Settings) -> None:
    # Two app instances share the database and its per-incident file lock.
    release = asyncio.Event()
    migrate(settings.database_path)
    apps = [create_app(settings), create_app(settings)]
    fakes = [ScriptedProvider(blocking(release, answer_json())) for _ in apps]
    for worker, fake in zip(apps, fakes, strict=True):
        worker.dependency_overrides[get_llm_provider] = _returning(fake)
    clients = [
        httpx.AsyncClient(transport=httpx.ASGITransport(app=a), base_url="http://test")
        for a in apps
    ]
    try:
        incident_id = await make_incident(clients[0])
        pending = asyncio.create_task(turn(clients[0], incident_id))
        try:
            await asyncio.wait_for(fakes[0].called.wait(), timeout=5)
            rejected = await turn(clients[1], incident_id)
            assert rejected.status_code == 409
            assert rejected.json()["reason"] == "turn_in_progress"
            assert not fakes[1].called.is_set()
        finally:
            release.set()
            assert (await pending).status_code == 201
        assert len(await stored_turns(clients[0], incident_id)) == 1
    finally:
        for c in clients:
            await c.aclose()


@pytest.mark.parametrize(
    ("fuel_type", "problem_type", "mentions_lpg"),
    [
        ("lpg", "out_of_fuel", True),
        ("lpg", "other", True),
        ("lpg", "flat_tyre", False),
        ("petrol", "out_of_fuel", False),
        (None, "other", False),
    ],
)
async def test_lpg_switching_is_mentioned_only_for_an_lpg_car_that_ran_dry_or_wont_start(
    client: httpx.AsyncClient,
    install: Install,
    fuel_type: str | None,
    problem_type: str,
    mentions_lpg: bool,
) -> None:
    """#90: null fuel type is unknown, so it never gets the LPG line (ADR 0003)."""
    fake = install(answer_json())
    vehicle = (await client.post(V, json={"name": "Golf", "fuel_type": fuel_type})).json()
    incident_id = await make_incident(client, vehicle_id=vehicle["id"], problem_type=problem_type)

    await turn(client, incident_id)

    assert ("most LPG systems switch to petrol" in fake.prompt_text()) is mentions_lpg


async def test_no_vehicle_never_mentions_lpg(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(answer_json())
    incident_id = await make_incident(client, problem_type="out_of_fuel")

    await turn(client, incident_id)

    assert "LPG" not in fake.prompt_text()
