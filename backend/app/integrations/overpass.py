"""Overpass lookup for nearby places (ADR 0004).

One query covers all four categories. Public Overpass is slow and flaky (research #5): the
endpoints are tried primary first, then the mirrors, with a doubling backoff between attempts,
and HTTP 200 is not trusted on its own (a server-side timeout answers 200 with a `remark`).
Coordinates are never logged.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.domain.nearby import CATEGORY_TAGS

logger = logging.getLogger(__name__)


class NearbyUnavailable(Exception):
    """No endpoint gave a usable answer in time."""


@dataclass(frozen=True, slots=True)
class OverpassResult:
    elements: list[object]
    # The endpoint that answered, stored with the snapshot.
    endpoint: str


class PlaceSource(Protocol):
    async def search(self, lat: float, lon: float, radius_m: int) -> OverpassResult:
        """Raises `NearbyUnavailable` when the lookup failed."""
        ...


class _Retry(Exception):
    """This attempt failed; the next endpoint may still answer."""


def build_query(lat: float, lon: float, radius_m: int, timeout_s: int) -> str:
    around = f"around:{radius_m},{lat:.6f},{lon:.6f}"
    clauses = "\n".join(f'  nwr({around})["{k}"="{v}"];' for k, v, _ in CATEGORY_TAGS)
    # A small declared timeout is admitted sooner and ends before the client gives up.
    return f"[out:json][timeout:{timeout_s}];\n(\n{clauses}\n);\nout center tags;\n"


class OverpassClient:
    def __init__(
        self,
        *,
        urls: Sequence[str],
        user_agent: str,
        timeout_s: float = 25.0,
        budget_s: float = 60.0,
        attempts: int = 3,
        backoff_s: float = 1.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not urls:
            raise ValueError("Overpass needs at least one endpoint")
        self._urls = list(urls)
        self._headers = {"User-Agent": user_agent}
        self._timeout_s = timeout_s
        self._budget_s = budget_s
        self._attempts = attempts
        self._backoff_s = backoff_s
        self._sleep = sleep
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, lat: float, lon: float, radius_m: int) -> OverpassResult:
        query = build_query(lat, lon, radius_m, max(1, int(self._timeout_s)))
        try:
            async with asyncio.timeout(self._budget_s):
                for attempt in range(self._attempts):
                    if attempt > 0:
                        await self._sleep(self._backoff_s * 2 ** (attempt - 1))
                    url = self._urls[attempt % len(self._urls)]
                    try:
                        return await self._attempt(url, query)
                    except _Retry as exc:
                        logger.info("overpass attempt %d failed: %s", attempt + 1, exc)
        except TimeoutError:
            logger.info("overpass ran out of its %.0f s budget", self._budget_s)
        raise NearbyUnavailable

    async def _attempt(self, url: str, query: str) -> OverpassResult:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout_s), headers=self._headers
            )
        try:
            # httpx times each phase separately; this bounds the whole attempt.
            async with asyncio.timeout(self._timeout_s):
                response = await self._client.post(url, data={"data": query})
        except TimeoutError as exc:
            raise _Retry("timed out") from exc
        except httpx.HTTPError as exc:
            raise _Retry(type(exc).__name__) from exc
        if response.status_code == 400:
            # The query itself is wrong: another endpoint would refuse it too.
            logger.warning("overpass refused the query (HTTP 400)")
            raise NearbyUnavailable
        if response.status_code != 200:
            raise _Retry(f"HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise _Retry("invalid JSON") from exc
        if not isinstance(body, dict):
            raise _Retry("unexpected JSON")
        # A server-side timeout or quota error answers 200 with a remark and maybe no
        # elements: never mistake it for "nothing nearby".
        if body.get("remark"):
            raise _Retry("remark on HTTP 200")
        elements = body.get("elements")
        if not isinstance(elements, list):
            raise _Retry("no elements")
        return OverpassResult(elements=elements, endpoint=url)
