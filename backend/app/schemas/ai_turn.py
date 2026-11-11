from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.assist.contract import Confidence, NearbyCategory
from app.domain.ai_turn import AiTurn, AiTurnKind, Locale, Reply
from app.domain.incident import NOTE_MAX_LENGTH

ReplyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NOTE_MAX_LENGTH)
]


class ReplyCreate(BaseModel):
    """The driver's reply to the open clarifying question. Exactly one field is set: one of
    the question's `option`s, a short free `text` ("Other"), or `skip` ("Just give me the
    steps", which asks for the advice at once)."""

    model_config = ConfigDict(extra="forbid")

    option: str | None = None
    text: ReplyText | None = None
    skip: Literal[True] | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if sum(v is not None for v in (self.option, self.text, self.skip)) != 1:
            raise ValueError("set exactly one of option, text or skip")
        return self

    def to_domain(self) -> Reply:
        return Reply(option=self.option, text=self.text, skip=self.skip is True)


class AiTurnCreate(BaseModel):
    """Ask for the next turn. `locale` is the UI language, the only language of the answer.

    `reply` is the driver's reply to the open clarifying question, required while one is
    open. It is stored as its own turn before the model is asked, and stays if that call
    fails.
    """

    model_config = ConfigDict(extra="forbid")

    locale: Locale
    reply: ReplyCreate | None = None


class QuestionRead(BaseModel):
    """A clarifying question: one immediate safety step, then two to four options."""

    now: str
    question: str
    options: list[str]


class ReplyRead(BaseModel):
    """The driver's reply: an option, a short text, or `skip` ("Just give me the steps")."""

    option: str | None
    text: str | None
    skip: bool


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
    question: QuestionRead | None
    advice: AdviceRead | None
    # Reply turns only.
    reply: ReplyRead | None
    inputs: TurnInputsRead | None
    locale: Locale | None
    prompt_version: str | None
    provider: str | None
    model: str | None

    @classmethod
    def from_domain(cls, t: AiTurn) -> "AiTurnRead":
        p = t.provenance
        answer = t.payload.get("answer")
        ask = t.payload.get("ask")
        reply = Reply.from_payload(t.payload) if t.kind is AiTurnKind.REPLY else None
        return cls(
            id=t.id,
            seq=t.seq,
            kind=t.kind,
            created_at=t.created_at,
            urgent=t.payload.get("urgent") if p else None,
            question=QuestionRead.model_validate(ask) if ask else None,
            advice=AdviceRead.model_validate(answer) if answer else None,
            reply=ReplyRead(option=reply.option, text=reply.text, skip=reply.skip)
            if reply
            else None,
            inputs=TurnInputsRead.model_validate(p.inputs) if p else None,
            locale=p.locale if p else None,
            prompt_version=p.prompt_version if p else None,
            provider=p.provider if p else None,
            model=p.model if p else None,
        )
