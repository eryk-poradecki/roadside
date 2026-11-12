"""Demo mode's recorded location context and nearby places (ADR 0004, #58).

Demo mode calls neither Nominatim nor Overpass (ADR 0011): what they answered comes with the
scenario. One JSON file per scenario key (the part of the replay key known when the incident
is created) holds the location context with its label, whether it was dark, and one nearby
snapshot per radius: `{key, location, dark, nearby[], recorded_at}`. A recording run with a
live provider writes them into `places/` next to the AI recordings; each successful lookup
merges into the file.

The recorded point itself is never stored, only what was derived from it. A file holds one
point's lookups: the recorder remembers the point in memory, and a lookup from another point
(or the first one of a run) starts the file afresh, so a label and places from two points
never mix.
"""

import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.incident import Location
from app.domain.location_context import LocationContext, ResolvedLocation, RoadClass, Settlement
from app.domain.nearby import MAX_PLACES, NearbyCategory, NearbySnapshot, OsmType, Place
from app.integrations.llm.recording import file_name, write_json
from app.services.clock import real_utc_now

logger = logging.getLogger(__name__)


def places_dir(recordings_dir: Path) -> Path:
    return recordings_dir / "places"


@dataclass(frozen=True, slots=True)
class PlaceRecording:
    key: str
    location: ResolvedLocation | None
    # By radius in km.
    nearby: Mapping[int, NearbySnapshot]
    recorded_at: str
    # Whether it was dark when the scenario was recorded (#63): demo mode replays it in place
    # of the visitor's clock. None in a file recorded before it was kept.
    dark: bool | None = None


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _LocationJson(_Strict):
    road_class: RoadClass
    settlement: Settlement
    label: str | None


class _PlaceJson(_Strict):
    osm_type: OsmType
    osm_id: int
    category: NearbyCategory
    name: str | None
    lat: float
    lon: float
    distance_m: int
    phone: str | None
    opening_hours: str | None


class _SnapshotJson(_Strict):
    radius_km: int
    places: Annotated[list[_PlaceJson], Field(max_length=MAX_PLACES)]
    fetched_at: str
    source: str


class _FileJson(_Strict):
    key: str
    location: _LocationJson | None
    dark: bool | None = None
    nearby: list[_SnapshotJson]
    recorded_at: str


def _from_json(data: object) -> PlaceRecording:
    f = _FileJson.model_validate(data)
    radii = [s.radius_km for s in f.nearby]
    if len(set(radii)) != len(radii):
        raise ValueError("a place recording holds one snapshot per radius")
    loc = f.location
    return PlaceRecording(
        key=f.key,
        location=(
            ResolvedLocation(LocationContext(loc.road_class, loc.settlement), loc.label)
            if loc
            else None
        ),
        nearby={
            s.radius_km: NearbySnapshot(
                places=tuple(Place(**p.model_dump()) for p in s.places),
                radius_km=s.radius_km,
                fetched_at=s.fetched_at,
                source=s.source,
            )
            for s in f.nearby
        },
        recorded_at=f.recorded_at,
        dark=f.dark,
    )


def _to_json(rec: PlaceRecording) -> dict[str, object]:
    loc = rec.location
    return {
        "key": rec.key,
        "location": (
            {
                "road_class": loc.context.road_class.value,
                "settlement": loc.context.settlement.value,
                "label": loc.label,
            }
            if loc
            else None
        ),
        "dark": rec.dark,
        "nearby": [
            {
                "radius_km": s.radius_km,
                "places": [asdict(p) for p in s.places],
                "fetched_at": s.fetched_at,
                "source": s.source,
            }
            for _, s in sorted(rec.nearby.items())
        ],
        "recorded_at": rec.recorded_at,
    }


def _read(path: Path) -> PlaceRecording:
    try:
        return _from_json(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, ValidationError) as exc:
        raise ValueError(f"place recording {path.name} is not valid: {exc}") from exc


def load_place_recordings(directory: Path) -> dict[str, PlaceRecording]:
    """Every place recording in `directory`, by scenario key. A malformed file or a repeated
    key fails startup; a missing directory holds none."""
    recordings: dict[str, PlaceRecording] = {}
    if not directory.is_dir():
        return recordings
    for path in sorted(directory.glob("*.json")):
        rec = _read(path)
        if rec.key in recordings:
            raise ValueError(f"two place recordings have the key {rec.key}")
        recordings[rec.key] = rec
    return recordings


class PlaceRecorder:
    """Merges each live lookup into its scenario's file. Only with `LLM_RECORD=true`, which
    settings refuse in demo mode and on a public deploy.

    A write that fails is logged and lost: the driver still gets the live result.
    """

    def __init__(self, directory: Path, *, clock: Callable[[], str] = real_utc_now) -> None:
        self._directory = directory
        self._clock = clock
        # The context and the places of one incident are looked up in parallel; one process.
        self._lock = asyncio.Lock()
        # The point each scenario was recorded at in this run. Never written to disk.
        self._points: dict[str, tuple[float, float]] = {}

    async def record_location(self, key: str, point: Location, location: ResolvedLocation) -> None:
        await self._merge(key, point, lambda rec: replace(rec, location=location))

    async def record_nearby(self, key: str, point: Location, snapshot: NearbySnapshot) -> None:
        await self._merge(
            key,
            point,
            lambda rec: replace(rec, nearby={**rec.nearby, snapshot.radius_km: snapshot}),
        )

    async def record_dark(self, key: str, point: Location, *, dark: bool) -> None:
        await self._merge(key, point, lambda rec: replace(rec, dark=dark))

    async def _merge(
        self, key: str, point: Location, change: Callable[[PlaceRecording], PlaceRecording]
    ) -> None:
        path = self._directory / file_name(key)
        async with self._lock:
            fresh = self._points.get(key) != (point.lat, point.lon)
            try:
                await asyncio.to_thread(self._merge_file, path, key, fresh, change)
            except (OSError, ValueError):
                logger.exception("could not write place recording %s", path.name)
            else:
                self._points[key] = (point.lat, point.lon)
                logger.info("recorded places %s", path.name)

    def _merge_file(
        self,
        path: Path,
        key: str,
        fresh: bool,
        change: Callable[[PlaceRecording], PlaceRecording],
    ) -> None:
        current = (
            PlaceRecording(key, None, {}, recorded_at="")
            if fresh or not path.exists()
            else _read(path)
        )
        if current.key != key:
            raise ValueError(f"{path.name} holds another key")
        write_json(path, _to_json(replace(change(current), recorded_at=self._clock())))
