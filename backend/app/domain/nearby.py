"""Nearby places: real places from OpenStreetMap, never from the model (ADR 0004, 0005)."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

# The snapshot keeps at most this many places (ADR 0005).
MAX_PLACES = 20
RADIUS_KM_MIN = 1
RADIUS_KM_MAX = 25
_EARTH_RADIUS_M = 6_371_008.8

OsmType = Literal["node", "way", "relation"]


class NearbyCategory(StrEnum):
    """The four chips. Towing has no settled OSM tag, so it is not one (ADR 0004)."""

    TYRES = "tyres"
    FUEL = "fuel"
    CHARGING = "charging"
    REPAIR = "repair"


# One Overpass query covers all four. The first matching tag decides an element's category.
CATEGORY_TAGS: tuple[tuple[str, str, NearbyCategory], ...] = (
    ("shop", "tyres", NearbyCategory.TYRES),
    ("amenity", "fuel", NearbyCategory.FUEL),
    ("amenity", "charging_station", NearbyCategory.CHARGING),
    ("shop", "car_repair", NearbyCategory.REPAIR),
)


@dataclass(frozen=True, slots=True)
class Place:
    osm_type: OsmType
    osm_id: int
    category: NearbyCategory
    name: str | None
    lat: float
    lon: float
    distance_m: int
    phone: str | None
    # The raw OSM string; the frontend shows only the simple forms.
    opening_hours: str | None


@dataclass(frozen=True, slots=True)
class NearbySnapshot:
    """One successful lookup, stored on the incident and replaced only by another success."""

    places: tuple[Place, ...]
    radius_km: int
    fetched_at: str
    # The Overpass endpoint that answered.
    source: str

    @property
    def status(self) -> Literal["found", "none"]:
        return "found" if self.places else "none"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, a)))


def places_from_elements(elements: Iterable[object], lat: float, lon: float) -> list[Place]:
    """Overpass `out center tags` elements → at most `MAX_PLACES` places, nearest first.

    Elements with no category tag or no usable point are skipped. When there are more than
    the cap, each category found keeps its nearest places in turn, so a crowded category
    (e.g. garages in a city) can't push a sparse one (the only tyre shop) off the list; the
    chips filter on the client.
    """
    seen: set[tuple[str, int]] = set()
    by_category: dict[NearbyCategory, list[Place]] = {}
    for element in elements:
        place = _place(element, lat, lon)
        if place is None or (place.osm_type, place.osm_id) in seen:
            continue
        seen.add((place.osm_type, place.osm_id))
        by_category.setdefault(place.category, []).append(place)

    queues = [sorted(ps, key=_order) for ps in by_category.values()]
    chosen: list[Place] = []
    rank = 0
    while len(chosen) < MAX_PLACES and any(rank < len(q) for q in queues):
        # Nearest-first within each round, so ties at the cap go to the closer place.
        round_ = sorted((q[rank] for q in queues if rank < len(q)), key=_order)
        chosen.extend(round_[: MAX_PLACES - len(chosen)])
        rank += 1
    return sorted(chosen, key=_order)


def _order(p: Place) -> tuple[int, str, int]:
    return (p.distance_m, p.osm_type, p.osm_id)


def _place(element: object, lat: float, lon: float) -> Place | None:
    if not isinstance(element, dict):
        return None
    osm_type = element.get("type")
    osm_id = element.get("id")
    tags = element.get("tags")
    if osm_type not in ("node", "way", "relation") or not isinstance(osm_id, int):
        return None
    if not isinstance(tags, dict):
        return None
    category = next((c for key, value, c in CATEGORY_TAGS if tags.get(key) == value), None)
    if category is None:
        return None
    point = _point(element)
    if point is None:
        return None
    p_lat, p_lon = point
    return Place(
        osm_type=osm_type,
        osm_id=osm_id,
        category=category,
        name=_text(tags, "name") or _text(tags, "brand"),
        lat=p_lat,
        lon=p_lon,
        distance_m=round(haversine_m(lat, lon, p_lat, p_lon)),
        phone=_first(_text(tags, "phone") or _text(tags, "contact:phone")),
        opening_hours=_text(tags, "opening_hours"),
    )


def _point(element: dict[Any, Any]) -> tuple[float, float] | None:
    """A node's own point, or the centre `out center` adds to ways and relations."""
    source = element if "lat" in element else element.get("center")
    if not isinstance(source, dict):
        return None
    p_lat, p_lon = source.get("lat"), source.get("lon")
    if not isinstance(p_lat, int | float) or not isinstance(p_lon, int | float):
        return None
    if not (-90 <= p_lat <= 90 and -180 <= p_lon <= 180):
        return None
    return float(p_lat), float(p_lon)


def _text(tags: dict[Any, Any], key: str) -> str | None:
    value = tags.get(key)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _first(value: str | None) -> str | None:
    """OSM separates several phone numbers with `;`. One is enough for a call button."""
    if value is None:
        return None
    return value.split(";")[0].strip() or None
