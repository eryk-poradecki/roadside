"""The damage report sub-resource (ADR 0009, #59): drafted by one schema-constrained call,
rendered by the backend into a per-locale letter, edited and marked sent by the driver."""

import asyncio
import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI

from app.deps import get_geocoder, get_llm_provider
from app.integrations.llm.base import ProviderError, ProviderTimeoutError
from app.settings import Settings
from tests.fakes import (
    FakeGeocoder,
    Script,
    ScriptedProvider,
    answer_json,
    blocking,
    nominatim_result,
    report_json,
)

INC = "/api/v1/incidents"
V = "/api/v1/vehicles"
LOCATION = {"lat": 52.231234, "lon": 21.016789, "accuracy_m": 9.5}
VEHICLE = {
    "name": "Family Golf",
    "make_model": "VW Golf VII",
    "year": 2016,
    "fuel_type": "diesel",
    "transmission": "manual",
    "spare_wheel": "space_saver",
    "registration": "WX 1234K",
    "assistance_insurer": "PZU",
    "assistance_phone": "+48 600 700 800",
    "policy_number": "POL-998877",
}

Install = Callable[..., ScriptedProvider]


@pytest.fixture
def install(app: FastAPI) -> Install:
    def run(*script: Script) -> ScriptedProvider:
        fake = ScriptedProvider(*script)
        app.dependency_overrides[get_llm_provider] = lambda: fake
        return fake

    return run


