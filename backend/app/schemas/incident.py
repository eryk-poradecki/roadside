from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.incident import Incident, IncidentStatus, Location, NewIncident, ProblemType

NOTE_MAX_LENGTH = 280
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

    @classmethod
    def from_domain(cls, i: Incident) -> "IncidentRead":
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
        )
