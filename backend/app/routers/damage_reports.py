from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.deps import get_damage_report_service
from app.routers.incidents import IncidentId
from app.schemas.damage_report import DamageReportCreate, DamageReportPatch, DamageReportRead
from app.services.damage_reports import DamageReportEdit, DamageReportService

router = APIRouter(prefix="/incidents/{incident_id}/damage-report", tags=["damage-report"])
Service = Annotated[DamageReportService, Depends(get_damage_report_service)]


@router.get("", response_model=DamageReportRead)
async def get_damage_report(incident_id: IncidentId, service: Service) -> DamageReportRead:
    """The incident's damage report; 404 when the incident or the report doesn't exist."""
    return DamageReportRead.from_domain(await service.get(incident_id))


@router.post(
    "",
    status_code=201,
    response_model=DamageReportRead,
    responses={200: {"model": DamageReportRead, "description": "`replace: true` overwrote it"}},
)
async def create_damage_report(
    incident_id: IncidentId, body: DamageReportCreate, service: Service, response: Response
) -> DamageReportRead:
    """Draft the damage report with the assistant and wait for it (ADR 0009).

    Only for a pothole incident (422 `not_pothole_damage`); a later type change keeps it. One
    per incident (409 `damage_report_exists`) unless `replace: true`, which overwrites it,
    sets it back to `draft` and answers 200. It runs under the incident's turn lock (409
    `turn_in_progress`) and fails like an AI turn (502 `provider_error` / `invalid_output`,
    504 `timeout`, 503 `no_recording` in demo mode), storing nothing.
    """
    report, created = await service.generate(incident_id, body.locale, replace=body.replace)
    if not created:
        response.status_code = 200
    return DamageReportRead.from_domain(report)


@router.patch("", response_model=DamageReportRead)
async def update_damage_report(
    incident_id: IncidentId, body: DamageReportPatch, service: Service
) -> DamageReportRead:
    """Edit the body, or mark it `sent` (or back to `draft`)."""
    edit = DamageReportEdit(body=body.body, status=body.status)
    return DamageReportRead.from_domain(await service.edit(incident_id, edit))


@router.delete("", status_code=204)
async def delete_damage_report(incident_id: IncidentId, service: Service) -> Response:
    await service.delete(incident_id)
    return Response(status_code=204)
