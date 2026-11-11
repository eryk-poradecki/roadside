"""The damage report letter (ADR 0009): the one place its layout lives.

The backend renders the facts it already knows into a per-locale template, around the narrative
the model wrote. The registration comes in here, never through the prompt. The driver's own
details (name, address, phone, bank account) and the addressee stay placeholders: the browser
fills the driver's at copy time, and the stored body keeps them. The frontend matches these
placeholder strings in `src/lib/claimant.ts`.
"""

from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo

from app.domain.ai_turn import Locale

_LETTERS = Path(__file__).parent / "letters"
_TZ = ZoneInfo("Europe/Warsaw")

# Facts the incident may not have: the driver fills them in.
_MISSING: dict[Locale, dict[str, str]] = {
    "en": {
        "place": "[Place of the incident]",
        "vehicle": "[Vehicle make and model]",
        "registration": "[Registration number]",
    },
    "pl": {
        "place": "[Miejsce zdarzenia]",
        "vehicle": "[Marka i model pojazdu]",
        "registration": "[Numer rejestracyjny]",
    },
}


@dataclass(frozen=True, slots=True)
class LetterFacts:
    """What the backend knows, snapshotted when the report is generated."""

    # The incident's `created_at`: when the driver asked for help.
    occurred_at: str
    location_label: str | None
    lat: float | None
    lon: float | None
    make_model: str | None
    year: int | None
    vehicle_name: str | None
    registration: str | None
    photo_count: int


@cache
def _template(locale: Locale) -> Template:
    return Template((_LETTERS / f"damage_report_{locale}.txt").read_text(encoding="utf-8"))


def _place(facts: LetterFacts, missing: str) -> str:
    coords = (
        f"{facts.lat:.5f}, {facts.lon:.5f}"
        if facts.lat is not None and facts.lon is not None
        else None
    )
    if facts.location_label and coords:
        return f"{facts.location_label} ({coords})"
    return facts.location_label or coords or missing


def _vehicle(facts: LetterFacts, missing: str) -> str:
    name = facts.make_model or facts.vehicle_name
    if name is None:
        return missing
    return f"{name} ({facts.year})" if facts.year is not None else name


def render_letter(
    facts: LetterFacts, locale: Locale, *, description: str, damage_summary: str
) -> str:
    missing = _MISSING[locale]
    when = datetime.fromisoformat(facts.occurred_at).astimezone(_TZ)
    return _template(locale).substitute(
        when=when.strftime("%d.%m.%Y %H:%M"),
        place=_place(facts, missing["place"]),
        vehicle=_vehicle(facts, missing["vehicle"]),
        registration=facts.registration or missing["registration"],
        description=description,
        damage_summary=damage_summary,
        photos=str(facts.photo_count),
    )
