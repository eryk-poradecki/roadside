"""Run the AI turn evals against the configured live provider (ADR 0004, #64).

    cd backend && uv run python -m scripts.eval_assist [--scenario ID ...] [--out FILE]

Run by hand, never in CI or `make check`: it calls a real model and costs time or quota. It
reads the same settings as the app (`backend/.env` and the environment) and needs
`DEMO_MODE=false`; recording is turned off for the run. Progress goes to stderr, and the
Markdown report (paste it into AI_USAGE) to stdout. Exits 1 when any rule fails.
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.assist.prompt import PROMPT_VERSION
from app.integrations.llm.factory import build_provider
from app.settings import Settings
from scripts.evals.run import ScenarioResult, report, run_all
from scripts.evals.scenarios import SCENARIOS


def _progress(result: ScenarioResult) -> None:
    t = result.transcript
    seconds = sum(turn.seconds for turn in t.turns)
    verdict = "pass" if result.passed else "FAIL " + ", ".join(c.rule for c in result.failed)
    print(f"  {result.scenario.id}: {verdict} ({seconds:.1f} s)", file=sys.stderr, flush=True)


async def _main(args: argparse.Namespace) -> int:
    scenarios = [s for s in SCENARIOS if not args.scenario or s.id in args.scenario]
    unknown = set(args.scenario or ()) - {s.id for s in SCENARIOS}
    if unknown:
        print(f"Unknown scenario: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    try:
        settings = Settings()
    except ValidationError as exc:
        print(f"Invalid settings: {exc}", file=sys.stderr)
        return 2
    if settings.demo_mode:
        print(
            "Evals need a live model: set DEMO_MODE=false and the LLM_* settings.", file=sys.stderr
        )
        return 2
    budget_s = settings.llm_turn_budget_s
    provider = build_provider(settings.model_copy(update={"llm_record": False}))
    print(
        f"Running {len(scenarios)} scenarios on {provider.name} / {settings.llm_model}"
        f" (prompt {PROMPT_VERSION}, budget {budget_s:.0f} s)",
        file=sys.stderr,
        flush=True,
    )
    try:
        results = await run_all(provider, scenarios, budget_s=budget_s, on_result=_progress)
    finally:
        await provider.aclose()
    text = report(
        results, budget_s=budget_s, prompt_version=PROMPT_VERSION, date=date.today().isoformat()
    )
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if all(r.passed for r in results) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--scenario",
        action="append",
        metavar="ID",
        help="run only this scenario (repeatable); see --list",
    )
    parser.add_argument("--list", action="store_true", help="list the scenario ids and exit")
    parser.add_argument("--out", type=Path, help="also write the Markdown report to this file")
    args = parser.parse_args()
    if args.list:
        print("\n".join(s.id for s in SCENARIOS))
        return
    sys.exit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
