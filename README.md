<div align="center">

<img src="docs/assets/logo.svg" alt="Roadside" width="300">

**Calm, step-by-step help when your car lets you down, and a tidy record of it afterwards.**

[![CI](https://github.com/eryk-poradecki/roadside/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/eryk-poradecki/roadside/actions/workflows/ci.yml)
![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white)
![Node 24.15+](https://img.shields.io/badge/node-24.15%2B-5FA04E?logo=nodedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![mypy strict](https://img.shields.io/badge/mypy-strict-2A6DB2)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

[**Live demo**](https://roadside.eryk-poradecki.dev) · [**Demo video**](docs/roadside-demo.mp4) · [Decisions](docs/adr/) · [AI usage](AI_USAGE.md)

</div>

Roadside is a roadside assistant for drivers: say what happened, get safety steps at once, AI
advice fitted to your car and real places nearby, and keep every incident for later. Try the
[live demo](https://roadside.eryk-poradecki.dev) (notes [below](#live-demo)) or watch the [demo video](docs/roadside-demo.mp4).


https://github.com/user-attachments/assets/dab9cf95-f164-45de-a985-ad2756e2a991


## What it does

Roadside is built for two moments. **At the roadside**, on a phone, often at night and under
stress, it answers one question: *what do I do now?* Big tap targets, quick picks instead of
typing, and 112 always one tap away. **Later, at home**, on a desktop, the same app is where you
go through your incident history on a map, keep your cars' details up to date and finish a damage
report for a pothole. Every feature works on both; the layout changes to suit the moment.

- **Safety first, and not from the AI.** The moment you tap *Get help now*, a fixed safety
  checklist for your problem appears (hazard lights, vest, behind the barrier, triangle, when to
  call 112). It is written in advance with official sources, ships with the app and works with
  no signal. The AI is told never to contradict it.
- **Vehicle profiles that change the advice.** Fuel type, transmission, spare wheel (full size,
  space saver, repair kit or none), locking wheel bolts and their key, roadside assistance. A few
  examples of what this changes:
  - an automatic or an electric car gets *"tell the tow company, a flatbed is preferred"*, and a
    push start is only ever suggested for a manual that isn't electric or hybrid;
  - with roadside assistance on file, the AI suggests calling your insurer, and the app shows
    the *Call* button with your saved number (the AI never writes a phone number);
  - a diesel that ran dry gets the fuel-priming note;
  - for an electric car, *out of fuel* becomes *out of charge* and nearby shows chargers instead
    of fuel stations.

  Unknown is never treated as "none": if you didn't say whether you have a spare, the AI won't
  assume you don't.
- **AI advice that asks before it guesses.** When the answer depends on something it can't tell,
  the assistant asks up to two short clarifying questions. Each comes with one safety action to
  take *right now* while you answer, and tap-to-answer options; you can also type a short reply
  or tap *Just give me the steps*. The answer is numbered steps, flags urgency (then *Call 112*
  comes first), says whether it saw your photos, and is always labelled as AI.
- **Real places nearby.** Tyre shops, fuel stations, EV chargers and garages from OpenStreetMap,
  on a map and in a list with distance, and phone and opening hours where available. One tap
  opens directions in Google Maps. The search covers 5 km, and you can widen it to 25 km. The AI
  can suggest which categories matter, but it never names a place.
- **Your incident history.** Every help request is saved the moment you ask, so nothing is lost
  if the app or the connection dies. Review them on a list or a map, resolve and reopen them, add
  photos, and see exactly which car and facts each answer was given for.
- **Damage report drafts for potholes.** Turn a pothole incident into a letter to the road
  manager: the facts (date, place, car, photos) come from the incident, the AI writes only the
  description of what happened. Edit it, copy it or print it to PDF, and mark it sent. It also
  explains who manages which road in Poland.
- **Personal data stays out of the model.** Your registration, policy number and assistance phone
  never reach the AI, and neither do your coordinates or address: the model only sees a coarse
  context: the kind of road (motorway or expressway, main road, local street), the kind of place
  (city, town, village, countryside) and whether it's dark. Location is used by the backend
  itself, to work out that context and find nearby places. Your name, address and bank account
  for the damage report never leave your browser.
- **Polish and English**, installable as a PWA, and a local **MCP server** so an AI client can
  read your incidents and draft a report.

## Key decisions

The reasoning behind the app, with the options that were turned down, is recorded in
[Architecture Decision Records](docs/adr/). The ones that shaped it most:

| Decision | Why | ADR |
| --- | --- | --- |
| **The AI does only what needs judgement.** Each AI turn is one schema-constrained call with no tool loop. The backend looks up nearby places itself, in parallel with the model. | Public Overpass took 13–47 s and failed about half the time in research. As a model tool, that delay and those failures would sit in series with the answer and cost an extra model call. The category was never a real choice anyway: the problem and the fuel type decide it. | [0004](docs/adr/0004-ai-turns-without-tools.md) |
| **Safety steps are static copy, not AI output.** | They must show instantly and offline, exactly when the AI is most likely to fail, and they must be right. The prompt carries the same six safety invariants, so the AI leads with safety without contradicting the list. | [0010](docs/adr/0010-static-safety-checklist-in-frontend.md) |
| **Vehicle facts are injected into the prompt, from an allow-list.** | Every answer needs them, and a small local model can't be forced to call a tool. The allow-list is also the privacy boundary: a new field stays out of the prompt until someone adds it on purpose. The answer stores the exact fact block it was given. | [0003](docs/adr/0003-vehicle-facts-injected-into-prompt.md) |
| **Places come from OpenStreetMap, never from the model.** | A model can invent a garage that doesn't exist; a map can't. Map data and AI content are visibly separate. | [0004](docs/adr/0004-ai-turns-without-tools.md) |
| **An incident is created at the help request.** | No "save" step for the common case, and the request survives a crash or a lost connection. An idempotency key stops a retry on a weak signal from creating a duplicate. | [0001](docs/adr/0001-incident-starts-at-help-request.md), [0005](docs/adr/0005-rest-conventions-and-endpoints.md) |
| **The damage report is a template plus one AI call.** | The template owns the facts and the layout; the model writes only the narrative. Claimant details never reach the server, so a public demo holds no personal data. | [0009](docs/adr/0009-damage-report-drafted-from-incident.md) |
| **Demo mode replays real model answers.** | Answers were recorded from a live model and are matched on the exact inputs, so everything runs without an AI API key. | [0004](docs/adr/0004-ai-turns-without-tools.md), [0013](docs/adr/0013-demo-mode-follows-the-scenario.md) |
| **Plain SQL over aiosqlite**, numbered migrations, `STRICT` tables. | A small schema, SQL in plain view, and constraints that the database enforces itself. | [0006](docs/adr/0006-plain-sql-over-aiosqlite.md) |
| **REST under `/api/v1`, one error format** (RFC 9457), a TypeScript client generated from OpenAPI. | The contract can't drift: CI regenerates the client and fails on any diff. | [0005](docs/adr/0005-rest-conventions-and-endpoints.md), [0008](docs/adr/0008-frontend-structure-and-tooling.md) |

## Tech stack

| | |
| --- | --- |
| **Backend** | Python 3.13+ (3.14 in Docker and CI), FastAPI, Pydantic v2, SQLite 3.37+ via aiosqlite, uv |
| **AI** | Any OpenAI-compatible API (hosted or local Ollama), optional vision; a dev-only Claude Code CLI provider for recording; recorded replays in demo mode |
| **Maps** | OpenStreetMap: Overpass (places), Nominatim (road context), Leaflet with OSM tiles |
| **Frontend** | React 19, TypeScript 6, Vite 8, TanStack Query 5, React Router, react-i18next, PWA; Node 24.15+ |
| **Quality** | ruff, mypy `--strict`, pytest; ESLint (with jsx-a11y), Prettier, tsc, Vitest; Playwright end to end; pre-commit; GitHub Actions |
| **Runtime** | Docker Compose: the API behind nginx on a single origin |

The backend is layered routers → services → repositories, and the frontend mirrors that layout.

## Running locally

### Quick start: Docker

Needs Docker with Compose. No keys and no `.env` file.

```sh
docker compose up --build
```

Open <http://localhost:8080>. Stop it with `docker compose down` (your data volume is kept; add
`-v` to remove it).

> [!NOTE]
> **Demo mode vs live mode.** Out of the box the app runs in **demo mode**: you pick one of eight
> recorded scenarios and the AI answers, nearby places and report drafts are replayed from real
> recordings. Nothing is sent to a model or to OpenStreetMap services. **Live mode**
> (`DEMO_MODE=false` in `backend/.env`) calls a real model and real OSM services and lets you
> describe your own situation. Both the Docker stack and local development read the same
> `backend/.env`.

### Local development: backend and frontend as two processes

Needs Python 3.13+ and Node.js 24.15+ with npm. The backend runs on <http://localhost:8000>
(interactive API docs at <http://localhost:8000/docs>), the frontend on <http://localhost:5173>.
No environment file is needed for demo mode. CORS allows only `http://localhost:5173` by default;
other origins go in `FRONTEND_ORIGINS` in `backend/.env` (explicit origins, never `*`).

**1. Backend** (first terminal)

<details open>
<summary><b>With uv</b> (recommended)</summary>

```sh
cd backend
uv sync
uv run uvicorn --factory app.main:create_app --reload --port 8000
```

</details>

<details>
<summary><b>With pip</b></summary>

`requirements-dev.txt` is exported from `uv.lock`, so the versions are the same as with uv.

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt -e .
uvicorn --factory app.main:create_app --reload --port 8000
```

</details>

Migrations run when the backend starts (`python -m app.db migrate` runs them on their own).

**2. Frontend** (second terminal)

```sh
cd frontend
npm ci
npm run dev
```

<details>
<summary><b>With Make</b></summary>

`make install` installs both apps and the git pre-commit hook, then `make dev-api` and
`make dev-web` start the two processes. `make help` lists every target.

</details>

<details>
<summary><b>Live mode: connect a model</b></summary>

```sh
cp backend/.env.example backend/.env
```

Set `DEMO_MODE=false`, then `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` for any
OpenAI-compatible endpoint. The example file has a hosted preset and a local Ollama preset.
Set `LLM_VISION=true` only for a model that takes images. Startup fails if a setting is missing;
it never falls back to demo mode quietly. Under Docker, for a local Ollama, that's typically
`http://host.docker.internal:11434/v1/`.

</details>

<details>
<summary><b>Tests and checks</b></summary>

```sh
make check        # ruff, mypy, pytest, eslint, prettier, tsc, vitest, build, OpenAPI drift
make e2e          # Playwright against a disposable demo stack (needs Docker)
```

Before the first `make e2e`, run `npx playwright install --with-deps chromium` in `frontend/`.
CI runs the same targets, plus a Docker smoke test.

</details>

<details>
<summary><b>MCP server</b></summary>

A local stdio MCP server shares the backend's database, settings and services; the backend
doesn't need to be running. Add this to your MCP client, with your checkout's absolute path:

```json
{
  "mcpServers": {
    "roadside": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/roadside/backend", "run", "python", "-m", "app.mcp"]
    }
  }
}
```

Tools: `list_incidents`, `get_incident`, `find_nearby` (real OSM data; it doesn't change the
incident) and `draft_damage_report` (pothole incidents only, never overwrites a report). There
are no edit, send or delete tools. The server exposes your incidents to the MCP client, so keep
the connection local.

</details>

## Live demo

**<https://roadside.eryk-poradecki.dev>**, available during the review period.

- There is no live model. You pick a demo scenario, its details are filled in for you, and the
  answers are pre-recorded for it. The app never asks for your location.
- The three demo vehicles can't be edited or deleted, because the recordings depend on them.
  Cars you add yourself can.
- Photo uploads are off; only bundled sample photos can be attached.
- Everything is held in memory and wiped nightly. It is a shared demo: other visitors can see
  what you entered until then.
- It runs on a Raspberry Pi at home and may sometimes be offline.

## Privacy

Roadside is provider-neutral: live mode works with any OpenAI-compatible provider, whether a
model on your own machine (Ollama) or a hosted API, and a dev-only provider uses an installed
Claude Code CLI. Whatever you configure is what receives the data below, under its own terms.

- **What the model gets:** the problem, your note, the time of day, a coarse road context, the
  non-sensitive vehicle facts and, if vision is on, up to three photos. Hosted providers,
  especially free tiers, may use inputs to improve their products, and photos can show plates,
  faces or a street. When vision is on, the photo sheet says *"Photos are sent to the AI
  provider"*. Uploaded photos are re-encoded without EXIF metadata, GPS included, when saved.
- **What it never gets:** your registration, policy number, assistance phone, coordinates,
  address, or your details for the damage report.
- **Coordinates** go to the Nominatim server (configurable) and to Overpass, not to the model
  provider.
- **Map tiles** are loaded by your browser directly from OpenStreetMap's tile servers, in the
  public demo too, so the OpenStreetMap Foundation sees your IP address and the map area you view.
- **The public demo** sends nothing to any model provider or OSM service: it replays
  recordings. Those were made through the **Claude Code CLI** with the model
  **`claude-opus-5-5`**; each recording names its model ([details](AI_USAGE.md)).

## Roadmap

Out of scope for this MVP, on purpose:

- **Accounts and authentication.** The app is single-user. Login adds little to an MVP and would
  have to be disabled or faked in the public demo anyway.
- **Towing and roadside assistance in Nearby.** OpenStreetMap has no consistent tag for them; in
  Poland they are often findable only by name (*pomoc drogowa*, *holowanie*, *laweta*), so a
  reliable source still has to be chosen.
- **Fleets.** Shared vehicle management for whoever runs many cars: taxi companies, car sharing,
  company fleets. It builds on accounts.
- **More incident types**, beyond the five presets.
- **Truck drivers.** Truck repair, HGV-accessible services and truck parking, and local guidance
  for the many countries they cross in a day.
- **Local services.** Integrations with services such as taxi companies. Besides getting you
  and your passengers home, many of them bring enough fuel to reach a station or jump-start a
  car with a flat battery.
- **Local transit.** When the car can't go on, show the bus and tram lines nearby and their
  schedules.
- **Manual location entry** (address search) when location access is denied.
- **Better place coverage.** OSM coverage varies by region. A commercial places API such as
  Google Places has more local businesses, but its licence and per-request fees aren't justified
  for an MVP, and it isn't open data.

## How AI was used

Planning and scope started in a Claude chat. Matt Pocock's skills then turned the plan into a
map of tickets and grilling sessions, with every decision recorded as an [ADR](docs/adr/).
Claude Code (Opus) implemented most tickets and Codex the smaller ones, one session per ticket
(`/implement issue #49` → answer questions → review → PR), with Impeccable for the UI. Manual QA
caught what the tests didn't. Details, examples and where the agent configuration lives:
**[AI_USAGE.md](AI_USAGE.md)**.
