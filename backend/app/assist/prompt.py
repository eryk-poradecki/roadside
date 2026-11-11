"""Versioned prompt files and what goes into them (ADR 0003, 0004, 0010).

Privacy: the registration, the assistance phone, the policy number, the coordinates and the
location label never reach the model. The fact block is built from an allow-list, so a new
vehicle field stays out until it is added here on purpose.
"""

import json
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from string import Template
from typing import Any

from app.assist.contract import model_schema
from app.domain.ai_turn import Locale, Reply
from app.domain.vehicle import VehicleFacts

PROMPT_VERSION = "v2"
_PROMPTS = Path(__file__).parent / "prompts"

_LANGUAGES: dict[Locale, str] = {"pl": "Polish", "en": "English"}

# Only on a motorway or expressway (ADR 0004): elsewhere the number would mislead.
_ROAD_HELP = (
    "\nRoad help: on this road you may mention that road help on national roads can also be"
    " called on GDDKiA's 19 111, which is not an emergency number."
)

# Only for an LPG car that ran dry or won't start (#90): an unconditional rule leaked into advice
# for petrol cars and cars with an unknown fuel type, against ADR 0003's "unknown is not none".
_LPG = (
    "\n\nLPG: most LPG systems switch to petrol on their own when the gas runs out, with a beep"
    " and a change on the LPG indicator. If the car ran out of fuel, won't start or cut out, you"
    " may tell the driver to check on the indicator whether it has switched to petrol."
)
_LPG_PROBLEMS = frozenset({"out_of_fuel", "other"})


@dataclass(frozen=True, slots=True)
class VehicleFactBlock:
    """What the model is told about the vehicle; None means unknown."""

    name: str
    make_model: str | None
    year: int | None
    fuel_type: str | None
    transmission: str | None
    tyre_size: str | None
    spare_wheel: str | None
    wheel_locks: bool | None
    lock_key_location: str | None
    # Assistance counts only when a phone number is known; the phone itself stays out.
    has_assistance: bool
    assistance_insurer: str | None

    @classmethod
    def from_facts(cls, f: VehicleFacts) -> "VehicleFactBlock":
        has_assistance = bool(f.assistance_phone and f.assistance_phone.strip())
        return cls(
            name=f.name,
            make_model=f.make_model,
            year=f.year,
            fuel_type=f.fuel_type.value if f.fuel_type else None,
            transmission=f.transmission.value if f.transmission else None,
            tyre_size=f.tyre_size,
            spare_wheel=f.spare_wheel.value if f.spare_wheel else None,
            wheel_locks=f.wheel_locks,
            lock_key_location=f.lock_key_location if f.wheel_locks else None,
            has_assistance=has_assistance,
            assistance_insurer=f.assistance_insurer if has_assistance else None,
        )

    def render(self) -> str:
        def v(value: object) -> str:
            return "unknown" if value is None else str(value)

        if self.wheel_locks is None:
            locks = "unknown"
        elif self.wheel_locks:
            locks = f"yes, key location: {v(self.lock_key_location)}"
        else:
            locks = "no"
        if self.has_assistance:
            assistance = f"has assistance, insurer {v(self.assistance_insurer)}"
        else:
            assistance = "unknown"
        lines = [
            ("Name", self.name),
            ("Model", v(self.make_model)),
            ("Year", v(self.year)),
            ("Fuel type", v(self.fuel_type)),
            ("Transmission", v(self.transmission)),
            ("Tyre size", v(self.tyre_size)),
            ("Spare wheel", v(self.spare_wheel)),
            ("Wheel locks", locks),
            ("Assistance insurance", assistance),
        ]
        return "\n".join(f"- {label}: {value}" for label, value in lines)


# What the driver chose in the help sheet (#93), keyed by the `Situation` values.
_SITUATIONS = {
    "on_road": "on the road (stopped on or beside a road with traffic)",
    "parked": "parked off the road (a parking lot or a driveway), away from moving traffic",
}


@dataclass(frozen=True, slots=True)
class TurnInputs:
    """The inputs snapshot: everything a turn was produced from, stored with it (ADR 0004)."""

    vehicle: VehicleFactBlock | None
    problem_type: str
    note: str | None
    local_time: str
    dark: bool
    road_class: str = "unknown"
    settlement: str = "unknown"
    situation: str = "on_road"
    photo_ids_seen: tuple[int, ...] = field(default=())
    photos_not_sent: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Exchange:
    """A clarifying question already asked, and the driver's reply to it."""

    question: str
    reply: Reply

    def render(self, n: int) -> str:
        r = self.reply
        if r.option is not None:
            said = f"The driver tapped: {json.dumps(r.option, ensure_ascii=False)}"
        elif r.text is not None:
            said = f"The driver wrote: {json.dumps(r.text, ensure_ascii=False)}"
        else:
            said = "The driver skipped further questions and wants the steps now"
        return f"{n}. You asked: {json.dumps(self.question, ensure_ascii=False)}\n   {said}."


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    system: str
    user: str
    schema: dict[str, Any]


@cache
def _template(name: str) -> Template:
    return Template((_PROMPTS / PROMPT_VERSION / name).read_text(encoding="utf-8"))


def render(
    inputs: TurnInputs,
    locale: Locale,
    *,
    allow_ask: bool,
    exchanges: tuple[Exchange, ...] = (),
) -> RenderedPrompt:
    schema = model_schema(allow_ask=allow_ask)
    system = _template("system.md").substitute(
        questions=_template("ask_allowed.md" if allow_ask else "ask_forbidden.md").template,
        schema=json.dumps(schema, indent=2),
    )
    seen = len(inputs.photo_ids_seen)
    photos = f"{seen} attached and shown to you" if seen else "none shown to you"
    if inputs.photos_not_sent:
        photos += f"; {inputs.photos_not_sent} more not sent to you"
    language = _LANGUAGES[locale]
    conversation = (
        "\n\nClarifying questions so far:\n"
        + "\n".join(e.render(n) for n, e in enumerate(exchanges, start=1))
        if exchanges
        else ""
    )
    user = _template("user.md").substitute(
        problem=inputs.problem_type,
        note=inputs.note or "(none)",
        vehicle=inputs.vehicle.render() if inputs.vehicle else "No vehicle details were given.",
        lpg=_LPG
        if inputs.vehicle
        and inputs.vehicle.fuel_type == "lpg"
        and inputs.problem_type in _LPG_PROBLEMS
        else "",
        road_class=inputs.road_class,
        settlement=inputs.settlement,
        situation=_SITUATIONS[inputs.situation],
        # A parked car near a motorway (a service area) still reads as motorway: no road help.
        road_help=_ROAD_HELP
        if inputs.road_class == "motorway_expressway" and inputs.situation != "parked"
        else "",
        local_time=inputs.local_time,
        light="dark" if inputs.dark else "daylight",
        photos=photos,
        conversation=conversation,
        language=language,
    )
    return RenderedPrompt(system=system, user=user, schema=schema)
