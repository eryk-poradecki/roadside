from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from app.deps import get_vehicle_service
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services.vehicles import VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
VehicleId = Annotated[int, Path(ge=1, le=2**63 - 1)]
Service = Annotated[VehicleService, Depends(get_vehicle_service)]


@router.get("", response_model=list[VehicleRead])
async def list_vehicles(service: Service) -> list[VehicleRead]:
    return [VehicleRead.from_domain(v) for v in await service.list()]


@router.post("", status_code=201, response_model=VehicleRead)
async def create_vehicle(body: VehicleCreate, service: Service, response: Response) -> VehicleRead:
    vehicle = await service.create(body)
    response.headers["Location"] = f"/api/v1/vehicles/{vehicle.id}"
    return VehicleRead.from_domain(vehicle)


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(vehicle_id: VehicleId, service: Service) -> VehicleRead:
    return VehicleRead.from_domain(await service.get(vehicle_id))


@router.put("/{vehicle_id}", response_model=VehicleRead)
async def replace_vehicle(
    vehicle_id: VehicleId, body: VehicleUpdate, service: Service
) -> VehicleRead:
    return VehicleRead.from_domain(await service.replace(vehicle_id, body))


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: VehicleId, service: Service) -> Response:
    await service.delete(vehicle_id)
    return Response(status_code=204)
