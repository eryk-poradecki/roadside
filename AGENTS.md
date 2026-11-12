# AGENTS.md

Shared instructions for coding agents (Claude Code, Codex, others) working in this repo.

**Task requirements:** [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Every "Required" item must be met; check plans and PRs against it.

Prototype branches (`prototype/*`) are reference-only: they get a **draft** PR marked "do not merge", linked to their wayfinder ticket, and are closed (not merged, not deleted) once the build ticket that replaces them is merged.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `eryk-poradecki/roadside`, driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Demo recordings

What demo mode replays lives in `backend/recordings/`, made from `docs/demo-scenarios.md`. Two user-invoked project skills cover it:

- `/record-replays` records the scenarios against a live model on the owner's machine, reviews every recording against its good/bad examples, and commits only approved ones. Run it after any change to the prompt, the replay key or a scenario.
- `/demo-check` starts the stack in demo mode and walks every scenario, failing on any replay miss.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

Triage label vocabulary: [docs/agents/triage-labels.md](docs/agents/triage-labels.md)

## External requests

- When an agent makes HTTP requests to third-party services itself (research, API checks, curl), it uses a **generic User-Agent** (e.g. `research-agent/1.0`). Never include personal data, emails, usernames, repo names or other identifiers in request headers, URLs or payloads.
- The **application's** own User-Agent for OSM services (Overpass, Nominatim) is a product decision, recorded in an ADR. Use the value from the ADR. Don't invent one.

## Commands

- **`make check` is the gate before opening a PR.** CI (`.github/workflows/ci.yml`) runs the same targets (`check-backend`, `check-frontend`, `openapi-drift`): backend ruff, mypy strict, pytest, requirements drift; frontend eslint, prettier, tsc, vitest, build; and the OpenAPI drift check (`make openapi-drift`, which regenerates `frontend/openapi.json` and `frontend/src/api/generated/` and fails on a diff, so commit what it writes). CI also runs `make docker-smoke` (builds and starts the compose stack); it needs Docker, so it isn't part of `make check`: run it yourself when you touch a Dockerfile, `compose.yaml` or the nginx config.
- `make install` installs both apps' dependencies and the git `pre-commit` hook. `make pre-commit` runs every hook on all files.
- `pre-commit` runs on each commit: ruff, file hygiene, private-key detection, a large-file guard, `uv export` to `backend/requirements*.txt`, prettier and eslint on frontend files. mypy, tsc and tests are left to `make check` and CI. Never skip hooks with `--no-verify`.
- Agent hook: after every Edit/Write/apply_patch, `.claude/hooks/format.py` formats the edited file (ruff for `backend/`, prettier for `frontend/`) for Claude Code and Codex. It never fails, so it doesn't report lint or type errors: run `make check` for those.
- `make help` lists the rest (`dev-api`, `dev-web`, `migrate`, `format`, `openapi`, `requirements`).
