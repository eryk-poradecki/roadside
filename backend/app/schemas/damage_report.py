from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.domain.ai_turn import Locale
from app.domain.damage_report import BODY_MAX_LENGTH, DamageReport, DamageReportStatus
from app.schemas.incident import non_nullable

Body = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=BODY_MAX_LENGTH)
]


class DamageReportCreate(BaseModel):
    """Draft the report in `locale`, the letter's language: Polish unless the driver picks
    English, because the letter goes to a Polish road manager whatever the UI language.
    `replace: true` overwrites an existing report and sets it back to `draft`. The driver's
    own details are never sent: they fill the body's placeholders in the browser.
    """

    model_config = ConfigDict(extra="forbid")

    locale: Locale = "pl"
    replace: bool = False


_NOT_NULL = ("body", "status")


class DamageReportPatch(BaseModel):
    """Send only the fields to change; neither can be null. Only the driver marks it sent."""

    model_config = ConfigDict(extra="forbid", json_schema_extra=non_nullable(_NOT_NULL))

    body: Body | None = None
    status: DamageReportStatus | None = None

    @field_validator(*_NOT_NULL)
    @classmethod
    def _not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Can't be null")
        return v


class DamageReportRead(BaseModel):
    """The letter as stored: its claimant and addressee placeholders are still in `body`."""

    status: DamageReportStatus
    locale: Locale
    body: str
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, r: DamageReport) -> "DamageReportRead":
        return cls(
            status=r.status,
            locale=r.locale,
            body=r.body,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


class DamageReportLocales(BaseModel):
    """The letter languages a draft can be made in now, Polish first. Empty for an incident
    that isn't a pothole, and in demo mode for one with no recorded draft (#143)."""

    locales: list[Locale]
