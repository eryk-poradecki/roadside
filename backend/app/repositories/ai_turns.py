import json
import sqlite3
from typing import Protocol, cast

import aiosqlite

from app.domain.ai_turn import AiTurn, AiTurnKind, Locale, ModelProvenance, NewAiTurn

_SELECT = (
    "SELECT id, incident_id, seq, kind, payload, inputs, locale, prompt_version, provider, "
    "model, created_at FROM ai_turns"
)


class AiTurnRepository(Protocol):
    async def list_for_incident(self, incident_id: int) -> list[AiTurn]: ...
    async def append(self, incident_id: int, turn: NewAiTurn, now: str) -> int: ...


def _to_domain(r: sqlite3.Row) -> AiTurn:
    provenance = (
        ModelProvenance(
            inputs=json.loads(r["inputs"]),
            locale=cast(Locale, r["locale"]),
            prompt_version=r["prompt_version"],
            provider=r["provider"],
            model=r["model"],
        )
        if r["inputs"] is not None
        else None
    )
    return AiTurn(
        id=r["id"],
        incident_id=r["incident_id"],
        seq=r["seq"],
        kind=AiTurnKind(r["kind"]),
        payload=json.loads(r["payload"]),
        provenance=provenance,
        created_at=r["created_at"],
    )


class SqliteAiTurnRepository:
    """Insert and read only: the AI answer is append-only (ADR 0004)."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def list_for_incident(self, incident_id: int) -> list[AiTurn]:
        cur = await self._conn.execute(
            f"{_SELECT} WHERE incident_id = ? ORDER BY seq", (incident_id,)
        )
        return [_to_domain(r) for r in await cur.fetchall()]

    async def append(self, incident_id: int, turn: NewAiTurn, now: str) -> int:
        """Insert with the next sequence number. Call inside the service's transaction."""
        p = turn.provenance
        cur = await self._conn.execute(
            "INSERT INTO ai_turns (incident_id, seq, kind, payload, inputs, locale, "
            "prompt_version, provider, model, created_at) VALUES (?, "
            "(SELECT coalesce(max(seq), 0) + 1 FROM ai_turns WHERE incident_id = ?), "
            "?, ?, ?, ?, ?, ?, ?, ?)",
            (
                incident_id,
                incident_id,
                turn.kind.value,
                json.dumps(turn.payload, ensure_ascii=False),
                json.dumps(p.inputs, ensure_ascii=False) if p else None,
                p.locale if p else None,
                p.prompt_version if p else None,
                p.provider if p else None,
                p.model if p else None,
                now,
            ),
        )
        if cur.lastrowid is None:
            raise RuntimeError("INSERT returned no row id")
        return cur.lastrowid
