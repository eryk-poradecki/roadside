from dataclasses import dataclass
from enum import StrEnum


class ProblemType(StrEnum):
    FLAT_TYRE = "flat_tyre"
    FLAT_BATTERY = "flat_battery"
    OUT_OF_FUEL = "out_of_fuel"
    POTHOLE_DAMAGE = "pothole_damage"
    OTHER = "other"


class IncidentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class Location:
    lat: float
    lon: float
    accuracy_m: float | None = None


@dataclass(frozen=True, slots=True)
class NewIncident:
    """What the driver supplies at the help request. Only the problem type is required."""

    problem_type: ProblemType
    vehicle_id: int | None = None
    note: str | None = None
    location: Location | None = None


@dataclass(frozen=True, slots=True)
class Incident:
    id: int
    problem_type: ProblemType
    status: IncidentStatus
    vehicle_id: int | None
    note: str | None
    location: Location | None
    location_label: str | None
    created_at: str
    updated_at: str
