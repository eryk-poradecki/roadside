"""Reusing recordings in a recording run (#63): a branch's reply is recorded against the very
question and options already recorded, instead of a new question the model words differently."""

from app.integrations.llm.base import LLMMessage, LLMRequest
from app.integrations.llm.recording import Recording
from scripts.demo.reuse import ReuseProvider
from tests.fakes import ScriptedProvider


def request(key: str) -> LLMRequest:
    return LLMRequest(
        messages=(LLMMessage("user", "help"),), schema={}, schema_name="ai_turn", replay_key=key
    )


def recorded(key: str, text: str) -> Recording:
    return Recording(key, {}, text, "cli", "claude-x", "v3", "t")


async def test_a_recorded_key_is_reused_without_a_call() -> None:
    live = ScriptedProvider()
    reuse = ReuseProvider(live, {"k": recorded("k", "old")})

    result = await reuse.complete(request("k"))

    assert (result.text, result.provider, result.model) == ("old", "cli", "claude-x")
    assert live.requests == []
    assert reuse.touched == {"k": "reused"}


async def test_an_unrecorded_key_is_recorded_live_and_reused_by_a_later_step() -> None:
    live = ScriptedProvider("new")
    reuse = ReuseProvider(live, {})
    await reuse.complete(request("k"))

    reuse.begin_step()
    again = await reuse.complete(request("k"))

    assert again.text == "new"
    assert len(live.requests) == 1
    assert reuse.touched == {"k": "recorded"}


async def test_a_repair_in_the_same_step_goes_live() -> None:
    """A reused output that fails validation gets a live repair, which replaces it."""
    live = ScriptedProvider("repaired")
    reuse = ReuseProvider(live, {"k": recorded("k", "not json")})
    reuse.begin_step()
    await reuse.complete(request("k"))

    repair = await reuse.complete(request("k"))

    assert repair.text == "repaired"
    assert reuse.touched == {"k": "recorded"}


async def test_fresh_records_every_key_anew() -> None:
    live = ScriptedProvider("new")
    reuse = ReuseProvider(live, {"k": recorded("k", "old")}, fresh=True)

    result = await reuse.complete(request("k"))

    assert result.text == "new"


async def test_the_step_log_names_each_key_and_what_happened() -> None:
    reuse = ReuseProvider(ScriptedProvider("new"), {"a": recorded("a", "old")})
    reuse.begin_step()
    await reuse.complete(request("a"))
    await reuse.complete(request("b"))

    assert reuse.step_log == [("a", "reused"), ("b", "recorded")]
