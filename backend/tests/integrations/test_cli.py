"""CLI transport contract, using an executable fake without network or Claude auth."""

import asyncio
from pathlib import Path

import pytest

from app.integrations.llm.base import (
    LLMImage,
    LLMMessage,
    LLMRequest,
    ProviderError,
    ProviderTimeoutError,
)
from app.integrations.llm.cli import CLIProvider
from app.integrations.llm.factory import build_provider
from app.integrations.llm.recording import RecordingProvider, load_recordings
from app.settings import Settings


def executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    import sys

    script = tmp_path / "claude"
    script.write_text(f"#!{sys.executable}\n" + body)
    script.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))


def request() -> LLMRequest:
    return LLMRequest(
        messages=(
            LLMMessage("system", "system rules"),
            LLMMessage("user", "help", (LLMImage("image/png", "aW1hZ2U="),)),
        ),
        schema={"type": "object"},
        schema_name="answer",
        replay_key="test-key",
    )


async def test_cli_records_and_uses_isolated_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable(
        tmp_path,
        monkeypatch,
        """import json, os, sys
args = sys.argv
assert args[args.index('--tools') + 1] == ''
assert args[args.index('--setting-sources') + 1] == ''
assert '--safe-mode' in args and '--strict-mcp-config' in args
assert '--json-schema' not in args
assert os.listdir('.') == []
assert 'system rules' in args[args.index('--system-prompt') + 1]
payload = json.loads(sys.stdin.readline())
assert payload['message']['content'][0]['text'] == 'user:\\nhelp'
assert payload['message']['content'][1]['source'] == {
    'type': 'base64', 'media_type': 'image/png', 'data': 'aW1hZ2U='}
print(json.dumps({'type': 'result', 'result': '{}', 'modelUsage': {'claude-test': {}},
                  'usage': {'input_tokens': 12}}))
""",
    )
    provider = build_provider(
        Settings(
            demo_mode=False,
            llm_provider="cli",
            llm_record=True,
            llm_recordings_dir=tmp_path / "records",
        )
    )
    assert isinstance(provider, RecordingProvider)
    result = await provider.complete(request())
    assert (result.text, result.model, result.provider) == ("{}", "claude-test", "cli")
    assert result.usage == {"input_tokens": 12}
    assert load_recordings(tmp_path / "records")


@pytest.mark.parametrize(
    "body",
    [
        "print('not json')",
        "raise SystemExit(1)",
        'print(\'{"type": "result", "is_error": true}\')',
        "print('{}')",
    ],
)
async def test_cli_failures_are_provider_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    executable(tmp_path, monkeypatch, body)
    with pytest.raises(ProviderError):
        await CLIProvider().complete(request())


async def test_timeout_and_cancellation_reap_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pid_file = tmp_path / "pid"
    executable(
        tmp_path,
        monkeypatch,
        f"import os, time\nopen({str(pid_file)!r}, 'w').write(str(os.getpid()))\ntime.sleep(30)",
    )
    with pytest.raises(ProviderTimeoutError):
        await CLIProvider(timeout_s=0.1).complete(request())
    import os

    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)
    task = asyncio.create_task(CLIProvider().complete(request()))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_missing_binary_fails_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(RuntimeError, match="claude binary"):
        build_provider(Settings(demo_mode=False, llm_provider="cli", llm_record=True))


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"demo_mode": False},
        {"public_deploy": True},
        {"demo_mode": False, "llm_record": True, "public_deploy": True},
    ],
)
def test_cli_is_only_for_local_recording(values: dict[str, bool]) -> None:
    with pytest.raises(ValueError, match=r"CLI|cli|PUBLIC_DEPLOY"):
        Settings.model_validate({"llm_provider": "cli", **values})
