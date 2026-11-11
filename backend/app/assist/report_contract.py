"""The damage report contract (ADR 0009): the model writes only the narrative.

Like the AI turn (ADR 0004), the schema sent to the model is flat and conservative, with no
length keywords; Pydantic enforces the real rules. Every fact the backend already knows (the
date, the place, the vehicle, the registration, the photo count) goes into the letter from the
template, never from the model.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.assist.contract import strip_fence

Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ReportOutput(BaseModel):
    """What happened, in the driver's first person, and what was damaged."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    description: Description
    damage_summary: Summary


def validate_report_output(raw: str) -> ReportOutput:
    """Parse the model's raw text. Raises ValueError (pydantic's included) when invalid."""
    return ReportOutput.model_validate_json(strip_fence(raw))


def report_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "damage_summary": {"type": "string"},
        },
        "required": ["description", "damage_summary"],
        "additionalProperties": False,
    }
