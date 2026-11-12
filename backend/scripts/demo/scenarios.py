"""The demo scenarios (`docs/demo-scenarios.md`, #62), as the recording run and the demo check
walk them (#63).

The document is the source: each `## Scenario` heading has a fenced YAML block. What the
document leaves to the runner sits here: the fixed demo vehicles as API bodies, and where and
when each scenario happens. The points are public roads, chosen because Nominatim classifies
them as the scenario's `road_class`; the recordings never store them (ADR 0004, #58).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any

import yaml

from app.domain.ai_turn import Locale
from app.services.assistant import LOCAL_TZ

DOC = Path(__file__).resolve().parents[3] / "docs" / "demo-scenarios.md"

# Planted in the demo vehicles so the privacy scan can prove they never reach a recording.
# Fictional, and not dialable: Polish numbers never start with 000.
CANARY_REGISTRATION = "ZZ 06363"
CANARY_POLICY = "CANARY-POLICY-0063"
CANARY_PHONE = "+48 000 063 063"

# The fixed demo vehicles of the document's table, as `POST /vehicles` bodies.
PROFILES: dict[str, dict[str, Any]] = {
    "golf_2017": {
        "name": "Golf",
        "make_model": "Volkswagen Golf VII 1.4 TSI",
        "year": 2017,
        "fuel_type": "petrol",
        "transmission": "manual",
        "spare_wheel": "full_size",
        "wheel_locks": True,
        "lock_key_location": "glovebox",
        "registration": CANARY_REGISTRATION,
        "policy_number": CANARY_POLICY,
    },
    "mini_ev_2021": {
        "name": "MINI",
        "make_model": "MINI Cooper SE Electric",
        "year": 2021,
        "fuel_type": "electric",
        "transmission": "automatic",
        "spare_wheel": "none",
        # Sets `has_assistance`; the number itself never reaches the model.
        "assistance_phone": CANARY_PHONE,
        "registration": CANARY_REGISTRATION,
        "policy_number": CANARY_POLICY,
    },
    "octavia_2015": {
        "name": "Octavia",
        "make_model": "Škoda Octavia III 1.6 TDI",
        "year": 2015,
        "fuel_type": "diesel",
        "transmission": "manual",
        "spare_wheel": "space_saver",
        "registration": CANARY_REGISTRATION,
        "policy_number": CANARY_POLICY,
    },
}


@dataclass(frozen=True, slots=True)
class Place:
    """Where a scenario happens, and at what local time of day."""

    lat: float
    lon: float
    accuracy_m: float
    at: time


_CITY_STREET = (52.4085, 16.9100)  # Adama Mickiewicza, Poznań: residential, city
_VILLAGE_MAIN_ROAD = (52.4567, 16.6934)  # Poznańska, Tarnowo Podgórne: primary, village
_VILLAGE_TERTIARY = (52.4203, 20.7722)  # Warszawska, Góra: tertiary, village
_MOTORWAY = (52.3286, 15.8498)  # A2: motorway, countryside
_NATIONAL_ROAD = (52.1006, 21.5015)  # DK50, Rudzienko: primary (a village, not countryside)
_LIVING_STREET = (52.4064, 16.9252)  # Święty Marcin, Poznań: living street, city

PLACES: dict[str, Place] = {
    "tyre_parked_morning": Place(*_CITY_STREET, 10, time(8, 30)),
    "battery_parked_night": Place(*_CITY_STREET, 10, time(22, 30)),
    "fuel_almost_at_station": Place(*_VILLAGE_MAIN_ROAD, 10, time(13, 0)),
    "pothole_damaged_wheel": Place(*_VILLAGE_TERTIARY, 10, time(13, 0)),
    "tyre_motorway_night": Place(*_MOTORWAY, 10, time(23, 0)),
    "ev_wont_power_on": Place(*_LIVING_STREET, 10, time(10, 0)),
    # A fix too coarse to trust any road: road_class is forced to unknown.
    "unknown_knocking_warning": Place(52.3600, 20.6200, 1000, time(13, 0)),
    "smoke_engine_bay": Place(*_NATIONAL_ROAD, 10, time(13, 0)),
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
