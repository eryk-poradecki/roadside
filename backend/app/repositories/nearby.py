import json
from dataclasses import asdict
from typing import Any, Protocol

import aiosqlite

from app.domain.nearby import NearbyCategory, NearbySnapshot, Place


class NearbyRepository(Protocol):
    async def get(self, incident_id: int) -> NearbySnapshot | None: ...
    async def replace(self, incident_id: int, snapshot: NearbySnapshot) -> None: ...
    async def delete(self, incident_id: int) -> None: ...


def _place(d: dict[str, Any]) -> Place:
    return Place(**{**d, "category": NearbyCategory(d["category"])})


class SqliteNearbyRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def get(self, incident_id: int) -> NearbySnapshot | None:
        cur = await self._conn.execute(
            "SELECT places, radius_km, fetched_at, source FROM incident_nearby "
            "WHERE incident_id = ?",
            (incident_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return NearbySnapshot(
            places=tuple(_place(p) for p in json.loads(row["places"])),
            radius_km=row["radius_km"],
            fetched_at=row["fetched_at"],
            source=row["source"],
        )

    async def replace(self, incident_id: int, snapshot: NearbySnapshot) -> None:
        places = json.dumps([asdict(p) for p in snapshot.places], ensure_ascii=False)
        await self._conn.execute(
            "INSERT INTO incident_nearby (incident_id, places, radius_km, fetched_at, source) "
            "VALUES (?,?,?,?,?) ON CONFLICT (incident_id) DO UPDATE SET places = excluded.places, "
            "radius_km = excluded.radius_km, fetched_at = excluded.fetched_at, "
            "source = excluded.source",
            (incident_id, places, snapshot.radius_km, snapshot.fetched_at, snapshot.source),
        )

    async def delete(self, incident_id: int) -> None:
        await self._conn.execute(
            "DELETE FROM incident_nearby WHERE incident_id = ?", (incident_id,)
        )
