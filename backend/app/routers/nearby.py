from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_nearby_service
from app.routers.incidents import IncidentId
from app.schemas.nearby import NearbyRead, NearbyRequest
from app.services.nearby import NearbyService

router = APIRouter(prefix="/incidents", tags=["nearby"])
Service = Annotated[NearbyService, Depends(get_nearby_service)]


@router.post("/{incident_id}/nearby", response_model=NearbyRead)
async def find_nearby(incident_id: IncidentId, body: NearbyRequest, service: Service) -> NearbyRead:
    """Look up real places around the incident's location and store them as its snapshot.

    Replaces the snapshot only on success: 503 `nearby_unavailable` keeps the previous one.
    409 `no_location` when the incident has none.
    """
    return NearbyRead.from_domain(await service.lookup(incident_id, body.radius_km))
