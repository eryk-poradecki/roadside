from pydantic import BaseModel, ConfigDict

from app.assist.contract import Confidence, NearbyCategory
from app.domain.ai_turn import AiTurn, AiTurnKind, Locale


class AiTurnCreate(BaseModel):
    """Ask for the next turn. `locale` is the UI language, the only language of the answer."""

    model_config = ConfigDict(extra="forbid")

    locale: Locale


class AdviceRead(BaseModel):
    """The advice: the diagnosis, numbered steps, and when to stop and call for help."""

    cause: str
    confidence: Confidence
    alternatives: list[str]
    steps: list[str]
    escalate_if: list[str]
    photo_observation: str | None
    extra_categories: list[NearbyCategory]


class VehicleFactsRead(BaseModel):
    """The vehicle fact block the model was given. Null means unknown."""

    name: str
    make_model: str | None
    year: int | None
    fuel_type: str | None
    transmission: str | None
    tyre_size: str | None
    spare_wheel: str | None
    wheel_locks: bool | None
    lock_key_location: str | None
    has_assistance: bool
    assistance_insurer: str | None


class TurnInputsRead(BaseModel):
    """What a model turn was produced from ("Answered for …"), frozen when it was stored."""

    vehicle: VehicleFactsRead | None
    problem_type: str
    note: str | None
    local_time: str
    dark: bool
    road_class: str
    settlement: str
    photo_ids_seen: list[int]
    photos_not_sent: int


class AiTurnRead(BaseModel):
    id: int
    seq: int
    kind: AiTurnKind
    created_at: str
    # Model turns only.
    urgent: bool | None
    advice: AdviceRead | None
    inputs: TurnInputsRead | None
    locale: Locale | None
    prompt_version: str | None
    provider: str | None
    model: str | None

    @classmethod
    def from_domain(cls, t: AiTurn) -> "AiTurnRead":
        p = t.provenance
        answer = t.payload.get("answer")
        return cls(
            id=t.id,
            seq=t.seq,
            kind=t.kind,
            created_at=t.created_at,
            urgent=t.payload.get("urgent") if p else None,
            advice=AdviceRead.model_validate(answer) if answer else None,
            inputs=TurnInputsRead.model_validate(p.inputs) if p else None,
            locale=p.locale if p else None,
            prompt_version=p.prompt_version if p else None,
            provider=p.provider if p else None,
            model=p.model if p else None,
        )
