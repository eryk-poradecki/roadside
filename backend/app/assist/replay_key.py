"""The semantic replay key (ADR 0004): which recorded answer a demo-mode turn replays.

Built from what changes the first steps, not from the prompt text, so a prompt wording fix or a
different note still replays the scenario. Settlement is left out on purpose: it rarely changes
the advice and would multiply the recordings needed. The key is canonical JSON, readable in a
recording file and stable across runs.
"""

import json
from collections.abc import Sequence
from typing import Any

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


def replay_key(
    inputs: TurnInputs,
    *,
    locale: Locale,
    sample_photo_ids: Sequence[str],
    vision: bool,
    replies: Sequence[Reply],
) -> str:
    """`vision` is whether the photos were shown to the model, not just attached."""
    parts = {
        **_scenario_parts(inputs.problem_type, inputs.situation, inputs.vehicle),
        "sample_photo_ids": sorted(set(sample_photo_ids)),
        "vision": vision,
        "locale": locale,
        "replies": [r.to_payload() for r in replies],
        "road_class": inputs.road_class,
        "dark": inputs.dark,
    }
    return _canonical(parts)
