import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.db.migrate import MIN_SQLITE, migrate, read_user_version
from app.domain.vehicle import FuelType, SpareWheel, Transmission


def test_migrate_is_idempotent_and_sets_user_version(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    migrate(db)
    v = read_user_version(db)
    assert v >= 1
    migrate(db)
    assert read_user_version(db) == v


def test_migrate_fails_fast_on_old_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 36, 0))
    monkeypatch.setattr(sqlite3, "sqlite_version", "3.36.0")
    with pytest.raises(RuntimeError, match=r"3\.36\.0.*3\.37"):
        migrate(tmp_path / "x.db")
    assert MIN_SQLITE == (3, 37, 0)


def _check_sql(db: Path) -> str:
    with closing(sqlite3.connect(db)) as c:
        row = c.execute("SELECT sql FROM sqlite_master WHERE name='vehicles'").fetchone()
    return str(row[0])


def test_sql_enum_lists_match_pydantic_enums(tmp_path: Path) -> None:
    db = tmp_path / "e.db"
    migrate(db)
    sql = _check_sql(db)
    assert "STRICT" in sql
    for enum in (FuelType, Transmission, SpareWheel):
        for member in enum:
            assert f"'{member.value}'" in sql
    # and no extra values: every quoted token in the CHECKs is a known enum value
    import re

    known = {m.value for e in (FuelType, Transmission, SpareWheel) for m in e}
    quoted = set(re.findall(r"'([a-z_]+)'", sql))
    assert quoted <= known


def test_partial_unique_index_allows_one_default(tmp_path: Path) -> None:
    db = tmp_path / "d.db"
    migrate(db)
    with closing(sqlite3.connect(db)) as c:
        ins = (
            "INSERT INTO vehicles(name,is_default,created_at,updated_at) "
            "VALUES(?,?,'2026-01-01T00:00:00.000Z','2026-01-01T00:00:00.000Z')"
        )
        c.execute(ins, ("a", 1))
        c.execute(ins, ("b", 0))
        c.execute(ins, ("c", 0))
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(ins, ("d", 1))


def test_incident_enum_lists_match_pydantic_enums(tmp_path: Path) -> None:
    import re

    from app.domain.incident import IncidentStatus, ProblemType
    from app.domain.location_context import RoadClass, Settlement

    db = tmp_path / "i.db"
    migrate(db)
    with closing(sqlite3.connect(db)) as c:
        sql = str(c.execute("SELECT sql FROM sqlite_master WHERE name='incidents'").fetchone()[0])
    assert "STRICT" in sql
    known = {m.value for e in (ProblemType, IncidentStatus, RoadClass, Settlement) for m in e}
    assert set(re.findall(r"'([a-z_]+)'", sql)) == known


def test_incident_location_needs_both_coordinates(tmp_path: Path) -> None:
    db = tmp_path / "l.db"
    migrate(db)
    ins = (
        "INSERT INTO incidents(problem_type,status,lat,lon,accuracy_m,created_at,updated_at) "
        "VALUES('other','open',?,?,?,'2026-01-01T00:00:00.000Z','2026-01-01T00:00:00.000Z')"
    )
    with closing(sqlite3.connect(db)) as c:
        c.execute(ins, (52.0, 21.0, None))
        c.execute(ins, (None, None, None))
        for bad in ((52.0, None, None), (None, None, 5.0)):
            with pytest.raises(sqlite3.IntegrityError):
                c.execute(ins, bad)
