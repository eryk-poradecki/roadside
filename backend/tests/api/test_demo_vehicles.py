"""Demo mode seeds the three fixed demo vehicles of `docs/demo-scenarios.md` (#122), so a
visitor can pick a scenario's car instead of guessing its facts."""

from pathlib import Path

import pytest

from app.settings import Settings
from tests.running import running

VEH = "/api/v1/vehicles"


def demo_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "demo.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=True,
        llm_recordings_dir=tmp_path / "recordings",
    )


async def test_a_fresh_demo_database_lists_the_three_demo_vehicles(tmp_path: Path) -> None:
    async with running(demo_settings(tmp_path)) as client:
        vehicles = (await client.get(VEH)).json()

    # The default first: the Octavia of the video scenario.
    assert [v["name"] for v in vehicles] == ["Octavia", "Golf", "MINI"]
    assert [v["is_default"] for v in vehicles] == [True, False, False]
    assert [v["demo_profile"] for v in vehicles] == ["octavia_2015", "golf_2017", "mini_ev_2021"]
    octavia, golf, mini = vehicles
    assert (golf["fuel_type"], golf["transmission"], golf["spare_wheel"]) == (
        "petrol",
        "manual",
        "full_size",
    )
    assert (mini["fuel_type"], mini["transmission"], mini["spare_wheel"]) == (
        "electric",
        "automatic",
        "none",
    )
    assert (octavia["fuel_type"], octavia["transmission"], octavia["spare_wheel"]) == (
        "diesel",
        "manual",
        "space_saver",
    )
    # No registration or policy number: nothing that reads as a real car's papers.
    assert all(v["registration"] is None and v["policy_number"] is None for v in vehicles)


async def test_the_minis_assistance_phone_is_a_placeholder_no_one_can_dial(
    tmp_path: Path,
) -> None:
    async with running(demo_settings(tmp_path)) as client:
        vehicles = {v["name"]: v for v in (await client.get(VEH)).json()}

    # Non-blank, so the MINI has assistance; no digit, so the app never offers to call it.
    phone = vehicles["MINI"]["assistance_phone"]
    assert phone.strip()
    assert not any(ch.isdigit() for ch in phone)
    assert vehicles["Golf"]["assistance_phone"] is None
    assert vehicles["Octavia"]["assistance_phone"] is None


async def test_a_live_database_lists_none(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "live.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=False,
        llm_base_url="http://llm.test/v1",
        llm_api_key="k",
        llm_model="m",
    )
    async with running(settings) as client:
        assert (await client.get(VEH)).json() == []


def writable(vehicle: dict[str, object]) -> dict[str, object]:
    return {
        k: v
        for k, v in vehicle.items()
        if k not in {"id", "created_at", "updated_at", "demo_profile"}
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "Changed"),
        ("make_model", "Other"),
        ("year", 2020),
        ("fuel_type", "lpg"),
        ("transmission", "automatic"),
        ("tyre_size", "205/55 R16"),
        ("spare_wheel", "none"),
        ("wheel_locks", False),
        ("lock_key_location", "boot"),
        ("registration", "ABC"),
        ("assistance_insurer", "Insurer"),
        ("assistance_phone", "demo"),
        ("policy_number", "P1"),
    ],
)
async def test_demo_vehicle_facts_are_read_only(tmp_path: Path, field: str, value: object) -> None:
    async with running(demo_settings(tmp_path)) as client:
        golf = next(v for v in (await client.get(VEH)).json() if v["name"] == "Golf")
        body = {**writable(golf), field: value, "is_default": True}
        if field == "wheel_locks":
            body["lock_key_location"] = None
        response = await client.put(f"{VEH}/{golf['id']}", json=body)
        assert response.status_code == 403
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["reason"] == "demo_vehicle_read_only"
        assert (await client.get(f"{VEH}/{golf['id']}")).json() == golf
        assert (await client.get(VEH)).json()[0]["name"] == "Octavia"


async def test_demo_vehicle_can_become_default_but_cannot_be_deleted(tmp_path: Path) -> None:
    async with running(demo_settings(tmp_path)) as client:
        vehicles = (await client.get(VEH)).json()
        golf = next(v for v in vehicles if v["name"] == "Golf")
        response = await client.put(
            f"{VEH}/{golf['id']}", json={**writable(golf), "is_default": True}
        )
        assert response.status_code == 200
        assert response.json()["is_default"] is True
        assert sum(v["is_default"] for v in (await client.get(VEH)).json()) == 1
        response = await client.delete(f"{VEH}/{golf['id']}")
        assert response.status_code == 403
        assert response.json()["reason"] == "demo_vehicle_read_only"


async def test_visitors_vehicles_keep_full_crud(tmp_path: Path) -> None:
    async with running(demo_settings(tmp_path)) as client:
        response = await client.post(VEH, json={"name": "Van"})
        assert response.status_code == 201
        vehicle = response.json()
        assert vehicle["demo_profile"] is None
        assert (
            await client.put(f"{VEH}/{vehicle['id']}", json={"name": "My van"})
        ).status_code == 200
        assert (await client.delete(f"{VEH}/{vehicle['id']}")).status_code == 204


async def test_marked_vehicles_are_ordinary_in_live_mode_and_missing_profile_returns(
    tmp_path: Path,
) -> None:
    settings = demo_settings(tmp_path)
    async with running(settings) as client:
        vehicles = (await client.get(VEH)).json()
    live = Settings.model_validate(
        {
            **settings.model_dump(),
            "demo_mode": False,
            "llm_base_url": "http://llm.test/v1",
            "llm_api_key": "k",
            "llm_model": "m",
        }
    )
    async with running(live) as client:
        golf = next(v for v in vehicles if v["name"] == "Golf")
        mini = next(v for v in vehicles if v["name"] == "MINI")
        assert (
            await client.put(f"{VEH}/{golf['id']}", json={"name": "My Golf", "is_default": True})
        ).status_code == 200
        assert (await client.delete(f"{VEH}/{mini['id']}")).status_code == 204
        assert (await client.post(VEH, json={"name": "Van"})).status_code == 201
        before = (await client.get(VEH)).json()
    async with running(settings) as client:
        after = (await client.get(VEH)).json()
    assert [v for v in after if v["demo_profile"] != "mini_ev_2021"] == before
    assert len(after) == 4
    assert sum(v["demo_profile"] == "mini_ev_2021" for v in after) == 1
    async with running(settings) as client:
        assert (await client.get(VEH)).json() == after


async def test_demo_seeding_preserves_an_existing_visitors_default(tmp_path: Path) -> None:
    settings = demo_settings(tmp_path)
    live = Settings.model_validate(
        {
            **settings.model_dump(),
            "demo_mode": False,
            "llm_base_url": "http://llm.test/v1",
            "llm_api_key": "k",
            "llm_model": "m",
        }
    )
    async with running(live) as client:
        visitor = (await client.post(VEH, json={"name": "Van"})).json()
    async with running(settings) as client:
        vehicles = (await client.get(VEH)).json()
        assert vehicles[0] == visitor
        assert len(vehicles) == 4
        assert sum(v["is_default"] for v in vehicles) == 1
