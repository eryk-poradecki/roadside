"""The AI turn pipeline every provider goes through (ADR 0004).

Read the incident → build the inputs snapshot → render the versioned prompt → one model call
→ validate → at most one repair call → store the turn. The whole turn runs under one
budget, and one turn at a time per incident. No transaction stays open across the model
call; a failed turn stores nothing.
"""

import asyncio
import logging
import sqlite3
import time
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite
from pydantic import ValidationError

from app.assist import prompt
from app.assist.contract import TurnOutput, validate_output
from app.assist.daylight import POLAND_CENTRE, is_dark
from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.db.connection import read_snapshot, transaction
from app.domain.ai_turn import AiTurn, AiTurnKind, Locale, ModelProvenance, NewAiTurn
from app.domain.incident import Incident
from app.errors import AppError, NotFoundError
from app.integrations.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResult,
    ProviderError,
    ProviderTimeoutError,
)
from app.repositories.ai_turns import AiTurnRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.vehicles import VehicleRepository
from app.services.clock import utc_now

logger = logging.getLogger(__name__)

# The region is fixed (Poland/EU): local time is Polish time.
LOCAL_TZ = ZoneInfo("Europe/Warsaw")


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


class _InvalidOutputError(Exception):
    pass


def _problem_for(exc: BaseException) -> AppError:
    if isinstance(exc, TimeoutError | ProviderTimeoutError):
        return AppError(504, "timeout", "The assistant did not answer in time")
    if isinstance(exc, _InvalidOutputError):
        return AppError(502, "invalid_output", "The assistant's answer was not valid")
    return AppError(502, "provider_error", "The assistant could not be reached")


def _repair_message(error: Exception) -> str:
    detail = (
        "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'output'}: {e['msg']}"
            for e in error.errors(include_url=False)
        )
        if isinstance(error, ValidationError)
        else str(error)
    )
    return (
        f"Your previous output was invalid: {detail}. "
        "Reply again with one corrected JSON object that follows the schema, and nothing else."
    )


class AssistantService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        turns: AiTurnRepository,
        provider: LLMProvider,
        locks: TurnLocks,
        turn_budget_s: float,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._vehicles = vehicles
        self._turns = turns
        self._provider = provider
        self._locks = locks
        self._budget_s = turn_budget_s

    async def take_turn(self, incident_id: int, locale: Locale) -> AiTurn:
        async with self._locks.hold(incident_id):
            inputs = await self._prepare(incident_id)
            started = time.monotonic()
            try:
                async with asyncio.timeout(self._budget_s):
                    output, result = await self._generate(inputs, locale)
            except (TimeoutError, ProviderError, _InvalidOutputError) as exc:
                problem = _problem_for(exc)
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
            return await self._store(incident_id, inputs, locale, output, result)

    async def _prepare(self, incident_id: int) -> TurnInputs:
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
        if any(t.kind is AiTurnKind.ADVICE for t in turns):
            raise AppError(409, "advice_exists", "The AI answer is complete")
        return _inputs(incident, VehicleFactBlock.from_facts(vehicle.facts) if vehicle else None)

    async def _generate(self, inputs: TurnInputs, locale: Locale) -> tuple[TurnOutput, LLMResult]:
        # Clarifying questions arrive with their own ticket; until then every turn answers.
        allow_ask = False
        rendered = prompt.render(inputs, locale, allow_ask=allow_ask)
        logger.debug("ai prompt:\n%s\n%s", rendered.system, rendered.user)
        messages = (LLMMessage("system", rendered.system), LLMMessage("user", rendered.user))
        request = LLMRequest(messages=messages, schema=rendered.schema, schema_name="ai_turn")

        result = await self._provider.complete(request)
        try:
            return validate_output(result.text, allow_ask=allow_ask), result
        except ValueError as exc:
            logger.info("ai output invalid, making the one repair call")
            repair = replace(
                request,
                messages=(
                    *messages,
                    LLMMessage("assistant", result.text),
                    LLMMessage("user", _repair_message(exc)),
                ),
            )
        result = await self._provider.complete(repair)
        try:
            return validate_output(result.text, allow_ask=allow_ask), result
        except ValueError as exc:
            raise _InvalidOutputError from exc

    async def _store(
        self,
        incident_id: int,
        inputs: TurnInputs,
        locale: Locale,
        output: TurnOutput,
        result: LLMResult,
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
                turn_id = await self._turns.append(incident_id, new, utc_now())
                turns = await self._turns.list_for_incident(incident_id)
        except sqlite3.IntegrityError as exc:
            # Only another worker can get here first; the in-process lock covers this one.
            raise AppError(409, "advice_exists", "The AI answer is complete") from exc
        return next(t for t in turns if t.id == turn_id)


def _inputs(incident: Incident, vehicle: VehicleFactBlock | None) -> TurnInputs:
    now = datetime.now(UTC)
    lat, lon = (
        (incident.location.lat, incident.location.lon) if incident.location else POLAND_CENTRE
    )
    return TurnInputs(
        vehicle=vehicle,
        problem_type=incident.problem_type.value,
        note=incident.note,
        local_time=now.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
        dark=is_dark(now, lat, lon),
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
