"""The damage report (ADR 0009): drafted from the incident by one model call, then the driver's.

Generation follows the AI turn pipeline (ADR 0004): read the incident, build the same fact set
as a turn plus the advice's cause, one schema-constrained call, validation, at most one repair
call, all within the turn budget and under the incident's turn lock. The backend renders the
letter around the narrative, with the facts snapshotted now. A failed generation stores
nothing, and a failed regeneration keeps the old report.
"""

import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

import aiosqlite

from app.assist import prompt
from app.assist.letter import LetterFacts, render_letter
from app.assist.prompt import TurnInputs, VehicleFactBlock
from app.assist.replay_key import damage_report_key, scenario_key
from app.assist.report_contract import validate_report_output
from app.db.connection import read_snapshot, transaction
from app.domain.ai_turn import AiTurn, AiTurnKind, Locale, ModelProvenance, Reply
from app.domain.damage_report import DamageReport, DamageReportStatus, NewDamageReport
from app.domain.incident import Incident, ProblemType
from app.domain.photo import Photo
from app.domain.vehicle import Vehicle
from app.errors import AppError, NotFoundError
from app.integrations.llm.base import LLMMessage, LLMProvider, LLMRequest, ProviderError
from app.integrations.llm.replay import ReplayProvider
from app.repositories.ai_turns import AiTurnRepository
from app.repositories.damage_reports import DamageReportRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.photos import PhotoRepository
from app.repositories.vehicles import VehicleRepository
from app.services.assistant import TurnLocks, turn_inputs
from app.services.clock import utc_now
from app.services.location import LocationResolver, refresh_location_context
from app.services.model_call import InvalidOutputError, complete_validated, problem_for

logger = logging.getLogger(__name__)

# The letter's languages, Polish first: the letter goes to a Polish road manager.
LETTER_LOCALES: tuple[Locale, ...] = ("pl", "en")


@dataclass(frozen=True, slots=True)
class DamageReportEdit:
    """The driver's PATCH: None leaves a field as it is."""

    body: str | None = None
    status: DamageReportStatus | None = None


def _check_pothole(incident: Incident) -> None:
    """The gate applies at creation only: a later type change keeps the report."""
    if incident.problem_type is not ProblemType.POTHOLE_DAMAGE:
        raise AppError(422, "not_pothole_damage", "Only a pothole incident gets a damage report")


def _exists() -> AppError:
    return AppError(409, "damage_report_exists", "This incident already has a damage report")


