"""Nearby places: a server-side Overpass lookup stored as a snapshot (ADR 0004, 0005)."""

import asyncio
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.deps import get_llm_provider, get_place_source
from app.integrations.overpass import NearbyUnavailable
from tests.fakes import FakePlaceSource, ScriptedProvider, answer_json, osm_node

INC = "/api/v1/incidents"
LOCATION = {"lat": 52.2297, "lon": 21.0122, "accuracy_m": 12}
FAR_FUEL = osm_node(2, 52.2600, 21.0122, amenity="fuel", name="Far fuel", opening_hours="24/7")
NEAR_TYRES = osm_node(
    1, 52.2300, 21.0122, shop="tyres", name="Wulkanizacja", phone="+48 22 000 00 01"
)


def use_source(app: FastAPI, *script: Any) -> FakePlaceSource:
    source = FakePlaceSource(*script)
    app.dependency_overrides[get_place_source] = lambda: source
    return source


async def make_incident(client: httpx.AsyncClient, **body: object) -> int:
    r = await client.post(INC, json={"problem_type": "flat_tyre", **body})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def nearby(client: httpx.AsyncClient, incident_id: int, radius_km: object = 5) -> Any:
    return await client.post(f"{INC}/{incident_id}/nearby", json={"radius_km": radius_km})


async def stored(client: httpx.AsyncClient, incident_id: int) -> Any:
    return (await client.get(f"{INC}/{incident_id}")).json()["nearby"]


async def test_a_new_incident_has_no_snapshot(client: httpx.AsyncClient) -> None:
    incident_id = await make_incident(client, location=LOCATION)
    assert await stored(client, incident_id) is None


