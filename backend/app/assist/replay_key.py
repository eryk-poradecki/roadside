"""The semantic replay key (ADR 0004): which recorded answer a demo-mode turn replays.

Built from what changes the first steps, not from the prompt text, so a prompt wording fix or a
different note still replays the scenario. Settlement is left out on purpose: it rarely changes
the advice and would multiply the recordings needed. The key is canonical JSON, readable in a
recording file and stable across runs.
"""

import json
from collections.abc import Sequence

from app.assist.prompt import TurnInputs
from app.domain.ai_turn import Locale, Reply


def replay_key(
    inputs: TurnInputs,
    *,
    locale: Locale,
    sample_photo_ids: Sequence[str],
    vision: bool,
    replies: Sequence[Reply],
) -> str:
    """`vision` is whether the photos were shown to the model, not just attached."""
    vehicle = inputs.vehicle
    parts = {
        "problem_type": inputs.problem_type,
        "fuel_type": vehicle.fuel_type if vehicle else None,
        "transmission": vehicle.transmission if vehicle else None,
        "spare_wheel": vehicle.spare_wheel if vehicle else None,
        "has_assistance": vehicle.has_assistance if vehicle else False,
        "sample_photo_ids": sorted(set(sample_photo_ids)),
        "vision": vision,
        "locale": locale,
        "replies": [r.to_payload() for r in replies],
        "road_class": inputs.road_class,
        "dark": inputs.dark,
        "situation": inputs.situation,
    }
    return json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
