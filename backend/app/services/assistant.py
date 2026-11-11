"""The AI turn pipeline every provider goes through (ADR 0004).

Read the incident → store the driver's reply, if any → build the inputs snapshot → render the
versioned prompt → one model call → validate → at most one repair call → store the turn. The
whole turn runs under one budget, and one turn at a time per incident. No transaction stays
open across the model call; a failed turn stores nothing, but a reply stored before it stays.

The backend enforces the cap on clarifying questions: after two, or after "Just give me the
steps", the schema allows only an answer.
"""

import asyncio
import logging
import sqlite3
import time
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from app.assist import prompt
from app.assist.contract import TurnOutput, validate_output
from app.assist.daylight import POLAND_CENTRE, is_dark
from app.assist.prompt import Exchange, TurnInputs, VehicleFactBlock
from app.assist.replay_key import replay_key, scenario_key
from app.db.connection import read_snapshot, transaction
from app.domain.ai_turn import AiTurn, AiTurnKind, Locale, ModelProvenance, NewAiTurn, Reply
from app.domain.incident import Incident
from app.domain.location_context import UNKNOWN_CONTEXT
from app.errors import AppError, FieldValidationError, NotFoundError
from app.integrations.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderError,
)
from app.repositories.ai_turns import AiTurnRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.photos import PhotoRepository
from app.repositories.vehicles import VehicleRepository
from app.services.clock import utc_now
from app.services.location import LocationResolver, refresh_location_context
from app.services.model_call import InvalidOutputError, complete_validated, problem_for

logger = logging.getLogger(__name__)

# The region is fixed (Poland/EU): local time is Polish time.
LOCAL_TZ = ZoneInfo("Europe/Warsaw")

# At most this many clarifying questions per incident (ADR 0004).
MAX_QUESTIONS = 2


