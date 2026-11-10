from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.domain.vehicle import FuelType, SpareWheel, Transmission, Vehicle, VehicleFacts

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
_TEXT_FIELDS = (
    "make_model",
    "tyre_size",
    "lock_key_location",
    "registration",
    "assistance_insurer",
    "assistance_phone",
    "policy_number",
)


class VehicleCreate(BaseModel):
    """Only `name` is required; null means unknown. `is_default` omitted = default rules apply."""

    model_config = ConfigDict(extra="forbid")

    name: Name
    make_model: Text | None = None
    year: Annotated[int, Field(ge=1900, le=2100)] | None = None
    fuel_type: FuelType | None = None
    transmission: Transmission | None = None
    tyre_size: Text | None = None
    spare_wheel: SpareWheel | None = None
    wheel_locks: bool | None = None
    lock_key_location: Text | None = None
    registration: Text | None = None
    assistance_insurer: Text | None = None
    assistance_phone: Text | None = None
    policy_number: Text | None = None
    is_default: bool | None = None

    @field_validator(*_TEXT_FIELDS)
    @classmethod
    def _blank_is_unknown(cls, v: str | None) -> str | None:
        return v or None

    @field_validator("lock_key_location")
    @classmethod
    def _only_with_wheel_locks(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is not None and "wheel_locks" in info.data and info.data["wheel_locks"] is not True:
            raise ValueError("lock_key_location is only allowed when wheel_locks is true")
        return v

    def to_facts(self) -> VehicleFacts:
        return VehicleFacts(**self.model_dump(exclude={"is_default"}))


class VehicleUpdate(VehicleCreate):
    """Full representation (PUT). Omitting `is_default` keeps the current value."""


class VehicleRead(BaseModel):
    id: int
    name: str
    make_model: str | None
    year: int | None
    fuel_type: FuelType | None
    transmission: Transmission | None
    tyre_size: str | None
    spare_wheel: SpareWheel | None
    wheel_locks: bool | None
    lock_key_location: str | None
    registration: str | None
    assistance_insurer: str | None
    assistance_phone: str | None
    policy_number: str | None
    is_default: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, v: Vehicle) -> "VehicleRead":
        return cls(
            id=v.id,
            is_default=v.is_default,
            created_at=v.created_at,
            updated_at=v.updated_at,
            **vars_of(v.facts),
        )


def vars_of(facts: VehicleFacts) -> dict[str, object]:
    return {name: getattr(facts, name) for name in VehicleFacts.__slots__}
