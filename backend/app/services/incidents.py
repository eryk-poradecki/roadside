import sqlite3

import aiosqlite

from app.db.connection import read_snapshot, transaction
from app.domain.incident import Incident, IncidentDetail, IncidentStatus, NewIncident
from app.errors import FieldValidationError, NotFoundError
from app.repositories.ai_turns import AiTurnRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.vehicles import VehicleRepository
from app.schemas.incident import IncidentPatch
from app.services.clock import utc_now


class IncidentService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        ai_turns: AiTurnRepository,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles
        self._ai_turns = ai_turns

    async def get(self, incident_id: int) -> Incident:
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("Incident")
        return incident

    async def detail(self, incident_id: int) -> IncidentDetail:
        async with read_snapshot(self._conn):
            incident = await self.get(incident_id)
            turns = await self._ai_turns.list_for_incident(incident_id)
        return IncidentDetail(incident, tuple(turns))

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
    ) -> tuple[list[Incident], int]:
        async with read_snapshot(self._conn):
            return await self._incidents.list_page(status, vehicle_id, limit, offset)

    async def update(self, incident_id: int, patch: IncidentPatch) -> IncidentDetail:
        """Apply a partial update. A patch that changes nothing writes nothing."""
        async with transaction(self._conn):
            current = await self.get(incident_id)
            new = patch.apply(current)
            if new != current:
                if (
                    new.vehicle_id is not None
                    and new.vehicle_id != current.vehicle_id
                    and await self._vehicles.get(new.vehicle_id) is None
                ):
                    raise FieldValidationError("vehicle_id", "Unknown vehicle")
                await self._incidents.update(new, utc_now())
        return await self.detail(incident_id)

    async def delete(self, incident_id: int) -> None:
        async with transaction(self._conn):
            if not await self._incidents.delete(incident_id):
                raise NotFoundError("Incident")
