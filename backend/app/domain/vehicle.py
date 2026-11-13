from dataclasses import dataclass
from enum import StrEnum


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    LPG = "lpg"
    HYBRID = "hybrid"
    PLUG_IN_HYBRID = "plug_in_hybrid"
    ELECTRIC = "electric"


class Transmission(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class SpareWheel(StrEnum):
    FULL_SIZE = "full_size"
    SPACE_SAVER = "space_saver"
    REPAIR_KIT = "repair_kit"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class VehicleFacts:
    """The writable attributes of a vehicle. None means unknown, never 'none'."""

    name: str
    make_model: str | None = None
    year: int | None = None
    fuel_type: FuelType | None = None
    transmission: Transmission | None = None
    tyre_size: str | None = None
    spare_wheel: SpareWheel | None = None
    wheel_locks: bool | None = None
    lock_key_location: str | None = None
    registration: str | None = None
    assistance_insurer: str | None = None
    assistance_phone: str | None = None
    policy_number: str | None = None


@dataclass(frozen=True, slots=True)
class Vehicle:
    id: int
    facts: VehicleFacts
    is_default: bool
    created_at: str
    updated_at: str
    demo_profile: str | None = None