async def make_incident(client: httpx.AsyncClient, **body: object) -> int:
    r = await client.post(INC, json={"problem_type": "pothole_damage", **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


def report_url(incident_id: int) -> str:
    return f"{INC}/{incident_id}/damage-report"


async def generate(client: httpx.AsyncClient, incident_id: int, **body: object) -> httpx.Response:
    return await client.post(report_url(incident_id), json=body)


def local_time(created_at: str) -> str:
    when = datetime.fromisoformat(created_at).astimezone(ZoneInfo("Europe/Warsaw"))
    return when.strftime("%d.%m.%Y %H:%M")


# --- generating ---------------------------------------------------------------------------


async def test_a_pothole_incident_gets_a_polish_draft_by_default(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client)

    r = await generate(client, incident_id)

    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"status", "locale", "body", "created_at", "updated_at"}
    assert body["status"] == "draft"
    assert body["locale"] == "pl"
    assert body["created_at"] == body["updated_at"]
    assert body["created_at"].endswith("Z")
    letter = body["body"]
    assert "While driving at about 50 km/h I hit a deep pothole" in letter
    assert "The front right tyre is cut and the rim is bent." in letter
    for placeholder in (
        "[Adresat: zarządca drogi]",
        "[Imię i nazwisko]",
        "[Adres]",
        "[Telefon]",
        "[Numer konta bankowego]",
    ):
        assert placeholder in letter
    assert "Answer language: Polish" in fake.prompt_text()
    assert fake.requests[0].schema_name == "damage_report"
    assert (await client.get(report_url(incident_id))).json() == body


async def test_an_english_draft_uses_the_english_template(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client)

    r = await generate(client, incident_id, locale="en")

    assert r.status_code == 201, r.text
    letter = r.json()["body"]
    assert r.json()["locale"] == "en"
    for placeholder in (
        "[Addressee: road manager]",
        "[Your name]",
        "[Your address]",
        "[Your phone]",
        "[Your bank account]",
    ):
        assert placeholder in letter
    assert "Answer language: English" in fake.prompt_text()


async def test_the_body_holds_the_incident_facts(
    app: FastAPI, client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    app.dependency_overrides[get_geocoder] = lambda: FakeGeocoder(
        nominatim_result(highway="primary", road="Puławska", locality=("city", "Piaseczno"))
    )
    vehicle = (await client.post(V, json=VEHICLE)).json()
    created = await client.post(
        INC,
        json={"problem_type": "pothole_damage", "vehicle_id": vehicle["id"], "location": LOCATION},
    )
    incident_id = created.json()["id"]
    for _ in range(2):
        await client.post(
            f"{INC}/{incident_id}/photos", json={"sample_id": "pothole"}
        )  # demo mode: samples only

    letter = (await generate(client, incident_id, locale="en")).json()["body"]

    assert local_time(created.json()["created_at"]) in letter
    assert "Puławska, Piaseczno" in letter
    assert "52.23123, 21.01679" in letter
    assert "VW Golf VII (2016)" in letter
    assert "WX 1234K" in letter
    assert "Photos attached: 2" in letter


async def test_missing_facts_become_placeholders(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)

    letter = (await generate(client, incident_id, locale="en")).json()["body"]

    assert "[Place of the incident]" in letter
    assert "[Vehicle make and model]" in letter
    assert "[Registration number]" in letter
    assert "Photos attached: 0" in letter


async def test_registration_is_in_the_body_but_never_in_the_prompt(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(report_json())
    vehicle = (await client.post(V, json=VEHICLE)).json()
    incident_id = await make_incident(
        client, vehicle_id=vehicle["id"], location=LOCATION, note="Deep hole on the right"
    )

    letter = (await generate(client, incident_id)).json()["body"]

    assert "WX 1234K" in letter
    prompt = fake.prompt_text()
    for secret in ("WX 1234K", "WX1234K", "600 700 800", "POL-998877", "52.23", "21.01"):
        assert secret not in prompt
    # The same fact set as an AI turn.
    for fact in ("VW Golf VII", "2016", "diesel", "Deep hole on the right", "pothole_damage"):
        assert fact in prompt


@pytest.mark.parametrize(
    "claimant",
    [{"name": "Jan Kowalski"}, {"bank_account": "PL61109010140000071219812874"}],
)
async def test_claimant_details_are_refused(
    client: httpx.AsyncClient, install: Install, claimant: dict[str, str]
) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client)

    r = await generate(client, incident_id, locale="pl", **claimant)

    assert r.status_code == 422
    assert fake.requests == []


async def test_the_advice_cause_is_in_the_prompt(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(cause="A tyre cut by the pothole's sharp edge"), report_json())
    incident_id = await make_incident(client)
    assert (await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": "en"})).is_success

    await generate(client, incident_id)

    assert "A tyre cut by the pothole's sharp edge" in fake.prompt_text(1)


async def test_the_schema_sent_is_flat(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client)

    await generate(client, incident_id)

    schema = fake.requests[0].schema
    assert schema["required"] == ["description", "damage_summary"]
    text = json.dumps(schema)
    for keyword in ("oneOf", "anyOf", "minItems", "maxItems", "maxLength", "minLength"):
        assert keyword not in text


async def test_only_a_pothole_incident_gets_a_report(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client, problem_type="flat_tyre")

    r = await generate(client, incident_id)

    assert r.status_code == 422
    assert r.json()["reason"] == "not_pothole_damage"
    assert fake.requests == []


async def test_changing_the_type_away_keeps_the_report(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)
    await generate(client, incident_id)

    r = await client.patch(f"{INC}/{incident_id}", json={"problem_type": "flat_tyre"})

    assert r.status_code == 200
    assert (await client.get(report_url(incident_id))).status_code == 200


async def test_a_second_report_is_409(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(report_json())
    incident_id = await make_incident(client)
    first = (await generate(client, incident_id)).json()

    r = await generate(client, incident_id)

    assert r.status_code == 409
    assert r.json()["reason"] == "damage_report_exists"
    assert len(fake.requests) == 1
    assert (await client.get(report_url(incident_id))).json() == first


async def test_replace_overwrites_and_resets_to_draft(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json(), report_json(damage_summary="Both right wheels are damaged."))
    incident_id = await make_incident(client)
    first = (await generate(client, incident_id)).json()
    await client.patch(report_url(incident_id), json={"status": "sent"})

    r = await generate(client, incident_id, locale="en", replace=True)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["locale"] == "en"
    assert "Both right wheels are damaged." in body["body"]
    assert body["created_at"] == first["created_at"]
    assert body["updated_at"] >= first["updated_at"]


async def test_replace_without_a_report_creates_one(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)

    r = await generate(client, incident_id, replace=True)

    assert r.status_code == 201


async def test_an_unknown_incident_is_404(client: httpx.AsyncClient, install: Install) -> None:
    install(report_json())

    assert (await generate(client, 999)).status_code == 404
    assert (await client.get(report_url(999))).status_code == 404


async def test_no_report_yet_is_404(client: httpx.AsyncClient, install: Install) -> None:
    incident_id = await make_incident(client)

    r = await client.get(report_url(incident_id))

    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"


# --- failures store nothing ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "status", "reason"),
    [
        (ProviderError("down"), 502, "provider_error"),
        (ProviderTimeoutError("slow"), 504, "timeout"),
    ],
)
async def test_a_failed_generation_stores_nothing(
    client: httpx.AsyncClient,
    install: Install,
    error: Exception,
    status: int,
    reason: str,
) -> None:
    install(error)
    incident_id = await make_incident(client)

    r = await generate(client, incident_id)

    assert r.status_code == status
    assert r.json()["reason"] == reason
    assert (await client.get(report_url(incident_id))).status_code == 404


async def test_a_failed_replace_keeps_the_old_report(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json(), ProviderError("down"))
    incident_id = await make_incident(client)
    first = (await generate(client, incident_id)).json()

    assert (await generate(client, incident_id, replace=True)).status_code == 502
    assert (await client.get(report_url(incident_id))).json() == first


async def test_invalid_output_gets_one_repair_call(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install('{"description": ""}', report_json())
    incident_id = await make_incident(client)

    r = await generate(client, incident_id)

    assert r.status_code == 201
    assert len(fake.requests) == 2
    assert "Your previous output was invalid" in fake.requests[1].messages[-1].text


async def test_a_second_invalid_output_is_502(client: httpx.AsyncClient, install: Install) -> None:
    install("not json", '{"description": "x"}')
    incident_id = await make_incident(client)

    r = await generate(client, incident_id)

    assert r.status_code == 502
    assert r.json()["reason"] == "invalid_output"
    assert (await client.get(report_url(incident_id))).status_code == 404


async def test_one_generation_at_a_time_shared_with_ai_turns(
    client: httpx.AsyncClient, install: Install
) -> None:
    release = asyncio.Event()
    fake = install(blocking(release, report_json()))
    incident_id = await make_incident(client)

    pending = asyncio.create_task(generate(client, incident_id))
    await fake.called.wait()

    again = await generate(client, incident_id)
    turn = await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": "en"})
    for r in (again, turn):
        assert r.status_code == 409
        assert r.json()["reason"] == "turn_in_progress"

    release.set()
    assert (await pending).status_code == 201


async def test_an_incident_deleted_during_generation_is_404(
    client: httpx.AsyncClient, install: Install
) -> None:
    release = asyncio.Event()
    fake = install(blocking(release, report_json()))
    incident_id = await make_incident(client)

    pending = asyncio.create_task(generate(client, incident_id))
    await fake.called.wait()
    assert (await client.delete(f"{INC}/{incident_id}")).status_code == 204
    release.set()

    assert (await pending).status_code == 404


# --- editing, marking sent, deleting -------------------------------------------------------


async def test_the_driver_edits_the_body_and_marks_it_sent(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)
    created = (await generate(client, incident_id)).json()

    edited = await client.patch(report_url(incident_id), json={"body": "My own letter"})
    sent = await client.patch(report_url(incident_id), json={"status": "sent"})

    assert edited.status_code == 200
    assert edited.json()["body"] == "My own letter"
    assert sent.json()["status"] == "sent"
    assert sent.json()["body"] == "My own letter"
    assert sent.json()["updated_at"] >= created["updated_at"]
    assert sent.json()["created_at"] == created["created_at"]
    back = await client.patch(report_url(incident_id), json={"status": "draft"})
    assert back.json()["status"] == "draft"


@pytest.mark.parametrize(
    "patch",
    [
        {"status": None},
        {"body": None},
        {"status": "archived"},
        {"body": "   "},
        {"body": "x" * 10_001},
        {"locale": "en"},
    ],
)
async def test_a_bad_patch_is_422(
    client: httpx.AsyncClient, install: Install, patch: dict[str, object]
) -> None:
    install(report_json())
    incident_id = await make_incident(client)
    await generate(client, incident_id)

    r = await client.patch(report_url(incident_id), json=patch)

    assert r.status_code == 422


async def test_patching_a_missing_report_is_404(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client)

    r = await client.patch(report_url(incident_id), json={"status": "sent"})

    assert r.status_code == 404


async def test_delete_removes_the_report(client: httpx.AsyncClient, install: Install) -> None:
    install(report_json(), report_json())
    incident_id = await make_incident(client)
    await generate(client, incident_id)

    assert (await client.delete(report_url(incident_id))).status_code == 204
    assert (await client.get(report_url(incident_id))).status_code == 404
    assert (await client.delete(report_url(incident_id))).status_code == 404
    # A new one can be generated afterwards.
    assert (await generate(client, incident_id)).status_code == 201


async def test_deleting_the_incident_deletes_the_report(
    settings: Settings, client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)
    await generate(client, incident_id)

    assert (await client.delete(f"{INC}/{incident_id}")).status_code == 204

    with closing(sqlite3.connect(settings.database_path)) as conn:
        assert conn.execute("SELECT count(*) FROM damage_reports").fetchone() == (0,)


# --- History -----------------------------------------------------------------------------------


async def test_history_shows_the_report_status(client: httpx.AsyncClient, install: Install) -> None:
    install(report_json(), report_json())
    none = await make_incident(client)
    draft = await make_incident(client)
    sent = await make_incident(client)
    await generate(client, draft)
    await generate(client, sent)
    await client.patch(report_url(sent), json={"status": "sent"})

    items = (await client.get(INC)).json()["items"]

    status = {i["id"]: i["damage_report_status"] for i in items}
    assert status == {none: None, draft: "draft", sent: "sent"}


async def test_an_incident_retyped_during_generation_is_422(
    client: httpx.AsyncClient, install: Install
) -> None:
    release = asyncio.Event()
    fake = install(blocking(release, report_json()))
    incident_id = await make_incident(client)

    pending = asyncio.create_task(generate(client, incident_id))
    await fake.called.wait()
    r = await client.patch(f"{INC}/{incident_id}", json={"problem_type": "flat_tyre"})
    assert r.status_code == 200
    release.set()

    r = await pending
    assert r.status_code == 422
    assert r.json()["reason"] == "not_pothole_damage"
    assert (await client.get(report_url(incident_id))).status_code == 404


async def test_the_incident_shows_its_report_status(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(report_json())
    incident_id = await make_incident(client)
    assert (await client.get(f"{INC}/{incident_id}")).json()["damage_report_status"] is None

    await generate(client, incident_id)
    assert (await client.get(f"{INC}/{incident_id}")).json()["damage_report_status"] == "draft"

    await client.patch(report_url(incident_id), json={"status": "sent"})
    assert (await client.get(f"{INC}/{incident_id}")).json()["damage_report_status"] == "sent"


async def test_a_live_model_drafts_a_pothole_report_in_either_language(
    client: httpx.AsyncClient, install: Install
) -> None:
    install()
    pothole = await make_incident(client, problem_type="pothole_damage")
    tyre = await make_incident(client, problem_type="flat_tyre")

    assert (await client.get(f"{report_url(pothole)}/locales")).json() == {"locales": ["pl", "en"]}
    # The draft would be 422 `not_pothole_damage`.
    assert (await client.get(f"{report_url(tyre)}/locales")).json() == {"locales": []}
    assert (await client.get(f"{report_url(9999)}/locales")).status_code == 404
