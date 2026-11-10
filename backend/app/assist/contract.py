"""The AI turn contract (ADR 0004).

The model gets one conservative flat JSON schema: both blocks nullable, no `oneOf`,
`minItems` or `maxLength`, because providers drop or reject those. Pydantic enforces the real
rules here (exactly one block matching `kind`, counts, lengths, `urgent` → 112 first) and
builds a proper union. Every model forbids extra keys, and no field holds a place: the
Nearby panel is filled by the backend from map data, never by the model.
"""

import re
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class Confidence(StrEnum):
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNSURE = "unsure"


class NearbyCategory(StrEnum):
    TYRES = "tyres"
    FUEL = "fuel"
    CHARGING = "charging"
    REPAIR = "repair"


Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=280)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Ask(_Strict):
    """A clarifying question: one immediate safety step, then two to four tappable options."""

    now: Line
    question: Line
    options: Annotated[list[Short], Field(min_length=2, max_length=4)]


class Answer(_Strict):
    cause: Line
    confidence: Confidence
    alternatives: Annotated[list[Line], Field(max_length=2)]
    steps: Annotated[list[Line], Field(min_length=2, max_length=6)]
    escalate_if: Annotated[list[Line], Field(min_length=1, max_length=4)]
    photo_observation: Line | None
    extra_categories: Annotated[list[NearbyCategory], Field(max_length=4)]

    @model_validator(mode="after")
    def _unique_categories(self) -> Self:
        if len(set(self.extra_categories)) != len(self.extra_categories):
            raise ValueError("extra_categories must not repeat a category")
        return self


class TurnOutput(_Strict):
    """What the model returns, validated. Exactly one block is set, the one `kind` names."""

    kind: Literal["ask", "answer"]
    urgent: bool
    ask: Ask | None
    answer: Answer | None

    @model_validator(mode="after")
    def _one_block(self) -> Self:
        if self.kind == "answer" and (self.answer is None or self.ask is not None):
            raise ValueError('kind "answer" needs "answer" set and "ask" null')
        if self.kind == "ask" and (self.ask is None or self.answer is not None):
            raise ValueError('kind "ask" needs "ask" set and "answer" null')
        if self.urgent and self.kind == "ask":
            raise ValueError("an urgent turn must answer, never ask")
        if self.urgent and self.answer is not None and "112" not in self.answer.steps[0]:
            raise ValueError('an urgent answer must make "call 112" the first step')
        return self


def validate_output(raw: str, *, allow_ask: bool) -> TurnOutput:
    """Parse the model's raw text. Raises ValueError (pydantic's included) when invalid."""
    output = TurnOutput.model_validate_json(_strip_fence(raw))
    if output.kind == "ask" and not allow_ask:
        raise ValueError('kind must be "answer" now; no more questions')
    return output


_FENCE = re.compile(r"```[a-zA-Z]*\s*(.*?)\s*```", re.DOTALL)


def _strip_fence(raw: str) -> str:
    """Some models wrap JSON in a ```json fence despite the schema."""
    match = _FENCE.fullmatch(raw.strip())
    return match.group(1) if match else raw


def _strings() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}


def model_schema(*, allow_ask: bool) -> dict[str, Any]:
    """The flat schema sent to the model. Without `allow_ask`, `kind` is narrowed to answer."""
    answer = {
        "type": ["object", "null"],
        "properties": {
            "cause": {"type": "string"},
            "confidence": {"type": "string", "enum": [c.value for c in Confidence]},
            "alternatives": _strings(),
            "steps": _strings(),
            "escalate_if": _strings(),
            "photo_observation": {"type": ["string", "null"]},
            "extra_categories": {
                "type": "array",
                "items": {"type": "string", "enum": [c.value for c in NearbyCategory]},
            },
        },
        "required": [
            "cause",
            "confidence",
            "alternatives",
            "steps",
            "escalate_if",
            "photo_observation",
            "extra_categories",
        ],
        "additionalProperties": False,
    }
    ask = {
        "type": ["object", "null"],
        "properties": {
            "now": {"type": "string"},
            "question": {"type": "string"},
            "options": _strings(),
        },
        "required": ["now", "question", "options"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["ask", "answer"] if allow_ask else ["answer"]},
            "urgent": {"type": "boolean"},
            "ask": ask,
            "answer": answer,
        },
        "required": ["kind", "urgent", "ask", "answer"],
        "additionalProperties": False,
    }
