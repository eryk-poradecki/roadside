"""The demo scenario list (`docs/demo-scenarios.md`, #62) stays usable by the recording run (#63).

Each scenario's YAML block must use the domain's own values, cover what the list promises, and
give every recording variant its own replay key, so no recording can replay in another's place.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.assist.replay_key import replay_key
from app.domain.incident import ProblemType, Situation
from app.domain.location_context import RoadClass, Settlement
from app.domain.sample_photo import find_sample
from app.domain.vehicle import FuelType, SpareWheel, Transmission

DOC = Path(__file__).resolve().parents[3] / "docs" / "demo-scenarios.md"

# Named in the list but not bundled yet: no licensed source found (see the doc's photo table).
UNBUNDLED_SAMPLES = {"rim_damage"}


def _scenarios() -> list[dict[str, Any]]:
    blocks = re.findall(r"^## Scenario .*?^```yaml\n(.*?)^```", DOC.read_text(), re.M | re.S)
    return [yaml.safe_load(b) for b in blocks]


SCENARIOS = _scenarios()


def _vehicle(s: dict[str, Any]) -> VehicleFactBlock | None:
    v = s["vehicle"]
    if v is None:
        return None
    return VehicleFactBlock(
        name=v["profile_id"],
        make_model=None,
        year=None,
        fuel_type=v["fuel_type"],
        transmission=v["transmission"],
        tyre_size=None,
        spare_wheel=v["spare_wheel"],
        wheel_locks=None,
        lock_key_location=None,
        has_assistance=v["has_assistance"],
        assistance_insurer=None,
    )


def test_lists_eight_scenarios_with_unique_ids() -> None:
    ids = [s["id"] for s in SCENARIOS]
    assert len(ids) == 8
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("s", SCENARIOS, ids=lambda s: s["id"])
def test_scenario_uses_domain_values(s: dict[str, Any]) -> None:
    assert s["problem_type"] in set(ProblemType)
    assert s["situation"] in set(Situation)
    assert s["road_class"] in set(RoadClass)
    assert s["settlement"] in set(Settlement)
    assert isinstance(s["dark"], bool)
    assert isinstance(s["vision"], bool)
    if s["vehicle"] is not None:
        assert s["vehicle"]["fuel_type"] in set(FuelType)
        assert s["vehicle"]["transmission"] in set(Transmission)
        assert s["vehicle"]["spare_wheel"] in set(SpareWheel)
        assert isinstance(s["vehicle"]["has_assistance"], bool)
    assert s["vision"] == bool(s["sample_photos"])


@pytest.mark.parametrize("s", SCENARIOS, ids=lambda s: s["id"])
def test_scenario_has_both_locales_with_a_note_and_a_branch(s: dict[str, Any]) -> None:
    assert set(s["locales"]) == {"pl", "en"}
    for variant in s["locales"].values():
        assert variant["note"].strip()
        assert variant["reply_branches"]


def test_samples_are_bundled_or_known_to_be_missing() -> None:
    used = {sid for s in SCENARIOS for sid in s["sample_photos"]}
    assert {sid for sid in used if find_sample(sid) is None} == UNBUNDLED_SAMPLES


def test_covers_what_the_list_promises() -> None:
    assert {s["problem_type"] for s in SCENARIOS} == set(ProblemType)
    assert any(s["vehicle"] and s["vehicle"]["fuel_type"] == "electric" for s in SCENARIOS)
    assert any(s["expect"]["first_turn"] == "ask" for s in SCENARIOS)
    assert any(s["expect"]["urgent"] for s in SCENARIOS)
    assert any(s["expect"].get("damage_report_followup") for s in SCENARIOS)
    assert sum(1 for s in SCENARIOS if s.get("video")) == 1


def test_every_first_turn_has_its_own_replay_key() -> None:
    keys = [
        replay_key(
            TurnInputs(
                vehicle=_vehicle(s),
                problem_type=s["problem_type"],
                note=variant["note"],
                local_time="2026-11-12T12:00+01:00",
                dark=s["dark"],
                road_class=s["road_class"],
                settlement=s["settlement"],
                situation=s["situation"],
            ),
            locale=locale,
            sample_photo_ids=s["sample_photos"],
            vision=s["vision"],
            replies=[],
        )
        for s in SCENARIOS
        for locale, variant in s["locales"].items()
    ]
    assert len(keys) == 16
    assert len(set(keys)) == len(keys)
