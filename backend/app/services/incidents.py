import sqlite3
from dataclasses import replace

import aiosqlite

from app.db.connection import read_snapshot, transaction
from app.domain.ai_turn import Locale
from app.domain.damage_report import DamageReportStatus
from app.domain.incident import Incident, IncidentDetail, IncidentStatus, NewIncident
from app.errors import FieldValidationError, NotFoundError
from app.repositories.ai_turns import AiTurnRepository
from app.repositories.damage_reports import DamageReportRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nearby import NearbyRepository
from app.repositories.photos import PhotoFiles, PhotoRepository
from app.repositories.vehicles import VehicleRepository
from app.schemas.incident import IncidentPatch
from app.services.clock import utc_now
from app.services.location import (
    LocationResolver,
    load_scenario_key,
    refresh_location_context,
)

DEFAULT_LOCALE: Locale = "en"


class IncidentService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        ai_turns: AiTurnRepository,
        nearby: NearbyRepository,
        photos: PhotoRepository,
        reports: DamageReportRepository,
        files: PhotoFiles,
        location: LocationResolver,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles
        self._ai_turns = ai_turns
        self._nearby = nearby
        self._photos = photos
        self._reports = reports
        self._files = files
        self._location = location

    async def get(self, incident_id: int) -> Incident:
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("Incident")
        return incident

    async def detail(self, incident_id: int) -> IncidentDetail:
        async with read_snapshot(self._conn):
            incident = await self.get(incident_id)
            turns = await self._ai_turns.list_for_incident(incident_id)
            nearby = await self._nearby.get(incident_id)
            photos = await self._photos.list_for_incident(incident_id)
            report = await self._reports.get(incident_id)
        return IncidentDetail(
            incident,
            tuple(turns),
            nearby,
            tuple(photos),
            report.status if report else None,
        )

    async def create(
        self, data: NewIncident, idempotency_key: str | None = None
    ) -> tuple[IncidentDetail, bool]:
        """Create and commit an open incident. Returns it and whether it is new.

        A repeated idempotency key returns the incident it first created, whatever the body
        (ADR 0005). BEGIN IMMEDIATE serialises writers, so the key lookup and the insert
        cannot interleave; the UNIQUE constraint backs that up.
        """
        now = utc_now()
        try:
            async with transaction(self._conn):
                existing = (
                    await self._incidents.get_by_idempotency_key(idempotency_key)
                    if idempotency_key is not None
                    else None
                )
                if existing is None:
                    if (
                        data.vehicle_id is not None
                        and await self._vehicles.get(data.vehicle_id) is None
                    ):
                        raise FieldValidationError("vehicle_id", "Unknown vehicle")
                    new_id = await self._incidents.insert(data, idempotency_key, now)
        except sqlite3.IntegrityError:
            if idempotency_key is None:
                raise
            existing = await self._incidents.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
        if existing is not None:
            return await self.detail(existing.id), False
        return await self.detail(new_id), True

    async def list(
        self, status: IncidentStatus | None, vehicle_id: int | None, limit: int, offset: int
    ) -> tuple[list[Incident], int, dict[int, DamageReportStatus]]:
        """One page, the filtered total, and the damage report status of each that has one."""
        async with read_snapshot(self._conn):
            items, total = await self._incidents.list_page(status, vehicle_id, limit, offset)
            reports = await self._reports.statuses([i.id for i in items])
        return items, total, reports

    async def update(self, incident_id: int, patch: IncidentPatch) -> IncidentDetail:
        """Apply a partial update. A patch that changes nothing writes nothing.

        A new location recomputes the location context and label inline (ADR 0005), in the
        locale of the latest AI turn. A failed lookup leaves them empty for the next turn.
        It also clears the nearby snapshot, whose places were found around the old point.
        In demo mode and recording runs, a new scenario (problem type, situation or vehicle)
        does the same: the recorded context and places belong to the scenario (#58).
        """
        async with transaction(self._conn):
            current = await self.get(incident_id)
            new = patch.apply(current)
            moved = False
            if new != current:
                if (
                    new.vehicle_id is not None
                    and new.vehicle_id != current.vehicle_id
                    and await self._vehicles.get(new.vehicle_id) is None
                ):
                    raise FieldValidationError("vehicle_id", "Unknown vehicle")
                moved = new.location != current.location or (
                    self._location.keyed_by_scenario
                    and await load_scenario_key(new, self._vehicles)
                    != await load_scenario_key(current, self._vehicles)
                )
                if moved:
                    new = replace(new, location_context=None, location_label=None)
                await self._incidents.update(new, utc_now())
                if moved:
                    await self._nearby.delete(incident_id)
        if new.location is not None and moved:
            turns = await self._ai_turns.list_for_incident(incident_id)
            locales = [t.provenance.locale for t in turns if t.provenance is not None]
            locale = locales[-1] if locales else DEFAULT_LOCALE
            scenario = await load_scenario_key(new, self._vehicles)
            await refresh_location_context(
                self._conn, self._incidents, self._location, new, locale, scenario
            )
        return await self.detail(incident_id)

    async def delete(self, incident_id: int) -> None:
        """The cascade removes the photo rows; their files go once the delete is committed."""
        async with transaction(self._conn):
            photos = await self._photos.list_for_incident(incident_id)
            if not await self._incidents.delete(incident_id):
                raise NotFoundError("Incident")
        for photo in photos:
            await self._files.remove(photo.stored_name)
