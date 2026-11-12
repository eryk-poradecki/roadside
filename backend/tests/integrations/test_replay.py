"""ReplayProvider and RecordingProvider (ADR 0004): demo answers from recordings, and how
recordings are made."""

import json
from pathlib import Path

import pytest

from app.integrations.llm.base import LLMImage, LLMMessage, LLMRequest, ProviderError
from app.integrations.llm.recording import RecordingProvider, load_recordings
from app.integrations.llm.replay import NoRecordingError, ReplayProvider
from tests.fakes import ScriptedProvider, answer_json, ask_json

FIXTURES = Path(__file__).parents[1] / "fixtures" / "recordings"


def request(key: str | None, text: str = "Flat tyre, what now?") -> LLMRequest:
    return LLMRequest(
        messages=(LLMMessage("system", "You are a roadside assistant."), LLMMessage("user", text)),
        schema={"type": "object"},
        schema_name="ai_turn",
        replay_key=key,
    )


def recording(key: str, raw_output: str, model: str = "recorded-model") -> dict[str, object]:
    return {
        "key": key,
        "request": {"schema_name": "ai_turn", "messages": []},
        "raw_output": raw_output,
        "provider": "openai_compatible",
        "model": model,
        "prompt_version": "v1",
        "recorded_at": "2026-11-01T10:00:00.000Z",
    }


def json_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.json"))


def write(directory: Path, name: str, data: dict[str, object]) -> None:
    (directory / name).write_text(json.dumps(data), encoding="utf-8")


# --- replay ----------------------------------------------------------------------------------


async def test_a_matching_key_replays_the_recorded_output(tmp_path: Path) -> None:
    write(tmp_path, "a.json", recording('{"case":"a"}', answer_json(), model="gemini-2.5-flash"))
    provider = ReplayProvider.from_dir(tmp_path)

    result = await provider.complete(request('{"case":"a"}'))

    assert result.text == answer_json()
    assert result.provider == "replay"
    assert result.model == "gemini-2.5-flash"


async def test_a_key_miss_is_never_a_nearest_match(tmp_path: Path) -> None:
    write(tmp_path, "a.json", recording('{"locale":"en","vision":false}', answer_json()))
    provider = ReplayProvider.from_dir(tmp_path)

    for miss in ('{"locale":"pl","vision":false}', '{"locale":"en","vision":true}'):
        with pytest.raises(NoRecordingError):
            await provider.complete(request(miss))


async def test_a_request_without_a_key_has_no_recording(tmp_path: Path) -> None:
    write(tmp_path, "a.json", recording("k", answer_json()))
    with pytest.raises(NoRecordingError):
        await ReplayProvider.from_dir(tmp_path).complete(request(None))


def test_a_key_miss_is_a_provider_error() -> None:
    # So the service's failure path catches it; it still gets its own reason there.
    assert issubclass(NoRecordingError, ProviderError)


async def test_a_missing_recordings_directory_replays_nothing(tmp_path: Path) -> None:
    provider = ReplayProvider.from_dir(tmp_path / "absent")
    with pytest.raises(NoRecordingError):
        await provider.complete(request("k"))


def test_two_recordings_with_one_key_fail_at_startup(tmp_path: Path) -> None:
    write(tmp_path, "a.json", recording("k", answer_json()))
    write(tmp_path, "b.json", recording("k", ask_json()))
    with pytest.raises(ValueError, match="k"):
        load_recordings(tmp_path)


def test_a_malformed_recording_fails_at_startup(tmp_path: Path) -> None:
    write(tmp_path, "a.json", {"key": "k"})
    with pytest.raises(ValueError, match=r"a\.json"):
        load_recordings(tmp_path)


def test_the_fixture_recordings_load() -> None:
    assert len(load_recordings(FIXTURES)) >= 2


# --- recording -------------------------------------------------------------------------------


