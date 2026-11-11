"""The damage report (ADR 0009): a draft letter to the road manager about pothole damage."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain.ai_turn import Locale, ModelProvenance

# The longest body the driver can save: a letter, not a document.
BODY_MAX_LENGTH = 10_000


class DamageReportStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"


@dataclass(frozen=True, slots=True)
class NewDamageReport:
    """A freshly generated report: always a draft (ADR 0009)."""

    locale: Locale
    body: str
    # The validated model output the body was rendered from.
    narrative: dict[str, Any]
    provenance: ModelProvenance


@dataclass(frozen=True, slots=True)
class DamageReport:
    incident_id: int
    status: DamageReportStatus
    locale: Locale
    body: str
    narrative: dict[str, Any]
    provenance: ModelProvenance
    created_at: str
    updated_at: str
