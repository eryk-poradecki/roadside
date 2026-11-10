import httpx

V = "/api/v1/vehicles"


async def make(client: httpx.AsyncClient, **kw: object) -> dict[str, object]:
    r = await client.post(V, json={"name": "Golf", **kw})
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def test_create_returns_201_location_and_defaults_null(client: httpx.AsyncClient) -> None:
    r = await client.post(V, json={"name": "Golf"})
    assert r.status_code == 201
    body = r.json()
    assert r.headers["location"] == f"{V}/{body['id']}"
    assert isinstance(body["id"], int)
    assert body["name"] == "Golf"
    for f in (
        "make_model",
        "year",
        "fuel_type",
        "transmission",
        "tyre_size",
        "spare_wheel",
        "wheel_locks",
        "lock_key_location",
        "registration",
        "assistance_insurer",
        "assistance_phone",
        "policy_number",
    ):
        assert body[f] is None
    assert body["created_at"].endswith("Z")


async def test_create_with_all_fields_and_read_back(client: httpx.AsyncClient) -> None:
    v = await make(
        client,
        make_model="VW Golf",
        year=2019,
        fuel_type="diesel",
        transmission="manual",
        tyre_size="205/55 R16",
        spare_wheel="space_saver",
        wheel_locks=True,
        lock_key_location="glovebox",
        registration="WX 12345",
        assistance_insurer="PZU",
        assistance_phone="+48123456789",
        policy_number="P1",
    )
    r = await client.get(f"{V}/{v['id']}")
    assert r.status_code == 200
    assert r.json() == v


async def test_name_is_required_and_blank_rejected(client: httpx.AsyncClient) -> None:
    for body in ({}, {"name": ""}, {"name": "   "}):
        r = await client.post(V, json=body)
        assert r.status_code == 422
        assert r.headers["content-type"].startswith("application/problem+json")
        p = r.json()
        assert p["reason"] == "validation_error"
        assert p["status"] == 422
        assert p["errors"][0]["field"] == "name"


async def test_invalid_enum_and_year_rejected(client: httpx.AsyncClient) -> None:
    assert (await client.post(V, json={"name": "a", "fuel_type": "steam"})).status_code == 422
    assert (await client.post(V, json={"name": "a", "year": 1700})).status_code == 422
    assert (await client.post(V, json={"name": "a", "transmission": "cvt"})).status_code == 422


async def test_lock_key_location_only_when_wheel_locks_true(client: httpx.AsyncClient) -> None:
    r = await client.post(V, json={"name": "a", "wheel_locks": False, "lock_key_location": "x"})
    assert r.status_code == 422


async def test_overlong_text_rejected(client: httpx.AsyncClient) -> None:
    assert (await client.post(V, json={"name": "x" * 500})).status_code == 422


async def test_first_vehicle_becomes_default_second_does_not(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A")
    b = await make(client, name="B")
    assert a["is_default"] is True
    assert b["is_default"] is False


async def test_is_default_false_opts_out_when_none_exists(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A", is_default=False)
    assert a["is_default"] is False


async def test_new_default_unsets_old(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A")
    b = await make(client, name="B", is_default=True)
    assert b["is_default"] is True
    assert (await client.get(f"{V}/{a['id']}")).json()["is_default"] is False


async def test_list_default_first_then_oldest(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A")
    b = await make(client, name="B")
    c = await make(client, name="C", is_default=True)
    ids = [v["id"] for v in (await client.get(V)).json()]
    assert ids == [c["id"], a["id"], b["id"]]


async def test_put_replaces_everything_and_can_change_default(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A", year=2000)
    b = await make(client, name="B")
    r = await client.put(f"{V}/{b['id']}", json={"name": "B2", "is_default": True})
    assert r.status_code == 200
    assert r.json()["name"] == "B2"
    assert r.json()["is_default"] is True
    assert (await client.get(f"{V}/{a['id']}")).json()["is_default"] is False
    r = await client.put(f"{V}/{a['id']}", json={"name": "A2"})
    assert r.json()["year"] is None  # full replacement
    assert r.json()["is_default"] is False  # omitted keeps current


async def test_put_default_false_leaves_none(client: httpx.AsyncClient) -> None:
    a = await make(client, name="A")
    r = await client.put(f"{V}/{a['id']}", json={"name": "A", "is_default": False})
    assert r.json()["is_default"] is False
    assert all(not v["is_default"] for v in (await client.get(V)).json())


async def test_delete_default_leaves_none_and_next_add_becomes_default(
    client: httpx.AsyncClient,
) -> None:
    a = await make(client, name="A")
    b = await make(client, name="B")
    assert (await client.delete(f"{V}/{a['id']}")).status_code == 204
    assert (await client.get(f"{V}/{b['id']}")).json()["is_default"] is False
    c = await make(client, name="C")
    assert c["is_default"] is True


async def test_missing_vehicle_is_404_problem(client: httpx.AsyncClient) -> None:
    for r in (
        await client.get(f"{V}/999"),
        await client.put(f"{V}/999", json={"name": "x"}),
        await client.delete(f"{V}/999"),
    ):
        assert r.status_code == 404
        assert r.json()["reason"] == "not_found"
        assert r.headers["content-type"].startswith("application/problem+json")


async def test_non_integer_id_is_422(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{V}/abc")
    assert r.status_code == 422
    assert r.json()["reason"] == "validation_error"


async def test_blank_optional_text_is_stored_as_unknown(client: httpx.AsyncClient) -> None:
    v = await make(client, registration="  ")
    assert v["registration"] is None


async def test_huge_id_is_422_not_500(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"{V}/99999999999999999999")).status_code == 422


async def test_405_keeps_allow_header(client: httpx.AsyncClient) -> None:
    r = await client.delete(V)
    assert r.status_code == 405
    assert "allow" in r.headers
