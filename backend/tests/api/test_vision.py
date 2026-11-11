"""The model sees the incident's photos when the provider can (#79, ADR 0002 and 0004)."""

import base64
import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from io import BytesIO

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from app.deps import get_llm_provider
from app.settings import Settings
from tests.fakes import ScriptedProvider, answer_json

INC = "/api/v1/incidents"

Install = Callable[..., ScriptedProvider]


@pytest.fixture
def install(app: FastAPI) -> Install:
    def run(*script: str, vision: bool = True, max_images: int = 3) -> ScriptedProvider:
        fake = ScriptedProvider(*script, vision=vision, max_images=max_images)
        app.dependency_overrides[get_llm_provider] = lambda: fake
        return fake

    return run


async def incident_with_samples(client: httpx.AsyncClient, *samples: str) -> tuple[int, list[int]]:
    r = await client.post(INC, json={"problem_type": "flat_tyre"})
    assert r.status_code == 201, r.text
    incident_id = int(r.json()["id"])
    ids = []
    for sample in samples:
        r = await client.post(f"{INC}/{incident_id}/photos", json={"sample_id": sample})
        assert r.status_code == 201, r.text
        ids.append(int(r.json()["id"]))
    return incident_id, ids


async def turn(client: httpx.AsyncClient, incident_id: int) -> httpx.Response:
    return await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": "en"})


def stored_name(settings: Settings, photo_id: int) -> str:
    with closing(sqlite3.connect(settings.database_path)) as db:
        row = db.execute(
            "SELECT stored_name FROM incident_photos WHERE id = ?", (photo_id,)
        ).fetchone()
    return str(row[0])


def sizes(fake: ScriptedProvider) -> list[tuple[int, int]]:
    """The size of every image in the first request, in order."""
    images = [i for m in fake.requests[0].messages for i in m.images]
    return [Image.open(BytesIO(base64.b64decode(i.data_b64))).size for i in images]


async def test_a_vision_provider_sees_the_photos_and_the_advice_keeps_its_observation(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(photo_observation="A screw in the tread"))
    incident_id, ids = await incident_with_samples(client, "screw_in_tread", "flat_tyre")

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["advice"]["photo_observation"] == "A screw in the tread"
    assert body["inputs"]["photo_ids_seen"] == ids
    assert body["inputs"]["photos_not_sent"] == 0
    user = fake.requests[0].messages[-1]
    assert user.role == "user"
    assert len(user.images) == 2
    assert all(i.media_type == "image/jpeg" for i in user.images)
    assert "Photos: 2 attached and shown to you\n" in fake.prompt_text()


async def test_photos_go_in_upload_order_up_to_the_cap(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(), max_images=3)
    # Told apart by size: pothole is 1280x720, the other two 1280x960.
    incident_id, ids = await incident_with_samples(
        client, "pothole", "flat_tyre", "pothole", "screw_in_tread", "pothole"
    )

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert sizes(fake) == [(1024, 576), (1024, 768), (1024, 576)]
    assert r.json()["inputs"]["photo_ids_seen"] == ids[:3]
    assert r.json()["inputs"]["photos_not_sent"] == 2
    assert "Photos: 3 attached and shown to you; 2 more attached but not sent to you" in (
        fake.prompt_text()
    )


async def test_photos_are_downscaled_for_the_request_only(
    client: httpx.AsyncClient, install: Install, settings: Settings
) -> None:
    fake = install(answer_json())
    incident_id, _ = await incident_with_samples(client, "flat_tyre")

    await turn(client, incident_id)

    assert sizes(fake) == [(1024, 768)]
    (stored,) = [p for p in settings.upload_dir.iterdir()]
    with Image.open(stored) as img:
        assert img.size == (1280, 960)


async def test_a_text_only_provider_gets_no_images_and_is_told_none_were_seen(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(photo_observation="A nail"), vision=False, max_images=0)
    incident_id, _ = await incident_with_samples(client, "flat_tyre", "pothole")

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert all(not m.images for m in fake.requests[0].messages)
    assert "Photos: none shown to you; 2 attached but not sent to you" in fake.prompt_text()
    assert r.json()["inputs"]["photo_ids_seen"] == []
    assert r.json()["inputs"]["photos_not_sent"] == 2
    # The backend, not the model, says whether photos were seen.
    assert r.json()["advice"]["photo_observation"] is None


async def test_no_photos_leaves_the_request_unchanged(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    incident_id, _ = await incident_with_samples(client)

    await turn(client, incident_id)

    assert all(not m.images for m in fake.requests[0].messages)
    assert "Photos: none shown to you\n" in fake.prompt_text()


async def test_the_replay_key_says_vision_was_used_and_names_the_samples(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json())
    incident_id, _ = await incident_with_samples(client, "flat_tyre")

    await turn(client, incident_id)

    key = json.loads(fake.requests[0].replay_key or "")
    assert (key["vision"], key["sample_photo_ids"]) == (True, ["flat_tyre"])


async def test_a_text_only_turn_keys_vision_off(
    client: httpx.AsyncClient, install: Install
) -> None:
    fake = install(answer_json(), vision=False, max_images=0)
    incident_id, _ = await incident_with_samples(client, "flat_tyre")

    await turn(client, incident_id)

    key = json.loads(fake.requests[0].replay_key or "")
    assert (key["vision"], key["sample_photo_ids"]) == (False, ["flat_tyre"])


async def test_a_photo_whose_file_is_gone_is_counted_as_not_sent(
    client: httpx.AsyncClient, install: Install, settings: Settings
) -> None:
    fake = install(answer_json())
    incident_id, ids = await incident_with_samples(client, "flat_tyre", "pothole")
    name = stored_name(settings, ids[0])
    (settings.upload_dir / name).unlink()

    r = await turn(client, incident_id)

    assert r.status_code == 201, r.text
    assert sizes(fake) == [(1024, 576)]
    assert r.json()["inputs"]["photo_ids_seen"] == [ids[1]]
    assert r.json()["inputs"]["photos_not_sent"] == 1


async def test_a_transparent_photo_is_flattened_onto_white(
    client: httpx.AsyncClient, install: Install, settings: Settings
) -> None:
    fake = install(answer_json())
    incident_id, ids = await incident_with_samples(client, "flat_tyre")
    name = stored_name(settings, ids[0])
    # Stored PNGs and WebPs keep their alpha channel (ADR 0002, #56).
    Image.new("RGBA", (40, 30), (0, 0, 0, 0)).save(settings.upload_dir / name, "PNG")

    await turn(client, incident_id)

    (image,) = fake.requests[0].messages[-1].images
    sent = Image.open(BytesIO(base64.b64decode(image.data_b64)))
    assert sent.getpixel((20, 15)) == (255, 255, 255)
