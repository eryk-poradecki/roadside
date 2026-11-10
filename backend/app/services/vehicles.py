import aiosqlite

from app.db.connection import transaction
from app.domain.vehicle import Vehicle
from app.errors import NotFoundError
from app.repositories.vehicles import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services.clock import utc_now


class VehicleService:
    def __init__(self, conn: aiosqlite.Connection, repo: VehicleRepository) -> None:
        self._conn = conn
        self._repo = repo

    async def list(self) -> list[Vehicle]:
        return await self._repo.list_all()

    async def get(self, vehicle_id: int) -> Vehicle:
        vehicle = await self._repo.get(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle")
        return vehicle

    async def create(self, data: VehicleCreate) -> Vehicle:
        now = utc_now()
        async with transaction(self._conn):
            if data.is_default is None:
                is_default = not await self._repo.has_default()
            else:
                is_default = data.is_default
            if is_default:
                await self._repo.clear_default(now)
            new_id = await self._repo.insert(data.to_facts(), is_default, now)
        return await self.get(new_id)

    async def replace(self, vehicle_id: int, data: VehicleUpdate) -> Vehicle:
        now = utc_now()
        async with transaction(self._conn):
            current = await self._repo.get(vehicle_id)
            if current is None:
                raise NotFoundError("Vehicle")
            is_default = current.is_default if data.is_default is None else data.is_default
            if is_default and not current.is_default:
                await self._repo.clear_default(now)
            await self._repo.update(vehicle_id, data.to_facts(), is_default, now)
        return await self.get(vehicle_id)

    async def delete(self, vehicle_id: int) -> None:
        # Deleting the default leaves no default until the driver picks one.
        async with transaction(self._conn):
            if not await self._repo.delete(vehicle_id):
                raise NotFoundError("Vehicle")
