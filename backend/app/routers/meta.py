from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import Connection, get_llm_provider, get_settings
from app.errors import AppError
from app.integrations.llm.base import LLMProvider
from app.schemas.meta import ConfigRead, HealthRead
from app.settings import Settings

health_router = APIRouter(tags=["meta"])
config_router = APIRouter(tags=["meta"])


@health_router.get("/health", response_model=HealthRead)
async def health(conn: Connection) -> HealthRead:
    try:
        await conn.execute("SELECT 1")
    except Exception as exc:
        raise AppError(503, "database_unavailable", "Database is not reachable") from exc
    return HealthRead(status="ok")


@config_router.get("/config", response_model=ConfigRead)
async def read_config(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ConfigRead:
    return ConfigRead(
        demo_mode=settings.demo_mode,
        # What the provider in use can do, not what was asked for (demo mode has no vision).
        vision_enabled=provider.vision and provider.max_images > 0,
        max_photos=settings.max_photos,
        max_photo_bytes=settings.max_photo_bytes,
        sample_photos=[],
    )
