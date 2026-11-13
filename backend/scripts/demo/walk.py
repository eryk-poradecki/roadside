"""Walk one demo scenario branch through the HTTP API, as a visitor's browser would (#63).

The recording run walks it in-process against the live model, and the demo check walks it
against a running demo-mode stack, so both exercise the very requests a visitor makes: the
help request, its sample photos, the nearby lookups, each turn and reply, the damage report.

A branch's semantic steps (`intent: safe_walk_to_station`) become exact option texts through
`choices`, written by whoever reviewed the recorded question (the `/record-replays` skill).
"""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.domain.ai_turn import Locale
from app.schemas.incident import LocationRead
from scripts.demo.scenarios import PROFILES, Branch, Scenario, Variant

API = "/api/v1"
FIRST_RADIUS_KM = 5
WIDE_RADIUS_KM = 25

# {scenario id: {locale: {intent: exact option text}}}
Choices = Mapping[str, Mapping[str, Mapping[str, str]]]


class StepHook(Protocol):
    """Told around each request that may reach the model, so a recording run can say which
    recording each one used."""

    def begin(self, label: str) -> None: ...

    def end(self, label: str) -> None: ...


@dataclass(slots=True)
class Walk:
    scenario: Scenario
    variant: Variant
    branch: Branch
    # Each model turn as the API returned it, in order.
    turns: list[dict[str, Any]] = field(default_factory=list)
    # The damage report drafts, by letter locale.
    reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Each nearby lookup: radius → "found" | "none" | the problem's reason.
    nearby: dict[int, str] = field(default_factory=dict)
    location_label: str | None = None
    # The incident's API path, once created.
    incident: str | None = None
    # What makes the walk fail: a request that failed, a key miss, an option not offered.
    problems: list[str] = field(default_factory=list)
    # What a reviewer must look at, but which can be right: a first turn of the other kind.
    deviations: list[str] = field(default_factory=list)
    # The question still waiting for a reviewer's choice: (intent, question, options).
    needs_choice: tuple[str, str, list[str]] | None = None

    @property
    def name(self) -> str:
        return f"{self.scenario.id} · {self.variant.locale} · {self.branch.id}"

    @property
    def ok(self) -> bool:
        return not self.problems and self.needs_choice is None


def walkable(scenario: Scenario, variant: Variant, branch: Branch, choices: Choices) -> bool:
    """Whether to walk a branch: every required one, and an optional one once it has choices."""
    if not branch.optional:
        return True
    chosen = choices.get(scenario.id, {}).get(variant.locale, {})
    return all(step.skip or step.intent in chosen for step in branch.steps)


def _reason(r: httpx.Response) -> str:
    try:
        body = r.json()
    except ValueError:
        return f"HTTP {r.status_code}"
    reason = body.get("reason") if isinstance(body, dict) else None
    return f"HTTP {r.status_code} {reason or ''}".strip()


class _NoHook:
    def begin(self, label: str) -> None:
        pass

    def end(self, label: str) -> None:
        pass


async def walk(
    client: httpx.AsyncClient,
    scenario: Scenario,
    variant: Variant,
    branch: Branch,
    *,
    vehicle_id: int | None,
    choices: Choices,
    location: LocationRead | None = None,
    radii: tuple[int, ...] = (),
    report_locales: tuple[Locale, ...] = (),
    hook: StepHook | None = None,
    nearby_attempts: int = 1,
    retry_wait_s: float = 0.0,
) -> Walk:
    """`nearby_attempts` > 1 retries a failed nearby lookup, `retry_wait_s` apart: live
    Overpass often fails, and an unrecorded radius is a miss in demo mode."""
    w = Walk(scenario, variant, branch)
    await _steps(
        client,
        w,
        vehicle_id=vehicle_id,
        choices=choices,
        location=location,
        radii=radii,
        nearby_attempts=nearby_attempts,
        retry_wait_s=retry_wait_s,
        report_locales=report_locales,
        hook=hook or _NoHook(),
    )
    if w.incident is not None:
        r = await client.get(w.incident)
        if r.status_code == 200:
            w.location_label = r.json()["location_label"]
    return w


