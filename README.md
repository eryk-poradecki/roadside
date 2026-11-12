# Roadside

A roadside assistant for drivers: immediate safety steps, recorded AI advice,
nearby places, vehicles and incident history.

## Technology

The separated Python/FastAPI backend uses SQLite, startup migrations and a REST
API. The React/TypeScript frontend uses Vite, TanStack Query and Leaflet, with a
client generated from OpenAPI. nginx provides a single origin in Docker. Demo mode
replays recorded AI answers without a model or API key; live mode supports an
OpenAI-compatible model. Safety checklists remain available alongside AI advice.

## Run locally

For the quickest demo, install Docker Engine with Compose, then run:

```sh
docker compose up --build
```

Open <http://localhost:8080>. No keys or environment files are needed in a fresh
checkout. Stop with `docker compose down`; the local SQLite volume is retained.
An existing `backend/.env` can change local demo settings.

For development, install Python 3.14, uv, Node.js 24.15 or newer, npm and Make:

1. From the repository root, run `make install`.
2. Copy `backend/.env.example` to `backend/.env`, keeping `DEMO_MODE=true` for
   key-free replay. The example explains live-model settings too.
3. Run `make migrate`, then `make dev-api`. The API is at <http://localhost:8000>
   and interactive API documentation at <http://localhost:8000/docs>.
4. In another terminal at the repository root, run `make dev-web` and open
   <http://localhost:5173>. The default CORS origin permits this frontend.
5. Run `make check` for lint, typechecking, tests, build and generated-client drift.

For the browser smoke test, run `cd frontend && npx playwright install --with-deps chromium`
once, then `make e2e` from the repository root (Docker Compose 2.24.4+ required).
It builds a separate disposable demo stack on <http://localhost:18080>, runs the
recorded parked-battery scenario through History, then removes the stack. It ignores
`backend/.env`, uses temporary data, and blocks external traffic from the backend and
browser. CI runs the same target in its `e2e` job; failure traces and screenshots
are in `frontend/test-results/`.

## AI development workflow

The repository includes shared instructions for Codex and Claude Code in
[AGENTS.md](AGENTS.md), project skills and architectural decisions in `docs/adr/`.
Agents use GitHub issues as implementation specs, run checks and review changes
against both the spec and repository standards. For example, the prompt
`$implement issue #72` drove the public-demo deployment configuration and runbook.
The `/record-replays` and `/demo-check` workflows record and review real model
answers, then verify the demo scenarios. See [demo scenarios](docs/demo-scenarios.md).

## Live demo

**URL: to be added before deployment.** Available during the review period.

- AI answers are pre-recorded and follow fixed scenarios.
- Photo uploads are refused; only bundled sample photos can be attached.
- Anything entered is held in memory only and wiped nightly. This is a shared demo.
- In demo mode, the server calls neither Overpass nor Nominatim. The browser loads
  map tiles directly from OpenStreetMap's standard tile servers, so the OpenStreetMap
  Foundation sees your IP address and the map area you view.
- It runs on a home Raspberry Pi and may sometimes be offline.

Deployment and updates: [Pi runbook](docs/deploy.md).
