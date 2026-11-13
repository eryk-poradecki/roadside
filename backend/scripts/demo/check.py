"""The demo check behind `/demo-check` (#63): walk every recorded scenario against a running
demo-mode app and fail on any key miss, unrecorded places or invalid replay.

It makes what a visitor makes: the help request on the seeded demo vehicle (#122), the sample
photos, both nearby radii, each turn and reply, and for the pothole scenario a damage report in
both letter languages. It cleans up the incidents it made and leaves the vehicles as it found
them.
"""

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

import httpx

from app.domain.ai_turn import Locale
from app.schemas.meta import DemoScenario
from app.schemas.vehicle import VehicleUpdate
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


class DemoCheckFailed(Exception):
    """The running stack cannot fulfil the demo contract."""


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
    """The seeded demo vehicles as a visitor picks them, by demo_profile, with their replay facts
    intact: profile id → id. An edited one is missing, not walked into a recording miss."""
    r = await client.get(f"{API}/vehicles")
    r.raise_for_status()
    found: dict[str, int] = {}
    for profile_id, seeded in DEMO_VEHICLES.items():
        want = _replay_facts(seeded.model_dump(mode="json"))
        for v in r.json():
            if v.get("demo_profile") == profile_id and _replay_facts(v) == want:
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
    missing = sorted(set(DEMO_VEHICLES) - set(vehicles))
    if missing:
        names = ", ".join(DEMO_VEHICLES[p].name for p in missing)
        raise NoDemoVehicle(f"the demo vehicles are not seeded or were edited: {names}")
    catalogue = {s.id: s for s in map(DemoScenario.model_validate, r.json()["demo_scenarios"])}
    for scenario in scenarios:
        offered = catalogue.get(scenario.id)
        if offered is None:
            raise DemoCheckFailed(
                f"/config is missing scenario {scenario.id}: check its recordings"
            )
        missing_locales = {v.locale for v in scenario.variants} - offered.locales.keys()
        if missing_locales:
            raise DemoCheckFailed(
                f"/config scenario {scenario.id} is missing locales "
                f"{', '.join(sorted(missing_locales))}: "
                "check its recordings"
            )
    await check_vehicle_protection(client)
    walks: list[Walk] = []
    try:
        for documented in scenarios:
            offered = catalogue[documented.id]
            s = replace(
                documented,
                problem_type=offered.problem_type.value,
                profile_id=offered.vehicle_profile,
                situation=offered.situation.value,
                sample_photos=tuple(offered.sample_photo_ids),
            )
            if s.profile_id and s.profile_id not in vehicles:
                raise NoDemoVehicle(f"the demo vehicle is not seeded or was edited: {s.profile_id}")
            vehicle_id = vehicles[s.profile_id] if s.profile_id else None
            for locale, copy in offered.locales.items():
                variant = replace(
                    next(v for v in documented.variants if v.locale == locale), note=copy.note
                )
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
                        location=offered.location,
                        radii=(FIRST_RADIUS_KM, WIDE_RADIUS_KM) if first else (),
                        report_locales=LETTER_LOCALES if s.damage_report and first else (),
                    )
                    walks.append(w)
    finally:
        for w in walks:
            if w.incident is not None:
                await client.delete(w.incident)
    return walks


async def check_vehicle_protection(client: httpx.AsyncClient) -> None:
    """Try forbidden mutations and allowed default changes, restoring the original default."""
    response = await client.get(f"{API}/vehicles")
    response.raise_for_status()
    vehicles = response.json()
    demo = [v for v in vehicles if v.get("demo_profile") in DEMO_VEHICLES]
    try:
        for vehicle in demo:
            path = f"{API}/vehicles/{vehicle['id']}"
            body = {key: vehicle[key] for key in VehicleUpdate.model_fields}
            changed = body | {"fuel_type": "diesel" if body["fuel_type"] != "diesel" else "petrol"}
            for method, payload in (("PUT", changed), ("DELETE", None)):
                response = await client.request(method, path, json=payload)
                if (
                    response.status_code != 403
                    or response.json().get("reason") != "demo_vehicle_read_only"
                ):
                    raise DemoCheckFailed(
                        f"{vehicle['demo_profile']}: {method} must return "
                        "403 demo_vehicle_read_only "
                        f"(got {response.status_code})"
                    )
            response = await client.put(path, json=body | {"is_default": not body["is_default"]})
            if response.status_code != 200 or response.json()["is_default"] is body["is_default"]:
                raise DemoCheckFailed(f"{vehicle['demo_profile']}: changing only is_default failed")
    finally:
        # Clear any temporary default first, then restore the original (possibly a visitor's).
        response = await client.get(f"{API}/vehicles")
        response.raise_for_status()
        original = {v["id"]: v for v in vehicles}
        current = response.json()
        for vehicle in sorted(current, key=lambda v: original[v["id"]]["is_default"]):
            wanted = original[vehicle["id"]]["is_default"]
            if vehicle["is_default"] != wanted:
                body = {key: vehicle[key] for key in VehicleUpdate.model_fields} | {
                    "is_default": wanted
                }
                response = await client.put(f"{API}/vehicles/{vehicle['id']}", json=body)
                if response.status_code != 200:
                    raise DemoCheckFailed(f"could not restore default vehicle {vehicle['id']}")
