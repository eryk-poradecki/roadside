# AI where it adds value: one schema-constrained turn, no tools in the help request

The help request runs **no tool loop**. Each AI turn is one schema-constrained model call. The backend does the nearby lookup itself, deterministically and in parallel with the model, and the model never sees or names a place. The kickoff plan was "one agent with 2–3 tools" (`get_vehicle_profile`, `find_nearby`, optionally `draft_damage_report`). ADR 0003 already dropped the first. `find_nearby` is dropped here because AI should be used where it adds value, not where it only adds latency and failure points. Public Overpass answered in 13–47 s per query and failed about half the time ([research #5](https://github.com/eryk-poradecki/roadside/issues/5)), and live Overpass was unavailable in all 5 attempts while the Result screen was prototyped ([#8](https://github.com/eryk-poradecki/roadside/issues/8)). As a tool, that latency and those failures would sit in series with the model, and they would cost at least one extra model call. Research rules out `tools` and `response_format` in one request ([#6](https://github.com/eryk-poradecki/roadside/issues/6), [#7](https://github.com/eryk-poradecki/roadside/issues/7)), and that extra call is slow on an 8 GB GPU. Choosing the category is not a real decision either: the problem type and fuel type already settle it.

The agentic parts that remain are the ones where the model's judgment matters:
- bounded multi-turn clarification with stored state;
- the model choosing `extra_categories`;
- the `urgent` flag that changes the UI.

Tools come back where the model makes a real choice: the damage report (if it becomes a tool) and the MCP server.

## Considered Options

- **`find_nearby(category)` as an agent tool**, followed by a separate schema-constrained final call. Rejected: at least two model calls plus a slow, flaky Overpass call in series, and Overpass failures would delay or break the AI answer.
- **Keep a tool only to have an "agent".** Rejected: it adds complexity that does nothing.
- **A discriminated union (`oneOf`/`anyOf`) as the schema sent to the model.** Rejected: Cerebras rejects `oneOf` and `minItems`, Gemini silently drops length keywords, and small local models do worse on branching grammars. One conservative flat schema works on every shortlisted provider.
- **Turns as a background job with polling or SSE**, or streamed tokens. Rejected for the MVP: job state and extra endpoints, and nothing to stream in a JSON object that is validated whole. ADR 0001 already keeps the incident safe if the tab closes.
- **Coordinates in the prompt.** Rejected for privacy: they are personal data sent to a hosted provider, and a model can't use raw coordinates well. A coarse derived context carries what the advice needs.

## Consequences

### The turn contract

- **The model fills in:**
  ```
  kind: ask | answer
  urgent: bool
  ask:    { now, question, options[2–4] }                  # free-text "Other" is UI-only
  answer: { cause, confidence: likely|possible|unsure, alternatives[0–2],
            steps[2–6], escalate_if[1–4], photo_observation|null,
            extra_categories[] ⊆ {tyres, fuel, charging, repair} }
  ```
  The schema sent to the model is one flat object with both blocks nullable and no `oneOf`, `minItems` or `maxLength`. Pydantic enforces the real rules: exactly one block matches `kind`, plus the counts and length caps. It then builds a proper internal union. If validation fails, **one repair call** is made with the Pydantic error appended. If that also fails, the turn fails.
- **A fact the backend already knows is never asked from the model.** The backend fills in: photos seen and not sent (cap or text-only provider), the inputs snapshot, the locale, `prompt_version`, provider and model. This follows ADR 0003's phone-number rule. Steps are plain strings numbered by the UI. There is no per-step safety flag, because "stop and call for help if" carries the danger signals.
- **`urgent`** is set when the note, photos or context suggest injury, fire, smoke, a fuel leak, or a car standing in a live lane. The prompt then also requires "call 112" as the first step and forbids a clarifying question. The UI moves 112 to the primary dock slot and shows a banner. It is only ever an addition: 112 stays visible regardless.

### Clarifying questions and storage (amends ADR 0001)

- **The model decides whether to ask**, under prompt rules. It asks only when the answer would change the first steps and the problem type, note, photos, vehicle facts and location context don't already settle it.
- **The backend enforces the cap.** After two questions, the schema for the next turn narrows `kind` to `["answer"]`, so a third question can't be generated. The reply "Just give me the steps" narrows it the same way.
- **The AI answer becomes append-only instead of write-once.** An `ai_turns` table has an `incident_id` FK (`ON DELETE CASCADE`), a unique `(incident_id, seq)`, and `kind ∈ {question, reply, advice}`. Rows are only inserted, never updated.
  - A reply is its own row (option, free text, or `skipped`), so a question row is never mutated.
  - Model rows store `payload` (validated output), an **inputs snapshot**, `locale`, `prompt_version`, `provider`, `model` and `created_at`. The snapshot holds the vehicle fact block plus name, problem type, note, photo ids seen, the not-sent count, the location context and local time. It is stored on every model turn, and "Answered for…" reads from the advice turn.
- **One synchronous endpoint:** `POST /api/incidents/{id}/ai-turns` with body `{reply?}`. The request holds until the next turn is validated and stored or has failed.
  - If the last row is an unanswered question, a reply is required and is appended first.
  - If generation fails, the reply stays, and "Try again" posts with no body.
  - The server returns 409 when the advice already exists (the advice closes the AI answer), or when a reply comes with no question to answer. The exact path is confirmed in *API conventions & endpoint list*.

### Nearby is a server-side lookup next to the AI answer

- **Category mapping:** tyre/pothole → `tyres`; fuel → `fuel`, or `charging` for an EV (ADR 0003); battery → `repair`; something else → all.
- **One Overpass query covers all four categories** within the radius. The chips filter on the client, so `extra_categories` only changes the preselected chips and never starts a second lookup. Towing is not a category, because it has no settled OSM tag. It is a phone call, and the 112/assistance dock covers it.
- **The snapshot is stored next to the AI answer.** `incident_nearby` holds places, radius, `fetched_at` and source endpoint. `POST /api/incidents/{id}/nearby {radius_km}` runs the lookup and replaces the snapshot only on success, which covers "search within 25 km" and retry. The frontend fires it right after creating the incident, in parallel with photo uploads and the first turn.
- **The server always does the lookup itself**, so "map data, not AI" can't be whatever a client posted.

### What the model is told

- **Location context, not coordinates.** After the incident is created, the backend makes one Nominatim reverse call: `format=jsonv2`, `zoom=17` (roads, not buildings), `addressdetails=1`, `extratags=1`, `accept-language=<UI locale>`. It has a 3 s timeout, is cached by rounded coordinates, and follows the 1 request/s policy ([research #32](https://github.com/eryk-poradecki/roadside/issues/32)). Any failure gives `unknown`.
  - **`road_class`:**
    - `motorway`, `trunk` (+ `_link`) → `motorway_expressway`. Polish S roads are mostly tagged `motorway`. `trunk` also covers some non-expressway national roads, but keeping it here errs on the safe side.
    - `primary`, `secondary`, `tertiary` (+ `_link`) → `main_road`.
    - `residential`, `unclassified`, `living_street`, `service` → `local_street`.
    - Anything else, including a result that isn't a highway, and tracks and paths → `unknown`.
  - **`settlement`:** `address.city` → city, `town` → town, `village` → village. With only `hamlet` or `isolated_dwelling` → countryside, and `village` wins when both are present. With no locality key → countryside if a road matched, else unknown. `municipality` (the gmina) is never used. The value is the nearest named locality, not a built-up area, so it is weak evidence next to `road_class`.
  - **`road_class` is forced to `unknown`** when the browser reports GPS accuracy worse than ~150 m, **or when the matched road is more than ~50 m from the location** (computed by the backend; Nominatim has no distance limit and snapped a rural point to a street 370 m away). A point near a motorway could snap to a side road, and "local street, handle it yourself" is the dangerous mistake. Both thresholds are config values, to be tuned.
  - The same call gives the **location label** shown on the Result screen (`"{road name}, {city|town|village|hamlet}"`, never `display_name`). The label is stored on the incident and never sent to the model.
  - **Privacy:** the coordinates go to the OSMF Nominatim server (whose policy says not to submit personal data), not to the model provider. The README's privacy note says so. Demo mode makes no call, and the server URL is configurable (`NOMINATIM_URL`), so a self-hosted or commercial instance can replace the public one.
  - The first turn waits for the context (≤3 s), in parallel with photo uploads.
  - When the context is `unknown` and it would change the first steps, the model may ask a clarifying question about it.
- **Fixed in the prompt:** the region ("Poland/EU, emergency number 112, warning triangle and high-vis vest required").
- **Sent with each turn:** local time with a `dark` hint.
- **The Nearby panel:** the model knows it exists, so steps can point to it, but it never gets its contents and never names a business.
- **Prompt files:** `backend/app/assist/prompts/v1/system.md` and `v1/user.md`, written in English. A breaking change means copying them to `v2/`. `prompt_version` is stored on every turn and every recording.
- **Language:** the output is in the **UI locale only**, never detected from the note. A Polish note with the English UI gets an English answer. Enums stay English, the UI translates labels, and the README's AI section states the rule.

### Providers

- **`LLMProvider` is a thin transport:** `complete(LLMRequest) -> LLMResult`. The request carries messages with optional images, the JSON schema and a `replay_key`. The result carries raw text, provider, model and usage. Capabilities are `vision` and `max_images`. The assistant service above it owns the prompts, the fact block, validation, repair and the cap. That means every provider, Replay included, goes through the same validation pipeline.
- **`OpenAICompatibleProvider`** is the live path for reviewers (Gemini Flash, or Ollama `qwen3-vl:4b` / `qwen3:8b`). `.env.example` has both presets, and the README points reviewers to Gemini.
- **`ReplayProvider`:** the key is **semantic**, built by the service, not a hash of the prompt. It contains:
  - problem type, fuel type, transmission, the spare-wheel and assistance flags;
  - sample photo ids, whether vision was used, the locale, the replies so far;
  - `road_class` and `dark`.

  Settlement is left out of the key, because it rarely changes the first steps and including it multiplies the recordings needed. Demo mode makes no Nominatim or Overpass calls: its location context and nearby results come with the scenario.
- **`RecordingProvider`** is a decorator around a real provider. When `LLM_RECORD=true` it writes `{key, request, raw_output, provider, model, prompt_version, recorded_at}` to `backend/recordings/`. It is refused when `DEMO_MODE=true`.
- **`CLIProvider`** (Claude Code `claude -p`) is the provider that records the demo replays and the demo video, for the best model quality available.
  - It is dev-only: allowed only with `LLM_RECORD=true`, refused in demo mode, never deployed.
  - It runs as a bare model: all tools disabled, an empty temporary working directory, no repo access.
    - Verified flags ([research #31](https://github.com/eryk-poradecki/roadside/issues/31)): `--tools "" --disallowedTools "mcp__*" --strict-mcp-config --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt <file contents>`. `--bare` is not used, because it needs an API key instead of the subscription login.
    - Images go in as base64 `image` blocks in one `stream-json` stdin message, so vision needs no tool.
    - **`--json-schema` is not used.** It enforces the schema by injecting a synthetic `StructuredOutput` tool, which would break the no-tools rule. The schema is put in the prompt instead, and the output goes through the same Pydantic validation and repair call as every other provider.
    - The model id is read from the `modelUsage` key. Failure is detected from `is_error` in the result JSON, not only from the exit code.
  - Its output goes through the same validation and repair as every other provider.
  - Image input has to be verified before anything relies on it.
  - The README and AI_USAGE name the CLI and model that recorded the demo.
  - If time runs short, the fallback is recording with Gemini.
- **Config:**
  - `DEMO_MODE` is a single switch, `true` in `.env.example`. It means replay, uploads refused (ADR 0002), and recorded location context and nearby results.
  - With `DEMO_MODE=false` the server needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_VISION`, `LLM_MAX_IMAGES`, `LLM_TIMEOUT_S`, `LLM_TURN_BUDGET_S` and `LLM_TEMPERATURE` (0.2).
  - Startup fails fast when required values are missing. It never falls back to replay silently.

### Timeouts and failure

- **Model calls:** 5 s connect timeout, read timeout `LLM_TIMEOUT_S` (default 60 s).
- **Retries:** one retry on 429 or 5xx with backoff, honouring `retry-after` for up to a few seconds. No retry on 400.
- **Whole-turn budget:** `LLM_TURN_BUDGET_S`, default **90 s**, covering the repair call and retries. **Startup refuses values ≥100 s**, because the public deploy goes through Cloudflare Tunnel, which ends proxied requests at ~100 s (HTTP 524).
- **A failed turn stores nothing.** The endpoint returns a problem response with reason `timeout | provider_error | invalid_output`. The UI shows "The assistant couldn't answer" and "Try again". The safety checklist stays expanded, and nearby is unaffected.
- All the values are env-configurable and will be tuned after measuring on the RTX 4060.

### OSM User-Agent

- Overpass and Nominatim requests send `Roadside/<backend version> (+https://github.com/eryk-poradecki/roadside)`.
- There is no email: the public repo is the contact. Forks can override the value with `OSM_USER_AGENT`.

### MCP server (stretch, first to cut)

- A separate entry point (`python -m app.mcp`) that calls the services directly, not over HTTP.
- Tools: `list_incidents(status?)`, `get_incident(id)`, `find_nearby(lat, lon, category)`, and `draft_damage_report(incident_id)` if the damage report ticket makes it a tool.
- Read-only except the damage report draft. Never delete.

### Tests and evals

- **pytest in CI, with no network.** A `FakeProvider` with scripted outputs covers:
  - validation, the repair call and the second failure;
  - the narrowed schema after two questions, and skip;
  - the 409 cases and the budget timeout;
  - the snapshot contents;
  - that no field can carry a place;
  - replay key matching, including locale and vision mismatches.
- **`scripts/eval_assist.py`** is run by hand against a live provider or CLIProvider, never in CI, and logs the provider and model of every run.
  - About 10 scenarios, with scripted replies for the multi-turn ones.
  - Rule checks in code: the schema is valid, at most two questions, no push start for automatic/EV/hybrid, EVs get charging, "no spare" only for `none`, the output language matches the locale, smoke sets `urgent`, and the turn time stays under budget.
  - Results go into AI_USAGE per model. There is no LLM-as-judge in the MVP.
