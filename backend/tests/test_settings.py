from pathlib import Path

import pytest
from pydantic import ValidationError

from app.integrations.llm.factory import NoRecordingsProvider, build_provider
from app.integrations.llm.openai_compatible import OpenAICompatibleProvider
from app.main import create_app
from app.settings import Settings

LIVE = {
    "demo_mode": False,
    "llm_base_url": "http://localhost:11434/v1/",
    "llm_api_key": "ollama",
    "llm_model": "qwen3:8b",
}


@pytest.fixture(autouse=True)
def _no_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep a developer's .env and LLM_* variables out of these tests."""
    monkeypatch.chdir(tmp_path)
    for name in ("DEMO_MODE", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "LLM_TURN_BUDGET_S"):
        monkeypatch.delenv(name, raising=False)


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


def test_demo_mode_needs_no_llm_settings() -> None:
    provider = build_provider(Settings())
    assert isinstance(provider, NoRecordingsProvider)


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
