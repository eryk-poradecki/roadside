"""The recording run behind `/record-replays` (#63, ADR 0004).

It walks every demo scenario through the app in-process, with the live model wrapped in
`RecordingProvider` and live Nominatim and Overpass recorded by `PlaceRecorder`, so what it
writes is exactly what demo mode replays. Each scenario runs on a clock shifted to its time
of day, so `dark` (in the replay key) and the local time the model reads agree with the
scenario whatever the hour of the run; the light is recorded with the scenario's places,
and demo mode replays it in place of the visitor's clock.

What is already recorded is reused, not asked again (`ReuseProvider`): delete a recording, or
pass `--fresh`, to record it anew. A question's branches wait for a reviewer's choice of
option; rerun with the choice and the replies are recorded against the same question.
"""

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI

from app.deps import get_llm_provider
from app.domain.ai_turn import Locale
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.recording import file_name, load_recordings
from app.integrations.place_recording import places_dir
from app.services import clock
from scripts.demo.privacy import Finding, scan
from scripts.demo.reuse import Outcome, ReuseProvider
from scripts.demo.scenarios import Scenario
from scripts.demo.walk import (
    FIRST_RADIUS_KM,
    WIDE_RADIUS_KM,
    Choices,
    Walk,
    ensure_vehicle,
    walk,
    walkable,
)

# Above the turn budget (<100 s) and the Overpass budget, which cap every request.
_REQUEST_TIMEOUT_S = 300.0


def load_choices(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} holds an object: {{scenario: {{locale: {{intent: option}}}}}}")
    return data


@dataclass(slots=True)
class RecordRun:
    walks: list[Walk] = field(default_factory=list)
    # Per walk name: (step label, recording file, reused or recorded).
    steps: dict[str, list[tuple[str, str, Outcome]]] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    # Recordings no walk of a full run reached: an old question's replies, a stale key.
    orphans: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(w.ok for w in self.walks) and not self.findings


class _StepLog:
    def __init__(self, reuse: ReuseProvider, run: RecordRun) -> None:
        self._reuse = reuse
        self._run = run
        self.walk_name = ""

    def begin(self, label: str) -> None:
        self._reuse.begin_step()

    def end(self, label: str) -> None:
        self._run.steps.setdefault(self.walk_name, []).extend(
            (label, file_name(key), outcome) for key, outcome in self._reuse.step_log
        )


async def record(
    app: FastAPI,
    live: LLMProvider,
    recordings_dir: Path,
    scenarios: Iterable[Scenario],
    choices: Choices,
    *,
    fresh: bool = False,
    full_run: bool = False,
    today: datetime | None = None,
    nearby_attempts: int = 4,
    retry_wait_s: float = 15.0,
) -> RecordRun:
    """Walk the scenarios against `live` (a `RecordingProvider`) and record what is missing.

    `app` is a recording app (`DEMO_MODE=false`, `LLM_RECORD=true`) whose lifespan has run.
    `full_run` means every scenario was walked, so recordings none reached are orphans.
    """
    # Real time, not the shifted clock: place files written by this run are newer.
    started = time.time()
    today = today or clock.now()
    reuse = ReuseProvider(live, load_recordings(recordings_dir), fresh=fresh)
    app.dependency_overrides[get_llm_provider] = lambda: reuse
    run = RecordRun()
    log = _StepLog(reuse, run)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://record", timeout=_REQUEST_TIMEOUT_S
    ) as c:
        vehicles: dict[str, int] = {}
        for s in scenarios:
            vehicle_id = await ensure_vehicle(c, s, vehicles)
            first_of_scenario = True
            for variant in s.variants:
                branches = [b for b in variant.branches if walkable(s, variant, b, choices)]
                for i, branch in enumerate(branches):
                    # The places are looked up once per scenario: the first lookup of a run
                    # starts its file afresh, and the later walks start from the same point.
                    radii = (FIRST_RADIUS_KM, WIDE_RADIUS_KM) if first_of_scenario else ()
                    letters: tuple[Locale, ...] = (
                        (variant.locale,) if s.damage_report and i == 0 else ()
                    )
                    log.walk_name = f"{s.id} · {variant.locale} · {branch.id}"
                    with clock.shifted_to(s.at(today)):
                        w = await walk(
                            c,
                            s,
                            variant,
                            branch,
                            vehicle_id=vehicle_id,
                            choices=choices,
                            radii=radii,
                            report_locales=letters,
                            hook=log,
                            nearby_attempts=nearby_attempts,
                            retry_wait_s=retry_wait_s,
                        )
                    first_of_scenario = False
                    run.walks.append(w)
    run.findings = scan(recordings_dir)
    if full_run:
        run.orphans = _orphans(recordings_dir, set(reuse.touched), started)
    return run


def _orphans(directory: Path, touched: set[str], started: float) -> list[Path]:
    """AI recordings no walk asked for, and place files this run didn't write."""
    reached = {file_name(key) for key in touched}
    orphans = [p for p in sorted(directory.glob("*.json")) if p.name not in reached]
    places = sorted(places_dir(directory).glob("*.json"))
    return orphans + [p for p in places if p.stat().st_mtime < started]
