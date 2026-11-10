from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import get_assistant_service
from app.routers.incidents import IncidentId
from app.schemas.ai_turn import AiTurnCreate, AiTurnRead
from app.services.assistant import AssistantService

router = APIRouter(prefix="/incidents/{incident_id}/ai-turns", tags=["ai"])
Service = Annotated[AssistantService, Depends(get_assistant_service)]


@router.post("", status_code=201, response_model=AiTurnRead)
async def take_ai_turn(incident_id: IncidentId, body: AiTurnCreate, service: Service) -> AiTurnRead:
    """Ask the assistant for the next turn of the AI answer and wait for it.

    Synchronous: the request holds until the turn is validated and stored, or has failed
    (nothing is stored then). One turn at a time per incident (409 `turn_in_progress`); the
    advice closes the AI answer (409 `advice_exists`). Failures: 502 `provider_error` or
    `invalid_output`, 504 `timeout`. "Try again" repeats the same request.
    """
    return AiTurnRead.from_domain(await service.take_turn(incident_id, body.locale))
