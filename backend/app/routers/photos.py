from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.deps import get_photo_service, get_settings
from app.errors import AppError
from app.routers.incidents import IncidentId
from app.schemas.photo import PhotoRead, SamplePhotoCreate, photo_url
from app.services.photos import PhotoService
from app.settings import Settings

router = APIRouter(tags=["photos"])
PhotoId = Annotated[int, Path(ge=1, le=2**63 - 1)]
Service = Annotated[PhotoService, Depends(get_photo_service)]

_IMAGE_CONTENT: dict[str, Any] = {
    t: {"schema": {"type": "string", "format": "binary"}}
    for t in ("image/jpeg", "image/png", "image/webp")
}

# One endpoint, two bodies (ADR 0002): FastAPI can't declare that, so the router reads the
# body itself and the OpenAPI document says what it accepts.
_ADD_PHOTO_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {"file": {"type": "string", "format": "binary"}},
                }
            },
            "application/json": {"schema": SamplePhotoCreate.model_json_schema()},
        },
    }
}


async def _read_file(request: Request, max_bytes: int) -> bytes:
    """The `file` part of a multipart body, refused past `max_bytes` (413)."""
    async with request.form(max_files=1, max_fields=10) as form:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise AppError(
                422,
                "validation_error",
                "Invalid request",
                [{"field": "file", "message": "A file is required"}],
            )
        data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AppError(413, "photo_too_large", f"A photo is at most {max_bytes} bytes")
    return data


def _parse_sample(raw: bytes) -> SamplePhotoCreate:
    try:
        return SamplePhotoCreate.model_validate_json(raw)
    except ValidationError as exc:
        # Shaped like FastAPI's own body errors, so the handler reports `errors[].field`.
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in exc.errors(include_url=False)]
        ) from exc


@router.post(
    "/incidents/{incident_id}/photos",
    status_code=201,
    response_model=PhotoRead,
    openapi_extra=_ADD_PHOTO_BODY,
)
async def add_photo(
    incident_id: IncidentId,
    request: Request,
    response: Response,
    service: Service,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PhotoRead:
    """Add one photo: a multipart `file`, or `{sample_id}` for a bundled sample photo.

    The server re-encodes every file (EXIF orientation applied, long edge at most 2048 px,
    no metadata). 409 `photo_limit` past five, 413 `photo_too_large`, 415
    `unsupported_media_type` for anything but a decodable JPEG, PNG or WebP, 403
    `demo_uploads_disabled` for a file in demo mode, 422 `unknown_sample`.
    """
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type == "multipart/form-data":
        service.check_uploads_allowed()
        photo = await service.add_upload(
            incident_id, await _read_file(request, settings.max_photo_bytes)
        )
    elif media_type == "application/json":
        body = _parse_sample(await request.body())
        photo = await service.add_sample(incident_id, body.sample_id)
    else:
        raise AppError(415, "unsupported_media_type", "Send multipart/form-data or JSON")
    response.headers["Location"] = photo_url(photo.id)
    return PhotoRead.from_domain(photo)


@router.get(
    "/photos/{photo_id}",
    response_class=FileResponse,
    responses={200: {"content": _IMAGE_CONTENT, "description": "The image file"}},
)
async def get_photo(photo_id: PhotoId, service: Service) -> FileResponse:
    """The stored file. Never a static mount: a deleted row's file is unreachable at once."""
    photo, path = await service.get(photo_id)
    # Ids can be reused after a delete, so revalidate (the ETag makes that cheap).
    return FileResponse(
        path, media_type=photo.content_type, headers={"Cache-Control": "private, no-cache"}
    )


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(photo_id: PhotoId, service: Service) -> Response:
    await service.delete(photo_id)
    return Response(status_code=204)
