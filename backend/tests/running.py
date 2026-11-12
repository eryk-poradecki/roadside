from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.main import create_app
from app.settings import Settings


@asynccontextmanager
async def running(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """An app whose lifespan has run, as it does on `docker compose up`.

    ASGITransport skips the lifespan, so the `app` fixture does its setup by hand; this runs
    the real one, demo vehicle seeding included.
    """
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
