"""Demo mode seeds the three fixed demo vehicles of `docs/demo-scenarios.md` (#122), so a
visitor can pick a scenario's car instead of guessing its facts."""

from pathlib import Path

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


async def test_a_restart_keeps_the_visitors_vehicles_and_edits(tmp_path: Path) -> None:
    settings = demo_settings(tmp_path)
    async with running(settings) as client:
        by_name = {v["name"]: v for v in (await client.get(VEH)).json()}
        golf = by_name["Golf"]
        r = await client.put(
            f"{VEH}/{golf['id']}", json={"name": "My Golf", "fuel_type": "lpg", "is_default": True}
        )
        assert r.status_code == 200, r.text
        assert (await client.delete(f"{VEH}/{by_name['MINI']['id']}")).status_code == 204
        assert (await client.post(VEH, json={"name": "Van"})).status_code == 201
        before = (await client.get(VEH)).json()

    async with running(settings) as client:
        after = (await client.get(VEH)).json()

    assert after == before
    assert [v["name"] for v in after] == ["My Golf", "Octavia", "Van"]


async def test_a_visitor_who_deleted_every_vehicle_gets_the_demo_vehicles_back(
    tmp_path: Path,
) -> None:
    """Seeding needs only an empty table, as after the public demo's nightly wipe (ADR 0011)."""
    settings = demo_settings(tmp_path)
    async with running(settings) as client:
        for v in (await client.get(VEH)).json():
            await client.delete(f"{VEH}/{v['id']}")

    async with running(settings) as client:
        assert len((await client.get(VEH)).json()) == 3
