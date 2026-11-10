from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response

from app.deps import get_incident_service
from app.schemas.incident import IncidentCreate, IncidentRead
from app.services.incidents import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])
IncidentId = Annotated[int, Path(ge=1, le=2**63 - 1)]
Service = Annotated[IncidentService, Depends(get_incident_service)]
IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
        description="A fresh value (e.g. a UUID) per help request. A repeat returns 200 with "
        "the incident the key first created.",
    ),
]


@router.post(
    "",
    status_code=201,
    response_model=IncidentRead,
    responses={200: {"model": IncidentRead, "description": "Repeated Idempotency-Key"}},
)
async def create_incident(
    body: IncidentCreate,
    service: Service,
    response: Response,
    idempotency_key: IdempotencyKey = None,
) -> IncidentRead:
    incident, created = await service.create(body.to_domain(), idempotency_key)
    if created:
        response.headers["Location"] = f"/api/v1/incidents/{incident.id}"
    else:
        response.status_code = 200
    return IncidentRead.from_domain(incident)


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: IncidentId, service: Service) -> IncidentRead:
    return IncidentRead.from_domain(await service.get(incident_id))
