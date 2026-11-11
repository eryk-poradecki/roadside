from collections.abc import Callable
from dataclasses import replace
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.incident import (
    NOTE_MAX_LENGTH,
    Incident,
    IncidentDetail,
    IncidentStatus,
    Location,
    NewIncident,
    ProblemType,
)
from app.schemas.ai_turn import AiTurnRead
from app.schemas.nearby import NearbyRead

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=NOTE_MAX_LENGTH)]
DbId = Annotated[int, Field(ge=1, le=2**63 - 1)]


class LocationIn(BaseModel):
    """A GPS fix from the browser. `accuracy_m` is the reported radius in metres."""

    model_config = ConfigDict(extra="forbid")

    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    accuracy_m: Annotated[float, Field(ge=0)] | None = None


class LocationRead(BaseModel):
    lat: float
    lon: float
    accuracy_m: float | None


class IncidentCreate(BaseModel):
    """Only `problem_type` is required. The server sets the status (`open`) and `created_at`."""

    model_config = ConfigDict(extra="forbid")

    problem_type: ProblemType
    vehicle_id: DbId | None = None
    note: Note | None = None
    location: LocationIn | None = None

    @field_validator("note")
    @classmethod
    def _blank_is_none(cls, v: str | None) -> str | None:
        return v or None

    def to_domain(self) -> NewIncident:
        loc = self.location
        return NewIncident(
            problem_type=self.problem_type,
            vehicle_id=self.vehicle_id,
            note=self.note,
            location=Location(loc.lat, loc.lon, loc.accuracy_m) if loc else None,
        )


_REQUIRED_VALUE = ("status", "problem_type")


def _non_nullable(fields: tuple[str, ...]) -> Callable[[dict[str, Any]], None]:
    """Drop the null branch from these optional properties in the JSON schema."""

    def edit(schema: dict[str, Any]) -> None:
        for name in fields:
            prop = schema["properties"][name]
            branches = [b for b in prop.pop("anyOf") if b != {"type": "null"}]
            prop.update(branches[0])
            prop.pop("default", None)

    return edit


class IncidentPatch(BaseModel):
    """Send only the fields to change. `null` clears `note`, `vehicle_id` and `location`;
    `status` and `problem_type` can't be null. The status moves freely either way (ADR 0001).
    """

    model_config = ConfigDict(extra="forbid", json_schema_extra=_non_nullable(_REQUIRED_VALUE))

    # Optional but not nullable: omitted means unchanged (defaults aren't validated), an
    # explicit null is refused below, and the schema doesn't advertise null.
    status: IncidentStatus | None = None
    problem_type: ProblemType | None = None
    vehicle_id: DbId | None = None
    note: Note | None = None
    location: LocationIn | None = None

    @field_validator(*_REQUIRED_VALUE)
    @classmethod
    def _not_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("Can't be null")
        return v

    @field_validator("note")
    @classmethod
    def _blank_is_none(cls, v: str | None) -> str | None:
        return v or None

    def apply(self, current: Incident) -> Incident:
        """The incident with the sent fields replaced. A new location drops the old label."""
        sent = self.model_fields_set
        new = current
        if self.status is not None:
            new = replace(new, status=self.status)
        if self.problem_type is not None:
            new = replace(new, problem_type=self.problem_type)
        if "vehicle_id" in sent:
            new = replace(new, vehicle_id=self.vehicle_id)
        if "note" in sent:
            new = replace(new, note=self.note)
        if "location" in sent:
            loc = self.location
            location = Location(loc.lat, loc.lon, loc.accuracy_m) if loc else None
            if location != current.location:
                new = replace(new, location=location, location_label=None, location_context=None)
        return new


class IncidentRead(BaseModel):
    id: int
    problem_type: ProblemType
    status: IncidentStatus
    vehicle_id: int | None
    note: str | None
    location: LocationRead | None
    location_label: str | None
    created_at: str
    updated_at: str
    # The AI answer in sequence order: append-only, the advice last (ADR 0004).
    ai_turns: list[AiTurnRead]
    # Null until the first successful lookup, and again after a location change.
    nearby: NearbyRead | None

    @classmethod
    def from_domain(cls, detail: IncidentDetail) -> "IncidentRead":
        i = detail.incident
        loc = i.location
        return cls(
            id=i.id,
            problem_type=i.problem_type,
            status=i.status,
            vehicle_id=i.vehicle_id,
            note=i.note,
            location=LocationRead(lat=loc.lat, lon=loc.lon, accuracy_m=loc.accuracy_m)
            if loc
            else None,
            location_label=i.location_label,
            created_at=i.created_at,
            updated_at=i.updated_at,
            ai_turns=[AiTurnRead.from_domain(t) for t in detail.ai_turns],
            nearby=NearbyRead.from_domain(detail.nearby) if detail.nearby else None,
        )


class LocationPoint(BaseModel):
    lat: float
    lon: float


class IncidentSummary(BaseModel):
    """One row of the History list and a pin on its map: no note, no owned parts (ADR 0005)."""

    id: int
    problem_type: ProblemType
    status: IncidentStatus
    created_at: str
    location: LocationPoint | None
    location_label: str | None
    vehicle_id: int | None

    @classmethod
    def from_domain(cls, i: Incident) -> "IncidentSummary":
        loc = i.location
        return cls(
            id=i.id,
            problem_type=i.problem_type,
            status=i.status,
            created_at=i.created_at,
            location=LocationPoint(lat=loc.lat, lon=loc.lon) if loc else None,
            location_label=i.location_label,
            vehicle_id=i.vehicle_id,
        )


class IncidentPage(BaseModel):
    items: list[IncidentSummary]
    total: int
    limit: int
    offset: int
