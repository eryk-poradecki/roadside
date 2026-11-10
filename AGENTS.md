# AGENTS.md

Shared instructions for coding agents (Claude Code, Codex, others) working in this repo.

**Task requirements:** [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Every "Required" item must be met; check plans and PRs against it.

Prototype branches (`prototype/*`) are reference-only: they get a **draft** PR marked "do not merge", linked to their wayfinder ticket, and are closed (not merged, not deleted) once the build ticket that replaces them is merged.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `eryk-poradecki/roadside`, driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

Triage label vocabulary: [docs/agents/triage-labels.md](docs/agents/triage-labels.md)

## External requests

- When an agent makes HTTP requests to third-party services itself (research, API checks, curl), it uses a **generic User-Agent** (e.g. `research-agent/1.0`). Never include personal data, emails, usernames, repo names or other identifiers in request headers, URLs or payloads.
- The **application's** own User-Agent for OSM services (Overpass, Nominatim) is a product decision, recorded in an ADR. Use the value from the ADR. Don't invent one.

## Commands

`make check` runs everything CI runs for the backend (ruff lint and format check, mypy strict, pytest, requirements drift check). It is the gate before opening a PR. Run `make help` for the rest (`install`, `dev-api`, `migrate`, `format`, `requirements`).
