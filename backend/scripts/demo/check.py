"""The demo check behind `/demo-check` (#63): walk every recorded scenario against a running
demo-mode app and fail on any key miss, unrecorded places or invalid replay.

It makes what a visitor makes: the help request on the seeded demo vehicle (#122), the sample
photos, both nearby radii, each turn and reply, and for the pothole scenario a damage report in
both letter languages. It cleans up the incidents it made and leaves the vehicles as it found
them.
"""

from collections.abc import Iterable, Mapping
from typing import Any

import httpx

from app.domain.ai_turn import Locale
from app.services.demo_vehicles import DEMO_VEHICLES
from scripts.demo.scenarios import Scenario
from scripts.demo.walk import (
    API,
    FIRST_RADIUS_KM,
    WIDE_RADIUS_KM,
    Choices,
    Walk,
    walk,
    walkable,
)

LETTER_LOCALES: tuple[Locale, ...] = ("en", "pl")


class NotDemoMode(Exception):
    """The app answering is not in demo mode: a check would call the live model."""


class NoDemoVehicle(Exception):
    """A scenario's demo vehicle is not seeded: a visitor could not pick it either."""


def _replay_facts(v: Mapping[str, Any]) -> tuple[object, ...]:
    """What puts a vehicle in the replay key (ADR 0004)."""
    phone = v.get("assistance_phone")
    return (
        v.get("fuel_type"),
        v.get("transmission"),
        v.get("spare_wheel"),
        bool(phone and phone.strip()),
    )


async def seeded_vehicles(client: httpx.AsyncClient) -> dict[str, int]:
    """The seeded demo vehicles as a visitor picks them, by name, with their replay facts
    intact: profile id → id. An edited one is missing, not walked into a recording miss."""
    r = await client.get(f"{API}/vehicles")
    r.raise_for_status()
    found: dict[str, int] = {}
    for profile_id, seeded in DEMO_VEHICLES.items():
        want = (seeded.name, _replay_facts(seeded.model_dump(mode="json")))
        for v in r.json():
            if (v["name"], _replay_facts(v)) == want:
                found[profile_id] = int(v["id"])
                break
    return found


async def check(
    client: httpx.AsyncClient, scenarios: Iterable[Scenario], choices: Choices
) -> list[Walk]:
    r = await client.get(f"{API}/config")
    r.raise_for_status()
    if r.json().get("demo_mode") is not True:
        raise NotDemoMode("the app is not in demo mode")
    scenarios = list(scenarios)
    vehicles = await seeded_vehicles(client)
    missing = sorted({s.profile_id for s in scenarios if s.profile_id} - set(vehicles))
    if missing:
        names = ", ".join(DEMO_VEHICLES[p].name for p in missing)
        raise NoDemoVehicle(f"the demo vehicles are not seeded or were edited: {names}")
    walks: list[Walk] = []
    try:
        for s in scenarios:
            vehicle_id = vehicles[s.profile_id] if s.profile_id else None
            for variant in s.variants:
                branches = [b for b in variant.branches if walkable(s, variant, b, choices)]
                for i, branch in enumerate(branches):
                    # The variant's first walk checks its places and letters.
                    first = i == 0
                    w = await walk(
                        client,
                        s,
                        variant,
                        branch,
                        vehicle_id=vehicle_id,
                        choices=choices,
                        radii=(FIRST_RADIUS_KM, WIDE_RADIUS_KM) if first else (),
                        report_locales=LETTER_LOCALES if s.damage_report and first else (),
                    )
                    walks.append(w)
    finally:
        for w in walks:
            if w.incident is not None:
                await client.delete(w.incident)
    return walks
