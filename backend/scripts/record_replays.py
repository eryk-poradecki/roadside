"""Record the demo scenarios against the configured live provider (ADR 0004, #63).

    cd backend && uv run python -m scripts.record_replays [--scenario ID ...] [--fresh]
        [--prune] [--choices FILE] [--out FILE]

Run by hand through the `/record-replays` skill, never in CI: it calls a real model, Nominatim
and Overpass. It reads the app's settings (`backend/.env` and the environment) and needs
`DEMO_MODE=false` and `LLM_RECORD=true`; it writes to `LLM_RECORDINGS_DIR`. The database is a
throwaway one. Progress goes to stderr, and the Markdown review of every walk to stdout.
Exits 1 when a walk is incomplete (a failure, or a question waiting for a choice) or the
privacy scan finds something.
"""

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.assist.prompt import PROMPT_VERSION
from app.db.migrate import migrate
from app.main import create_app
from app.settings import Settings
from scripts.demo.record import load_choices, record
from scripts.demo.report import review_markdown
from scripts.demo.scenarios import load_scenarios

CHOICES = Path("recordings/branches/choices.json")


async def _main(args: argparse.Namespace) -> int:
    scenarios = load_scenarios()
    unknown = set(args.scenario or ()) - {s.id for s in scenarios}
    if unknown:
        print(f"Unknown scenario: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    selected = [s for s in scenarios if not args.scenario or s.id in args.scenario]
    try:
        settings = Settings()
    except ValidationError as exc:
        print(f"Invalid settings: {exc}", file=sys.stderr)
        return 2
    if settings.demo_mode or not settings.llm_record:
        print("Recording needs DEMO_MODE=false and LLM_RECORD=true.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="record-replays-") as tmp:
        run_settings = settings.model_copy(
            update={"database_path": Path(tmp) / "record.db", "upload_dir": Path(tmp) / "uploads"}
        )
        migrate(run_settings.database_path)
        app = create_app(run_settings)
        print(
            f"Recording {len(selected)} scenarios with {settings.llm_provider} /"
            f" {settings.llm_model or 'default model'} (prompt {PROMPT_VERSION}) into"
            f" {settings.llm_recordings_dir}",
            file=sys.stderr,
            flush=True,
        )
        async with app.router.lifespan_context(app):
            run = await record(
                app,
                app.state.llm_provider,
                settings.llm_recordings_dir,
                selected,
                load_choices(args.choices),
                fresh=args.fresh,
                full_run=not args.scenario,
            )
    if args.prune and not run.ok:
        print(
            "Not pruning: a walk is incomplete, so its later recordings look unreached.",
            file=sys.stderr,
        )
    elif args.prune:
        for path in run.orphans:
            path.unlink()
            print(f"pruned {path}", file=sys.stderr)
    text = review_markdown(run)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if run.ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--scenario", action="append", metavar="ID", help="walk only this scenario (repeatable)"
    )
    parser.add_argument(
        "--fresh", action="store_true", help="ask the model again even where a recording exists"
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="delete the recordings no walk reached (a full run only)",
    )
    parser.add_argument(
        "--choices",
        type=Path,
        default=CHOICES,
        help=f"the reviewed option for each branch intent (default {CHOICES})",
    )
    parser.add_argument("--out", type=Path, help="also write the Markdown review to this file")
    sys.exit(asyncio.run(_main(parser.parse_args())))


if __name__ == "__main__":
    main()
