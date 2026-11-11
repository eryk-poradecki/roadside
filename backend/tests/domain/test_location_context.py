"""Mapping rules from a Nominatim reverse result to the coarse location context (ADR 0004)."""

from typing import Any

import pytest

from app.domain.incident import Location
from app.domain.location_context import (
    UNKNOWN_CONTEXT,
    LocationContext,
    RoadClass,
    Settlement,
    derive_location,
)

HERE = Location(lat=52.0, lon=21.0, accuracy_m=10)
GPS_LIMIT_M = 150.0
ROAD_LIMIT_M = 50.0


def _result(
    highway: str | None = "primary",
    *,
    address: dict[str, str] | None = None,
    lat: float = 52.0,
    lon: float = 21.0,
    name: str | None = "Puławska",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "lat": str(lat),
        "lon": str(lon),
        "address": {"road": name, "city": "Warszawa"} if address is None else address,
    }
    if highway is not None:
        result["category"] = "highway"
        result["type"] = highway
    else:
        result["category"] = "building"
        result["type"] = "yes"
    if name is None:
        result["address"].pop("road", None)
    return result


def _derive(
    result: dict[str, Any] | None, location: Location = HERE
) -> tuple[LocationContext, str | None]:
    return derive_location(
        result, location, max_gps_accuracy_m=GPS_LIMIT_M, max_road_distance_m=ROAD_LIMIT_M
    )


@pytest.mark.parametrize(
    ("highway", "expected"),
    [
        ("motorway", RoadClass.MOTORWAY_EXPRESSWAY),
        ("trunk_link", RoadClass.MOTORWAY_EXPRESSWAY),
        ("primary", RoadClass.MAIN_ROAD),
        ("secondary_link", RoadClass.MAIN_ROAD),
        ("tertiary", RoadClass.MAIN_ROAD),
        ("residential", RoadClass.LOCAL_STREET),
        ("unclassified", RoadClass.LOCAL_STREET),
        ("living_street", RoadClass.LOCAL_STREET),
        ("service", RoadClass.LOCAL_STREET),
        ("track", RoadClass.UNKNOWN),
        ("footway", RoadClass.UNKNOWN),
        (None, RoadClass.UNKNOWN),
    ],
)
def test_road_class_follows_the_highway_tag(highway: str | None, expected: RoadClass) -> None:
    context, _ = _derive(_result(highway))
    assert context.road_class is expected


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ({"city": "Warszawa"}, Settlement.CITY),
        ({"town": "Piaseczno"}, Settlement.TOWN),
        ({"village": "Złotokłos"}, Settlement.VILLAGE),
        ({"village": "Złotokłos", "hamlet": "Kolonia"}, Settlement.VILLAGE),
        ({"hamlet": "Kolonia"}, Settlement.COUNTRYSIDE),
        ({"isolated_dwelling": "Leśniczówka"}, Settlement.COUNTRYSIDE),
        ({"municipality": "gmina Tarczyn"}, Settlement.COUNTRYSIDE),
    ],
)
def test_settlement_is_the_nearest_named_locality(
    address: dict[str, str], expected: Settlement
) -> None:
    context, _ = _derive(_result(address={"road": "Polna", **address}))
    assert context.settlement is expected


def test_no_locality_and_no_road_is_unknown_settlement() -> None:
    context, _ = _derive(_result(None, address={"municipality": "gmina Tarczyn"}, name=None))
    assert context.settlement is Settlement.UNKNOWN


def test_poor_gps_accuracy_forces_unknown_road_class() -> None:
    context, _ = _derive(_result("motorway"), Location(52.0, 21.0, accuracy_m=GPS_LIMIT_M + 1))
    assert context.road_class is RoadClass.UNKNOWN
    assert context.settlement is Settlement.CITY


def test_accuracy_at_the_limit_is_still_trusted() -> None:
    context, _ = _derive(_result("motorway"), Location(52.0, 21.0, accuracy_m=GPS_LIMIT_M))
    assert context.road_class is RoadClass.MOTORWAY_EXPRESSWAY


def test_a_distant_matched_road_forces_unknown_road_class() -> None:
    # ~0.0009° latitude is about 100 m.
    context, _ = _derive(_result("residential", lat=52.0009))
    assert context.road_class is RoadClass.UNKNOWN


def test_a_road_within_the_distance_limit_is_trusted() -> None:
    # ~0.0003° latitude is about 33 m.
    context, _ = _derive(_result("residential", lat=52.0003))
    assert context.road_class is RoadClass.LOCAL_STREET


def test_label_is_road_and_locality() -> None:
    _, label = _derive(_result(address={"road": "Polna", "hamlet": "Kolonia"}))
    assert label == "Polna, Kolonia"


def test_label_falls_back_to_whichever_part_exists() -> None:
    assert _derive(_result(address={"city": "Warszawa"}, name=None))[1] == "Warszawa"
    assert _derive(_result(address={"road": "S7"}))[1] == "S7"
    assert _derive(_result(None, address={}, name=None))[1] is None


def test_no_result_is_unknown() -> None:
    assert _derive(None) == (UNKNOWN_CONTEXT, None)
