import json
import sqlite3
from collections.abc import Sequence
from typing import Protocol, cast

import aiosqlite

from app.domain.ai_turn import Locale, ModelProvenance
from app.domain.damage_report import DamageReport, DamageReportStatus, NewDamageReport

_SELECT = (
    "SELECT incident_id, status, locale, body, narrative, inputs, prompt_version, provider, "
    "model, created_at, updated_at FROM damage_reports"
)


class DamageReportRepository(Protocol):
    async def get(self, incident_id: int) -> DamageReport | None: ...
    async def put(self, incident_id: int, report: NewDamageReport, now: str) -> None: ...
    async def update(
        self, incident_id: int, body: str, status: DamageReportStatus, now: str
    ) -> None: ...
    async def delete(self, incident_id: int) -> bool: ...
    async def statuses(self, incident_ids: Sequence[int]) -> dict[int, DamageReportStatus]: ...


def _to_domain(r: sqlite3.Row) -> DamageReport:
    locale = cast(Locale, r["locale"])
    return DamageReport(
        incident_id=r["incident_id"],
        status=DamageReportStatus(r["status"]),
        locale=locale,
        body=r["body"],
        narrative=json.loads(r["narrative"]),
        provenance=ModelProvenance(
            inputs=json.loads(r["inputs"]),
            locale=locale,
            prompt_version=r["prompt_version"],
            provider=r["provider"],
            model=r["model"],
        ),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


class SqliteDamageReportRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def get(self, incident_id: int) -> DamageReport | None:
        cur = await self._conn.execute(f"{_SELECT} WHERE incident_id = ?", (incident_id,))
        row = await cur.fetchone()
        return _to_domain(row) if row else None

    async def put(self, incident_id: int, report: NewDamageReport, now: str) -> None:
        """Insert, or overwrite an existing report as a new draft that keeps its `created_at`."""
        p = report.provenance
        await self._conn.execute(
            "INSERT INTO damage_reports (incident_id, status, locale, body, narrative, inputs, "
            "prompt_version, provider, model, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (incident_id) DO UPDATE SET "
            "status = excluded.status, locale = excluded.locale, body = excluded.body, "
            "narrative = excluded.narrative, inputs = excluded.inputs, "
            "prompt_version = excluded.prompt_version, provider = excluded.provider, "
            "model = excluded.model, updated_at = excluded.updated_at",
            (
                incident_id,
                DamageReportStatus.DRAFT.value,
                report.locale,
                report.body,
                json.dumps(report.narrative, ensure_ascii=False),
                json.dumps(p.inputs, ensure_ascii=False),
                p.prompt_version,
                p.provider,
                p.model,
                now,
                now,
            ),
        )

    async def update(
        self, incident_id: int, body: str, status: DamageReportStatus, now: str
    ) -> None:
        await self._conn.execute(
            "UPDATE damage_reports SET body = ?, status = ?, updated_at = ? WHERE incident_id = ?",
            (body, status.value, now, incident_id),
        )

    async def delete(self, incident_id: int) -> bool:
        cur = await self._conn.execute(
            "DELETE FROM damage_reports WHERE incident_id = ?", (incident_id,)
        )
        return cur.rowcount > 0

    async def statuses(self, incident_ids: Sequence[int]) -> dict[int, DamageReportStatus]:
        """The report status of each of these incidents that has a report."""
        if not incident_ids:
            return {}
        marks = ",".join("?" * len(incident_ids))
        cur = await self._conn.execute(
            f"SELECT incident_id, status FROM damage_reports WHERE incident_id IN ({marks})",  # noqa: S608
            tuple(incident_ids),
        )
        return {r["incident_id"]: DamageReportStatus(r["status"]) for r in await cur.fetchall()}
