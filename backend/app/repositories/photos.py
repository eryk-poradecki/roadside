import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import aiosqlite

from app.domain.photo import EXTENSIONS, Photo, PreparedPhoto

logger = logging.getLogger("roadside.photos")

_SELECT = (
    "SELECT id, incident_id, stored_name, content_type, size_bytes, width, height, sample_id, "
    "created_at FROM incident_photos"
)


class PhotoRepository(Protocol):
    async def get(self, photo_id: int) -> Photo | None: ...
    async def list_for_incident(self, incident_id: int) -> list[Photo]: ...
    async def count_for_incident(self, incident_id: int) -> int: ...
    async def insert(
        self,
        incident_id: int,
        stored_name: str,
        photo: PreparedPhoto,
        sample_id: str | None,
        now: str,
    ) -> int: ...
    async def delete(self, photo_id: int) -> bool: ...
    async def has_stored_name(self, stored_name: str) -> bool: ...


def _to_domain(r: sqlite3.Row) -> Photo:
    return Photo(
        id=r["id"],
        incident_id=r["incident_id"],
        stored_name=r["stored_name"],
        content_type=r["content_type"],
        size_bytes=r["size_bytes"],
        width=r["width"],
        height=r["height"],
        sample_id=r["sample_id"],
        created_at=r["created_at"],
    )


class SqlitePhotoRepository:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def get(self, photo_id: int) -> Photo | None:
        cur = await self._conn.execute(f"{_SELECT} WHERE id = ?", (photo_id,))
        row = await cur.fetchone()
        return _to_domain(row) if row else None

    async def list_for_incident(self, incident_id: int) -> list[Photo]:
        """In upload order."""
        cur = await self._conn.execute(
            f"{_SELECT} WHERE incident_id = ? ORDER BY id", (incident_id,)
        )
        return [_to_domain(r) for r in await cur.fetchall()]

    async def count_for_incident(self, incident_id: int) -> int:
        cur = await self._conn.execute(
            "SELECT count(*) FROM incident_photos WHERE incident_id = ?", (incident_id,)
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def insert(
        self,
        incident_id: int,
        stored_name: str,
        photo: PreparedPhoto,
        sample_id: str | None,
        now: str,
    ) -> int:
        cur = await self._conn.execute(
            "INSERT INTO incident_photos (incident_id, stored_name, content_type, size_bytes, "
            "width, height, sample_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                incident_id,
                stored_name,
                photo.content_type,
                len(photo.data),
                photo.width,
                photo.height,
                sample_id,
                now,
            ),
        )
        if cur.lastrowid is None:
            raise RuntimeError("INSERT returned no row id")
        return cur.lastrowid

    async def delete(self, photo_id: int) -> bool:
        cur = await self._conn.execute("DELETE FROM incident_photos WHERE id = ?", (photo_id,))
        return cur.rowcount > 0

    async def has_stored_name(self, stored_name: str) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM incident_photos WHERE stored_name = ?", (stored_name,)
        )
        return await cur.fetchone() is not None


class PhotoFiles:
    """The photo files in `UPLOAD_DIR`. Names are generated here, never taken from a client."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @staticmethod
    def new_name(content_type: str) -> str:
        return f"{uuid4().hex}.{EXTENSIONS[content_type]}"

    def path(self, stored_name: str) -> Path:
        return self._root / stored_name

    async def write(self, stored_name: str, data: bytes) -> None:
        def run() -> None:
            # "x": never overwrite, even on a (practically impossible) name clash.
            with self.path(stored_name).open("xb") as f:
                f.write(data)

        await asyncio.to_thread(run)

    async def remove(self, stored_name: str) -> None:
        """Best effort, after the row is gone: a file that is already gone is fine, and a
        failure is logged rather than failing a delete that has already committed."""
        try:
            await asyncio.to_thread(self.path(stored_name).unlink, missing_ok=True)
        except OSError:
            logger.warning("could not remove photo file %s", stored_name, exc_info=True)