async def _steps(
    client: httpx.AsyncClient,
    w: Walk,
    *,
    vehicle_id: int | None,
    choices: Choices,
    location: LocationRead | None = None,
    radii: tuple[int, ...] = (),
    report_locales: tuple[Locale, ...] = (),
    hook: StepHook,
    nearby_attempts: int,
    retry_wait_s: float,
) -> None:
    scenario, variant, branch = w.scenario, w.variant, w.branch
    place = scenario.place
    r = await client.post(
        f"{API}/incidents",
        json={
            "problem_type": scenario.problem_type,
            "vehicle_id": vehicle_id,
            "note": variant.note,
            "situation": scenario.situation,
            "location": location.model_dump(mode="json")
            if location
            else {"lat": place.lat, "lon": place.lon, "accuracy_m": place.accuracy_m},
        },
    )
    if r.status_code != 201:
        w.problems.append(f"help request: {_reason(r)}")
        return
    incident = f"{API}/incidents/{r.json()['id']}"
    w.incident = incident

    for sample_id in scenario.sample_photos:
        r = await client.post(f"{incident}/photos", json={"sample_id": sample_id})
        if r.status_code != 201:
            w.problems.append(f"sample photo {sample_id}: {_reason(r)}")
            return

    for radius in radii:
        for attempt in range(nearby_attempts):
            if attempt:
                await asyncio.sleep(retry_wait_s)
            r = await client.post(f"{incident}/nearby", json={"radius_km": radius})
            if r.status_code != 503:
                break
        w.nearby[radius] = r.json()["status"] if r.status_code == 200 else _reason(r)
        if r.status_code != 200:
            w.problems.append(f"nearby {radius} km: {_reason(r)}")

    if not await _turn(client, incident, w, {"locale": variant.locale}, "first turn", hook):
        return
    _check_first_turn(w)

    chosen = choices.get(scenario.id, {}).get(variant.locale, {})
    for step in branch.steps:
        last = w.turns[-1]
        if last["kind"] != "question":
            w.deviations.append(f"no question to reply {step.label()!r} to")
            break
        options: list[str] = last["question"]["options"]
        reply: dict[str, Any]
        if step.skip:
            reply = {"skip": True}
        else:
            intent = str(step.intent)
            option = chosen.get(intent)
            if option is None:
                w.needs_choice = (intent, last["question"]["question"], options)
                return
            if option not in options:
                w.problems.append(f"chosen option {option!r} is not offered: {options}")
                return
            reply = {"option": option}
        body = {"locale": variant.locale, "reply": reply}
        if not await _turn(client, incident, w, body, f"reply {step.label()}", hook):
            return
    if w.turns[-1]["kind"] == "question" and branch.steps:
        w.deviations.append("the branch ends on another question")

    _check_context(w)
    for i, locale in enumerate(report_locales):
        label = f"damage report {locale}"
        hook.begin(label)
        r = await client.post(
            f"{incident}/damage-report", json={"locale": locale, "replace": i > 0}
        )
        hook.end(label)
        if r.status_code not in (200, 201):
            w.problems.append(f"{label}: {_reason(r)}")
        else:
            w.reports[locale] = r.json()

    return


async def _turn(
    client: httpx.AsyncClient,
    incident: str,
    w: Walk,
    body: dict[str, Any],
    label: str,
    hook: StepHook,
) -> bool:
    hook.begin(label)
    r = await client.post(f"{incident}/ai-turns", json=body)
    hook.end(label)
    if r.status_code != 201:
        w.problems.append(f"{label}: {_reason(r)}")
        return False
    w.turns.append(r.json())
    return True


def _check_first_turn(w: Walk) -> None:
    first = w.turns[0]
    planned = w.variant.first_turn or w.scenario.first_turn
    expected = "question" if planned == "ask" else "advice"
    if first["kind"] != expected:
        w.deviations.append(f"first turn is {first['kind']}, the scenario expects {expected}")
    urgent = w.scenario.expect.get("urgent")
    if urgent is not None and first["urgent"] is not urgent:
        w.deviations.append(f"first turn urgent={first['urgent']}, the scenario expects {urgent}")


def _check_context(w: Walk) -> None:
    """`road_class` and `dark` are in the replay key: a wrong one recorded the wrong key."""
    inputs = w.turns[-1]["inputs"]
    s = w.scenario
    if inputs["road_class"] != s.road_class:
        w.problems.append(f"road_class {inputs['road_class']}, the scenario is {s.road_class}")
    if inputs["dark"] is not s.dark:
        w.problems.append(f"dark={inputs['dark']}, the scenario is dark={s.dark}")
    if inputs["settlement"] != s.settlement:
        w.deviations.append(
            f"settlement {inputs['settlement']} (not in the key), the scenario says {s.settlement}"
        )


async def ensure_vehicle(c: httpx.AsyncClient, s: Scenario, vehicles: dict[str, int]) -> int | None:
    """The scenario's demo vehicle, made once per run; `vehicles` maps profile ids to ids."""
    if s.profile_id is None:
        return None
    if s.profile_id not in vehicles:
        r = await c.post(f"{API}/vehicles", json=PROFILES[s.profile_id])
        r.raise_for_status()
        vehicles[s.profile_id] = int(r.json()["id"])
    return vehicles[s.profile_id]
