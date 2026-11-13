"""The scenario picker receives exactly the facts whose first turns can replay."""

import json
import shutil
from pathlib import Path

import httpx
from pydantic import SecretStr

from app.main import create_app
from app.settings import Settings
from scripts.demo.scenarios import raw_blocks
from tests.running import running

RECORDINGS = Path(__file__).parents[2] / "recordings"


async def test_config_catalogue_matches_document(settings: Settings) -> None:
    settings.llm_recordings_dir = RECORDINGS
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/config")
    assert response.status_code == 200
    body = response.json()
    assert body["public_deploy"] is False
    scenarios = body["demo_scenarios"]
    assert len(scenarios) == 8
    for actual, expected in zip(scenarios, raw_blocks(), strict=True):
        assert actual["id"] == expected["id"]
        assert actual["problem_type"] == expected["problem_type"]
        vehicle = expected["vehicle"]
        assert actual["vehicle_profile"] == (vehicle["profile_id"] if vehicle else None)
        assert actual["situation"] == expected["situation"]
        assert actual["sample_photo_ids"] == expected["sample_photos"]
        assert set(actual["locales"]) == {"en", "pl"}
        for locale, copy in actual["locales"].items():
            assert copy["note"] == expected["locales"][locale]["note"]
            assert copy["title"].strip()
            assert copy["summary"].strip()


async def test_every_advertised_locale_replays_first_turn(settings: Settings) -> None:
    settings.llm_recordings_dir = RECORDINGS
    async with running(settings) as client:
        config = (await client.get("/api/v1/config")).json()
        vehicles = (await client.get("/api/v1/vehicles")).json()
        profiles = {v["demo_profile"]: v["id"] for v in vehicles}
        for scenario in config["demo_scenarios"]:
            for locale, copy in scenario["locales"].items():
                response = await client.post(
                    "/api/v1/incidents",
                    json={
                        "problem_type": scenario["problem_type"],
                        "vehicle_id": profiles.get(scenario["vehicle_profile"]),
                        "situation": scenario["situation"],
                        "note": copy["note"],
                        "location": scenario["location"],
                    },
                )
                assert response.status_code == 201, response.text
                incident = f"/api/v1/incidents/{response.json()['id']}"
                for sample in scenario["sample_photo_ids"]:
                    response = await client.post(f"{incident}/photos", json={"sample_id": sample})
                    assert response.status_code == 201, response.text
                response = await client.post(f"{incident}/ai-turns", json={"locale": locale})
                assert response.status_code == 201, (scenario["id"], locale, response.text)
                assert response.json()["kind"] in {"question", "advice"}


async def test_only_locales_with_first_turn_recordings_are_listed(
    settings: Settings, tmp_path: Path
) -> None:
    target = tmp_path / "partial"
    shutil.copytree(RECORDINGS, target)
    # Remove every Polish recording for the parked flat tyre, including any follow-up.
    # Also remove both languages for the smoke scenario, so it disappears altogether.
    for path in target.glob("*.json"):
        key = json.loads(json.loads(path.read_text())["key"])
        if (
            key["problem_type"] == "flat_tyre"
            and key["situation"] == "parked"
            and key["locale"] == "pl"
        ) or (key["problem_type"] == "other" and key["fuel_type"] == "diesel"):
            path.unlink()
    settings.llm_recordings_dir = target
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://test"
    ) as client:
        scenarios = (await client.get("/api/v1/config")).json()["demo_scenarios"]
    assert len(scenarios) == 7
    assert set(scenarios[0]["locales"]) == {"en"}
    assert "smoke_engine_bay" not in {s["id"] for s in scenarios}


async def test_live_mode_returns_no_scenarios(settings: Settings) -> None:
    settings.demo_mode = False
    settings.llm_provider = "openai_compatible"
    settings.llm_base_url = "http://model.invalid/v1"
    settings.llm_api_key = SecretStr("unused")
    settings.llm_model = "unused"
    settings.llm_recordings_dir = RECORDINGS
    async with running(settings) as client:
        body = (await client.get("/api/v1/config")).json()
    assert body["demo_scenarios"] == []
    assert body["public_deploy"] is False


async def test_config_exposes_public_deploy(settings: Settings) -> None:
    settings.public_deploy = True
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://test"
    ) as client:
        body = (await client.get("/api/v1/config")).json()
    assert body["public_deploy"] is True
    assert body["demo_scenarios"] == []
