import asyncio

import httpx

INC = "/api/v1/incidents"
V = "/api/v1/vehicles"


async def make_vehicle(client: httpx.AsyncClient, **kw: object) -> int:
    r = await client.post(V, json={"name": "Golf", **kw})
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


async def test_create_needs_only_the_problem_type(client: httpx.AsyncClient) -> None:
    r = await client.post(INC, json={"problem_type": "flat_tyre"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert r.headers["location"] == f"{INC}/{body['id']}"
    assert isinstance(body["id"], int)
    assert body["problem_type"] == "flat_tyre"
    assert body["status"] == "open"
    assert body["vehicle_id"] is None
    assert body["note"] is None
    assert body["location"] is None
    assert body["location_label"] is None
    assert body["created_at"].endswith("Z")


async def test_create_with_every_field_and_read_back(client: httpx.AsyncClient) -> None:
    vehicle_id = await make_vehicle(client)
    r = await client.post(
        INC,
        json={
            "problem_type": "out_of_fuel",
            "vehicle_id": vehicle_id,
            "note": "  Warning light is on  ",
            "location": {"lat": 52.2297, "lon": 21.0122, "accuracy_m": 12.5},
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["vehicle_id"] == vehicle_id
    assert created["note"] == "Warning light is on"
    assert created["location"] == {"lat": 52.2297, "lon": 21.0122, "accuracy_m": 12.5}

    got = await client.get(f"{INC}/{created['id']}")
    assert got.status_code == 200
    assert got.json() == created


async def test_client_cannot_set_status_or_created_at(client: httpx.AsyncClient) -> None:
    for extra in ({"status": "resolved"}, {"created_at": "2020-01-01T00:00:00.000Z"}):
        r = await client.post(INC, json={"problem_type": "other", **extra})
        assert r.status_code == 422


async def test_every_problem_type_is_accepted(client: httpx.AsyncClient) -> None:
    for pt in ("flat_tyre", "flat_battery", "out_of_fuel", "pothole_damage", "other"):
        r = await client.post(INC, json={"problem_type": pt})
        assert r.status_code == 201, pt


async def test_missing_or_unknown_problem_type_is_422(client: httpx.AsyncClient) -> None:
    for body in ({}, {"problem_type": "engine_fire"}, {"problem_type": None}):
        r = await client.post(INC, json=body)
        assert r.status_code == 422
        assert r.headers["content-type"].startswith("application/problem+json")
        p = r.json()
        assert p["reason"] == "validation_error"
        assert p["errors"][0]["field"] == "problem_type"


async def test_unknown_vehicle_id_is_422_on_that_field(client: httpx.AsyncClient) -> None:
    r = await client.post(INC, json={"problem_type": "flat_tyre", "vehicle_id": 999})
    assert r.status_code == 422
    p = r.json()
    assert p["reason"] == "validation_error"
    assert p["errors"] == [{"field": "vehicle_id", "message": "Unknown vehicle"}]
    # Nothing was stored.
    assert (await client.get(f"{INC}/1")).status_code == 404


async def test_blank_note_is_null_and_overlong_note_is_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(INC, json={"problem_type": "other", "note": "   "})
    assert r.status_code == 201
    assert r.json()["note"] is None
    r = await client.post(INC, json={"problem_type": "other", "note": "x" * 281})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "note"


async def test_invalid_location_is_rejected(client: httpx.AsyncClient) -> None:
    for location in (
        {"lat": 91, "lon": 0},
        {"lat": 0, "lon": 181},
        {"lat": 52.0},
        {"lat": 52.0, "lon": 21.0, "accuracy_m": -1},
    ):
        r = await client.post(INC, json={"problem_type": "other", "location": location})
        assert r.status_code == 422, location


async def test_location_without_accuracy(client: httpx.AsyncClient) -> None:
    r = await client.post(INC, json={"problem_type": "other", "location": {"lat": 1, "lon": 2}})
    assert r.status_code == 201
    assert r.json()["location"] == {"lat": 1.0, "lon": 2.0, "accuracy_m": None}


async def test_repeated_idempotency_key_returns_the_existing_incident(
    client: httpx.AsyncClient,
) -> None:
    headers = {"Idempotency-Key": "6f1c1d0e-6a43-4c55-9c7e-1d2f3a4b5c6d"}
    first = await client.post(INC, json={"problem_type": "flat_tyre"}, headers=headers)
    assert first.status_code == 201
    again = await client.post(INC, json={"problem_type": "flat_tyre"}, headers=headers)
    assert again.status_code == 200
    assert again.json() == first.json()


async def test_same_key_with_a_different_body_still_returns_the_existing_incident(
    client: httpx.AsyncClient,
) -> None:
    headers = {"Idempotency-Key": "k-1"}
    first = await client.post(INC, json={"problem_type": "flat_tyre"}, headers=headers)
    # Even an unknown vehicle: the key wins, because the first request already committed.
    again = await client.post(
        INC, json={"problem_type": "other", "vehicle_id": 999}, headers=headers
    )
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert again.json()["problem_type"] == "flat_tyre"


async def test_different_keys_and_no_key_create_separate_incidents(
    client: httpx.AsyncClient,
) -> None:
    ids = set()
    for headers in ({"Idempotency-Key": "a"}, {"Idempotency-Key": "b"}, {}, {}):
        r = await client.post(INC, json={"problem_type": "other"}, headers=headers)
        assert r.status_code == 201
        ids.add(r.json()["id"])
    assert len(ids) == 4


async def test_concurrent_requests_with_one_key_create_one_incident(
    client: httpx.AsyncClient,
) -> None:
    headers = {"Idempotency-Key": "race"}
    responses = await asyncio.gather(
        *(client.post(INC, json={"problem_type": "other"}, headers=headers) for _ in range(5))
    )
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 200, 201]
    assert len({r.json()["id"] for r in responses}) == 1


async def test_invalid_idempotency_key_is_422(client: httpx.AsyncClient) -> None:
    for key in ("", "x" * 201):
        r = await client.post(INC, json={"problem_type": "other"}, headers={"Idempotency-Key": key})
        assert r.status_code == 422, key
        assert r.json()["errors"][0]["field"] == "Idempotency-Key"


async def test_get_missing_incident_is_404(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{INC}/12345")
    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"
    assert (await client.get(f"{INC}/0")).status_code == 422


async def test_deleting_the_vehicle_keeps_the_incident(client: httpx.AsyncClient) -> None:
    vehicle_id = await make_vehicle(client)
    r = await client.post(INC, json={"problem_type": "flat_tyre", "vehicle_id": vehicle_id})
    incident_id = r.json()["id"]
    assert (await client.delete(f"{V}/{vehicle_id}")).status_code == 204

    got = await client.get(f"{INC}/{incident_id}")
    assert got.status_code == 200
    assert got.json()["vehicle_id"] is None
