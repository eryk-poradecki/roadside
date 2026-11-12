import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.db.connection import connect
from app.db.migrate import migrate
from app.errors import install_error_handlers
from app.integrations.llm.factory import build_provider
from app.integrations.nominatim import NominatimGeocoder
from app.integrations.overpass import OverpassClient
from app.integrations.place_recording import PlaceRecorder, load_place_recordings, places_dir
from app.middleware import BodyLimitMiddleware
from app.repositories.vehicles import SqliteVehicleRepository
from app.routers import ai_turns, damage_reports, incidents, meta, nearby, photos, vehicles
from app.services.assistant import TurnLocks
from app.services.demo_vehicles import seed_demo_vehicles
from app.settings import Settings

logger = logging.getLogger("roadside")


def _operation_id(route: APIRoute) -> str:
    # The route function name, so generated clients read `listVehicles`, not a path slug.
    return route.name


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    provider = build_provider(settings)
    # Demo mode makes no Nominatim call (ADR 0004).
    geocoder = (
        None
        if settings.demo_mode
        else NominatimGeocoder(
            base_url=settings.nominatim_url,
            user_agent=settings.osm_user_agent,
            timeout_s=settings.nominatim_timeout_s,
        )
    )

    # Nor any Overpass call: recorded places come with the demo scenarios (ADR 0004).
    place_source = (
        None
        if settings.demo_mode
        else OverpassClient(
            urls=settings.overpass_urls,
            user_agent=settings.osm_user_agent,
            timeout_s=settings.overpass_timeout_s,
            budget_s=settings.overpass_budget_s,
            attempts=settings.overpass_attempts,
            backoff_s=settings.overpass_backoff_s,
        )
    )

    # Demo mode's location context and places come with the scenarios instead (#58), and a
    # recording run writes them next to the AI recordings.
    place_recordings = (
        load_place_recordings(places_dir(settings.llm_recordings_dir)) if settings.demo_mode else {}
    )
    place_recorder = (
        PlaceRecorder(places_dir(settings.llm_recordings_dir)) if settings.llm_record else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        version = migrate(settings.database_path)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        if settings.demo_mode:
            conn = await connect(settings.database_path)
            try:
                seeded = await seed_demo_vehicles(conn, SqliteVehicleRepository(conn))
            finally:
                await conn.close()
            if seeded:
                logger.info("seeded %d demo vehicles", seeded)
        logger.info(
            "database ready at schema version %d (demo_mode=%s, llm_provider=%s)",
            version,
            settings.demo_mode,
            provider.name,
        )
        try:
            yield
        finally:
            await provider.aclose()
            if geocoder is not None:
                await geocoder.aclose()
            if place_source is not None:
                await place_source.aclose()

    app = FastAPI(
        title="Roadside API",
        version="1.0.0",
        lifespan=lifespan,
        generate_unique_id_function=_operation_id,
    )
    app.state.settings = settings
    app.state.llm_provider = provider
    app.state.turn_locks = TurnLocks(settings.database_path)
    app.state.geocoder = geocoder
    app.state.place_source = place_source
    app.state.place_recordings = place_recordings
    app.state.place_recorder = place_recorder

    api = APIRouter(prefix="/api/v1")
    api.include_router(meta.config_router)
    api.include_router(vehicles.router)
    api.include_router(incidents.router)
    api.include_router(ai_turns.router)
    api.include_router(damage_reports.router)
    api.include_router(nearby.router)
    api.include_router(photos.router)
    app.include_router(api)
    app.include_router(meta.health_router)

    install_error_handlers(app)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)
    # Added last = outermost, so even 413 problem responses carry CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key"],
        expose_headers=["Location"],
    )
    return app
