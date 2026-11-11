from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.domain.photo import Photo


def photo_url(photo_id: int) -> str:
    return f"/api/v1/photos/{photo_id}"


def sample_photo_url(sample_id: str) -> str:
    return f"/api/v1/sample-photos/{sample_id}"


class PhotoRead(BaseModel):
    """A stored photo. `url` serves the file; there are no thumbnails (ADR 0002)."""

    id: int
    url: str
    content_type: str
    width: int
    height: int
    created_at: str

    @classmethod
    def from_domain(cls, p: Photo) -> "PhotoRead":
        return cls(
            id=p.id,
            url=photo_url(p.id),
            content_type=p.content_type,
            width=p.width,
            height=p.height,
            created_at=p.created_at,
        )


class SamplePhotoCreate(BaseModel):
    """Attach a bundled sample photo (`GET /config` lists them) instead of uploading a file."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sample_id: Annotated[str, StringConstraints(min_length=1, max_length=64)]
