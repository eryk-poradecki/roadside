from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.db.migrate import migrate
from app.main import create_app
from app.settings import Settings

ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def _no_developer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a developer's backend/.env and exported settings out of every test."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        frontend_origins=[ORIGIN],
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    # ASGITransport does not run the lifespan, so migrate here with the same function.
    migrate(settings.database_path)
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