class TurnLocks:
    """One in-process lock per incident (ADR 0005). Assumes one uvicorn worker."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[int, asyncio.Lock] = weakref.WeakValueDictionary()

    @asynccontextmanager
    async def hold(self, incident_id: int) -> AsyncIterator[None]:
        lock = self._locks.get(incident_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[incident_id] = lock
        if lock.locked():
            raise AppError(409, "turn_in_progress", "A turn for this incident is running")
        async with lock:
            yield


class AssistantService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        turns: AiTurnRepository,
        photos: PhotoRepository,
        provider: LLMProvider,
        locks: TurnLocks,
        turn_budget_s: float,
        location: LocationResolver,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles
        self._turns = turns
        self._photos = photos
        self._provider = provider
        self._locks = locks
        self._budget_s = turn_budget_s
        self._location = location

    async def take_turn(
        self, incident_id: int, locale: Locale, reply: Reply | None = None
    ) -> AiTurn:
        async with self._locks.hold(incident_id):
            inputs, turns, sample_ids = await self._prepare(incident_id, locale, reply)
            allow_ask = _may_ask(turns)
            key = replay_key(
                inputs,
                locale=locale,
                sample_photo_ids=sample_ids,
                vision=bool(inputs.photo_ids_seen),
                replies=_replies(turns),
            )
            started = time.monotonic()
            try:
                async with asyncio.timeout(self._budget_s):
                    output, result = await self._generate(
                        inputs,
                        locale,
                        allow_ask=allow_ask,
                        exchanges=_exchanges(turns),
                        replay_key=key,
                    )
            except (TimeoutError, ProviderError, InvalidOutputError) as exc:
                problem = problem_for(exc)
                logger.info(
                    "ai turn failed: incident=%d provider=%s reason=%s latency_ms=%d",
                    incident_id,
                    self._provider.name,
                    problem.reason,
                    (time.monotonic() - started) * 1000,
                )
                raise problem from exc
            logger.info(
                "ai turn ok: incident=%d provider=%s model=%s kind=%s latency_ms=%d",
                incident_id,
                result.provider,
                result.model,
                output.kind,
                (time.monotonic() - started) * 1000,
            )
            return await self._store(incident_id, inputs, locale, output, result, len(turns))

    async def _prepare(
        self, incident_id: int, locale: Locale, reply: Reply | None
    ) -> tuple[TurnInputs, list[AiTurn], list[str]]:
        """The inputs, the turns so far, and the ids of the sample photos attached."""
        async with read_snapshot(self._conn):
            incident = await self._incidents.get(incident_id)
            if incident is None:
                raise NotFoundError("Incident")
            turns = await self._turns.list_for_incident(incident_id)
            vehicle = (
                await self._vehicles.get(incident.vehicle_id)
                if incident.vehicle_id is not None
                else None
            )
            photos = await self._photos.list_for_incident(incident_id)
        _check_can_take(turns, reply)
        if reply is not None:
            turns = await self._store_reply(incident_id, reply)
        facts = VehicleFactBlock.from_facts(vehicle.facts) if vehicle else None
        scenario = scenario_key(incident.problem_type.value, incident.situation.value, facts)
        incident = await self._with_location_context(incident, locale, scenario)
        sample_ids = [p.sample_id for p in photos if p.sample_id is not None]
        return turn_inputs(incident, facts, datetime.now(UTC)), turns, sample_ids

    async def _store_reply(self, incident_id: int, reply: Reply) -> list[AiTurn]:
        """Append the reply in its own transaction, so it stays if the model call fails."""
        async with transaction(self._conn):
            if await self._incidents.get(incident_id) is None:
                raise NotFoundError("Incident")
            # Checked again under the write lock: another worker may have replied first.
            _check_can_take(await self._turns.list_for_incident(incident_id), reply)
            new = NewAiTurn(kind=AiTurnKind.REPLY, payload=reply.to_payload(), provenance=None)
            await self._turns.append(incident_id, new, utc_now())
            return await self._turns.list_for_incident(incident_id)

    async def _with_location_context(
        self, incident: Incident, locale: Locale, scenario: str
    ) -> Incident:
        """Look the context up once, lazily, and cache it with the label on the incident.

        A failed lookup gives unknown for this turn and caches nothing, so a later turn tries again.
        """
        if incident.location_context is not None:
            return incident
        return await refresh_location_context(
            self._conn, self._incidents, self._location, incident, locale, scenario
        )

    async def _generate(
        self,
        inputs: TurnInputs,
        locale: Locale,
        *,
        allow_ask: bool,
        exchanges: tuple[Exchange, ...],
        replay_key: str,
    ) -> tuple[TurnOutput, LLMResult]:
        rendered = prompt.render(inputs, locale, allow_ask=allow_ask, exchanges=exchanges)
        logger.debug("ai prompt:\n%s\n%s", rendered.system, rendered.user)
        messages = (LLMMessage("system", rendered.system), LLMMessage("user", rendered.user))
        request = LLMRequest(
            messages=messages, schema=rendered.schema, schema_name="ai_turn", replay_key=replay_key
        )

        return await complete_validated(
            self._provider, request, lambda raw: validate_output(raw, allow_ask=allow_ask)
        )

    async def _store(
        self,
        incident_id: int,
        inputs: TurnInputs,
        locale: Locale,
        output: TurnOutput,
        result: LLMResult,
        turns_seen: int,
    ) -> AiTurn:
        payload = _payload(output, inputs)
        new = NewAiTurn(
            kind=AiTurnKind.ADVICE if output.kind == "answer" else AiTurnKind.QUESTION,
            payload=payload,
            provenance=ModelProvenance(
                inputs=inputs.to_json(),
                locale=locale,
                prompt_version=prompt.PROMPT_VERSION,
                provider=result.provider,
                model=result.model,
            ),
        )
        try:
            async with transaction(self._conn):
                # The incident may have been deleted while the model was answering.
                if await self._incidents.get(incident_id) is None:
                    raise NotFoundError("Incident")
                # Only another worker can have appended since; the in-process lock covers
                # this one. Storing anyway could put two questions in a row.
                current = await self._turns.list_for_incident(incident_id)
                _check_no_advice(current)
                if len(current) != turns_seen:
                    raise AppError(409, "turn_in_progress", "A turn for this incident is running")
                turn_id = await self._turns.append(incident_id, new, utc_now())
                turns = await self._turns.list_for_incident(incident_id)
        except sqlite3.IntegrityError as exc:
            # Only another worker can get here first; the in-process lock covers this one.
            raise AppError(409, "advice_exists", "The AI answer is complete") from exc
        return next(t for t in turns if t.id == turn_id)


def _check_no_advice(turns: list[AiTurn]) -> None:
    """The advice closes the AI answer."""
    if any(t.kind is AiTurnKind.ADVICE for t in turns):
        raise AppError(409, "advice_exists", "The AI answer is complete")


def _check_can_take(turns: list[AiTurn], reply: Reply | None) -> None:
    """The 409s of ADR 0005, and a reply's option must be one the question offered."""
    _check_no_advice(turns)
    open_question = turns[-1] if turns and turns[-1].kind is AiTurnKind.QUESTION else None
    if open_question is None:
        if reply is not None:
            raise AppError(409, "no_open_question", "There is no question to reply to")
        return
    if reply is None:
        raise AppError(409, "reply_required", "Reply to the open question first")
    if reply.option is not None and reply.option not in open_question.payload["ask"]["options"]:
        raise FieldValidationError("reply.option", "Not one of the question's options")


