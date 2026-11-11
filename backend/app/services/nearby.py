"""The nearby lookup (ADR 0004, 0005): the server asks Overpass itself, so "map data, not AI"
can't be whatever a client posted, and the model never supplies a place. Demo mode makes no
call: the places recorded for the scenario, at that radius, stand in for it (#58)."""

from collections.abc import Mapping

import aiosqlite

from app.db.connection import transaction
from app.domain.nearby import NearbySnapshot, places_from_elements
from app.errors import AppError, NotFoundError
from app.integrations.overpass import NearbyUnavailable, PlaceSource
from app.integrations.place_recording import PlaceRecorder, PlaceRecording
from app.repositories.incidents import IncidentRepository
from app.repositories.nearby import NearbyRepository
from app.repositories.vehicles import VehicleRepository
from app.services.clock import utc_now
from app.services.location import load_scenario_key


class NearbyService:
    """`source` is None in demo mode, where no Overpass call is made and `recorded` answers
    instead. With `recorder`, each live result is also recorded for demo mode."""

    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        nearby: NearbyRepository,
        source: PlaceSource | None,
        *,
        recorded: Mapping[str, PlaceRecording] | None = None,
        recorder: PlaceRecorder | None = None,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles
        self._nearby = nearby
        self._source = source
        self._recorded = recorded or {}
        self._recorder = recorder

    async def lookup(self, incident_id: int, radius_km: int) -> NearbySnapshot:
        """Look up places around the incident and store them as its snapshot.

        No transaction is open during the lookup, which can take most of a minute. A failure
        stores nothing, so the previous snapshot stays (503). A location changed meanwhile
        stores nothing either: the places were found around the old point.
        """
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("Incident")
        location = incident.location
        if location is None:
            raise AppError(409, "no_location", "The incident has no location")
        scenario = await load_scenario_key(incident, self._vehicles)
        if self._source is None:
            snapshot = self._replay(scenario, radius_km)
        else:
            try:
                result = await self._source.search(location.lat, location.lon, radius_km * 1000)
            except NearbyUnavailable as exc:
                raise AppError(503, "nearby_unavailable", "The map service is unavailable") from exc
            snapshot = NearbySnapshot(
                places=tuple(places_from_elements(result.elements, location.lat, location.lon)),
                radius_km=radius_km,
                fetched_at=utc_now(),
                source=result.endpoint,
            )
        async with transaction(self._conn):
            current = await self._incidents.get(incident_id)
            if current is None:
                raise NotFoundError("Incident")
            if current.location != location:
                raise AppError(409, "location_changed", "The location changed during the lookup")
            await self._nearby.replace(incident_id, snapshot)
        if self._recorder is not None:
            await self._recorder.record_nearby(scenario, location, snapshot)
        return snapshot

    def _replay(self, scenario: str, radius_km: int) -> NearbySnapshot:
        """The places recorded for the scenario at this radius, as they were recorded: real
        places near the recorded point, never moved to the driver's.

        Not recorded is a labelled 503, not a `none`: nothing was looked up, and retrying
        can't help.
        """
        rec = self._recorded.get(scenario)
        snapshot = rec.nearby.get(radius_km) if rec else None
        if snapshot is None:
            raise AppError(503, "nearby_not_recorded", "Demo mode has no recorded places")
        return snapshot
