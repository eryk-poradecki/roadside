import sqlite3

import aiosqlite

from app.db.connection import transaction
from app.domain.incident import Incident, NewIncident
from app.errors import FieldValidationError, NotFoundError
from app.repositories.incidents import IncidentRepository
from app.repositories.vehicles import VehicleRepository
from app.services.clock import utc_now


class IncidentService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles

    async def get(self, incident_id: int) -> Incident:
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("Incident")
        return incident

    async def create(
        self, data: NewIncident, idempotency_key: str | None = None
    ) -> tuple[Incident, bool]:
        """Create and commit an open incident. Returns it and whether it is new.

        A repeated idempotency key returns the incident it first created, whatever the body
        (ADR 0005). BEGIN IMMEDIATE serialises writers, so the key lookup and the insert
        cannot interleave; the UNIQUE constraint backs that up.
        """
        now = utc_now()
        try:
            async with transaction(self._conn):
                if idempotency_key is not None:
                    existing = await self._incidents.get_by_idempotency_key(idempotency_key)
                    if existing is not None:
                        return existing, False
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
            return existing, False
        return await self.get(new_id), True