class DamageReportService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        vehicles: VehicleRepository,
        turns: AiTurnRepository,
        photos: PhotoRepository,
        reports: DamageReportRepository,
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
        self._reports = reports
        self._provider = provider
        self._locks = locks
        self._budget_s = turn_budget_s
        self._location = location

    async def get(self, incident_id: int) -> DamageReport:
        async with read_snapshot(self._conn):
            if await self._incidents.get(incident_id) is None:
                raise NotFoundError("Incident")
            report = await self._reports.get(incident_id)
        if report is None:
            raise NotFoundError("Damage report")
        return report

    async def locales(self, incident_id: int) -> list[Locale]:
        """The letter languages a draft can be made in now (#143).

        Empty for an incident that isn't a pothole. A live model drafts in either; demo mode
        only where a draft is recorded for the incident as it stands, so the driver is never
        offered a draft that can only fail. Nothing is written: the location context it needs
        is looked up as the draft would look it up, but not cached.
        """
        incident, _, turns, vehicle, photos = await self._read(incident_id)
        if incident.problem_type is not ProblemType.POTHOLE_DAMAGE:
            return []
        if not isinstance(self._provider, ReplayProvider):
            return list(LETTER_LOCALES)
        facts = VehicleFactBlock.from_facts(vehicle.facts) if vehicle else None
        scenario = scenario_key(incident.problem_type.value, incident.situation.value, facts)
        if incident.location_context is None and incident.location is not None:
            # Demo mode resolves from the scenario's recording, in any language.
            resolved = await self._location.resolve(incident.location, "pl", scenario)
            if resolved is not None:
                incident = replace(incident, location_context=resolved.context)
        offered: list[Locale] = []
        for locale in LETTER_LOCALES:
            _, request = self._request(incident, facts, photos, turns, locale, scenario)
            if request.replay_key is not None and self._provider.has_recording(request.replay_key):
                offered.append(locale)
        return offered

    async def _read(
        self, incident_id: int
    ) -> tuple[Incident, DamageReport | None, list[AiTurn], Vehicle | None, list[Photo]]:
        """What a draft is made from, read in one snapshot: the incident, its report, turns,
        vehicle and photos."""
        async with read_snapshot(self._conn):
            incident = await self._incidents.get(incident_id)
            if incident is None:
                raise NotFoundError("Incident")
            existing = await self._reports.get(incident_id)
            turns = await self._turns.list_for_incident(incident_id)
            vehicle = (
                await self._vehicles.get(incident.vehicle_id)
                if incident.vehicle_id is not None
                else None
            )
            photos = await self._photos.list_for_incident(incident_id)
        return incident, existing, list(turns), vehicle, list(photos)

    def _request(
        self,
        incident: Incident,
        facts: VehicleFactBlock | None,
        photos: Sequence[Photo],
        turns: Sequence[AiTurn],
        locale: Locale,
        scenario: str,
    ) -> tuple[TurnInputs, LLMRequest]:
        """The model call that drafts the letter in `locale`, with the facts it is told."""
        # The letter tells the story of the incident's moment, not of now.
        inputs = turn_inputs(
            incident,
            facts,
            datetime.fromisoformat(incident.created_at),
            dark=self._location.recorded_dark(scenario),
        )
        advice = next((t for t in turns if t.kind is AiTurnKind.ADVICE), None)
        cause = advice.payload["answer"]["cause"] if advice else None
        rendered = prompt.render_report(inputs, locale, photo_count=len(photos), cause=cause)
        request = LLMRequest(
            messages=(
                LLMMessage("system", rendered.system),
                LLMMessage("user", rendered.user),
            ),
            schema=rendered.schema,
            schema_name="damage_report",
            replay_key=damage_report_key(
                inputs,
                locale=locale,
                sample_photo_ids=[p.sample_id for p in photos if p.sample_id is not None],
                vision=bool(inputs.photo_ids_seen),
                replies=[
                    Reply.from_payload(t.payload) for t in turns if t.kind is AiTurnKind.REPLY
                ],
            ),
        )
        return inputs, request

    async def generate(
        self, incident_id: int, locale: Locale, *, replace: bool
    ) -> tuple[DamageReport, bool]:
        """Draft the report. Returns it and whether it is new (False: it replaced one)."""
        async with self._locks.hold(incident_id):
            incident, existing, turns, vehicle, photos = await self._read(incident_id)
            _check_pothole(incident)
            if existing is not None and not replace:
                raise _exists()

            facts = VehicleFactBlock.from_facts(vehicle.facts) if vehicle else None
            scenario = scenario_key(incident.problem_type.value, incident.situation.value, facts)
            if incident.location_context is None:
                incident = await refresh_location_context(
                    self._conn, self._incidents, self._location, incident, locale, scenario
                )
            inputs, request = self._request(incident, facts, photos, turns, locale, scenario)
            started = time.monotonic()
            try:
                async with asyncio.timeout(self._budget_s):
                    output, result = await complete_validated(
                        self._provider, request, validate_report_output
                    )
            except (TimeoutError, ProviderError, InvalidOutputError) as exc:
                problem = problem_for(exc)
                logger.info(
                    "damage report failed: incident=%d provider=%s reason=%s latency_ms=%d",
                    incident_id,
                    self._provider.name,
                    problem.reason,
                    (time.monotonic() - started) * 1000,
                )
                raise problem from exc
            logger.info(
                "damage report ok: incident=%d provider=%s model=%s latency_ms=%d",
                incident_id,
                result.provider,
                result.model,
                (time.monotonic() - started) * 1000,
            )

            loc = incident.location
            letter = LetterFacts(
                occurred_at=incident.created_at,
                location_label=incident.location_label,
                lat=loc.lat if loc else None,
                lon=loc.lon if loc else None,
                make_model=vehicle.facts.make_model if vehicle else None,
                year=vehicle.facts.year if vehicle else None,
                vehicle_name=vehicle.facts.name if vehicle else None,
                registration=vehicle.facts.registration if vehicle else None,
                photo_count=len(photos),
            )
            new = NewDamageReport(
                locale=locale,
                body=render_letter(
                    letter,
                    locale,
                    description=output.description,
                    damage_summary=output.damage_summary,
                ),
                narrative=output.model_dump(mode="json"),
                provenance=ModelProvenance(
                    inputs=inputs.to_json(),
                    locale=locale,
                    prompt_version=prompt.PROMPT_VERSION,
                    provider=result.provider,
                    model=result.model,
                ),
            )
            async with transaction(self._conn):
                # The incident may have been deleted or retyped while the model was writing.
                current_incident = await self._incidents.get(incident_id)
                if current_incident is None:
                    raise NotFoundError("Incident")
                _check_pothole(current_incident)
                current = await self._reports.get(incident_id)
                if current is not None and not replace:
                    raise _exists()
                await self._reports.put(incident_id, new, utc_now())
                stored = await self._reports.get(incident_id)
        if stored is None:  # pragma: no cover - written in the same transaction
            raise RuntimeError("damage report not stored")
        return stored, current is None

    async def edit(self, incident_id: int, edit: DamageReportEdit) -> DamageReport:
        """Only the driver changes the body and the status; a no-op edit writes nothing."""
        async with transaction(self._conn):
            if await self._incidents.get(incident_id) is None:
                raise NotFoundError("Incident")
            report = await self._reports.get(incident_id)
            if report is None:
                raise NotFoundError("Damage report")
            body = edit.body if edit.body is not None else report.body
            status = edit.status if edit.status is not None else report.status
            if (body, status) == (report.body, report.status):
                return report
            await self._reports.update(incident_id, body, status, utc_now())
            updated = await self._reports.get(incident_id)
        if updated is None:  # pragma: no cover - written in the same transaction
            raise RuntimeError("damage report not stored")
        return updated

    async def delete(self, incident_id: int) -> None:
        async with transaction(self._conn):
            if await self._incidents.get(incident_id) is None:
                raise NotFoundError("Incident")
            if not await self._reports.delete(incident_id):
                raise NotFoundError("Damage report")
