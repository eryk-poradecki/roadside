"""Run scenarios against a provider and report the rule checks as Markdown (#64).

Each scenario plays a whole conversation through the app's own turn pipeline (prompt, call,
validation, one repair): questions are answered with the scenario's scripted replies, then
skipped, and the cap of two questions narrows the schema exactly as the service does.
Scenarios run one at a time, so the timings aren't skewed by sharing a local GPU.
"""

import asyncio
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.assist.contract import TurnOutput
from app.assist.prompt import Exchange
from app.domain.ai_turn import Reply
from app.integrations.llm.base import LLMProvider, ProviderError
from app.services.assistant import MAX_QUESTIONS, generate_turn
from app.services.model_call import InvalidOutputError, problem_for
from scripts.evals.model import Scenario, Transcript, Turn
from scripts.evals.rules import RULES, Check, Status, check_all


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario: Scenario
    transcript: Transcript
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(c.status is not Status.FAIL for c in self.checks)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status is Status.FAIL]


async def run_scenario(provider: LLMProvider, s: Scenario, *, budget_s: float) -> Transcript:
    turns: list[Turn] = []
    exchanges: list[Exchange] = []
    replies = list(s.replies)
    skipped = False
    while True:
        allow_ask = len(exchanges) < MAX_QUESTIONS and not skipped
        started = time.monotonic()
        try:
            async with asyncio.timeout(budget_s):
                output, result = await generate_turn(
                    provider, s.inputs, s.locale, allow_ask=allow_ask, exchanges=tuple(exchanges)
                )
        except (TimeoutError, ProviderError, InvalidOutputError) as exc:
            turns.append(Turn(time.monotonic() - started, error=problem_for(exc).reason))
            return Transcript(tuple(turns))
        seconds = time.monotonic() - started
        turns.append(Turn(seconds, output, provider=result.provider, model=result.model))
        if output.ask is None:
            return Transcript(tuple(turns))
        reply = replies.pop(0) if replies else Reply(skip=True)
        skipped = reply.skip
        exchanges.append(Exchange(question=output.ask.question, reply=reply))


async def run_all(
    provider: LLMProvider,
    scenarios: Iterable[Scenario],
    *,
    budget_s: float,
    on_result: Callable[[ScenarioResult], None] | None = None,
) -> list[ScenarioResult]:
    results = []
    for s in scenarios:
        transcript = await run_scenario(provider, s, budget_s=budget_s)
        result = ScenarioResult(s, transcript, check_all(s, transcript, budget_s=budget_s))
        if on_result is not None:
            on_result(result)
        results.append(result)
    return results


def _row(cells: Iterable[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _table(header: list[str], rows: Iterable[Iterable[object]]) -> list[str]:
    return [_row(header), _row("---" for _ in header), *(_row(r) for r in rows)]


def _output_lines(output: TurnOutput) -> list[str]:
    if output.ask is not None:
        ask = output.ask
        return [
            f"- asked: {ask.question} (now: {ask.now}; options: {' / '.join(ask.options)})",
        ]
    if output.answer is None:  # pragma: no cover - TurnOutput guarantees one block
        return []
    a = output.answer
    lines = [f"- answer (urgent: {str(output.urgent).lower()}): {a.cause}"]
    lines += [f"  {n}. {step}" for n, step in enumerate(a.steps, start=1)]
    lines += [f"  - stop if: {cond}" for cond in a.escalate_if]
    if a.extra_categories:
        lines.append(f"  - extra categories: {', '.join(a.extra_categories)}")
    return lines


def report(
    results: list[ScenarioResult], *, budget_s: float, prompt_version: str, date: str
) -> str:
    """A Markdown report to paste into AI_USAGE: one row per scenario, one per rule, then the
    failing conversations in full."""
    # Every model that answered, in case the server routed some turns to another one.
    models = {
        f"{t.provider} / {t.model}": None for r in results for t in r.transcript.turns if t.model
    }
    who = ", ".join(models) or "unknown provider / unknown model"
    passed = sum(r.passed for r in results)
    lines = [
        f"## Evals · {who} · prompt {prompt_version} · {date}",
        "",
        f"Turn budget {budget_s:.0f} s. {passed}/{len(results)} scenarios passed.",
        "",
    ]
    lines += _table(
        ["Scenario", "Locale", "Questions", "Turn times (s)", "Result", "Failed rules"],
        (
            [
                r.scenario.id,
                r.scenario.locale,
                len(r.transcript.asks),
                " + ".join(f"{t.seconds:.1f}" for t in r.transcript.turns),
                "pass" if r.passed else "**fail**",
                ", ".join(c.rule for c in r.failed),
            ]
            for r in results
        ),
    )
    lines.append("")
    lines += _table(
        ["Rule", "Pass", "Fail", "n/a"],
        ([rule, *(_count(results, rule, status) for status in Status)] for rule in RULES),
    )
    failures = [r for r in results if not r.passed]
    if failures:
        lines += ["", "### Failures"]
    for r in failures:
        lines += ["", f"#### {r.scenario.id}", ""]
        lines += [f"- **{c.rule}**: {c.detail}" for c in r.failed]
        lines.append("")
        for turn in r.transcript.turns:
            if turn.output is not None:
                lines += _output_lines(turn.output)
            else:
                lines.append(f"- turn failed: {turn.error}")
    return "\n".join(lines) + "\n"


def _count(results: list[ScenarioResult], rule: str, status: Status) -> int:
    return sum(c.rule == rule and c.status is status for r in results for c in r.checks)
