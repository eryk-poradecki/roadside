from collections.abc import AsyncIterator
from typing import Annotated

import aiosqlite
from fastapi import Depends, Request

from app.db.connection import connect
from app.integrations.llm.base import LLMProvider
from app.integrations.nominatim import ReverseGeocoder
from app.integrations.overpass import PlaceSource
from app.repositories.ai_turns import SqliteAiTurnRepository
from app.repositories.incidents import SqliteIncidentRepository
from app.repositories.nearby import SqliteNearbyRepository
from app.repositories.photos import PhotoFiles, SqlitePhotoRepository
from app.repositories.vehicles import SqliteVehicleRepository
from app.services.assistant import AssistantService, TurnLocks
from app.services.incidents import IncidentService
from app.services.location import LocationResolver
from app.services.nearby import NearbyService
from app.services.photos import PhotoService
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


def get_llm_provider(request: Request) -> LLMProvider:
    """Built once in the app factory from settings; tests override it with a fake."""
    provider: LLMProvider = request.app.state.llm_provider
    return provider


def get_turn_locks(request: Request) -> TurnLocks:
    locks: TurnLocks = request.app.state.turn_locks
    return locks


def get_geocoder(request: Request) -> ReverseGeocoder | None:
    """None in demo mode; tests override it with a fake."""
    geocoder: ReverseGeocoder | None = request.app.state.geocoder
    return geocoder


def get_location_resolver(
    settings: Annotated[Settings, Depends(get_settings)],
    geocoder: Annotated[ReverseGeocoder | None, Depends(get_geocoder)],
) -> LocationResolver:
    return LocationResolver(
        geocoder,
        max_gps_accuracy_m=settings.location_max_gps_accuracy_m,
        max_road_distance_m=settings.location_max_road_distance_m,
    )


def get_photo_files(settings: Annotated[Settings, Depends(get_settings)]) -> PhotoFiles:
    return PhotoFiles(settings.upload_dir)


def get_incident_service(
    conn: Connection,
    location: Annotated[LocationResolver, Depends(get_location_resolver)],
    files: Annotated[PhotoFiles, Depends(get_photo_files)],
) -> IncidentService:
    return IncidentService(
        conn,
        SqliteIncidentRepository(conn),
        SqliteVehicleRepository(conn),
        SqliteAiTurnRepository(conn),
        SqliteNearbyRepository(conn),
        SqlitePhotoRepository(conn),
        files,
        location,
    )


def get_photo_service(
    conn: Connection,
    settings: Annotated[Settings, Depends(get_settings)],
    files: Annotated[PhotoFiles, Depends(get_photo_files)],
) -> PhotoService:
    return PhotoService(
        conn,
        SqliteIncidentRepository(conn),
        SqlitePhotoRepository(conn),
        files,
        max_photos=settings.max_photos,
        demo_mode=settings.demo_mode,
    )


def get_place_source(request: Request) -> PlaceSource | None:
    """None in demo mode; tests override it with a fake."""
    source: PlaceSource | None = request.app.state.place_source
    return source


def get_nearby_service(
    conn: Connection,
    source: Annotated[PlaceSource | None, Depends(get_place_source)],
) -> NearbyService:
    return NearbyService(conn, SqliteIncidentRepository(conn), SqliteNearbyRepository(conn), source)


def get_assistant_service(
    conn: Connection,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
    locks: Annotated[TurnLocks, Depends(get_turn_locks)],
    location: Annotated[LocationResolver, Depends(get_location_resolver)],
) -> AssistantService:
    return AssistantService(
        conn,
        SqliteIncidentRepository(conn),
        SqliteVehicleRepository(conn),
        SqliteAiTurnRepository(conn),
        provider,
        locks,
        settings.llm_turn_budget_s,
        location,
    )
