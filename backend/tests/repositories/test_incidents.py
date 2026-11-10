from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest

from app.db.connection import connect
from app.db.migrate import migrate
from app.domain.incident import NewIncident, ProblemType
from app.domain.vehicle import VehicleFacts
from app.repositories.incidents import SqliteIncidentRepository
from app.repositories.vehicles import SqliteVehicleRepository

NOW = "2026-01-01T00:00:00.000Z"


@pytest.fixture
async def conn(tmp_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    db = tmp_path / "r.db"
    migrate(db)
    c = await connect(db)
    try:
        yield c
    finally:
        await c.close()


async def _child_tables(conn: aiosqlite.Connection) -> list[str]:
    """Every table with a foreign key to incidents, as later tickets add them."""
    cur = await conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = [r[0] for r in await cur.fetchall()]
    children = []
    for t in tables:
        fks = await (await conn.execute(f"PRAGMA foreign_key_list({t})")).fetchall()
        if any(fk["table"] == "incidents" for fk in fks):
            children.append(t)
    return children


async def test_foreign_keys_to_incidents_cascade(conn: aiosqlite.Connection) -> None:
    # Any table that references incidents must cascade, so a hard delete removes everything
    # the incident owns (ADR 0001, ADR 0006).
    for t in await _child_tables(conn):
        fks = await (await conn.execute(f"PRAGMA foreign_key_list({t})")).fetchall()
        for fk in fks:
            if fk["table"] == "incidents":
                assert fk["on_delete"] == "CASCADE", t


async def test_delete_removes_the_incident(conn: aiosqlite.Connection) -> None:
    repo = SqliteIncidentRepository(conn)
    keep = await repo.insert(NewIncident(ProblemType.OTHER), None, NOW)
    gone = await repo.insert(NewIncident(ProblemType.FLAT_TYRE), "k", NOW)
    assert await repo.delete(gone) is True
    assert await repo.get(gone) is None
    assert await repo.get_by_idempotency_key("k") is None
    assert await repo.get(keep) is not None
    assert await repo.delete(gone) is False


async def test_deleting_a_vehicle_sets_the_incident_vehicle_to_null(
    conn: aiosqlite.Connection,
) -> None:
    vehicles = SqliteVehicleRepository(conn)
    incidents = SqliteIncidentRepository(conn)
    vehicle_id = await vehicles.insert(VehicleFacts(name="Golf"), True, NOW)
    incident_id = await incidents.insert(
        NewIncident(ProblemType.FLAT_TYRE, vehicle_id=vehicle_id), None, NOW
    )
    assert await vehicles.delete(vehicle_id)
    incident = await incidents.get(incident_id)
    assert incident is not None
    assert incident.vehicle_id is None
