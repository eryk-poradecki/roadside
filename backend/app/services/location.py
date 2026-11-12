"""Location context for the AI turn: one reverse lookup, mapped by the pure rules (ADR 0004).

Demo mode makes no lookup: the context recorded for the scenario stands in for it (#58).
"""

from collections.abc import Mapping
from dataclasses import replace

import aiosqlite

from app.assist.prompt import VehicleFactBlock
from app.assist.replay_key import scenario_key
from app.db.connection import transaction
from app.domain.ai_turn import Locale
from app.domain.incident import Incident, Location
from app.domain.location_context import ResolvedLocation, derive_location
from app.integrations.nominatim import ReverseGeocoder
from app.integrations.place_recording import PlaceRecorder, PlaceRecording
from app.repositories.incidents import IncidentRepository
from app.repositories.vehicles import VehicleRepository
from app.services.clock import utc_now


async def load_scenario_key(incident: Incident, vehicles: VehicleRepository) -> str:
    """The incident's scenario key, which its recorded places sit under (#58)."""
    vehicle = await vehicles.get(incident.vehicle_id) if incident.vehicle_id is not None else None
    facts = VehicleFactBlock.from_facts(vehicle.facts) if vehicle else None
    return scenario_key(incident.problem_type.value, incident.situation.value, facts)


class LocationResolver:
    """`geocoder` is None in demo mode, where no call is made and `recorded` answers instead.
    With `recorder`, each live result is also recorded for demo mode."""

    def __init__(
        self,
        geocoder: ReverseGeocoder | None,
        *,
        max_gps_accuracy_m: float,
        max_road_distance_m: float,
        recorded: Mapping[str, PlaceRecording] | None = None,
        recorder: PlaceRecorder | None = None,
    ) -> None:
        self._geocoder = geocoder
        self._max_gps_accuracy_m = max_gps_accuracy_m
        self._max_road_distance_m = max_road_distance_m
        self._recorded = recorded or {}
        self._recorder = recorder

    async def resolve(
        self, location: Location, locale: Locale, scenario_key: str
    ) -> ResolvedLocation | None:
        """None when there is no lookup or it failed: the caller uses unknown and caches nothing.

        In demo mode, the recorded context and label of the scenario, wherever the driver is.
        """
        if self._geocoder is None:
            rec = self._recorded.get(scenario_key)
            return rec.location if rec else None
        result = await self._geocoder.reverse(location.lat, location.lon, locale)
        if result is None:
            return None
        context, label = derive_location(
            result,
            location,
            max_gps_accuracy_m=self._max_gps_accuracy_m,
            max_road_distance_m=self._max_road_distance_m,
        )
        return ResolvedLocation(context, label)

    def recorded_dark(self, scenario_key: str) -> bool | None:
        """Demo mode: whether the scenario was recorded in the dark, which stands in for the
        visitor's clock, since `dark` is in the replay key (#63). None when live, or when
        nothing recorded says."""
        if self._geocoder is not None:
            return None
        rec = self._recorded.get(scenario_key)
        return rec.dark if rec else None

    async def record_dark(self, location: Location, scenario_key: str, *, dark: bool) -> None:
        """Record the light a live turn was given (recording runs only)."""
        if self._recorder is not None and self._geocoder is not None:
            await self._recorder.record_dark(scenario_key, location, dark=dark)

    @property
    def keyed_by_scenario(self) -> bool:
        """Whether the context depends on the incident's scenario: replayed or recorded."""
        return self._geocoder is None or self._recorder is not None

    async def record(
        self, location: Location, scenario_key: str, resolved: ResolvedLocation
    ) -> None:
        """Record a live context once it is cached on the incident (recording runs only)."""
        if self._recorder is not None and self._geocoder is not None:
            await self._recorder.record_location(scenario_key, location, resolved)


async def refresh_location_context(
    conn: aiosqlite.Connection,
    incidents: IncidentRepository,
    resolver: LocationResolver,
    incident: Incident,
    locale: Locale,
    scenario_key: str,
) -> Incident:
    """Look the context up for the incident's location and cache it with the label.

    Runs outside any transaction, so no write lock is held during the lookup. A failed lookup
    caches nothing. Returns the incident as stored, or unchanged when nothing was written.
    """
    if incident.location is None:
        return incident
    resolved = await resolver.resolve(incident.location, locale, scenario_key)
    if resolved is None:
        return incident
    async with transaction(conn):
        current = await incidents.get(incident.id)
        # A PATCH may have moved or deleted the incident during the lookup.
        if current is None or current.location != incident.location:
            return incident
        updated = replace(current, location_context=resolved.context, location_label=resolved.label)
        await incidents.update(updated, utc_now())
    await resolver.record(incident.location, scenario_key, resolved)
    return updated
