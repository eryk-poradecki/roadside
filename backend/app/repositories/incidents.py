import sqlite3
from typing import Protocol

import aiosqlite

from app.domain.incident import Incident, IncidentStatus, Location, NewIncident, ProblemType

_SELECT = (
    "SELECT id, problem_type, status, vehicle_id, note, lat, lon, accuracy_m, location_label, "
    "created_at, updated_at FROM incidents"
)


class IncidentRepository(Protocol):
    async def get(self, incident_id: int) -> Incident | None: ...
    async def get_by_idempotency_key(self, key: str) -> Incident | None: ...
    async def insert(self, data: NewIncident, idempotency_key: str | None, now: str) -> int: ...


def _to_domain(r: sqlite3.Row) -> Incident:
    location = (
        Location(lat=r["lat"], lon=r["lon"], accuracy_m=r["accuracy_m"])
        if r["lat"] is not None
        else None
    )
    return Incident(
        id=r["id"],
        problem_type=ProblemType(r["problem_type"]),
        status=IncidentStatus(r["status"]),
        vehicle_id=r["vehicle_id"],
        note=r["note"],
        location=location,
        location_label=r["location_label"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


class SqliteIncidentRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def get(self, incident_id: int) -> Incident | None:
        cur = await self._conn.execute(f"{_SELECT} WHERE id = ?", (incident_id,))
        row = await cur.fetchone()
        return _to_domain(row) if row else None

    async def get_by_idempotency_key(self, key: str) -> Incident | None:
        cur = await self._conn.execute(
            f"{_SELECT} WHERE idempotency_key = ?",
            (key,),
        )
        row = await cur.fetchone()
        return _to_domain(row) if row else None

    async def insert(self, data: NewIncident, idempotency_key: str | None, now: str) -> int:
        loc = data.location
        cur = await self._conn.execute(
            "INSERT INTO incidents (problem_type, status, vehicle_id, note, lat, lon, accuracy_m, "
            "idempotency_key, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                data.problem_type.value,
                IncidentStatus.OPEN.value,
                data.vehicle_id,
                data.note,
                loc.lat if loc else None,
                loc.lon if loc else None,
                loc.accuracy_m if loc else None,
                idempotency_key,
                now,
                now,
            ),
        )
        if cur.lastrowid is None:
            raise RuntimeError("INSERT returned no row id")
        return cur.lastrowid
