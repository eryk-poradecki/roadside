from collections.abc import AsyncIterator
from typing import Annotated

import aiosqlite
from fastapi import Depends, Request

from app.db.connection import connect
from app.repositories.vehicles import SqliteVehicleRepository
from app.services.vehicles import VehicleService
from app.settings import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_connection(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[aiosqlite.Connection]:
    """One connection per request."""
    conn = await connect(settings.database_path)
    try:
        yield conn
    finally:
        await conn.close()


Connection = Annotated[aiosqlite.Connection, Depends(get_connection)]


def get_vehicle_service(conn: Connection) -> VehicleService:
    return VehicleService(conn, SqliteVehicleRepository(conn))
