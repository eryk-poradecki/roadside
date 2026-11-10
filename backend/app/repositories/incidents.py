import sqlite3
from typing import Protocol

import aiosqlite

from app.domain.incident import Incident, IncidentStatus, Location, NewIncident, ProblemType
from app.domain.location_context import LocationContext, RoadClass, Settlement

_SELECT = (
    "SELECT id, problem_type, status, vehicle_id, note, lat, lon, accuracy_m, location_label, "
    "road_class, settlement, created_at, updated_at FROM incidents"
)


class IncidentRepository(Protocol):
    async def get(self, incident_id: int) -> Incident | None: ...
    async def get_by_idempotency_key(self, key: str) -> Incident | None: ...
    async def insert(self, data: NewIncident, idempotency_key: str | None, now: str) -> int: ...
    async def list_page(
        self, status: IncidentStatus | None, vehicle_id: int | None, limit: int, offset: int
    ) -> tuple[list[Incident], int]: ...
    async def update(self, incident: Incident, now: str) -> None: ...
    async def delete(self, incident_id: int) -> bool: ...


def _to_domain(r: sqlite3.Row) -> Incident:
    location = (
        Location(lat=r["lat"], lon=r["lon"], accuracy_m=r["accuracy_m"])
        if r["lat"] is not None
        else None
    )
    context = (
        LocationContext(RoadClass(r["road_class"]), Settlement(r["settlement"]))
        if r["road_class"] is not None
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
        location_context=context,
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

    async def list_page(
        self, status: IncidentStatus | None, vehicle_id: int | None, limit: int, offset: int
    ) -> tuple[list[Incident], int]:
        """One page newest first (id breaks ties within a millisecond) and the filtered total."""
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if vehicle_id is not None:
            clauses.append("vehicle_id = ?")
            params.append(vehicle_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = await self._conn.execute(f"SELECT count(*) FROM incidents{where}", params)  # noqa: S608
        row = await cur.fetchone()
        total = int(row[0]) if row else 0
        cur = await self._conn.execute(
            f"{_SELECT}{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [_to_domain(r) for r in await cur.fetchall()], total

    async def update(self, incident: Incident, now: str) -> None:
        """Write every driver-editable field of `incident`. The status is one of them."""
        loc, ctx = incident.location, incident.location_context
        await self._conn.execute(
            "UPDATE incidents SET problem_type = ?, status = ?, vehicle_id = ?, note = ?, "
            "lat = ?, lon = ?, accuracy_m = ?, location_label = ?, road_class = ?, settlement = ?, "
            "updated_at = ? WHERE id = ?",
            (
                incident.problem_type.value,
                incident.status.value,
                incident.vehicle_id,
                incident.note,
                loc.lat if loc else None,
                loc.lon if loc else None,
                loc.accuracy_m if loc else None,
                incident.location_label,
                ctx.road_class.value if ctx else None,
                ctx.settlement.value if ctx else None,
                now,
                incident.id,
            ),
        )

    async def delete(self, incident_id: int) -> bool:
        """Hard delete. Owned rows go with it through ON DELETE CASCADE (ADR 0001, 0006)."""
        cur = await self._conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
        return cur.rowcount > 0