def _may_ask(turns: list[AiTurn]) -> bool:
    """The cap: no question after two, or after the driver skipped to the steps."""
    questions = sum(t.kind is AiTurnKind.QUESTION for t in turns)
    skipped = any(t.kind is AiTurnKind.REPLY and Reply.from_payload(t.payload).skip for t in turns)
    return questions < MAX_QUESTIONS and not skipped


def _replies(turns: list[AiTurn]) -> list[Reply]:
    """The driver's replies so far, in order."""
    return [Reply.from_payload(t.payload) for t in turns if t.kind is AiTurnKind.REPLY]


def _exchanges(turns: list[AiTurn]) -> tuple[Exchange, ...]:
    """Each question with the reply that follows it, in order."""
    return tuple(
        Exchange(question=q.payload["ask"]["question"], reply=Reply.from_payload(r.payload))
        for q, r in pairwise(turns)
        if q.kind is AiTurnKind.QUESTION and r.kind is AiTurnKind.REPLY
    )


def turn_inputs(incident: Incident, vehicle: VehicleFactBlock | None, at: datetime) -> TurnInputs:
    """The fact set the model is told, as of `at`: now for a turn, the incident's time for a
    damage report."""
    lat, lon = (
        (incident.location.lat, incident.location.lon) if incident.location else POLAND_CENTRE
    )
    context = incident.location_context or UNKNOWN_CONTEXT
    return TurnInputs(
        vehicle=vehicle,
        road_class=context.road_class.value,
        settlement=context.settlement.value,
        situation=incident.situation.value,
        problem_type=incident.problem_type.value,
        note=incident.note,
        local_time=at.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
        dark=is_dark(at, lat, lon),
    )


def _payload(output: TurnOutput, inputs: TurnInputs) -> dict[str, Any]:
    """The validated output to store. Facts the backend knows overrule the model's."""
    if output.answer is not None:
        answer = output.answer
        if not inputs.photo_ids_seen:
            answer = answer.model_copy(update={"photo_observation": None})
        return {"urgent": output.urgent, "answer": answer.model_dump(mode="json")}
    if output.ask is None:  # pragma: no cover - TurnOutput guarantees one block
        raise RuntimeError("validated output without a block")
    return {"urgent": output.urgent, "ask": output.ask.model_dump(mode="json")}
