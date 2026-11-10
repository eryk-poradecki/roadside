from collections.abc import AsyncIterator
from typing import Annotated

import aiosqlite
from fastapi import Depends, Request

from app.db.connection import connect
from app.integrations.llm.base import LLMProvider
from app.repositories.ai_turns import SqliteAiTurnRepository
from app.repositories.incidents import SqliteIncidentRepository
from app.repositories.vehicles import SqliteVehicleRepository
from app.services.assistant import AssistantService, TurnLocks
from app.services.incidents import IncidentService
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


def get_incident_service(conn: Connection) -> IncidentService:
    return IncidentService(
        conn,
        SqliteIncidentRepository(conn),
        SqliteVehicleRepository(conn),
        SqliteAiTurnRepository(conn),
    )


def get_llm_provider(request: Request) -> LLMProvider:
    """Built once in the app factory from settings; tests override it with a fake."""
    provider: LLMProvider = request.app.state.llm_provider
    return provider


def get_turn_locks(request: Request) -> TurnLocks:
    locks: TurnLocks = request.app.state.turn_locks
    return locks


def get_assistant_service(
    conn: Connection,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    locks: Annotated[TurnLocks, Depends(get_turn_locks)],
) -> AssistantService:
    return AssistantService(
        conn,
        SqliteIncidentRepository(conn),
        SqliteVehicleRepository(conn),
        SqliteAiTurnRepository(conn),
        provider,
        locks,
        settings.llm_turn_budget_s,
    )
