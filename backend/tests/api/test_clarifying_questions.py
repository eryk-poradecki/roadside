"""Clarifying questions: ask turns, replies and the cap (ADR 0004, ADR 0005)."""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.deps import get_llm_provider
from app.integrations.llm.base import ProviderError
from app.main import create_app
from app.settings import Settings
from tests.fakes import Script, ScriptedProvider, answer_json, ask_json, blocking

INC = "/api/v1/incidents"

Install = Callable[..., ScriptedProvider]


@pytest.fixture
def install(app: FastAPI) -> Install:
    def run(*script: Script) -> ScriptedProvider:
        fake = ScriptedProvider(*script)
        app.dependency_overrides[get_llm_provider] = lambda: fake
        return fake

    return run


async def make_incident(client: httpx.AsyncClient, **body: object) -> int:
    r = await client.post(INC, json={"problem_type": "flat_tyre", **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def turn(
    client: httpx.AsyncClient, incident_id: int, reply: dict[str, Any] | None = None
) -> httpx.Response:
    body: dict[str, Any] = {"locale": "en"}
    if reply is not None:
        body["reply"] = reply
    return await client.post(f"{INC}/{incident_id}/ai-turns", json=body)


async def stored_turns(client: httpx.AsyncClient, incident_id: int) -> list[dict[str, Any]]:
    r = await client.get(f"{INC}/{incident_id}")
    assert r.status_code == 200
    turns: list[dict[str, Any]] = r.json()["ai_turns"]
    return turns


def kinds(turns: list[dict[str, Any]]) -> list[str]:
    return [t["kind"] for t in turns]


def allowed_kinds(fake: ScriptedProvider, call: int) -> list[str]:
    kind: list[str] = fake.requests[call].schema["properties"]["kind"]["enum"]
    return kind


# --- the ask turn ----------------------------------------------------------------------------


async def test_the_first_turn_may_ask(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(ask_json())
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["seq"] == 1
    assert body["kind"] == "question"
    assert body["urgent"] is False
    assert body["advice"] is None
    assert body["reply"] is None
    assert body["question"] == {
        "now": "Get everyone behind the barrier",
        "question": "Is the car on the hard shoulder?",
        "options": ["Yes, on the hard shoulder", "No, off the road"],
    }
    assert body["inputs"]["problem_type"] == "flat_tyre"
    assert allowed_kinds(fake, 0) == ["ask", "answer"]
    assert "Do not ask a clarifying question." not in fake.prompt_text()
    assert await stored_turns(client, incident_id) == [body]


@pytest.mark.parametrize(
    "options",
    [("Only one",), ("a", "b", "c", "d", "e"), ("a", "a")],
    ids=["one option", "five options", "a repeated option"],
)
async def test_a_question_needs_two_to_four_distinct_options(
    client: httpx.AsyncClient, install: Install, options: tuple[str, ...]
) -> None:
    fake = install(ask_json(options=options), answer_json())
    incident_id = await make_incident(client)

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "advice"
    assert len(fake.requests) == 2  # the repair call


async def test_an_urgent_turn_can_never_ask(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(ask_json(urgent=True), ask_json(urgent=True))
    incident_id = await make_incident(client, note="Smoke from the bonnet")

    r = await turn(client, incident_id)

    assert r.status_code == 502
    assert r.json()["reason"] == "invalid_output"
    assert "urgent" in fake.requests[1].messages[-1].text
    assert await stored_turns(client, incident_id) == []


# --- replies -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reply", "stored"),
    [
        ({"option": "No, off the road"}, {"option": "No, off the road", "text": None}),
        ({"text": "  In a car park  "}, {"option": None, "text": "In a car park"}),
    ],
    ids=["option", "text"],
)
async def test_a_reply_is_its_own_row_before_the_next_turn(
    client: httpx.AsyncClient,
    install: Install,
    reply: dict[str, Any],
    stored: dict[str, Any],
) -> None:
    fake = install(ask_json(), answer_json())
    incident_id = await make_incident(client)
    question = (await turn(client, incident_id)).json()

    r = await turn(client, incident_id, reply)

    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "advice"
    assert r.json()["seq"] == 3
    turns = await stored_turns(client, incident_id)
    assert kinds(turns) == ["question", "reply", "advice"]
    assert turns[0] == question
    row = turns[1]
    assert row["seq"] == 2
    assert row["reply"] == {**stored, "skip": False}
    # A reply is the driver's: no model provenance.
    for field in ("urgent", "question", "advice", "inputs", "locale", "provider", "model"):
        assert row[field] is None
    # The model reads the question and the reply in the next turn.
    prompt = fake.prompt_text(1)
    assert "Is the car on the hard shoulder?" in prompt
    assert (stored["option"] or stored["text"]) in prompt


async def test_an_option_must_be_one_of_the_questions_options(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, {"option": "Something made up"})

    assert r.status_code == 422
    assert r.json()["reason"] == "validation_error"
    assert r.json()["errors"][0]["field"] == "reply.option"
    assert len(fake.requests) == 1
    assert kinds(await stored_turns(client, incident_id)) == ["question"]


@pytest.mark.parametrize(
    "reply",
    [
        {},
        {"option": "No, off the road", "text": "x"},
        {"option": "No, off the road", "skip": True},
        {"text": "x", "skip": True},
        {"skip": False},
        {"text": "   "},
        {"text": "x" * 281},
        {"option": "No, off the road", "extra": 1},
    ],
    ids=[
        "nothing set",
        "option and text",
        "option and skip",
        "text and skip",
        "skip false",
        "blank text",
        "text too long",
        "an extra key",
    ],
)
async def test_a_reply_with_not_exactly_one_field_is_422(
    client: httpx.AsyncClient, install: Install, reply: dict[str, Any]
) -> None:
    fake = install(ask_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, reply)

    assert r.status_code == 422, r.text
    assert r.json()["reason"] == "validation_error"
    assert len(fake.requests) == 1
    assert kinds(await stored_turns(client, incident_id)) == ["question"]


async def test_text_may_be_as_long_as_the_note(client: httpx.AsyncClient, install: Install) -> None:
    install(ask_json(), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, {"text": "x" * 280})

    assert r.status_code == 201, r.text


async def test_a_reply_survives_a_failed_following_turn(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json(), ProviderError("down"), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    failed = await turn(client, incident_id, {"option": "No, off the road"})

    assert failed.status_code == 502
    assert failed.json()["reason"] == "provider_error"
    assert kinds(await stored_turns(client, incident_id)) == ["question", "reply"]

    # "Try again" posts no reply: the stored one is answered.
    again = await turn(client, incident_id)

    assert again.status_code == 201, again.text
    assert kinds(await stored_turns(client, incident_id)) == ["question", "reply", "advice"]
    assert "No, off the road" in fake.prompt_text(2)


# --- 409s ----------------------------------------------------------------------------------


async def test_a_reply_without_an_open_question_is_409(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install()
    incident_id = await make_incident(client)

    r = await turn(client, incident_id, {"skip": True})

    assert r.status_code == 409
    assert r.json()["reason"] == "no_open_question"
    assert fake.requests == []
    assert await stored_turns(client, incident_id) == []


async def test_a_second_reply_to_the_same_question_is_409(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(ask_json(), ProviderError("down"))
    incident_id = await make_incident(client)
    await turn(client, incident_id)
    assert (await turn(client, incident_id, {"text": "first"})).status_code == 502

    r = await turn(client, incident_id, {"text": "second"})

    assert r.status_code == 409
    assert r.json()["reason"] == "no_open_question"
    assert kinds(await stored_turns(client, incident_id)) == ["question", "reply"]


async def test_an_open_question_needs_a_reply(client: httpx.AsyncClient, install: Install) -> None:
    fake = install(ask_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id)

    assert r.status_code == 409
    assert r.json()["reason"] == "reply_required"
    assert len(fake.requests) == 1


async def test_a_reply_after_the_advice_is_advice_exists(
    client: httpx.AsyncClient, install: Install
) -> None:
    install(answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, {"skip": True})

    assert r.status_code == 409
    assert r.json()["reason"] == "advice_exists"


# --- the cap -------------------------------------------------------------------------------


async def test_after_two_questions_the_schema_is_narrowed_to_answer(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json(), ask_json(question="Which tyre?"), answer_json())
    incident_id = await make_incident(client)

    assert (await turn(client, incident_id)).json()["kind"] == "question"
    second = await turn(client, incident_id, {"option": "No, off the road"})
    assert second.json()["kind"] == "question"
    third = await turn(client, incident_id, {"text": "Front left"})

    assert third.json()["kind"] == "advice"
    assert [allowed_kinds(fake, n) for n in range(3)] == [
        ["ask", "answer"],
        ["ask", "answer"],
        ["answer"],
    ]
    assert "Do not ask a clarifying question." in fake.prompt_text(2)
    assert kinds(await stored_turns(client, incident_id)) == [
        "question",
        "reply",
        "question",
        "reply",
        "advice",
    ]


async def test_a_third_question_is_refused_and_repaired(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json(), ask_json(), ask_json(question="A third?"), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)
    await turn(client, incident_id, {"text": "a"})

    r = await turn(client, incident_id, {"text": "b"})

    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "advice"
    assert len(fake.requests) == 4
    assert "no more questions" in fake.requests[3].messages[-1].text


async def test_skip_narrows_the_schema_after_one_question(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json(), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    r = await turn(client, incident_id, {"skip": True})

    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "advice"
    assert allowed_kinds(fake, 1) == ["answer"]
    assert "Do not ask a clarifying question." in fake.prompt_text(1)
    skipped = (await stored_turns(client, incident_id))[1]
    assert skipped["reply"] == {"option": None, "text": None, "skip": True}
    assert "skipped" in fake.prompt_text(1).lower()


async def test_skip_stays_narrowed_after_a_failed_turn(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(ask_json(), ProviderError("down"), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)
    assert (await turn(client, incident_id, {"skip": True})).status_code == 502

    assert (await turn(client, incident_id)).status_code == 201

    assert allowed_kinds(fake, 2) == ["answer"]


async def test_the_inputs_snapshot_carries_no_reply_text(
    client: httpx.AsyncClient, install: Install
) -> None:
    # Replies are their own rows; the snapshot stays the ADR's fact list.
    install(ask_json(), answer_json())
    incident_id = await make_incident(client)
    await turn(client, incident_id)

    advice = (await turn(client, incident_id, {"text": "Behind the barrier now"})).json()

    assert "Behind the barrier now" not in json.dumps(advice["inputs"])


# --- two workers ---------------------------------------------------------------------------


async def test_another_worker_cannot_start_a_question_for_the_same_incident(
    settings: Settings,
) -> None:
    # Two app instances share the database and its per-incident file lock.
    release = asyncio.Event()
    migrate(settings.database_path)
    apps = [create_app(settings), create_app(settings)]
    fakes = [ScriptedProvider(blocking(release, ask_json())) for _ in apps]
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
        # Never two questions in a row.
        assert kinds(await stored_turns(clients[0], incident_id)) == ["question"]
    finally:
        for c in clients:
            await c.aclose()


def _returning(fake: ScriptedProvider) -> Callable[[], ScriptedProvider]:
    return lambda: fake