async def test_recording_writes_the_request_and_raw_output(tmp_path: Path) -> None:
    inner = ScriptedProvider(answer_json(), model="qwen3:8b")
    provider = RecordingProvider(
        inner, tmp_path, prompt_version="v1", clock=lambda: "2026-11-11T10:00:00.000Z"
    )

    result = await provider.complete(request('{"case":"a"}'))

    assert result.text == answer_json()
    files = json_files(tmp_path)
    assert len(files) == 1
    saved = json.loads(files[0].read_text(encoding="utf-8"))
    assert set(saved) == {
        "key",
        "request",
        "raw_output",
        "provider",
        "model",
        "prompt_version",
        "recorded_at",
    }
    assert saved["key"] == '{"case":"a"}'
    assert saved["raw_output"] == answer_json()
    assert saved["provider"] == "fake"
    assert saved["model"] == "qwen3:8b"
    assert saved["prompt_version"] == "v1"
    assert saved["recorded_at"] == "2026-11-11T10:00:00.000Z"
    assert saved["request"]["schema_name"] == "ai_turn"
    assert [m["text"] for m in saved["request"]["messages"]] == [
        "You are a roadside assistant.",
        "Flat tyre, what now?",
    ]


async def test_a_recording_replays(tmp_path: Path) -> None:
    provider = RecordingProvider(ScriptedProvider(ask_json()), tmp_path, prompt_version="v1")
    await provider.complete(request("k"))

    replayed = await ReplayProvider.from_dir(tmp_path).complete(request("k"))

    assert replayed.text == ask_json()


async def test_a_repair_call_overwrites_the_turns_recording(tmp_path: Path) -> None:
    provider = RecordingProvider(
        ScriptedProvider("not json", answer_json()), tmp_path, prompt_version="v1"
    )
    await provider.complete(request("k"))
    await provider.complete(request("k", text="Your previous output was invalid"))

    [saved] = load_recordings(tmp_path).values()
    assert saved.raw_output == answer_json()


async def test_images_are_recorded_by_digest_not_content(tmp_path: Path) -> None:
    provider = RecordingProvider(ScriptedProvider(answer_json()), tmp_path, prompt_version="v1")
    image = LLMImage(media_type="image/jpeg", data_b64="aGVsbG8=")
    req = LLMRequest(
        messages=(LLMMessage("user", "look", images=(image,)),),
        schema={},
        schema_name="ai_turn",
        replay_key="k",
    )
    await provider.complete(req)

    [file] = json_files(tmp_path)
    text = file.read_text(encoding="utf-8")
    assert "aGVsbG8=" not in text
    [message] = json.loads(text)["request"]["messages"]
    assert message["images"][0]["media_type"] == "image/jpeg"
    assert len(message["images"][0]["sha256"]) == 64


async def test_a_failed_call_records_nothing(tmp_path: Path) -> None:
    provider = RecordingProvider(
        ScriptedProvider(ProviderError("down")), tmp_path, prompt_version="v1"
    )
    with pytest.raises(ProviderError):
        await provider.complete(request("k"))
    assert json_files(tmp_path) == []


async def test_a_failed_write_still_returns_the_live_answer(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf-8")
    provider = RecordingProvider(ScriptedProvider(answer_json()), blocked, prompt_version="v1")

    result = await provider.complete(request("k"))

    assert result.text == answer_json()


def test_recording_keeps_the_live_providers_capabilities(tmp_path: Path) -> None:
    inner = ScriptedProvider()
    inner.vision, inner.max_images = True, 3
    provider = RecordingProvider(inner, tmp_path, prompt_version="v1")
    assert (provider.name, provider.vision, provider.max_images) == ("fake", True, 3)


def test_replay_shows_photos_when_the_recordings_were_made_with_vision(tmp_path: Path) -> None:
    """`docker compose up` sets no LLM_VISION: the recordings say how they were made (#63)."""
    key = json.dumps({"vision": True, "sample_photo_ids": ["flat_tyre"]})
    (tmp_path / "a.json").write_text(json.dumps(recording(key, answer_json())))

    replay = ReplayProvider.from_dir(tmp_path, max_images=3)

    assert (replay.vision, replay.max_images) == (True, 3)


def test_replay_without_vision_recordings_shows_none() -> None:
    replay = ReplayProvider.from_dir(FIXTURES, max_images=3)

    assert (replay.vision, replay.max_images) == (False, 0)
