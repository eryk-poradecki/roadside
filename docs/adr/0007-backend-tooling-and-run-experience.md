# Backend tooling, quality gates and run experience

The backend is a uv project on Python 3.14, laid out layer-first. Quality is checked in three places that run the same tools: a formatting hook for agents, `pre-commit` for every commit, and GitHub Actions for every PR. `docker compose up` runs a production-like stack in demo mode with no keys and no `.env`. Local development runs the API and the frontend as two plain processes. Each choice is the simplest one that still shows the practice reviewers look for. Part of that is AI workflow, which weighs as much as the app, so the agents get the same gates as a human.

## Considered Options

- **pip + `requirements.txt` only.** Everyone knows it, but it has no real lock and no Python version management. **Poetry.** Slower, and less common now than uv. Chosen: **uv** (`pyproject.toml` + `uv.lock`). Reviewers without uv still get a pip path with the same pinned versions (see Consequences).
- **`requires-python = ">=3.14"`.** One version everywhere. Rejected: a reviewer on system Python 3.13 with no uv would be blocked, and nothing here needs 3.14-only syntax. Chosen: `>=3.13`, with 3.14 used in `.python-version`, Docker and CI.
- **Feature-first layout** (`app/incidents/{router,service,repository}.py`). It scales better, but with two or three aggregates it hides the routers → services → repositories layering that reviewers grade. Chosen: **layer-first and mostly flat**, one module per aggregate in each layer.
- **pyright / basedpyright.** Faster, with better inference. Rejected in favour of **mypy `--strict`** with the first-party pydantic plugin, the checker reviewers know best.
- **lefthook**, or **CI only with no git hooks.** lefthook covers Python and JS with one tool, but `pre-commit` is the standard in Python and has ready-made hooks for ruff, secrets and `uv export`. CI only would catch formatting noise too late.
- **mypy and tests in the pre-commit hook.** Rejected: too slow per commit. They run in CI and in `make check`.
- **Starlette `TestClient`.** Sync, and it runs the app in a portal thread. Rejected: every layer is `async` over aiosqlite (ADR 0006), so tests use `httpx.AsyncClient` + `ASGITransport` on the same event loop as their fixtures. **pytest-asyncio** rejected in favour of anyio's built-in pytest plugin (no extra dependency).
- **A coverage threshold.** Rejected: it encourages tests written for the number. Coverage is reported only.
- **Body limits only in the reverse proxy.** Rejected: the app must hold without nginx too (local dev, tests).
- **Rate limiting.** Rejected for the MVP: the public deploy runs in demo mode and makes no paid or third-party calls (ADR 0004). It's a README follow-up for a live-LLM deploy.
- **Structured JSON logs (structlog).** Rejected: a single-process demo has no log pipeline to feed.
- **Compose running dev servers with hot reload**, or **both, as profiles.** Rejected: the README has to document the manual path for API and frontend anyway (task requirement), so compose stays production-like and dev stays native.
- **One root `.env`** shared by both apps. Rejected: per-app env files keep each app runnable on its own, and frontend env vars are public build-time values anyway.
- **No task runner**, or **`just`.** `just` is one more install. Chosen: a small **Makefile**. Each target is one or two plain commands, and the README lists the raw commands as well, because Make isn't on Windows by default.
- **`fastapi run`.** Rejected: plain `uvicorn --factory app.main:create_app --workers 1` makes the one-worker constraint visible in the command (ADR 0005's in-process turn lock).
- **Dependabot** and **CI path filters.** Rejected as noise for a six-day project; CI is fast.

## Consequences

### Packaging

- Runtime deps go in `[project.dependencies]`. Dev deps go in a PEP 735 `[dependency-groups] dev`.
- The `uv-export` pre-commit hook writes `backend/requirements.txt` (runtime) and `backend/requirements-dev.txt` from `uv.lock`, and CI fails if they drift. The pip path is `python -m venv .venv`, then `pip install -r requirements-dev.txt -e .`.
- ruff `target-version = "py313"` keeps the code valid on the floor version.

### Layout

```
backend/
  app/
    main.py          # create_app(settings): app factory, lifespan runs migrations
    deps.py          # FastAPI dependencies (connection, repositories, providers)
    settings.py
    routers/  services/  repositories/  schemas/  domain/
    integrations/llm/  integrations/osm/
    db/              # connection, migrate (python -m app.db migrate)
  migrations/NNNN_<name>.sql
  tests/{api,services,repositories,integrations}/
```

### Lint, format, types

- ruff does both lint and format, with line length 100 and rules `E,F,W,I,UP,B,SIM,ASYNC,RUF,PT,S`. `S` (bandit) is there mainly to flag SQL built from strings, which matters with plain SQL (ADR 0006).
- `per-file-ignores` for `tests/**` turns off the `S` rules that only make sense in production code. That's `S101` (assert), `S105`/`S106` (hard-coded "passwords" such as fake API keys), `S108` (temp paths) and `S311` (non-crypto random). Add others only when a test really needs them.
- mypy runs `--strict` with `pydantic.mypy`.

### Hooks

- **`pre-commit`:**
  - ruff check `--fix`, ruff format;
  - end-of-file, trailing whitespace, check-yaml/toml;
  - `detect-private-key`;
  - a large-file guard set high enough for the demo video;
  - `uv-export`;
  - the frontend linters as local hooks, once the frontend ADR fixes them.
- **Agent hook:** one formatting-only script in `.claude/hooks/`, called from `PostToolUse` in both `.claude/settings.json` and `.codex/hooks.json`, next to the Impeccable hooks. It formats the edited `.py` file with ruff (and later TS with prettier). It never fails the tool call.

### CI (GitHub Actions)

- One `ci.yml` with parallel jobs:
  - **backend:** `uv sync --locked`, ruff check, ruff format `--check`, mypy, pytest with `pytest-cov` (report only), the requirements drift check;
  - **frontend:** `npm ci`, lint, typecheck, test, build;
  - **openapi-drift:** export `openapi.json`, regenerate the TS types and fail on a diff, which is the guarantee ADR 0005 relies on;
  - **docker:** `docker compose build`, on `main` and on PRs that touch Docker files;
  - **e2e:** the Playwright smoke test (below), once it exists.
- **Follow-up (ready-for-human, part of the CI ticket):** once `ci.yml` exists, make its `backend` and `frontend` jobs required status checks in the `main` branch ruleset. The ruleset already requires a PR and blocks force pushes and deletions.

### Tests

- Fixture chain: `settings` (temp DB file and upload dir, ADR 0006) → `app = create_app(settings)` → `client`. `ASGITransport` doesn't run the lifespan, so the fixture calls the same migrate function itself.
- External services (LLM, Overpass, Nominatim) are swapped for Protocol fakes through `app.dependency_overrides`. `respx` is used only in the adapter tests that check the HTTP clients themselves.
- **Playwright smoke test** (second in the cut order): one test of the core flow (tile → Get help now → checklist → AI answer → incident in History), against demo mode (uvicorn + `vite preview`) in CI. It's deterministic and needs no keys. It gets its own late ticket.

### Safety

- An ASGI middleware rejects bodies above ~12 MB with a 413 problem response (ADR 0005 format). It checks `Content-Length` and stops a streamed body once it passes the cap. nginx `client_max_body_size 12m` is a second layer. The 10 MB per-photo check (ADR 0002) stays in the photo endpoint.
- Every free-text field (note, reply, vehicle text fields) has a Pydantic `max_length`.
- `LLM_API_KEY` is a `SecretStr`. `.env` is gitignored, and only `.env.example` files are committed.
- CORS comes from `FRONTEND_ORIGINS` (ADR 0005).

### Config

- `backend/.env.example` → `backend/.env`. pydantic-settings reads it locally, and compose loads it through an optional `env_file`. `frontend/.env.example` holds `VITE_API_BASE_URL`.
- One flat `Settings` class with the names from ADRs 0002, 0004–0006, validated at startup (fail fast). Settings added by this ADR:
  - `LLM_PROVIDER = openai_compatible | cli`, read only when `DEMO_MODE=false`. `cli` checks at startup that the `claude` binary exists. The Docker image doesn't contain it, so `CLIProvider` can't ship by accident (ADR 0004).
  - `OVERPASS_URLS`: comma-separated, primary first, then mirrors.
  - `NOMINATIM_URL`, `OSM_USER_AGENT` (ADR 0004).
  - `LOG_LEVEL`.

### Logging

- stdlib `logging`, plain text, one access line per request.
- Never logged at INFO: the API key, prompts, notes, replies, coordinates. A turn logs provider, model, latency and outcome `reason`; prompts only at DEBUG. This backs up the README privacy note (ADR 0004).

### Run experience

- **`docker compose up`** → http://localhost:8080 in demo mode with no `.env`:
  - `backend`: multi-stage image (uv builder → slim runtime), non-root user, `uvicorn --factory app.main:create_app --workers 1 --proxy-headers`, `HEALTHCHECK` on `GET /health`, one named volume for `DATABASE_PATH` and `UPLOAD_DIR`;
  - `web`: nginx serving the Vite build and proxying `/api` on the same origin, `depends_on` the backend being healthy.
- **Local dev:** two processes, `uv run uvicorn … --reload` (or `make dev-api`) and `npm run dev` (or `make dev-web`). The frontend calls `http://localhost:8000` across origins, so the real CORS path is used.
- **Makefile:** `help` (default), `install` (uv sync + npm ci + pre-commit install), `dev-api`, `dev-web`, `lint`, `format`, `typecheck`, `test`, `e2e`, `openapi`, `migrate`, `up`/`down`, `check`. `make check` runs everything CI runs. `AGENTS.md` names it as the gate before opening a PR, and lists the commands in a "Commands" section.
- What the Pi + Cloudflare Tunnel deploy adds on top is still open (Deploy specifics on the map).
