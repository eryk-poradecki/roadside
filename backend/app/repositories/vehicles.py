import sqlite3
from typing import Protocol

import aiosqlite

from app.domain.vehicle import FuelType, SpareWheel, Transmission, Vehicle, VehicleFacts

_COLUMNS = (
    "name, make_model, year, fuel_type, transmission, tyre_size, spare_wheel, wheel_locks, "
    "lock_key_location, registration, assistance_insurer, assistance_phone, policy_number"
)


class VehicleRepository(Protocol):
    async def list_all(self) -> list[Vehicle]: ...
    async def get(self, vehicle_id: int) -> Vehicle | None: ...
    async def has_default(self) -> bool: ...
    async def clear_default(self, now: str) -> None: ...
    async def insert(self, facts: VehicleFacts, is_default: bool, now: str) -> int: ...
    async def update(
        self, vehicle_id: int, facts: VehicleFacts, is_default: bool, now: str
    ) -> None: ...
    async def delete(self, vehicle_id: int) -> bool: ...


def _values(f: VehicleFacts) -> tuple[object, ...]:
    return (
        f.name,
        f.make_model,
        f.year,
        f.fuel_type.value if f.fuel_type else None,
        f.transmission.value if f.transmission else None,
        f.tyre_size,
        f.spare_wheel.value if f.spare_wheel else None,
        None if f.wheel_locks is None else int(f.wheel_locks),
        f.lock_key_location,
        f.registration,
        f.assistance_insurer,
        f.assistance_phone,
        f.policy_number,
    )


def _to_domain(r: sqlite3.Row) -> Vehicle:
    facts = VehicleFacts(
        name=r["name"],
        make_model=r["make_model"],
        year=r["year"],
        fuel_type=FuelType(r["fuel_type"]) if r["fuel_type"] else None,
        transmission=Transmission(r["transmission"]) if r["transmission"] else None,
        tyre_size=r["tyre_size"],
        spare_wheel=SpareWheel(r["spare_wheel"]) if r["spare_wheel"] else None,
        wheel_locks=None if r["wheel_locks"] is None else bool(r["wheel_locks"]),
        lock_key_location=r["lock_key_location"],
        registration=r["registration"],
        assistance_insurer=r["assistance_insurer"],
        assistance_phone=r["assistance_phone"],
        policy_number=r["policy_number"],
    )
    return Vehicle(
        id=r["id"],
        facts=facts,
        is_default=bool(r["is_default"]),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


class SqliteVehicleRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def list_all(self) -> list[Vehicle]:
        cur = await self._conn.execute(
            f"SELECT id, is_default, created_at, updated_at, {_COLUMNS} "  # noqa: S608
            "FROM vehicles ORDER BY is_default DESC, created_at ASC, id ASC"
        )
        return [_to_domain(r) for r in await cur.fetchall()]

    async def get(self, vehicle_id: int) -> Vehicle | None:
        cur = await self._conn.execute(
            f"SELECT id, is_default, created_at, updated_at, {_COLUMNS} "  # noqa: S608
            "FROM vehicles WHERE id = ?",
            (vehicle_id,),
        )
        row = await cur.fetchone()
        return _to_domain(row) if row else None

    async def has_default(self) -> bool:
        cur = await self._conn.execute("SELECT 1 FROM vehicles WHERE is_default = 1")
        return await cur.fetchone() is not None

    async def clear_default(self, now: str) -> None:
        await self._conn.execute(
            "UPDATE vehicles SET is_default = 0, updated_at = ? WHERE is_default = 1", (now,)
        )

    async def insert(self, facts: VehicleFacts, is_default: bool, now: str) -> int:
        cur = await self._conn.execute(
            f"INSERT INTO vehicles ({_COLUMNS}, is_default, created_at, updated_at) "  # noqa: S608
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (*_values(facts), int(is_default), now, now),
        )
        if cur.lastrowid is None:
            raise RuntimeError("INSERT returned no row id")
        return cur.lastrowid

    async def update(
        self, vehicle_id: int, facts: VehicleFacts, is_default: bool, now: str
    ) -> None:
        sets = ", ".join(f"{c.strip()} = ?" for c in _COLUMNS.split(","))
        await self._conn.execute(
            f"UPDATE vehicles SET {sets}, is_default = ?, updated_at = ? WHERE id = ?",  # noqa: S608
            (*_values(facts), int(is_default), now, vehicle_id),
        )

    async def delete(self, vehicle_id: int) -> bool:
        cur = await self._conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        return cur.rowcount > 0
