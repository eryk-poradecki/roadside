"""Walk every demo scenario against a running demo-mode app and report any miss (#63).

    cd backend && uv run python -m scripts.demo_check [--base-url URL] [--choices FILE]

Used by the `/demo-check` skill after `docker compose up` (the default URL is its nginx on
:8080). It refuses an app that is not in demo mode, so it never calls a live model, and one
missing a seeded demo vehicle (#122), which a visitor could not pick either. The Markdown table
goes to stdout. Exits 1 when any walk hits `no_recording`, unrecorded places
or an invalid replay.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

from scripts.demo.check import DemoCheckFailed, NoDemoVehicle, NotDemoMode, check
from scripts.demo.record import load_choices
from scripts.demo.report import check_markdown
from scripts.demo.scenarios import load_scenarios
from scripts.record_replays import CHOICES


async def _main(args: argparse.Namespace) -> int:
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        try:
            walks = await check(client, load_scenarios(), load_choices(args.choices))
        except (DemoCheckFailed, NotDemoMode, NoDemoVehicle) as exc:
            print(f"{args.base_url}: {exc}", file=sys.stderr)
            return 2
        except httpx.HTTPError as exc:
            print(f"{args.base_url} is not reachable: {exc}", file=sys.stderr)
            return 2
    print(check_markdown(walks))
    return 0 if all(w.ok for w in walks) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--choices", type=Path, default=CHOICES)
    sys.exit(asyncio.run(_main(parser.parse_args())))


if __name__ == "__main__":
    main()
