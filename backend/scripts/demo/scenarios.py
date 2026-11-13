"""The demo scenarios (`docs/demo-scenarios.md`, #62), as the recording run and the demo check
walk them (#63).

The document is the source: each `## Scenario` heading has a fenced YAML block. What the
document leaves to the runner sits here: the fixed demo vehicles as API bodies (the ones demo
mode seeds, with canaries planted), and when each scenario happens. Points come from the app
catalogue: public roads chosen because Nominatim classifies them as the scenario's
`road_class`. Recordings never store them (ADR 0004, #58).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any

import yaml

from app.demo_scenarios import DEMO_SCENARIOS
from app.domain.ai_turn import Locale
from app.schemas.vehicle import VehicleCreate
from app.services.assistant import LOCAL_TZ
from app.services.demo_vehicles import DEMO_VEHICLES

DOC = Path(__file__).resolve().parents[3] / "docs" / "demo-scenarios.md"

# Planted in the demo vehicles so the privacy scan can prove they never reach a recording.
# Fictional, and not dialable: Polish numbers never start with 000.
CANARY_REGISTRATION = "ZZ 06363"
CANARY_POLICY = "CANARY-POLICY-0063"
CANARY_PHONE = "+48 000 063 063"


def _profile(seeded: VehicleCreate) -> dict[str, Any]:
    """A seeded demo vehicle as a `POST /vehicles` body, with the canaries planted."""
    body = seeded.model_dump(mode="json", exclude_none=True)
    body |= {"registration": CANARY_REGISTRATION, "policy_number": CANARY_POLICY}
    if seeded.assistance_phone:
        # Still sets `has_assistance`; the number itself never reaches the model.
        body["assistance_phone"] = CANARY_PHONE
    return body


# The demo vehicles demo mode seeds (#122), as the recording run creates them in a live app.
PROFILES: dict[str, dict[str, Any]] = {
    profile_id: _profile(seeded) for profile_id, seeded in DEMO_VEHICLES.items()
}


@dataclass(frozen=True, slots=True)
class Place:
    """Where a scenario happens, and at what local time of day."""

    lat: float
    lon: float
    accuracy_m: float
    at: time


_TIMES = {
    "tyre_parked_morning": time(8, 30),
    "battery_parked_night": time(22, 30),
    "fuel_almost_at_station": time(13, 0),
    "pothole_damaged_wheel": time(13, 0),
    "tyre_motorway_night": time(23, 0),
    "ev_wont_power_on": time(10, 0),
    "unknown_knocking_warning": time(13, 0),
    "smoke_engine_bay": time(13, 0),
}

PLACES: dict[str, Place] = {
    s.id: Place(s.location.lat, s.location.lon, float(s.location.accuracy_m or 0), _TIMES[s.id])
    for s in DEMO_SCENARIOS
}


@dataclass(frozen=True, slots=True)
class Step:
    """One reply: `skip`, or the option that means `intent`."""

    skip: bool = False
    intent: str | None = None
    option_meaning: str | None = None

    def label(self) -> str:
        return "skip" if self.skip else str(self.intent)


@dataclass(frozen=True, slots=True)
class Branch:
    id: str
    steps: tuple[Step, ...]
    optional: bool = False


@dataclass(frozen=True, slots=True)
class Variant:
    locale: Locale
    note: str
    branches: tuple[Branch, ...]
    # `answer` or `ask` when this locale's first turn differs from the scenario's.
    first_turn: str | None = None


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    problem_type: str
    profile_id: str | None
    vehicle: dict[str, Any] | None
    sample_photos: tuple[str, ...]
    vision: bool
    situation: str
    road_class: str
    settlement: str
    dark: bool
    variants: tuple[Variant, ...]
    expect: dict[str, Any] = field(default_factory=dict)

    @property
    def place(self) -> Place:
        return PLACES[self.id]

    @property
    def first_turn(self) -> str:
        return str(self.expect.get("first_turn", "answer"))

    @property
    def damage_report(self) -> bool:
        return bool(self.expect.get("damage_report_followup"))

    def at(self, day: datetime) -> datetime:
        """The moment the scenario happens on `day`, at its local time of day."""
        local = day.astimezone(LOCAL_TZ)
        return datetime.combine(local.date(), self.place.at, LOCAL_TZ)


def _step(raw: dict[str, Any]) -> Step:
    if raw.get("skip"):
        return Step(skip=True)
    return Step(intent=raw["intent"], option_meaning=raw.get("option_meaning"))


def _variant(locale: str, raw: dict[str, Any]) -> Variant:
    if locale not in ("en", "pl"):
        raise ValueError(f"unknown locale {locale}")
    return Variant(
        locale=locale,  # type: ignore[arg-type]
        note=raw["note"],
        branches=tuple(
            Branch(b["id"], tuple(_step(s) for s in b["steps"]), bool(b.get("optional")))
            for b in raw["reply_branches"]
        ),
        first_turn=raw.get("first_turn"),
    )


def raw_blocks(doc: Path = DOC) -> list[dict[str, Any]]:
    """Each scenario's YAML block, as written."""
    blocks = re.findall(r"^## Scenario .*?^```yaml\n(.*?)^```", doc.read_text(), re.M | re.S)
    return [yaml.safe_load(b) for b in blocks]


def _scenario(raw: dict[str, Any]) -> Scenario:
    vehicle = raw["vehicle"]
    return Scenario(
        id=raw["id"],
        problem_type=raw["problem_type"],
        profile_id=vehicle["profile_id"] if vehicle else None,
        vehicle=vehicle,
        sample_photos=tuple(raw["sample_photos"]),
        vision=raw["vision"],
        situation=raw["situation"],
        road_class=raw["road_class"],
        settlement=raw["settlement"],
        dark=raw["dark"],
        # Polish first, so the English label (the primary demo language) is recorded last.
        variants=tuple(
            _variant(locale, raw["locales"][locale])
            for locale in sorted(raw["locales"], key=lambda loc: loc != "pl")
        ),
        expect=raw.get("expect") or {},
    )


def load_scenarios(doc: Path = DOC) -> list[Scenario]:
    return [_scenario(raw) for raw in raw_blocks(doc)]
