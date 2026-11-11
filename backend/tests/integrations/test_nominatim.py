import asyncio
import time
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.integrations.nominatim import NominatimGeocoder

URL = "https://nominatim.test/reverse"
UA = "Roadside/0.1.0 (+https://example.test)"
RESULT = {"category": "highway", "type": "primary", "lat": "52.0", "lon": "21.0", "address": {}}


@pytest.fixture
async def geocoder() -> AsyncIterator[NominatimGeocoder]:
    g = NominatimGeocoder(
        base_url="https://nominatim.test/", user_agent=UA, timeout_s=0.5, min_interval_s=0
    )
    yield g
    await g.aclose()


@respx.mock
async def test_sends_the_adr_parameters_and_user_agent(geocoder: NominatimGeocoder) -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=RESULT))

    assert await geocoder.reverse(52.0, 21.0, "pl") == RESULT

    request = route.calls.last.request
    params = request.url.params
    assert params["format"] == "jsonv2"
    assert params["zoom"] == "17"
    assert params["addressdetails"] == "1"
    assert params["extratags"] == "1"
    assert params["accept-language"] == "pl"
    assert request.headers["user-agent"] == UA


@respx.mock
async def test_a_timeout_gives_none(geocoder: NominatimGeocoder) -> None:
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    assert await geocoder.reverse(52.0, 21.0, "en") is None


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"error": "Unable to geocode"}),
        httpx.Response(200, json=[1, 2]),
    ],
)
async def test_any_failure_gives_none(
    geocoder: NominatimGeocoder, response: httpx.Response
) -> None:
    respx.get(URL).mock(return_value=response)
    assert await geocoder.reverse(52.0, 21.0, "en") is None


@respx.mock
async def test_an_unreachable_server_gives_none(geocoder: NominatimGeocoder) -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectError("down"))
    assert await geocoder.reverse(52.0, 21.0, "en") is None


@respx.mock
async def test_results_are_cached_by_rounded_coordinates(geocoder: NominatimGeocoder) -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=RESULT))

    await geocoder.reverse(52.000001, 21.000001, "en")
    await geocoder.reverse(52.000002, 21.000002, "en")

    assert route.call_count == 1


@respx.mock
async def test_the_timeout_bounds_the_whole_request(geocoder: NominatimGeocoder) -> None:
    """httpx times each phase separately; the ADR's 3 s is for the whole lookup."""

    async def trickle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json=RESULT)

    respx.get(URL).mock(side_effect=trickle)
    started = time.monotonic()

    assert await geocoder.reverse(52.0, 21.0, "en") is None
    assert time.monotonic() - started < 1.5
