from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Response

from app.deps import get_incident_service
from app.domain.incident import IncidentStatus
from app.schemas.incident import (
    IncidentCreate,
    IncidentPage,
    IncidentPatch,
    IncidentRead,
    IncidentSummary,
)
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


@router.get("", response_model=IncidentPage)
async def list_incidents(
    service: Service,
    status: Annotated[IncidentStatus | None, Query()] = None,
    vehicle_id: Annotated[int | None, Query(ge=1, le=2**63 - 1)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0,
) -> IncidentPage:
    """Newest first, filtered by status and/or vehicle."""
    items, total, reports = await service.list(status, vehicle_id, limit, offset)
    return IncidentPage(
        items=[IncidentSummary.from_domain(i, reports.get(i.id)) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


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
    detail, created = await service.create(body.to_domain(), idempotency_key)
    if created:
        response.headers["Location"] = f"/api/v1/incidents/{detail.incident.id}"
    else:
        response.status_code = 200
    return IncidentRead.from_domain(detail)


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: IncidentId, service: Service) -> IncidentRead:
    return IncidentRead.from_domain(await service.detail(incident_id))


@router.patch("/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: IncidentId, body: IncidentPatch, service: Service
) -> IncidentRead:
    return IncidentRead.from_domain(await service.update(incident_id, body))


@router.delete("/{incident_id}", status_code=204)
async def delete_incident(incident_id: IncidentId, service: Service) -> Response:
    await service.delete(incident_id)
    return Response(status_code=204)
