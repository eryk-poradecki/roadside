import sqlite3
from pathlib import Path

MIN_SQLITE = (3, 37, 0)
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def check_sqlite_version() -> None:
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        need = ".".join(map(str, MIN_SQLITE))
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} found, but {need} or newer is required "
            "(STRICT tables)"
        )


def read_user_version(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    finally:
        conn.close()


def _statements(script: str) -> list[str]:
    """Split a migration into complete statements (sqlite3.complete_statement aware)."""
    out: list[str] = []
    buf = ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                out.append(buf)
            buf = ""
    if buf.strip():
        out.append(buf)
    return out


def migrate(path: Path, migrations_dir: Path = MIGRATIONS_DIR) -> int:
    """Apply forward-only numbered migrations; each runs in one transaction with user_version."""
    check_sqlite_version()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        current = int(conn.execute("PRAGMA user_version").fetchone()[0])
        for file in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            number = int(file.name[:4])
            if number <= current:
                continue
            try:
                conn.execute("BEGIN IMMEDIATE")
                # Re-check under the write lock: another process may have just applied it.
                if int(conn.execute("PRAGMA user_version").fetchone()[0]) >= number:
                    conn.execute("ROLLBACK")
                    current = number
                    continue
                for statement in _statements(file.read_text()):
                    conn.execute(statement)
                conn.execute(f"PRAGMA user_version = {number}")
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            current = number
        return current
    finally:
        conn.close()
