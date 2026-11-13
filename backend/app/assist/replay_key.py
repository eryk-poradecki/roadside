"""The semantic replay key (ADR 0004): which recorded answer a demo-mode turn replays.

Built from what changes the first steps, not from the prompt text, so a prompt wording fix or a
different note still replays the scenario. Settlement is left out on purpose: it rarely changes
the advice and would multiply the recordings needed. The key is canonical JSON, readable in a
recording file and stable across runs.
"""

import json
from collections.abc import Sequence
from typing import Any, Literal

from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.domain.ai_turn import Locale, Reply


def _scenario_parts(
    problem_type: str, situation: str, vehicle: VehicleFactBlock | None
) -> dict[str, Any]:
    return {
        "problem_type": problem_type,
        "fuel_type": vehicle.fuel_type if vehicle else None,
        "transmission": vehicle.transmission if vehicle else None,
        "spare_wheel": vehicle.spare_wheel if vehicle else None,
        "has_assistance": vehicle.has_assistance if vehicle else False,
        "situation": situation,
    }


def _canonical(parts: dict[str, Any]) -> str:
    return json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def scenario_key(problem_type: str, situation: str, vehicle: VehicleFactBlock | None) -> str:
    """The part of the replay key known when the incident is created (#58).

    Demo mode's recorded location context and nearby places sit under it. They can't sit under
    the whole replay key: `road_class` comes from the recorded context itself, and the places
    are looked up before the first turn, in parallel with the photos.
    """
    return _canonical(_scenario_parts(problem_type, situation, vehicle))


def _replay_parts(
    inputs: TurnInputs,
    *,
    locale: Locale,
    sample_photo_ids: Sequence[str],
    vision: bool,
    replies: Sequence[Reply],
) -> dict[str, Any]:
    return {
        **_scenario_parts(inputs.problem_type, inputs.situation, inputs.vehicle),
        "sample_photo_ids": sorted(set(sample_photo_ids)),
        "vision": vision,
        "locale": locale,
        "replies": [r.to_payload() for r in replies],
        "road_class": inputs.road_class,
        "dark": inputs.dark,
    }


def replay_key(
    inputs: TurnInputs,
    *,
    locale: Locale,
    sample_photo_ids: Sequence[str],
    vision: bool,
    replies: Sequence[Reply],
) -> str:
    """`vision` is whether the photos were shown to the model, not just attached."""
    return _canonical(
        _replay_parts(
            inputs,
            locale=locale,
            sample_photo_ids=sample_photo_ids,
            vision=vision,
            replies=replies,
        )
    )


def _parts_of(key: str) -> dict[str, Any]:
    try:
        parts = json.loads(key)
    except ValueError:
        return {}
    return parts if isinstance(parts, dict) else {}


def made_with_vision(key: str) -> bool:
    """Whether a recording under `key` was made with the photos shown to the model."""
    return _parts_of(key).get("vision") is True


KeyStage = Literal["first_turn", "after_reply", "artifact"]


def key_stage(key: str) -> KeyStage:
    """Which step a key replays: the first turn, a turn after the driver's reply, or an
    artifact such as the damage report draft."""
    parts = _parts_of(key)
    if "artifact" in parts:
        return "artifact"
    return "after_reply" if parts.get("replies") else "first_turn"


def damage_report_key(
    inputs: TurnInputs,
    *,
    locale: Locale,
    sample_photo_ids: Sequence[str],
    vision: bool,
    replies: Sequence[Reply],
) -> str:
    """The key a demo-mode damage report draft replays from (ADR 0009).

    The same semantic key as the incident's AI turns, so the draft sits beside its scenario's
    recordings; `artifact` keeps it apart from the turn under that key. `locale` is the
    letter's language, which the driver picks and which may differ from the advice's.
    """
    parts = _replay_parts(
        inputs,
        locale=locale,
        sample_photo_ids=sample_photo_ids,
        vision=vision,
        replies=replies,
    )
    return _canonical({**parts, "artifact": "damage_report"})
