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
    # Demo mode's simulated thinking (#143) would only slow the tests down.
    monkeypatch.setenv("DEMO_THINKING_S", "0")
    monkeypatch.setenv("DEMO_REPLY_THINKING_S", "0")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        # Empty: demo-mode tests bring their own recordings.
        llm_recordings_dir=tmp_path / "recordings",
        frontend_origins=[ORIGIN],
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    # ASGITransport does not run the lifespan, so do its setup here.
    migrate(settings.database_path)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
