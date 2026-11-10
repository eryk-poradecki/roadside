import asyncio
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


async def connect(path: Path) -> aiosqlite.Connection:
    """Open a connection in autocommit mode with the pragmas ADR 0006 requires."""
    conn = await aiosqlite.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@asynccontextmanager
async def read_snapshot(conn: aiosqlite.Connection) -> AsyncIterator[None]:
    """Several reads that must agree (e.g. a page and its total): one deferred read txn."""
    await conn.execute("BEGIN")
    try:
        yield
    finally:
        await asyncio.shield(conn.execute("COMMIT"))


@asynccontextmanager
async def transaction(conn: aiosqlite.Connection) -> AsyncIterator[None]:
    """Unit of work: BEGIN IMMEDIATE takes the write lock up front. Repositories never commit."""
    await conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        await asyncio.shield(conn.execute("ROLLBACK"))
        raise
    else:
        await conn.execute("COMMIT")
