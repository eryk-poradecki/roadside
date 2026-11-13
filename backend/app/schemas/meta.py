from pydantic import BaseModel

from app.domain.ai_turn import Locale
from app.domain.incident import ProblemType, Situation
from app.schemas.incident import LocationRead


class SamplePhoto(BaseModel):
    id: str
    url: str
    title: str
    credit: str


class DemoScenarioLocale(BaseModel):
    title: str
    summary: str
    note: str


class DemoScenario(BaseModel):
    id: str
    locales: dict[Locale, DemoScenarioLocale]
    problem_type: ProblemType
    vehicle_profile: str | None
    situation: Situation
    sample_photo_ids: list[str]
    location: LocationRead


class ConfigRead(BaseModel):
    demo_mode: bool
    public_deploy: bool
    demo_scenarios: list[DemoScenario]
    vision_enabled: bool
    max_photos: int
    max_photo_bytes: int
    sample_photos: list[SamplePhoto]


class HealthRead(BaseModel):
    status: str
