"""The semantic replay key (ADR 0004): what decides which recording a demo turn replays."""

import json
from dataclasses import replace

from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.assist.replay_key import replay_key
from app.domain.ai_turn import Reply

VEHICLE = VehicleFactBlock(
    name="Family car",
    make_model="Skoda Octavia",
    year=2019,
    fuel_type="diesel",
    transmission="manual",
    tyre_size="205/55 R16",
    spare_wheel="space_saver",
    wheel_locks=True,
    lock_key_location="glovebox",
    has_assistance=True,
    assistance_insurer="PZU",
)

INPUTS = TurnInputs(
    vehicle=VEHICLE,
    problem_type="flat_tyre",
    note="Loud bang, then wobbling",
    local_time="2026-11-11T14:05+01:00",
    dark=False,
    road_class="motorway_expressway",
    settlement="village",
)


def key(inputs: TurnInputs = INPUTS, **kw: object) -> str:
    args: dict[str, object] = {
        "locale": "en",
        "sample_photo_ids": (),
        "vision": False,
        "replies": (),
    }
    args.update(kw)
    return replay_key(inputs, **args)  # type: ignore[arg-type]


def test_the_key_holds_the_semantic_parts() -> None:
    parts = json.loads(
        key(sample_photo_ids=("flat_tyre",), vision=True, replies=(Reply(option="Yes"),))
    )
    assert parts == {
        "problem_type": "flat_tyre",
        "fuel_type": "diesel",
        "transmission": "manual",
        "spare_wheel": "space_saver",
        "has_assistance": True,
        "sample_photo_ids": ["flat_tyre"],
        "vision": True,
        "locale": "en",
        "replies": [{"option": "Yes"}],
        "road_class": "motorway_expressway",
        "dark": False,
        "situation": "on_road",
    }


def test_the_same_case_gives_the_same_key() -> None:
    assert key() == key()


def test_details_outside_the_key_do_not_change_it() -> None:
    other = replace(
        INPUTS,
        note="A different note",
        local_time="2026-11-12T09:00+01:00",
        settlement="city",
        vehicle=replace(VEHICLE, name="Work van", year=2008, tyre_size=None, wheel_locks=None),
    )
    assert key(other) == key()


def test_the_locale_is_part_of_the_key() -> None:
    assert key(locale="pl") != key(locale="en")


def test_whether_vision_was_used_is_part_of_the_key() -> None:
    assert key(sample_photo_ids=("flat_tyre",), vision=True) != key(
        sample_photo_ids=("flat_tyre",), vision=False
    )


def test_sample_photo_order_does_not_matter_but_the_set_does() -> None:
    assert key(sample_photo_ids=("pothole", "flat_tyre")) == key(
        sample_photo_ids=("flat_tyre", "pothole")
    )
    assert key(sample_photo_ids=("flat_tyre",)) != key()
    assert key(sample_photo_ids=("flat_tyre", "flat_tyre")) == key(sample_photo_ids=("flat_tyre",))


def test_each_reply_so_far_is_part_of_the_key_in_order() -> None:
    a, b = Reply(option="Yes"), Reply(text="on the shoulder")
    assert key(replies=(a,)) != key()
    assert key(replies=(a, b)) != key(replies=(b, a))
    assert key(replies=(Reply(skip=True),)) != key(replies=(a,))


def test_road_class_and_darkness_are_part_of_the_key() -> None:
    assert key(replace(INPUTS, road_class="local_street")) != key()
    assert key(replace(INPUTS, dark=True)) != key()


def test_the_situation_is_part_of_the_key() -> None:
    assert key(replace(INPUTS, situation="parked")) != key()


def test_each_vehicle_fact_in_the_key_changes_it() -> None:
    changes: list[dict[str, object]] = [
        {"fuel_type": "electric"},
        {"transmission": "automatic"},
        {"spare_wheel": "none"},
        {"has_assistance": False},
    ]
    for change in changes:
        vehicle = replace(VEHICLE, **change)  # type: ignore[arg-type]
        assert key(replace(INPUTS, vehicle=vehicle)) != key(), change


def test_no_vehicle_leaves_the_vehicle_parts_unknown() -> None:
    parts = json.loads(key(replace(INPUTS, vehicle=None)))
    assert parts["fuel_type"] is None
    assert parts["transmission"] is None
    assert parts["spare_wheel"] is None
    assert parts["has_assistance"] is False
