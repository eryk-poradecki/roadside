from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from app.domain.ai_turn import AiTurn

if TYPE_CHECKING:
    from app.domain.location_context import LocationContext
    from app.domain.nearby import NearbySnapshot


# The driver's note, and a free-text reply to a clarifying question, are at most this long.
NOTE_MAX_LENGTH = 280


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
    # Cached at the first AI turn; None until looked up, and cleared with a new location.
    location_context: "LocationContext | None" = None


@dataclass(frozen=True, slots=True)
class IncidentDetail:
    """An incident with the parts it owns, as one consistent read."""

    incident: Incident
    ai_turns: tuple[AiTurn, ...]
    # The last successful nearby lookup; None until one succeeds or after a location change.
    nearby: "NearbySnapshot | None" = None
