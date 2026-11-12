"""The demo check behind `/demo-check` (#63): walk every recorded scenario against a running
demo-mode app and fail on any key miss, unrecorded places or invalid replay.

It makes what a visitor makes: the help request, the sample photos, both nearby radii, each
turn and reply, and for the pothole scenario a damage report in both letter languages. It
cleans up the incidents and vehicles it made.
"""

from collections.abc import Iterable

import httpx

from app.domain.ai_turn import Locale
from scripts.demo.scenarios import Scenario
from scripts.demo.walk import (
    API,
    FIRST_RADIUS_KM,
    WIDE_RADIUS_KM,
    Choices,
    Walk,
    ensure_vehicle,
    walk,
    walkable,
)

LETTER_LOCALES: tuple[Locale, ...] = ("en", "pl")


class NotDemoMode(Exception):
    """The app answering is not in demo mode: a check would call the live model."""


async def check(
    client: httpx.AsyncClient, scenarios: Iterable[Scenario], choices: Choices
) -> list[Walk]:
    r = await client.get(f"{API}/config")
    r.raise_for_status()
    if r.json().get("demo_mode") is not True:
        raise NotDemoMode("the app is not in demo mode")
    walks: list[Walk] = []
    vehicles: dict[str, int] = {}
    try:
        for s in scenarios:
            vehicle_id = await ensure_vehicle(client, s, vehicles)
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
        for vehicle_id in vehicles.values():
            await client.delete(f"{API}/vehicles/{vehicle_id}")
    return walks