async def test_found_places_sorted_by_distance_and_stored(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = use_source(app, [FAR_FUEL, NEAR_TYRES])
    incident_id = await make_incident(client, location=LOCATION)

    r = await nearby(client, incident_id)

    assert r.status_code == 200, r.text
    body = r.json()
    assert source.calls == [(52.2297, 21.0122, 5000)]
    assert body["status"] == "found"
    assert body["radius_km"] == 5
    assert body["fetched_at"].endswith("Z")
    assert body["places"][0] == {
        "osm_type": "node",
        "osm_id": 1,
        "category": "tyres",
        "name": "Wulkanizacja",
        "lat": 52.23,
        "lon": 21.0122,
        "distance_m": 33,
        "phone": "+48 22 000 00 01",
        "opening_hours": None,
    }
    assert [p["osm_id"] for p in body["places"]] == [1, 2]
    assert body["places"][1]["opening_hours"] == "24/7"
    # The source endpoint is stored, not sent.
    assert "source" not in body
    assert await stored(client, incident_id) == body


async def test_none_is_a_success_too(app: FastAPI, client: httpx.AsyncClient) -> None:
    use_source(app, [])
    incident_id = await make_incident(client, location=LOCATION)

    r = await nearby(client, incident_id)

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "none"
    assert r.json()["places"] == []
    assert (await stored(client, incident_id))["status"] == "none"


async def test_search_within_25_km_replaces_the_snapshot(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = use_source(app, [], [FAR_FUEL])
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)

    r = await nearby(client, incident_id, 25)

    assert r.status_code == 200, r.text
    assert source.calls[-1][2] == 25_000
    snapshot = await stored(client, incident_id)
    assert snapshot["radius_km"] == 25
    assert snapshot["status"] == "found"


async def test_no_location_is_409(app: FastAPI, client: httpx.AsyncClient) -> None:
    source = use_source(app)
    incident_id = await make_incident(client)

    r = await nearby(client, incident_id)

    assert r.status_code == 409
    assert r.json()["reason"] == "no_location"
    assert source.calls == []


async def test_a_missing_incident_is_404(app: FastAPI, client: httpx.AsyncClient) -> None:
    use_source(app)
    r = await nearby(client, 999)
    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"


@pytest.mark.parametrize("radius_km", [0, 26, -5, 2.5, "five", None])
async def test_a_radius_outside_1_to_25_is_422(
    app: FastAPI, client: httpx.AsyncClient, radius_km: object
) -> None:
    source = use_source(app)
    incident_id = await make_incident(client, location=LOCATION)

    r = await nearby(client, incident_id, radius_km)

    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "radius_km"
    assert source.calls == []


async def test_a_missing_radius_is_422(app: FastAPI, client: httpx.AsyncClient) -> None:
    use_source(app)
    incident_id = await make_incident(client, location=LOCATION)
    r = await client.post(f"{INC}/{incident_id}/nearby", json={})
    assert r.status_code == 422


async def test_a_failed_lookup_is_503_and_keeps_the_previous_snapshot(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    use_source(app, [NEAR_TYRES], NearbyUnavailable())
    incident_id = await make_incident(client, location=LOCATION)
    first = (await nearby(client, incident_id)).json()

    r = await nearby(client, incident_id, 25)

    assert r.status_code == 503
    assert r.json()["reason"] == "nearby_unavailable"
    assert await stored(client, incident_id) == first


async def test_demo_mode_makes_no_overpass_call(client: httpx.AsyncClient) -> None:
    """Recorded results come with the demo scenarios (#58); until then, unavailable."""
    incident_id = await make_incident(client, location=LOCATION)

    r = await nearby(client, incident_id)

    assert r.status_code == 503
    assert r.json()["reason"] == "nearby_unavailable"


async def test_a_location_patch_clears_the_snapshot(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    use_source(app, [NEAR_TYRES])
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)

    r = await client.patch(f"{INC}/{incident_id}", json={"location": {"lat": 50.06, "lon": 19.94}})

    assert r.status_code == 200, r.text
    assert r.json()["nearby"] is None
    assert await stored(client, incident_id) is None


async def test_removing_the_location_clears_the_snapshot(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    use_source(app, [NEAR_TYRES])
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)

    r = await client.patch(f"{INC}/{incident_id}", json={"location": None})

    assert r.json()["nearby"] is None


@pytest.mark.parametrize(
    "patch",
    [{"problem_type": "out_of_fuel"}, {"status": "resolved"}, {"location": LOCATION}],
)
async def test_other_patches_keep_the_snapshot(
    app: FastAPI, client: httpx.AsyncClient, patch: dict[str, object]
) -> None:
    """One query covers every category, so a new problem type only changes the chips."""
    use_source(app, [NEAR_TYRES])
    incident_id = await make_incident(client, location=LOCATION)
    snapshot = (await nearby(client, incident_id)).json()

    r = await client.patch(f"{INC}/{incident_id}", json=patch)

    assert r.json()["nearby"] == snapshot


async def test_a_lookup_for_a_location_moved_meanwhile_stores_nothing(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    release = asyncio.Event()

    async def slow() -> list[object]:
        await release.wait()
        return [NEAR_TYRES]

    use_source(app, slow)
    incident_id = await make_incident(client, location=LOCATION)
    lookup = asyncio.create_task(nearby(client, incident_id))
    await asyncio.sleep(0.05)

    moved = await client.patch(
        f"{INC}/{incident_id}", json={"location": {"lat": 50.0, "lon": 19.0}}
    )
    assert moved.status_code == 200
    release.set()
    r = await lookup

    assert r.status_code == 409
    assert r.json()["reason"] == "location_changed"
    assert await stored(client, incident_id) is None


async def test_deleting_the_incident_deletes_the_snapshot(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    use_source(app, [NEAR_TYRES])
    incident_id = await make_incident(client, location=LOCATION)
    await nearby(client, incident_id)

    assert (await client.delete(f"{INC}/{incident_id}")).status_code == 204
    assert (await client.get(f"{INC}/{incident_id}")).status_code == 404


async def test_an_ai_turn_never_supplies_a_place(app: FastAPI, client: httpx.AsyncClient) -> None:
    """Even an advice that preselects categories leaves nearby to the map lookup."""
    fake = ScriptedProvider(answer_json(extra_categories=["fuel", "repair"]))
    app.dependency_overrides[get_llm_provider] = lambda: fake
    source = use_source(app)
    incident_id = await make_incident(client, location=LOCATION)

    r = await client.post(f"{INC}/{incident_id}/ai-turns", json={"locale": "en"})

    assert r.status_code == 201, r.text
    assert source.calls == []
    assert await stored(client, incident_id) is None
