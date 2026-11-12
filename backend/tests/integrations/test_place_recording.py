"""Demo mode's place recordings: the file format and the recorder that merges into it (#58)."""

import json
from pathlib import Path

import pytest

from app.domain.incident import Location
from app.domain.location_context import LocationContext, ResolvedLocation, RoadClass, Settlement
from app.domain.nearby import NearbyCategory, NearbySnapshot, Place
from app.integrations.place_recording import PlaceRecorder, load_place_recordings

FIXTURES = Path(__file__).parents[1] / "fixtures" / "recordings" / "places"
KEY = '{"problem_type":"flat_tyre"}'
CONTEXT = ResolvedLocation(LocationContext(RoadClass.MAIN_ROAD, Settlement.TOWN), "DK7, Grójec")
POINT = Location(51.86, 20.85, 10)
TYRES = Place("node", 1, NearbyCategory.TYRES, "Opony", 51.86, 20.86, 420, None, "24/7")


def snapshot(radius_km: int, *places: Place) -> NearbySnapshot:
    return NearbySnapshot(places, radius_km, "2026-11-11T10:00:00.000Z", "https://overpass.test")


def files(directory: Path) -> list[Path]:
    return list(directory.iterdir())


def recorder(directory: Path) -> PlaceRecorder:
    return PlaceRecorder(directory, clock=lambda: "2026-11-11T12:00:00.000Z")


def test_the_fixtures_load_by_scenario_key() -> None:
    recordings = load_place_recordings(FIXTURES)

    assert len(recordings) == 3
    for key, rec in recordings.items():
        assert json.loads(key)["problem_type"] in {"flat_tyre", "out_of_fuel", "pothole_damage"}
        assert all(radius == s.radius_km for radius, s in rec.nearby.items())


def test_a_missing_directory_holds_none(tmp_path: Path) -> None:
    assert load_place_recordings(tmp_path / "nowhere") == {}


async def test_the_context_and_each_radius_merge_into_one_file(tmp_path: Path) -> None:
    rec = recorder(tmp_path)

    await rec.record_nearby(KEY, POINT, snapshot(5))
    await rec.record_location(KEY, POINT, CONTEXT)
    await rec.record_nearby(KEY, POINT, snapshot(25, TYRES))
    await rec.record_nearby(KEY, POINT, snapshot(5, TYRES))

    [saved] = load_place_recordings(tmp_path).values()
    assert saved.key == KEY
    assert saved.location == CONTEXT
    assert saved.nearby == {5: snapshot(5, TYRES), 25: snapshot(25, TYRES)}
    assert saved.recorded_at == "2026-11-11T12:00:00.000Z"
    assert len(files(tmp_path)) == 1


async def test_a_lookup_from_another_point_starts_the_file_afresh(tmp_path: Path) -> None:
    rec = recorder(tmp_path)
    await rec.record_location(KEY, POINT, CONTEXT)
    await rec.record_nearby(KEY, POINT, snapshot(25, TYRES))

    await rec.record_nearby(KEY, Location(50.06, 19.94, 10), snapshot(5))

    [saved] = load_place_recordings(tmp_path).values()
    # No label of one point with the places of another.
    assert (saved.location, saved.nearby) == (None, {5: snapshot(5)})


async def test_a_new_run_starts_the_file_afresh(tmp_path: Path) -> None:
    await recorder(tmp_path).record_location(KEY, POINT, CONTEXT)

    await recorder(tmp_path).record_nearby(KEY, POINT, snapshot(5))

    [saved] = load_place_recordings(tmp_path).values()
    assert saved.location is None


async def test_no_coordinates_of_the_recorded_point_are_stored(tmp_path: Path) -> None:
    await recorder(tmp_path).record_location(KEY, POINT, CONTEXT)

    [path] = files(tmp_path)
    assert "51.86" not in path.read_text()
    assert json.loads(path.read_text())["location"] == {
        "road_class": "main_road",
        "settlement": "town",
        "label": "DK7, Grójec",
    }


async def test_a_write_that_fails_is_logged_not_raised(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("")

    await recorder(blocked / "places").record_location(KEY, POINT, CONTEXT)


@pytest.mark.parametrize(
    "change",
    [
        {"extra": 1},
        {"location": {"road_class": "highway", "settlement": "town", "label": None}},
        {"nearby": [{"radius_km": 5, "places": [], "fetched_at": "t", "source": "s"}] * 2},
    ],
)
def test_a_malformed_recording_fails_startup(tmp_path: Path, change: dict[str, object]) -> None:
    data = {"key": KEY, "location": None, "nearby": [], "recorded_at": "t", **change}
    (tmp_path / "bad.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match=r"bad\.json"):
        load_place_recordings(tmp_path)


def test_two_recordings_of_one_key_fail_startup(tmp_path: Path) -> None:
    data: dict[str, object] = {"key": KEY, "location": None, "nearby": [], "recorded_at": "t"}
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(data))

    with pytest.raises(ValueError, match="two place recordings"):
        load_place_recordings(tmp_path)


async def test_the_scenario_light_merges_into_the_file(tmp_path: Path) -> None:
    """`dark` belongs to the scenario, so demo mode can replay it at any hour (#63)."""
    rec = recorder(tmp_path)
    await rec.record_nearby(KEY, POINT, snapshot(5))

    await rec.record_dark(KEY, POINT, dark=True)

    [saved] = load_place_recordings(tmp_path).values()
    assert saved.dark is True
    assert saved.nearby == {5: snapshot(5)}
    assert json.loads(files(tmp_path)[0].read_text())["dark"] is True


def test_a_recording_without_the_light_leaves_it_unknown(tmp_path: Path) -> None:
    data: dict[str, object] = {"key": KEY, "location": None, "nearby": [], "recorded_at": "t"}
    (tmp_path / "old.json").write_text(json.dumps(data))

    [saved] = load_place_recordings(tmp_path).values()

    assert saved.dark is None
