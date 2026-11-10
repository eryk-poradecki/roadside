#!/usr/bin/env python3
"""Agent PostToolUse hook: format the files an agent just edited. Formatting only.

Called by Claude Code (.claude/settings.json) and Codex (.codex/hooks.json) after
Edit/Write/apply_patch. Reads the hook payload as JSON on stdin and formats:

- Python under backend/ with ruff (import sorting + format);
- files under frontend/ with prettier (it skips what .prettierignore lists).

It never fails the tool call: any problem (bad payload, missing tool, a file the
formatter can't parse, a timeout) is swallowed and the exit code is always 0.
Lint errors, types and tests are left to pre-commit, CI and `make check`.
Stdlib only, so it runs on any python3 without the backend's virtualenv.
"""

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
# Per formatter call; at most three calls, so the total stays under the 30 s hook timeout.
TIMEOUT_SECONDS = 8

# apply_patch headers for files that exist after the patch (not "*** Delete File:").
PATCH_PATH = re.compile(r"^\*\*\* (?:Add File|Update File|Move to): (.+?)\s*$", re.MULTILINE)


def edited_paths(payload: object) -> Iterator[Path]:
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    cwd = payload.get("cwd")
    base = Path(cwd) if isinstance(cwd, str) else ROOT

    # Claude Code Edit/Write/MultiEdit name the file directly. Their content may
    # quote patch headers, so it is never scanned.
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str):
        yield base / file_path
        return

    # Codex apply_patch: the patch text sits in a string field of tool_input.
    if payload.get("tool_name") != "apply_patch":
        return
    for value in tool_input.values():
        if isinstance(value, str):
            for match in PATCH_PATH.finditer(value):
                yield base / match.group(1)


# Third-party and build trees inside backend/ and frontend/ are never formatted.
SKIPPED_DIRS = {".venv", "node_modules", "dist", "__pycache__"}


def under(path: Path, directory: Path) -> bool:
    if not path.is_relative_to(directory):
        return False
    return not SKIPPED_DIRS.intersection(path.relative_to(directory).parts)


def run(args: list[str], cwd: Path) -> None:
    subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def ruff() -> str | None:
    local = BACKEND / ".venv" / "bin" / "ruff"
    return str(local) if local.exists() else shutil.which("ruff")


def prettier() -> str | None:
    local = FRONTEND / "node_modules" / ".bin" / "prettier"
    return str(local) if local.exists() else None


def format_files(paths: set[Path]) -> None:
    python = sorted(str(p) for p in paths if p.suffix == ".py" and under(p, BACKEND))
    web = sorted(str(p) for p in paths if under(p, FRONTEND))

    if python and (ruff_bin := ruff()):
        run([ruff_bin, "check", "--fix", "--select", "I", "--quiet", *python], cwd=BACKEND)
        run([ruff_bin, "format", "--quiet", *python], cwd=BACKEND)
    if web and (prettier_bin := prettier()):
        # cwd=frontend so prettier picks up frontend/.prettierignore.
        run([prettier_bin, "--write", "--ignore-unknown", "--log-level", "silent", *web], FRONTEND)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
        paths = {p.resolve() for p in edited_paths(payload)}
        format_files({p for p in paths if p.is_file()})
    except Exception:  # noqa: S110  # a formatter hook must never block the agent
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
