"""Pure nearby helpers: haversine and the Overpass element → place mapping (ADR 0004, 0005)."""

from typing import Any

import pytest

from app.domain.nearby import (
    MAX_PLACES,
    NearbyCategory,
    haversine_m,
    places_from_elements,
)

ORIGIN = (52.2297, 21.0122)


def node(osm_id: int, lat: float, lon: float, **tags: str) -> dict[str, Any]:
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": tags}


def way(osm_id: int, lat: float, lon: float, **tags: str) -> dict[str, Any]:
    return {"type": "way", "id": osm_id, "center": {"lat": lat, "lon": lon}, "tags": tags}


def test_haversine_is_zero_for_the_same_point() -> None:
    assert haversine_m(52.0, 21.0, 52.0, 21.0) == 0


def test_haversine_matches_a_known_distance() -> None:
    # Warsaw Centralna to Kraków Główny: about 252 km as the crow flies.
    assert haversine_m(52.2289, 21.0034, 50.0683, 19.9475) == pytest.approx(252_000, rel=0.01)


def test_one_degree_of_latitude_is_about_111_km() -> None:
    assert haversine_m(0.0, 0.0, 1.0, 0.0) == pytest.approx(111_195, rel=0.001)


def test_maps_each_category_tag() -> None:
    elements = [
        node(1, 52.23, 21.01, shop="tyres"),
        node(2, 52.23, 21.01, amenity="fuel"),
        node(3, 52.23, 21.01, amenity="charging_station"),
        node(4, 52.23, 21.01, shop="car_repair"),
    ]
    places = places_from_elements(elements, *ORIGIN)
    assert [(p.osm_id, p.category) for p in places] == [
        (1, NearbyCategory.TYRES),
        (2, NearbyCategory.FUEL),
        (3, NearbyCategory.CHARGING),
        (4, NearbyCategory.REPAIR),
    ]


def test_sorts_by_distance_and_takes_way_centres() -> None:
    elements = [
        node(1, 52.2600, 21.0122, amenity="fuel"),
        way(2, 52.2300, 21.0122, amenity="fuel"),
        node(3, 52.2400, 21.0122, amenity="fuel"),
    ]
    places = places_from_elements(elements, *ORIGIN)
    assert [p.osm_id for p in places] == [2, 3, 1]
    assert places[0].osm_type == "way"
    assert places[0].lat == 52.23
    assert places[0].distance_m == 33
    assert all(isinstance(p.distance_m, int) for p in places)


def test_keeps_name_phone_and_the_raw_opening_hours() -> None:
    [place] = places_from_elements(
        [
            node(
                1,
                52.23,
                21.01,
                shop="tyres",
                name="Wulkanizacja Hoża",
                phone="+48 22 000 00 01; +48 22 000 00 02",
                opening_hours="Mo-Fr 08:00-18:00; Sa 09:00-14:00",
            )
        ],
        *ORIGIN,
    )
    assert place.name == "Wulkanizacja Hoża"
    assert place.phone == "+48 22 000 00 01"
    assert place.opening_hours == "Mo-Fr 08:00-18:00; Sa 09:00-14:00"


def test_falls_back_to_brand_and_contact_phone() -> None:
    [place] = places_from_elements(
        [node(1, 52.23, 21.01, amenity="fuel", brand="Orlen", **{"contact:phone": "+48 1"})],
        *ORIGIN,
    )
    assert place.name == "Orlen"
    assert place.phone == "+48 1"


def test_missing_details_are_none() -> None:
    [place] = places_from_elements([node(1, 52.23, 21.01, amenity="fuel")], *ORIGIN)
    assert (place.name, place.phone, place.opening_hours) == (None, None, None)


def test_skips_elements_without_a_category_or_a_point() -> None:
    elements: list[Any] = [
        node(1, 52.23, 21.01, amenity="pharmacy"),
        {"type": "way", "id": 2, "tags": {"amenity": "fuel"}},
        {"type": "node", "id": 3, "lat": "x", "lon": 21.0, "tags": {"amenity": "fuel"}},
        {"type": "area", "id": 4, "lat": 52.23, "lon": 21.01, "tags": {"amenity": "fuel"}},
        "garbage",
        node(5, 52.23, 21.01),
        node(6, 52.23, 21.01, amenity="fuel"),
    ]
    assert [p.osm_id for p in places_from_elements(elements, *ORIGIN)] == [6]


def test_an_element_found_twice_is_listed_once() -> None:
    elements = [node(1, 52.23, 21.01, amenity="fuel"), node(1, 52.23, 21.01, amenity="fuel")]
    assert len(places_from_elements(elements, *ORIGIN)) == 1


def test_caps_at_twenty_nearest() -> None:
    elements = [node(i, 52.23 + i / 1000, 21.0122, amenity="fuel") for i in range(1, 40)]
    places = places_from_elements(elements, *ORIGIN)
    assert len(places) == MAX_PLACES == 20
    assert [p.osm_id for p in places] == list(range(1, 21))


def test_the_cap_keeps_every_category_that_was_found() -> None:
    """Chips filter on the client, so 20 garages must not crowd out the one tyre shop."""
    garages = [node(i, 52.2297 + i / 10_000, 21.0122, shop="car_repair") for i in range(1, 40)]
    far_tyres = node(100, 52.30, 21.0122, shop="tyres")
    places = places_from_elements([*garages, far_tyres], *ORIGIN)

    assert len(places) == 20
    assert places[-1].osm_id == 100
    distances = [p.distance_m for p in places]
    assert distances == sorted(distances)
