# Kickoff notes — decisions so far (input for grill-with-docs)

Recruitment task for Xelerit: small full-stack MVP related to transport. Deadline: **15 Nov 2026, 23:59**. Submit: public GitHub repo link + full name to recruitment@xeler.it.

## Product (working name: "Roadside")

Roadside assistant for drivers. Primary moment: stranded on the roadside (often at night, stressed, one hand). Secondary: at home on desktop, reviewing incidents and finishing damage reports. Details: `PRODUCT.md`, `DESIGN.md`.

**Core flow (must work end-to-end):** pick problem tile → bottom sheet (optional photo/text) → "Get help now" → static non-AI safety checklist shown immediately while AI loads → AI diagnosis + steps + nearby places → save as incident.

## Confirmed decisions

- **Backend:** Python + FastAPI, SQLite. Layered: routers → services → repositories. Pydantic schemas. CORS configured.
- **Frontend:** React + Vite + TypeScript, responsive / mobile-first PWA. i18n (PL/EN) from day one via react-i18next. Map: Leaflet + OpenStreetMap.
- **Entities (CRUD):** `Vehicle` (model, tyre size, spare wheel, wheel lock key, assistance insurance) and `Incident` (type, description, photo, location, status, AI response).
- **AI:** one agent with 2–3 tools: `get_vehicle_profile`, `find_nearby(category)` (OSM Overpass), optionally `draft_damage_report`.
- **LLM providers (behind an `LLMProvider` interface):**
  - `OpenAICompatibleProvider` — Ollama locally (main PC, RTX 4060) or a free-tier API; configured via `.env`.
  - `ReplayProvider` — replays recorded real responses; default when no key is configured, so the app always runs.
  - Stretch: `CLIProvider` (Claude Code / Codex headless) — dev-only, for recording demo scenarios; never deployed.
- **Tools exposed via an MCP server** (stretch, but high value): same tools serve the in-app agent and Claude Code.
- **Deploy (bonus, weekend):** Raspberry Pi 5 + Cloudflare Tunnel, subdomain on own domain, demo/replay mode only. docker-compose from day one.
- **UI prototype:** done with Impeccable (init → shape → build → critique → bolder) in a test folder; Start screen to be moved into `frontend/`.

## AI workflow (evaluated as much as the app)

- Process skills: Matt Pocock's skills (grill-with-docs, wayfinder, TDD), vendored into the repo with attribution + license, each with a note on why and what was changed.
- Design skills: Impeccable (frontend only). No `/prototype` — avoid mixing two design systems.
- 1–2 own project-specific skills/commands (e.g. `/add-agent-tool`, `/demo-check`).
- `CLAUDE.md` + `AI_USAGE.md` kept up to date during work (tools, prompts, what worked / what didn't).
- Model split: Fable for grilling, wayfinder, architecture; standard model for implementation. Save the Fable limit reset for the weekend.

## Working conventions

- **Git flow:** `main` is always working. Every ticket goes on its own branch (e.g. `feat/vehicle-crud`, `fix/...`, `docs/...`) and is merged through a pull request that links its issue. Conventional Commits for commit messages.
- **Existing UI prototype:** the mobile Start screen (tile → bottom sheet → checklist/loading → result stub) was already prototyped and critiqued with Impeccable in `../impeccable_testing` (React + Vite + TS, mocked data). It gets moved into `frontend/` once the frontend structure is decided; it should not be re-prototyped from scratch.
- **Thoroughness:** reviewers judge architecture, code quality, API design and AI workflow. For each decision that's visible to a reviewer, the planning should name the realistic options, weigh them against the MVP scope and the 15 Nov deadline, and record the reasoning so it can be explained in the interview. Prefer the simplest option that still shows good practice.

## Decisions to weigh (candidate grilling tickets)

- **Data access:** ORM (SQLAlchemy / SQLModel) vs. plain SQL via `sqlite3` behind a repository layer. The job ad lists SQL as a requirement, so hand-written SQL shows it directly; an ORM is the more standard choice. A repository interface makes either swappable.
- **Schema management:** a plain `schema.sql` run at startup vs. migrations (Alembic).
- **API conventions:** resource naming, `/api/v1` prefix, status codes, error response format (e.g. RFC 7807 problem details), DTOs separate from DB models.
- **Shared types FE/BE:** generate a TypeScript client or types from FastAPI's OpenAPI schema vs. hand-written types.
- **Frontend data layer:** TanStack Query vs. plain `fetch` + state; routing (React Router); styling approach (keep whatever the prototype uses unless there's a reason).
- **Quality tooling:** ruff + type checker (mypy / pyright), ESLint + Prettier, pre-commit hooks, a GitHub Actions CI workflow running lint + tests.
- **Testing:** pytest + FastAPI TestClient; Vitest + React Testing Library; optionally one Playwright smoke test of the core flow.
- **Python tooling:** uv vs. pip + requirements.txt; config via pydantic-settings + `.env.example`.
- **AI design:** structured JSON output with a schema, prompts as versioned files, tool definitions, timeouts/retries, and a guarantee that places shown to the user come only from OSM data, never from the model.
- **Basic safety:** upload size/type limits, CORS restricted to the frontend origin, no secrets in the repo.
- **Run experience:** one-command start via docker-compose, plus the manual steps the task requires in the README.

## Out of scope (README roadmap)

Auth / multi-user, public transport suggestions, taxi / fuel delivery integrations, offline incident queue, separate community pothole map, towing services in Nearby (name heuristics or a curated list; towing has no settled OSM tag, ADR 0004, #106).

## Open questions for grilling

1. Photo storage: filesystem folder + path in SQLite? Size limits?
2. Does the LLM need vision (photo analysis) in MVP, or is the photo only stored on the incident?
3. Exact `Incident` statuses and lifecycle.
4. Is the damage report (pothole) MVP or stretch?
5. API endpoint list and shape of the AI response (structured JSON: diagnosis, steps, confidence, nearby).
6. Checklist content per tile: where it lives (frontend static vs backend), and review of the copy.
7. Final product name.

## Schedule

- **Tue (Medikinet):** grilling → wayfinder issues → repo setup → backend skeleton + first vertical slice.
- **Wed–Thu (no meds, lighter):** execute small issues, i18n, checklist content. **Checkpoint Wed evening:** core flow works end-to-end, otherwise cut scope.
- **Fri (psychiatrist in the morning, Medikinet):** AI agent + tools, integration. Pharmacy right after the visit.
- **Sat–Sun:** polish, README, AI_USAGE, demo video (with subtitles), deploy, submit.
