# AGENTS.md

Shared instructions for coding agents (Claude Code, Codex, others) working in this repo.

**Task requirements:** [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). Every "Required" item must be met; check plans and PRs against it.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `eryk-poradecki/roadside`, driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

Triage label vocabulary: [docs/agents/triage-labels.md](docs/agents/triage-labels.md)
