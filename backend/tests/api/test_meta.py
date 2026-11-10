from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.db.migrate import migrate
from app.main import create_app
from app.settings import Settings


async def test_health(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_config_defaults_to_demo_mode(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["demo_mode"] is True
    assert body["vision_enabled"] is False
    assert body["max_photos"] == 5
    assert body["max_photo_bytes"] == 10 * 1024 * 1024
    assert body["sample_photos"] == []


async def test_unknown_route_is_problem_json(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["reason"] == "not_found"


async def test_cors_allows_configured_origin_only(client: httpx.AsyncClient) -> None:
    ok = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = await client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


async def test_cors_preflight_for_unlisted_origin_refused(client: httpx.AsyncClient) -> None:
    r = await client.options(
        "/api/v1/vehicles",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


async def test_body_over_limit_is_413_problem(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/v1/vehicles",
        content=b"x" * (13 * 1024 * 1024),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413
    assert r.json()["reason"] == "body_too_large"


def test_wildcard_cors_origin_refused() -> None:
    with pytest.raises(ValidationError):
        Settings(frontend_origins=["*"])


def test_origins_parse_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://a.test, http://b.test")
    assert Settings().frontend_origins == ["http://a.test", "http://b.test"]


def test_demo_mode_true_by_default() -> None:
    assert Settings().demo_mode is True


async def test_413_response_carries_cors_headers(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/v1/vehicles",
        content=b"x" * (13 * 1024 * 1024),
        headers={"Content-Type": "application/json", "Origin": "http://localhost:5173"},
    )
    assert r.status_code == 413
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_vision_follows_the_provider_in_use(tmp_path: Path) -> None:
    # Demo mode has no model that sees photos, whatever LLM_VISION says.
    settings = Settings(database_path=tmp_path / "v.db", upload_dir=tmp_path / "u", llm_vision=True)
    migrate(settings.database_path)
    transport = httpx.ASGITransport(app=create_app(settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        body = (await client.get("/api/v1/config")).json()
    assert body["vision_enabled"] is False
