from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.deps import Connection, get_llm_provider, get_settings
from app.domain.sample_photo import SAMPLE_PHOTOS, find_sample
from app.errors import AppError, NotFoundError
from app.integrations.llm.base import LLMProvider
from app.schemas.meta import ConfigRead, HealthRead, SamplePhoto
from app.schemas.photo import sample_photo_url
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
        # Whether photos reach a model: what the provider in use can do, not what was asked
        # for. Demo mode sends them nowhere, even when it replays recordings made with vision.
        vision_enabled=not settings.demo_mode and provider.vision and provider.max_images > 0,
        max_photos=settings.max_photos,
        max_photo_bytes=settings.max_photo_bytes,
        sample_photos=[
            SamplePhoto(id=s.id, url=sample_photo_url(s.id), title=s.title, credit=s.credit)
            for s in SAMPLE_PHOTOS
        ],
    )


@config_router.get(
    "/sample-photos/{sample_id}",
    response_class=FileResponse,
    responses={200: {"content": {"image/jpeg": {}}, "description": "The bundled image"}},
)
async def get_sample_photo(sample_id: str) -> FileResponse:
    """A bundled sample photo, freely licensed and credited (`credit` in `GET /config`)."""
    sample = find_sample(sample_id)
    if sample is None:
        raise NotFoundError("Sample photo")
    return FileResponse(
        sample.path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"}
    )
