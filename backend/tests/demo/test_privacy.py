"""The privacy scan run before recordings are committed (#63): no registration, policy number,
phone or coordinates of the driver's may end up in the repo."""

import json
from pathlib import Path

import pytest

from scripts.demo.privacy import scan
from scripts.demo.scenarios import CANARY_PHONE, CANARY_POLICY, CANARY_REGISTRATION


def recording(directory: Path, name: str, *, raw_output: str, user_text: str = "") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "key": name,
        "request": {"schema_name": "ai_turn", "messages": [{"role": "user", "text": user_text}]},
        "raw_output": raw_output,
        "provider": "cli",
        "model": "m",
        "prompt_version": "v3",
        "recorded_at": "t",
    }
    (directory / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False))


def test_clean_recordings_pass(tmp_path: Path) -> None:
    recording(tmp_path, "a", raw_output='{"steps": ["Call 112 now."]}', user_text="Golf 1.4 TSI")

    assert scan(tmp_path) == []


@pytest.mark.parametrize("canary", [CANARY_REGISTRATION, CANARY_POLICY, CANARY_PHONE])
def test_a_planted_vehicle_detail_anywhere_is_found(tmp_path: Path, canary: str) -> None:
    places = tmp_path / "places"
    places.mkdir()
    (places / "p.json").write_text(json.dumps({"label": f"near {canary}"}, ensure_ascii=False))

    [finding] = scan(tmp_path)

    assert finding.path.name == "p.json"


@pytest.mark.parametrize(
    "text",
    ["Your position is 52.40851, 16.91003.", "Call the garage on +48 612 345 678."],
)
def test_coordinates_or_a_phone_in_ai_text_are_found(tmp_path: Path, text: str) -> None:
    recording(tmp_path, "a", raw_output=json.dumps({"steps": [text]}))

    [finding] = scan(tmp_path)

    assert finding.path.name == "a.json"
