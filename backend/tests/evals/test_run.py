"""The eval runner and its report, against a scripted provider (#64)."""

from app.assist.contract import validate_output
from app.assist.prompt import TurnInputs
from app.domain.ai_turn import Reply
from app.integrations.llm.base import ProviderError
from scripts.evals import rules
from scripts.evals.model import Scenario, Transcript, Turn
from scripts.evals.rules import Status
from scripts.evals.run import report, run_all, run_scenario
from scripts.evals.scenarios import SCENARIOS
from tests.fakes import ScriptedProvider, answer_json, ask_json, sleeping

INPUTS = TurnInputs(
    vehicle=None,
    problem_type="other",
    note="Strange noise from the back",
    local_time="2026-11-11T14:00+01:00",
    dark=False,
)
SCENARIO = Scenario(id="noise", locale="en", inputs=INPUTS)


def kinds(provider: ScriptedProvider, call: int) -> list[str]:
    kind: list[str] = provider.requests[call].schema["properties"]["kind"]["enum"]
    return kind


async def test_an_answer_ends_the_conversation() -> None:
    provider = ScriptedProvider(answer_json())
    t = await run_scenario(provider, SCENARIO, budget_s=10)
    assert len(t.turns) == 1
    assert t.answer is not None
    assert t.model == "fake-model-1"
    assert t.provider == "fake"
    assert "Strange noise from the back" in provider.prompt_text()


async def test_scripted_replies_answer_the_questions_then_the_driver_skips() -> None:
    provider = ScriptedProvider(
        ask_json(question="Where is the noise?"),
        ask_json(question="Is it louder when you brake?"),
        answer_json(),
    )
    s = Scenario(id="noise", locale="en", inputs=INPUTS, replies=(Reply(text="From the back"),))
    t = await run_scenario(provider, s, budget_s=10)
    assert len(t.asks) == 2
    assert t.answer is not None
    assert "From the back" in provider.prompt_text(1)
    assert "skipped further questions" in provider.prompt_text(2)
    assert kinds(provider, 1) == ["ask", "answer"]
    assert kinds(provider, 2) == ["answer"]


async def test_after_two_questions_only_an_answer_is_allowed() -> None:
    provider = ScriptedProvider(ask_json(), ask_json(), answer_json())
    replies = (Reply(text="Yes"), Reply(text="No"))
    s = Scenario(id="noise", locale="en", inputs=INPUTS, replies=replies)
    await run_scenario(provider, s, budget_s=10)
    assert kinds(provider, 2) == ["answer"]


async def test_invalid_output_twice_fails_the_turn() -> None:
    provider = ScriptedProvider("not json", "still not json")
    t = await run_scenario(provider, SCENARIO, budget_s=10)
    assert t.error == "invalid_output"
    assert t.final is None


async def test_a_provider_error_fails_the_turn() -> None:
    t = await run_scenario(ScriptedProvider(ProviderError("down")), SCENARIO, budget_s=10)
    assert t.error == "provider_error"


async def test_the_budget_cuts_a_slow_turn() -> None:
    t = await run_scenario(ScriptedProvider(sleeping(1, answer_json())), SCENARIO, budget_s=0.05)
    assert t.error == "timeout"
    assert t.turns[0].seconds >= 0.05


async def test_run_all_checks_every_scenario_and_reports_each() -> None:
    other = Scenario(id="smoke", locale="en", inputs=INPUTS)
    seen: list[str] = []
    results = await run_all(
        ScriptedProvider(answer_json(), answer_json()),
        [SCENARIO, other],
        budget_s=10,
        on_result=lambda r: seen.append(r.scenario.id),
    )
    assert seen == ["noise", "smoke"]
    assert all(c.status is not Status.FAIL for r in results for c in r.checks)


async def test_the_report_is_a_markdown_table_with_failures_spelled_out() -> None:
    smoke = Scenario(
        id="smoke_en",
        locale="en",
        inputs=TurnInputs(
            vehicle=None,
            problem_type="other",
            note="Smoke from the bonnet",
            local_time="2026-11-11T14:00+01:00",
            dark=False,
        ),
    )
    results = await run_all(
        ScriptedProvider(answer_json(), answer_json()), [SCENARIO, smoke], budget_s=10
    )
    text = report(results, budget_s=10, prompt_version="v2", date="2026-11-11")
    assert "fake / fake-model-1" in text
    assert "prompt v2" in text
    assert "| noise | en | 0 |" in text
    assert "| smoke_en | en | 0 |" in text
    assert "urgent_on_danger" in text
    assert "urgent is false" in text
    # The failing answer is printed for a person to read.
    assert "A puncture in the rear left tyre" in text
    assert "1/2 scenarios passed" in text


def test_the_set_has_about_ten_scenarios_with_unique_ids() -> None:
    ids = [s.id for s in SCENARIOS]
    assert 10 <= len(ids) <= 16
    assert len(set(ids)) == len(ids)


def test_the_set_covers_every_rule() -> None:
    """Each rule applies to at least one scenario, so none of them is dead in a real run."""

    def applies(rule: str, s: Scenario) -> bool:
        checks = rules.check_all(s, _passing_answer(s), budget_s=90)
        return next(c for c in checks if c.rule == rule).status is not Status.NA

    for rule in rules.RULES:
        assert any(applies(rule, s) for s in SCENARIOS), rule


def _passing_answer(s: Scenario) -> Transcript:
    """A plausible good answer, standing in for the model."""
    urgent = rules.danger(s)
    steps = ["Call 112", "Get behind the barrier"] if urgent else ["Get behind the barrier", "Wait"]
    output = validate_output(answer_json(urgent=urgent, steps=steps), allow_ask=False)
    return Transcript((Turn(1.0, output, provider="fake", model="m"),))


async def test_show_all_prints_every_conversation_passing_ones_too() -> None:
    results = await run_all(ScriptedProvider(answer_json()), [SCENARIO], budget_s=10)
    quiet = report(results, budget_s=10, prompt_version="v2", date="2026-11-11")
    loud = report(results, budget_s=10, prompt_version="v2", date="2026-11-11", show_all=True)
    assert "A puncture in the rear left tyre" not in quiet
    assert "### Conversations" in loud
    assert "#### noise · pass" in loud
    assert "A puncture in the rear left tyre" in loud
