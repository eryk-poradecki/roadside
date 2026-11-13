"""The check follows the public picker contract and detects a broken demo stack."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.settings import Settings
from scripts.demo.check import check
from scripts.demo.record import load_choices
from scripts.demo.scenarios import load_scenarios
from tests.running import running

RECORDINGS = Path(__file__).parents[2] / "recordings"


@asynccontextmanager
async def demo(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    async with running(
        Settings(
            database_path=tmp_path / "demo.db",
            upload_dir=tmp_path / "uploads",
            demo_mode=True,
            llm_recordings_dir=RECORDINGS,
        )
    ) as client:
        yield client


async def test_check_sends_the_catalogue_inputs(tmp_path: Path) -> None:
    requests: list[dict[str, Any]] = []
    async with demo(tmp_path) as app:

        async def forward(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/incidents") and request.method == "POST":
                requests.append(json.loads(request.content))
            response = await app.request(
                request.method,
                str(request.url),
                content=request.content,
                headers={"Content-Type": "application/json"},
            )
            if request.url.path.endswith("/config"):
                body = response.json()
                scenario = body["demo_scenarios"][0]
                scenario["location"] = {"lat": 52.5, "lon": 16.8, "accuracy_m": 42}
                scenario["locales"]["en"]["note"] = "Catalogue note"
                scenario["vehicle_profile"] = "octavia_2015"
                return httpx.Response(200, json=body)
            return response

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(forward), base_url="http://test"
        ) as client:
            await check(
                client, load_scenarios()[:1], load_choices(RECORDINGS / "branches/choices.json")
            )
        vehicles = (await app.get("/api/v1/vehicles")).json()
    [english] = [r for r in requests if r["note"] == "Catalogue note"]
    assert english["location"] == {"lat": 52.5, "lon": 16.8, "accuracy_m": 42}
    assert english["vehicle_id"] == next(
        v["id"] for v in vehicles if v["demo_profile"] == "octavia_2015"
    )


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
async def test_check_rejects_unprotected_demo_vehicles(tmp_path: Path, method: str) -> None:
    from scripts.demo.check import DemoCheckFailed

    async with demo(tmp_path) as app:

        async def forward(request: httpx.Request) -> httpx.Response:
            if request.method == method and "/vehicles/" in request.url.path:
                if method == "DELETE":
                    return httpx.Response(204)
                body = json.loads(request.content)
                # Simulate a server accepting a changed fact, leaving the fixture intact.
                if body["fuel_type"] == "petrol":
                    return httpx.Response(200, json=body)
            return await app.request(
                request.method,
                str(request.url),
                content=request.content,
                headers={"Content-Type": "application/json"},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(forward), base_url="http://test"
        ) as client:
            with pytest.raises(
                DemoCheckFailed, match=f"{method} must return 403 demo_vehicle_read_only"
            ):
                await check(client, load_scenarios(), {})


@pytest.mark.parametrize("default", ["visitor", "none"])
async def test_check_restores_the_default_and_checks_every_demo_vehicle(
    tmp_path: Path,
    default: str,
) -> None:
    async with demo(tmp_path) as client:
        visitor = (
            await client.post("/api/v1/vehicles", json={"name": "Visitor", "is_default": True})
        ).json()
        if default == "none":
            await client.put(
                f"/api/v1/vehicles/{visitor['id']}", json={"name": "Visitor", "is_default": False}
            )
        before = (await client.get("/api/v1/vehicles")).json()
        walks = await check(
            client, load_scenarios(), load_choices(RECORDINGS / "branches/choices.json")
        )
        after = (await client.get("/api/v1/vehicles")).json()
        assert all(w.ok for w in walks), [(w.name, w.problems) for w in walks if not w.ok]
        assert {v["id"]: v["is_default"] for v in after} == {
            v["id"]: v["is_default"] for v in before
        }
        assert (await client.get("/api/v1/incidents")).json()["total"] == 0


@pytest.mark.parametrize("remove", ["scenario", "locale", "branch"])
async def test_check_detects_a_removed_recording(tmp_path: Path, remove: str) -> None:
    import shutil

    from scripts.demo.check import DemoCheckFailed

    recordings = tmp_path / "recordings"
    shutil.copytree(RECORDINGS, recordings)
    for path in recordings.glob("*.json"):
        key = json.loads(json.loads(path.read_text())["key"])
        if key["problem_type"] != "other" or key["fuel_type"] is not None:
            continue
        if remove == "locale" and key["locale"] != "pl":
            continue
        if remove == "branch" and not key["replies"]:
            continue
        path.unlink()
    async with running(
        Settings(
            database_path=tmp_path / "partial.db",
            upload_dir=tmp_path / "uploads",
            demo_mode=True,
            llm_recordings_dir=recordings,
        )
    ) as client:
        if remove == "branch":
            walks = await check(
                client, load_scenarios(), load_choices(RECORDINGS / "branches/choices.json")
            )
            assert any("no_recording" in p for w in walks for p in w.problems)
        else:
            message = (
                "missing scenario unknown_knocking_warning"
                if remove == "scenario"
                else "unknown_knocking_warning is missing locales pl"
            )
            with pytest.raises(DemoCheckFailed, match=message):
                await check(client, load_scenarios(), {})
