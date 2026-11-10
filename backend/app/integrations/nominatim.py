"""Nominatim reverse geocoding for the location context (ADR 0004).

Any failure gives `None`, so the caller falls back to an unknown context and the AI turn
still runs. Coordinates are never logged.
"""

import asyncio
import logging
import time
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

# ~11 m at 4 decimal places: one lookup per spot, well under the matched-road threshold.
_CACHE_DECIMALS = 4
_CACHE_SIZE = 256


class ReverseGeocoder(Protocol):
    async def reverse(self, lat: float, lon: float, locale: str) -> dict[str, Any] | None: ...


class NominatimGeocoder:
    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        timeout_s: float = 3.0,
        min_interval_s: float = 1.0,
    ) -> None:
        self._url = base_url.rstrip("/") + "/reverse"
        self._headers = {"User-Agent": user_agent}
        self._timeout = httpx.Timeout(timeout_s)
        self._min_interval_s = min_interval_s
        # The public server's policy is at most 1 request/s.
        self._lock = asyncio.Lock()
        self._last_request = float("-inf")
        self._cache: dict[tuple[float, float, str], dict[str, Any]] = {}
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def reverse(self, lat: float, lon: float, locale: str) -> dict[str, Any] | None:
        key = (round(lat, _CACHE_DECIMALS), round(lon, _CACHE_DECIMALS), locale)
        if key in self._cache:
            return self._cache[key]
        result = await self._fetch(lat, lon, locale)
        if result is not None:
            if len(self._cache) >= _CACHE_SIZE:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = result
        return result

    async def _fetch(self, lat: float, lon: float, locale: str) -> dict[str, Any] | None:
        params = {
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "format": "jsonv2",
            "zoom": "17",
            "addressdetails": "1",
            "extratags": "1",
            "accept-language": locale,
        }
        try:
            async with self._lock:
                wait = self._last_request + self._min_interval_s - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last_request = time.monotonic()
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=self._timeout, headers=self._headers)
                response = await self._client.get(self._url, params=params)
        except httpx.HTTPError as exc:
            logger.info("nominatim unavailable (%s)", type(exc).__name__)
            return None
        if response.status_code != 200:
            logger.info("nominatim answered HTTP %d", response.status_code)
            return None
        try:
            body = response.json()
        except ValueError:
            logger.info("nominatim answered invalid JSON")
            return None
        if not isinstance(body, dict) or "error" in body:
            return None
        return body
