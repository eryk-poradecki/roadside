import sqlite3
from collections.abc import AsyncIterator
from contextlib import closing
from pathlib import Path

import aiosqlite
import pytest

from app.db.connection import connect
from app.db.migrate import migrate
from app.domain.ai_turn import AiTurnKind, ModelProvenance, NewAiTurn
from app.domain.incident import NewIncident, ProblemType
from app.repositories.ai_turns import SqliteAiTurnRepository
from app.repositories.incidents import SqliteIncidentRepository

NOW = "2026-01-01T00:00:00.000Z"
PROVENANCE = ModelProvenance(
    inputs={"problem_type": "flat_tyre"},
    locale="pl",
    prompt_version="v1",
    provider="fake",
    model="m",
)


@pytest.fixture
async def conn(tmp_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    db = tmp_path / "t.db"
    migrate(db)
    c = await connect(db)
    try:
        yield c
    finally:
        await c.close()


async def _incident(conn: aiosqlite.Connection) -> int:
    return await SqliteIncidentRepository(conn).insert(
        NewIncident(ProblemType.FLAT_TYRE), None, NOW
    )


def _turn(kind: AiTurnKind) -> NewAiTurn:
    reply = kind is AiTurnKind.REPLY
    return NewAiTurn(kind, {"x": "zażółć"}, None if reply else PROVENANCE)


async def test_sequence_numbers_count_per_incident(conn: aiosqlite.Connection) -> None:
    repo = SqliteAiTurnRepository(conn)
    a, b = await _incident(conn), await _incident(conn)
    await repo.append(a, _turn(AiTurnKind.QUESTION), NOW)
    await repo.append(b, _turn(AiTurnKind.QUESTION), NOW)
    await repo.append(a, _turn(AiTurnKind.REPLY), NOW)
    await repo.append(a, _turn(AiTurnKind.ADVICE), NOW)

    turns = await repo.list_for_incident(a)

    assert [(t.seq, t.kind) for t in turns] == [
        (1, AiTurnKind.QUESTION),
        (2, AiTurnKind.REPLY),
        (3, AiTurnKind.ADVICE),
    ]
    assert turns[0].payload == {"x": "zażółć"}
    assert turns[0].provenance == PROVENANCE
    assert turns[1].provenance is None
    assert [t.seq for t in await repo.list_for_incident(b)] == [1]


async def test_at_most_one_advice_per_incident(conn: aiosqlite.Connection) -> None:
    repo = SqliteAiTurnRepository(conn)
    incident = await _incident(conn)
    await repo.append(incident, _turn(AiTurnKind.ADVICE), NOW)
    with pytest.raises(sqlite3.IntegrityError):
        await repo.append(incident, _turn(AiTurnKind.ADVICE), NOW)


async def test_a_model_turn_needs_its_provenance(conn: aiosqlite.Connection) -> None:
    repo = SqliteAiTurnRepository(conn)
    incident = await _incident(conn)
    with pytest.raises(sqlite3.IntegrityError):
        await repo.append(incident, NewAiTurn(AiTurnKind.ADVICE, {}, None), NOW)
    with pytest.raises(sqlite3.IntegrityError):
        await repo.append(incident, NewAiTurn(AiTurnKind.REPLY, {}, PROVENANCE), NOW)


def test_sql_kind_list_matches_the_enum(tmp_path: Path) -> None:
    db = tmp_path / "k.db"
    migrate(db)
    with closing(sqlite3.connect(db)) as c:
        sql = str(c.execute("SELECT sql FROM sqlite_master WHERE name='ai_turns'").fetchone()[0])
    assert "kind IN ('question', 'reply', 'advice')" in sql
    assert {k.value for k in AiTurnKind} == {"question", "reply", "advice"}
