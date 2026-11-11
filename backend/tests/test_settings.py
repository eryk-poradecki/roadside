from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.llm.factory import build_provider
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider
from app.integrations.llm.recording import RecordingProvider
from app.integrations.llm.replay import ReplayProvider
from app.integrations.overpass import OverpassClient
from app.main import create_app
from app.settings import Settings

LIVE = {
    "demo_mode": False,
    "llm_base_url": "http://localhost:11434/v1/",
    "llm_api_key": "ollama",
    "llm_model": "qwen3:8b",
}


@pytest.mark.parametrize("budget", [100, 100.5, 250])
def test_startup_refuses_a_turn_budget_of_100_s_or_more(budget: float) -> None:
    with pytest.raises(ValidationError, match="llm_turn_budget_s"):
        Settings(llm_turn_budget_s=budget)


def test_a_turn_budget_just_under_the_tunnel_limit_is_accepted() -> None:
    assert Settings(llm_turn_budget_s=99.9).llm_turn_budget_s == 99.9


def test_the_turn_budget_from_the_environment_is_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_TURN_BUDGET_S", "120")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("missing", ["llm_base_url", "llm_api_key", "llm_model"])
def test_demo_mode_off_needs_the_llm_settings(missing: str) -> None:
    values = {**LIVE, missing: ""}
    with pytest.raises(ValidationError, match=missing.upper()):
        Settings(**values)  # type: ignore[arg-type]


def test_demo_mode_off_with_nothing_set_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    with pytest.raises(ValidationError, match="LLM_BASE_URL, LLM_API_KEY, LLM_MODEL"):
        create_app()


def test_demo_mode_needs_no_llm_settings_and_replays() -> None:
    provider = build_provider(Settings())
    assert isinstance(provider, ReplayProvider)


# --- startup refusals (ADR 0004, 0011) -------------------------------------------------------


def test_a_public_deploy_refuses_a_live_model() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_DEPLOY"):
        Settings(**LIVE, public_deploy=True)  # type: ignore[arg-type]


def test_a_public_deploy_refuses_recording() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_DEPLOY"):
        Settings(**LIVE, public_deploy=True, llm_record=True)  # type: ignore[arg-type]


def test_a_public_deploy_refuses_recording_even_in_demo_mode() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_DEPLOY"):
        Settings(public_deploy=True, llm_record=True)


def test_a_public_deploy_in_demo_mode_starts() -> None:
    assert Settings(public_deploy=True).demo_mode is True


def test_recording_is_refused_in_demo_mode() -> None:
    with pytest.raises(ValidationError, match="LLM_RECORD"):
        Settings(llm_record=True)


def test_the_public_deploy_guard_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {**LIVE, "public_deploy": True}.items():
        monkeypatch.setenv(name.upper(), str(value))
    with pytest.raises(ValidationError, match="PUBLIC_DEPLOY"):
        create_app()


async def test_recording_wraps_the_live_provider(tmp_path: Path) -> None:
    settings = Settings(**LIVE, llm_record=True, llm_recordings_dir=tmp_path)  # type: ignore[arg-type]
    provider = build_provider(settings)
    try:
        assert isinstance(provider, RecordingProvider)
        assert provider.name == "openai_compatible"
    finally:
        await provider.aclose()


async def test_demo_mode_off_builds_the_openai_compatible_provider() -> None:
    settings = Settings(**LIVE, llm_timeout_s=30)  # type: ignore[arg-type]
    provider = build_provider(settings)
    try:
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.timeout.read == 30
        assert provider.timeout.connect == 5
    finally:
        await provider.aclose()


def test_the_api_key_is_never_printed() -> None:
    settings = Settings(**{**LIVE, "llm_api_key": "sk-very-secret"})  # type: ignore[arg-type]
    assert "sk-very-secret" not in repr(settings)
    assert "sk-very-secret" not in str(settings.model_dump())


def test_overpass_urls_come_from_a_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OVERPASS_URLS", "https://a.test/api/interpreter, https://b.test/api/x")
    assert Settings().overpass_urls == ["https://a.test/api/interpreter", "https://b.test/api/x"]


def test_overpass_needs_at_least_one_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OVERPASS_URLS", " , ")
    with pytest.raises(ValidationError, match="overpass_urls"):
        Settings()


def test_the_overpass_budget_stays_under_the_tunnel_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OVERPASS_BUDGET_S", "100")
    with pytest.raises(ValidationError, match="overpass_budget_s"):
        Settings()


def test_one_overpass_attempt_must_fit_in_the_budget() -> None:
    with pytest.raises(ValidationError, match="OVERPASS_TIMEOUT_S"):
        Settings(overpass_timeout_s=90, overpass_budget_s=75)


async def test_demo_mode_off_builds_the_overpass_client() -> None:
    app = create_app(Settings(**LIVE))  # type: ignore[arg-type]
    assert isinstance(app.state.place_source, OverpassClient)
    assert create_app(Settings()).state.place_source is None
    await app.state.place_source.aclose()


def test_empty_frontend_origins_allows_no_cross_origin_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The compose stack is same-origin behind nginx (ADR 0007, 0011), so it sets this empty.
    monkeypatch.setenv("FRONTEND_ORIGINS", "")
    assert Settings().frontend_origins == []
