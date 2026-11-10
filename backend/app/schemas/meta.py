from pydantic import BaseModel


class SamplePhoto(BaseModel):
    id: str
    url: str
    title: str
    credit: str


class ConfigRead(BaseModel):
    demo_mode: bool
    vision_enabled: bool
    max_photos: int
    max_photo_bytes: int
    sample_photos: list[SamplePhoto]


class HealthRead(BaseModel):
    status: str
