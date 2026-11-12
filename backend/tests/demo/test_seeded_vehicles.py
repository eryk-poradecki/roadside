"""Each scenario with a demo vehicle replays from the committed recordings when the visitor
picks the seeded car (#122), with no recording miss, at any hour."""

from pathlib import Path

import pytest

from app.services import assistant
from app.services.demo_vehicles import DEMO_VEHICLES
from app.settings import Settings
from scripts.demo.check import check
from scripts.demo.record import load_choices
from scripts.demo.scenarios import load_scenarios
from tests.running import running

BACKEND = Path(__file__).resolve().parents[2]
RECORDINGS = BACKEND / "recordings"
CHOICES = RECORDINGS / "branches" / "choices.json"


@pytest.mark.parametrize("profile_id", DEMO_VEHICLES)
async def test_the_scenarios_replay_on_the_seeded_car(
    profile_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The visitor's clock says night: the recorded light must win.
    monkeypatch.setattr(assistant, "is_dark", lambda *_: True)
    scenarios = [s for s in load_scenarios() if s.profile_id == profile_id]
    settings = Settings(
        database_path=tmp_path / "demo.db",
        upload_dir=tmp_path / "uploads",
        demo_mode=True,
        llm_recordings_dir=RECORDINGS,
    )

    async with running(settings) as client:
        walks = await check(client, scenarios, load_choices(CHOICES))

    assert scenarios
    assert {w.scenario.id for w in walks} == {s.id for s in scenarios}
    assert [(w.name, w.problems) for w in walks if not w.ok] == []
