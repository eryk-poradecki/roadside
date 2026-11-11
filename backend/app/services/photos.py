"""Photos (ADR 0002): file and row kept consistent by ordering, not by a transaction.

Adding: run the pipeline → write the file → commit the row, and remove the file when the
commit fails. Deleting: commit the row's removal, then remove the file.
"""

import asyncio
from pathlib import Path

import aiosqlite

from app.db.connection import read_snapshot, transaction
from app.domain.photo import (
    ImageTooLargeError,
    Photo,
    PreparedPhoto,
    UnsupportedImageError,
    prepare_photo,
)
from app.domain.sample_photo import find_sample
from app.errors import AppError, NotFoundError
from app.repositories.incidents import IncidentRepository
from app.repositories.photos import PhotoFiles, PhotoRepository
from app.services.clock import utc_now


class PhotoService:
    def __init__(
        self,
        conn: aiosqlite.Connection,
        incidents: IncidentRepository,
        photos: PhotoRepository,
        files: PhotoFiles,
        *,
        max_photos: int,
        demo_mode: bool,
    ) -> None:
        self._conn = conn
        self._incidents = incidents
        self._photos = photos
        self._files = files
        self._max_photos = max_photos
        self._demo_mode = demo_mode

    def check_uploads_allowed(self) -> None:
        """The public demo stores no strangers' files: the server refuses, not just the UI."""
        if self._demo_mode:
            raise AppError(403, "demo_uploads_disabled", "Demo mode accepts sample photos only")

    async def add_upload(self, incident_id: int, data: bytes) -> Photo:
        self.check_uploads_allowed()
        await self._check_room(incident_id)
        try:
            prepared = await asyncio.to_thread(prepare_photo, data)
        except UnsupportedImageError as exc:
            raise AppError(415, "unsupported_media_type", "Send a JPEG, PNG or WebP image") from exc
        except ImageTooLargeError as exc:
            raise AppError(413, "photo_too_large", "The image has too many pixels") from exc
        return await self._store(incident_id, prepared, sample_id=None)

    async def add_sample(self, incident_id: int, sample_id: str) -> Photo:
        """Copy a bundled sample in as an ordinary photo: same limit, deletion and vision."""
        sample = find_sample(sample_id)
        if sample is None:
            raise AppError(
                422,
                "unknown_sample",
                "Unknown sample photo",
                [{"field": "sample_id", "message": "Unknown sample photo"}],
            )
        await self._check_room(incident_id)
        data = await asyncio.to_thread(Path.read_bytes, sample.path)
        prepared = await asyncio.to_thread(prepare_photo, data)
        return await self._store(incident_id, prepared, sample_id=sample.id)

    async def get(self, photo_id: int) -> tuple[Photo, Path]:
        """The photo and its file; 404 when either is missing."""
        photo = await self._photos.get(photo_id)
        if photo is None:
            raise NotFoundError("Photo")
        path = self._files.path(photo.stored_name)
        if not path.is_file():
            raise NotFoundError("Photo")
        return photo, path

    async def delete(self, photo_id: int) -> None:
        async with transaction(self._conn):
            photo = await self._photos.get(photo_id)
            if photo is None or not await self._photos.delete(photo_id):
                raise NotFoundError("Photo")
        await self._files.remove(photo.stored_name)

    async def _check_room(self, incident_id: int) -> None:
        """404 for a missing incident, 409 when it has its five photos. Checked before the
        pipeline so a full incident costs no decoding; checked again before the insert."""
        async with read_snapshot(self._conn):
            await self._check_room_now(incident_id)

    async def _check_room_now(self, incident_id: int) -> None:
        if await self._incidents.get(incident_id) is None:
            raise NotFoundError("Incident")
        if await self._photos.count_for_incident(incident_id) >= self._max_photos:
            raise AppError(409, "photo_limit", f"An incident has at most {self._max_photos}")

    async def _remove_orphan(self, stored_name: str) -> None:
        """Remove a file whose row was not committed. A cancellation can land while COMMIT
        still completes in aiosqlite's thread, so check for the row first."""
        if not await self._photos.has_stored_name(stored_name):
            await self._files.remove(stored_name)

    async def _store(
        self, incident_id: int, prepared: PreparedPhoto, sample_id: str | None
    ) -> Photo:
        name = PhotoFiles.new_name(prepared.content_type)
        now = utc_now()
        # The file first, outside the write lock; the row commits only if it was written.
        await self._files.write(name, prepared.data)
        try:
            async with transaction(self._conn):
                # Under the write lock, so two parallel uploads can't both take the last slot.
                await self._check_room_now(incident_id)
                photo_id = await self._photos.insert(incident_id, name, prepared, sample_id, now)
        except BaseException:
            await asyncio.shield(self._remove_orphan(name))
            raise
        return Photo(
            id=photo_id,
            incident_id=incident_id,
            stored_name=name,
            content_type=prepared.content_type,
            size_bytes=len(prepared.data),
            width=prepared.width,
            height=prepared.height,
            sample_id=sample_id,
            created_at=now,
        )
