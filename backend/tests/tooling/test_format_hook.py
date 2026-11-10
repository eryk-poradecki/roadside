"""The agent format hook (.claude/hooks/format.py), driven the way Claude Code and Codex call it."""

import json
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / ".claude" / "hooks" / "format.py"

MESSY_PY = "import os\nx = {  'a':1 }\n"
CLEAN_PY = 'import os\n\nx = {"a": 1}\n'


def run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        check=False,
    )


def claude_payload(path: Path) -> str:
    return json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(REPO),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(path), "old_string": "a", "new_string": "b"},
        }
    )


def codex_patch_payload(patch: str) -> str:
    return json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "cwd": str(REPO),
            "tool_name": "apply_patch",
            "tool_input": {"command": patch},
        }
    )


@pytest.fixture
def scratch_dir() -> Iterator[Path]:
    """A throwaway directory inside backend/, where the hook formats Python."""
    path = REPO / "backend" / f".hook-test-{uuid.uuid4().hex}"
    path.mkdir()
    yield path
    shutil.rmtree(path)


def test_formats_python_file_edited_by_claude(scratch_dir: Path) -> None:
    target = scratch_dir / "messy.py"
    target.write_text(MESSY_PY)

    result = run_hook(claude_payload(target))

    assert result.returncode == 0
    assert target.read_text() == CLEAN_PY


def test_formats_files_added_and_updated_by_codex_patch(scratch_dir: Path) -> None:
    added = scratch_dir / "added.py"
    updated = scratch_dir / "updated.py"
    added.write_text(MESSY_PY)
    updated.write_text(MESSY_PY)
    rel = scratch_dir.relative_to(REPO)
    patch = (
        "*** Begin Patch\n"
        f"*** Add File: {rel}/added.py\n"
        "+import os\n"
        f"*** Update File: {rel}/updated.py\n"
        "@@\n"
        "-x = 1\n"
        "+x = 2\n"
        f"*** Delete File: {rel}/gone.py\n"
        "*** End Patch\n"
    )

    result = run_hook(codex_patch_payload(patch))

    assert result.returncode == 0
    assert added.read_text() == CLEAN_PY
    assert updated.read_text() == CLEAN_PY


def test_ignores_patch_headers_inside_content_claude_writes(scratch_dir: Path) -> None:
    bystander = scratch_dir / "bystander.py"
    bystander.write_text(MESSY_PY)
    written = scratch_dir / "notes.md"
    content = f"*** Update File: {bystander.relative_to(REPO)}\n"
    written.write_text(content)
    payload = json.dumps(
        {
            "cwd": str(REPO),
            "tool_name": "Write",
            "tool_input": {"file_path": str(written), "content": content},
        }
    )

    result = run_hook(payload)

    assert result.returncode == 0
    assert bystander.read_text() == MESSY_PY


def test_leaves_virtualenv_files_alone(scratch_dir: Path) -> None:
    target = scratch_dir / ".venv" / "lib" / "dep.py"
    target.parent.mkdir(parents=True)
    target.write_text(MESSY_PY)

    result = run_hook(claude_payload(target))

    assert result.returncode == 0
    assert target.read_text() == MESSY_PY


def test_leaves_python_outside_backend_alone(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.py"
    target.write_text(MESSY_PY)

    result = run_hook(claude_payload(target))

    assert result.returncode == 0
    assert target.read_text() == MESSY_PY


def test_does_not_fail_on_a_file_ruff_cannot_parse(scratch_dir: Path) -> None:
    target = scratch_dir / "broken.py"
    target.write_text("def (:\n")

    result = run_hook(claude_payload(target))

    assert result.returncode == 0
    assert result.stdout == ""
    assert target.read_text() == "def (:\n"


@pytest.mark.parametrize("stdin", ["", "not json", "[]", '{"tool_input": 5}'])
def test_never_fails_on_unexpected_input(stdin: str) -> None:
    result = run_hook(stdin)

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.skipif(
    not (REPO / "frontend" / "node_modules" / ".bin" / "prettier").exists(),
    reason="frontend dependencies not installed",
)
def test_formats_frontend_file_with_prettier() -> None:
    scratch = REPO / "frontend" / f".hook-test-{uuid.uuid4().hex}"
    scratch.mkdir()
    try:
        target = scratch / "messy.ts"
        target.write_text('const a = {b:"c"};\n')

        result = run_hook(claude_payload(target))

        assert result.returncode == 0
        assert target.read_text() == "const a = { b: 'c' }\n"
    finally:
        shutil.rmtree(scratch)
