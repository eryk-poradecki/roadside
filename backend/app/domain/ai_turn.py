from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

# The UI languages; an AI answer is written in the UI language only (ADR 0004).
Locale = Literal["pl", "en"]


class AiTurnKind(StrEnum):
    QUESTION = "question"
    REPLY = "reply"
    ADVICE = "advice"


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    """Who produced a model turn, from what, in which language (ADR 0004)."""

    inputs: dict[str, Any]
    locale: Locale
    prompt_version: str
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class Reply:
    """The driver's reply to a clarifying question: exactly one of the three is set."""

    option: str | None = None
    text: str | None = None
    # "Just give me the steps": no more questions, the advice now.
    skip: bool = False

    def to_payload(self) -> dict[str, Any]:
        if self.option is not None:
            return {"option": self.option}
        if self.text is not None:
            return {"text": self.text}
        return {"skip": True}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Reply":
        return cls(
            option=payload.get("option"), text=payload.get("text"), skip=bool(payload.get("skip"))
        )


@dataclass(frozen=True, slots=True)
class NewAiTurn:
    kind: AiTurnKind
    payload: dict[str, Any]
    # None for a reply, which is the driver's, not the model's.
    provenance: ModelProvenance | None


@dataclass(frozen=True, slots=True)
class AiTurn:
    """One row of the append-only AI answer. Never updated once stored."""

    id: int
    incident_id: int
    seq: int
    kind: AiTurnKind
    payload: dict[str, Any]
    provenance: ModelProvenance | None
    created_at: str
