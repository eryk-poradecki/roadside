import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.migrate import migrate
from app.errors import install_error_handlers
from app.middleware import BodyLimitMiddleware
from app.routers import meta, vehicles
from app.settings import Settings

logger = logging.getLogger("roadside")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        version = migrate(settings.database_path)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "database ready at schema version %d (demo_mode=%s)", version, settings.demo_mode
        )
        yield

    app = FastAPI(title="Roadside API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings

    api = APIRouter(prefix="/api/v1")
    api.include_router(meta.config_router)
    api.include_router(vehicles.router)
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
