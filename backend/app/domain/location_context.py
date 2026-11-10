"""The coarse location context and label derived from one Nominatim reverse result (ADR 0004).

The model gets only the context, never coordinates or the label.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain.incident import Location


class RoadClass(StrEnum):
    MOTORWAY_EXPRESSWAY = "motorway_expressway"
    MAIN_ROAD = "main_road"
    LOCAL_STREET = "local_street"
    UNKNOWN = "unknown"


class Settlement(StrEnum):
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    COUNTRYSIDE = "countryside"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LocationContext:
    road_class: RoadClass
    settlement: Settlement


UNKNOWN_CONTEXT = LocationContext(RoadClass.UNKNOWN, Settlement.UNKNOWN)

_ROAD_CLASSES: dict[str, RoadClass] = {
    **dict.fromkeys(("motorway", "trunk"), RoadClass.MOTORWAY_EXPRESSWAY),
    **dict.fromkeys(("primary", "secondary", "tertiary"), RoadClass.MAIN_ROAD),
    **dict.fromkeys(
        ("residential", "unclassified", "living_street", "service"), RoadClass.LOCAL_STREET
    ),
}
_LINKABLE = {"motorway", "trunk", "primary", "secondary", "tertiary"}
_SETTLEMENTS = (
    ("city", Settlement.CITY),
    ("town", Settlement.TOWN),
    ("village", Settlement.VILLAGE),
)
_RURAL_KEYS = ("hamlet", "isolated_dwelling")
_LABEL_LOCALITY_KEYS = ("city", "town", "village", "hamlet")
_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _road_class(result: Mapping[str, Any]) -> RoadClass:
    if result.get("category") != "highway":
        return RoadClass.UNKNOWN
    tag = str(result.get("type", ""))
    base = tag.removesuffix("_link")
    if tag != base and base not in _LINKABLE:
        return RoadClass.UNKNOWN
    return _ROAD_CLASSES.get(base, RoadClass.UNKNOWN)


def _road_distance_m(result: Mapping[str, Any], location: Location) -> float | None:
    try:
        return haversine_m(location.lat, location.lon, float(result["lat"]), float(result["lon"]))
    except (KeyError, TypeError, ValueError):
        return None


def _settlement(address: Mapping[str, Any], road_matched: bool) -> Settlement:
    for key, settlement in _SETTLEMENTS:
        if address.get(key):
            return settlement
    if any(address.get(key) for key in _RURAL_KEYS) or road_matched:
        return Settlement.COUNTRYSIDE
    return Settlement.UNKNOWN


def _label(address: Mapping[str, Any]) -> str | None:
    road = address.get("road")
    locality = next((address[k] for k in _LABEL_LOCALITY_KEYS if address.get(k)), None)
    parts = [str(p) for p in (road, locality) if p]
    return ", ".join(parts) or None


def derive_location(
    result: Mapping[str, Any] | None,
    location: Location,
    *,
    max_gps_accuracy_m: float,
    max_road_distance_m: float,
) -> tuple[LocationContext, str | None]:
    """Map a Nominatim `jsonv2` reverse result to the context and the label.

    `road_class` is forced to unknown when the GPS fix is too coarse or the matched
    road is too far from the point, because a wrong "local street" is the dangerous mistake.
    """
    if not result:
        return UNKNOWN_CONTEXT, None
    address = result.get("address")
    if not isinstance(address, Mapping):
        address = {}

    road_class = _road_class(result)
    road_matched = road_class is not RoadClass.UNKNOWN
    if location.accuracy_m is not None and location.accuracy_m > max_gps_accuracy_m:
        road_class = RoadClass.UNKNOWN
    distance = _road_distance_m(result, location)
    if distance is None or distance > max_road_distance_m:
        road_class = RoadClass.UNKNOWN

    return LocationContext(road_class, _settlement(address, road_matched)), _label(address)
