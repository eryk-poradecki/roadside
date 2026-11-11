import asyncio
import time
from collections.abc import AsyncIterator
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from app.integrations.overpass import NearbyUnavailable, OverpassClient

PRIMARY = "https://overpass.test/api/interpreter"
MIRROR = "https://mirror.test/api/interpreter"
UA = "Roadside/0.1.0 (+https://example.test)"
BODY = {"elements": [{"type": "node", "id": 1, "lat": 52.0, "lon": 21.0, "tags": {}}]}


class Sleeps:
    """Records backoff waits instead of sleeping."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


@pytest.fixture
def sleeps() -> Sleeps:
    return Sleeps()


@pytest.fixture
async def overpass(sleeps: Sleeps) -> AsyncIterator[OverpassClient]:
    client = OverpassClient(
        urls=[PRIMARY, MIRROR],
        user_agent=UA,
        timeout_s=0.5,
        budget_s=5,
        attempts=3,
        backoff_s=1.0,
        sleep=sleeps,
    )
    yield client
    await client.aclose()


def query_of(request: httpx.Request) -> str:
    return parse_qs(request.content.decode())["data"][0]


@respx.mock
async def test_posts_one_query_for_all_four_categories(overpass: OverpassClient) -> None:
    route = respx.post(PRIMARY).mock(return_value=httpx.Response(200, json=BODY))

    result = await overpass.search(52.2297, 21.0122, 5000)

    assert result.elements == BODY["elements"]
    assert result.endpoint == PRIMARY
    request = route.calls.last.request
    assert request.headers["user-agent"] == UA
    query = query_of(request)
    assert query.startswith("[out:json][timeout:")
    for tag in (
        '["shop"="tyres"]',
        '["amenity"="fuel"]',
        '["amenity"="charging_station"]',
        '["shop"="car_repair"]',
    ):
        assert f"nwr(around:5000,52.229700,21.012200){tag};" in query
    assert query.rstrip().endswith("out center tags;")


@respx.mock
async def test_falls_back_to_the_mirror_after_backing_off(
    overpass: OverpassClient, sleeps: Sleeps
) -> None:
    respx.post(PRIMARY).mock(return_value=httpx.Response(502, text="at capacity"))
    mirror = respx.post(MIRROR).mock(return_value=httpx.Response(200, json=BODY))

    result = await overpass.search(52.0, 21.0, 5000)

    assert result.endpoint == MIRROR
    assert mirror.call_count == 1
    assert sleeps.waits == [1.0]


@respx.mock
async def test_backoff_doubles_and_returns_to_the_primary(
    overpass: OverpassClient, sleeps: Sleeps
) -> None:
    primary = respx.post(PRIMARY).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=BODY)]
    )
    respx.post(MIRROR).mock(return_value=httpx.Response(504, text="<html>"))

    result = await overpass.search(52.0, 21.0, 5000)

    assert result.endpoint == PRIMARY
    assert primary.call_count == 2
    assert sleeps.waits == [1.0, 2.0]


@respx.mock
async def test_gives_up_after_the_attempts(overpass: OverpassClient, sleeps: Sleeps) -> None:
    primary = respx.post(PRIMARY).mock(return_value=httpx.Response(503))
    mirror = respx.post(MIRROR).mock(return_value=httpx.Response(503))

    with pytest.raises(NearbyUnavailable):
        await overpass.search(52.0, 21.0, 5000)

    assert primary.call_count + mirror.call_count == 3


@respx.mock
async def test_a_remark_on_http_200_is_a_failure_not_an_empty_result(
    overpass: OverpassClient,
) -> None:
    """A server-side timeout answers 200 with no elements and a `remark`."""
    timed_out = {"elements": [], "remark": 'runtime error: Query timed out in "query"'}
    respx.post(PRIMARY).mock(return_value=httpx.Response(200, json=timed_out))
    respx.post(MIRROR).mock(return_value=httpx.Response(200, json={"elements": []}))

    result = await overpass.search(52.0, 21.0, 5000)

    assert result.endpoint == MIRROR
    assert result.elements == []


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=[1, 2]),
        httpx.Response(200, json={"version": 0.6}),
    ],
)
async def test_a_malformed_200_is_retried(
    overpass: OverpassClient, response: httpx.Response
) -> None:
    respx.post(PRIMARY).mock(return_value=response)
    respx.post(MIRROR).mock(return_value=httpx.Response(200, json=BODY))

    assert (await overpass.search(52.0, 21.0, 5000)).endpoint == MIRROR


@respx.mock
async def test_a_bad_query_is_not_retried(overpass: OverpassClient) -> None:
    primary = respx.post(PRIMARY).mock(return_value=httpx.Response(400, text="parse error"))
    mirror = respx.post(MIRROR).mock(return_value=httpx.Response(200, json=BODY))

    with pytest.raises(NearbyUnavailable):
        await overpass.search(52.0, 21.0, 5000)

    assert (primary.call_count, mirror.call_count) == (1, 0)


@respx.mock
async def test_timeouts_and_connection_errors_move_on(overpass: OverpassClient) -> None:
    respx.post(PRIMARY).mock(side_effect=[httpx.ReadTimeout("slow"), httpx.ConnectError("down")])
    respx.post(MIRROR).mock(side_effect=httpx.ConnectError("down"))

    with pytest.raises(NearbyUnavailable):
        await overpass.search(52.0, 21.0, 5000)


@respx.mock
async def test_the_timeout_bounds_each_whole_attempt(overpass: OverpassClient) -> None:
    """httpx times each phase separately; a trickling answer must still be cut off."""

    async def trickle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json=BODY)

    respx.post(PRIMARY).mock(side_effect=trickle)
    respx.post(MIRROR).mock(return_value=httpx.Response(200, json=BODY))
    started = time.monotonic()

    assert (await overpass.search(52.0, 21.0, 5000)).endpoint == MIRROR
    assert time.monotonic() - started < 2


@respx.mock
async def test_the_budget_bounds_the_whole_lookup() -> None:
    async def trickle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json=BODY)

    respx.post(PRIMARY).mock(side_effect=trickle)
    client = OverpassClient(
        urls=[PRIMARY], user_agent=UA, timeout_s=3, budget_s=0.5, attempts=5, backoff_s=0
    )
    started = time.monotonic()
    try:
        with pytest.raises(NearbyUnavailable):
            await client.search(52.0, 21.0, 5000)
    finally:
        await client.aclose()
    assert time.monotonic() - started < 1.5
