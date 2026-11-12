# REST conventions and the MVP endpoint list

> **Amended by #70:** API and MCP may open the same local SQLite database. Generation
> keeps the in-process lock and also acquires a nonblocking OS file lock per incident
> under `<resolved database path>.locks/`, shared by both processes through `filelock`.
> Contention still answers `turn_in_progress`; process exit releases the lock. Lock files
> stay in place so concurrent processes never lock different files for the same incident.
> This replaces the generation lock's one-worker assumption below without holding a SQLite
> write transaction across a model call. Both entry points must use the same local database
> path; this is not a distributed deployment lock.

> **Amended by ADR 0008 and the spec #43:**
> - Types and the client are generated with `@hey-api/openapi-ts` (ADR 0008), not `openapi-typescript`.
> - Problem type wire values are `flat_tyre`, `flat_battery`, `out_of_fuel`, `pothole_damage`, `other`.
> - `AiTurnCreate` carries a reply as `{option?, text?, skip?}`.
> - `NearbyRead` has a fixed place shape, capped at 20.
> - The desktop History map needs no extra query parameters.

> **Amended by #55:**
> - `opening_hours` carries the raw OSM string; the frontend shows it only in the simple forms (`24/7`, `Mo-Su HH:MM-HH:MM`), because the display text is translated there.
> - When there are more than 20 places, each category found keeps its nearest places in turn before the list is sorted by distance, so a crowded category (garages in a city) can't push a sparse one (the only tyre shop) off the list.
> - `POST /incidents/{id}/nearby` also answers 409 `location_changed` when a PATCH moved the incident during the lookup (nothing is stored), and 503 `nearby_not_recorded` in demo mode when the scenario has no places recorded at that radius (#58). Retrying can't help, so the UI offers no retry, and the previous snapshot stays.
> - The snapshot's source endpoint is stored but not sent.

> **Amended by #53:** `AiTurnRead` carries `question` (`QuestionRead` `{now, question, options}`) on a question turn and `reply` (`ReplyRead` `{option, text, skip}`) on a reply turn; the reply body is `ReplyCreate`. A `reply.option` that is not one of the open question's options is 422 (`errors[].field` = `reply.option`).

The API is plain resource-oriented REST under `/api/v1`, with one error format (RFC 9457 problem details carrying a machine-readable `reason`) and Pydantic DTOs kept separate from database rows. The reviewers grade API design directly, so the conventions follow the standards a reviewer expects instead of FastAPI's defaults. The few places that are not plain CRUD (AI turns, the nearby lookup) are modelled as sub-resources, not RPC verbs. The endpoint table below is the spec input for the build.

## Considered Options

- **`/api` without a version**, or a version header. Rejected: `/api/v1` costs nothing, is what readers expect, and the stretch MCP server is a second client. The paths in ADRs 0002 and 0004 live under `/api/v1`.
- **FastAPI's default `{"detail": ...}` errors**, with our own shape only for AI failures. Rejected: two error shapes, and the UI would parse strings. Every error, including request validation, goes through exception handlers into `application/problem+json`.
- **RPC-style `/assist` or `/diagnosis`** for the AI. Rejected: `POST /incidents/{id}/ai-turns` appends to an append-only collection that matches the glossary (ADR 0004).
- **Cursor pagination**, or none. Rejected: limit/offset with a `total` is enough for one driver's history in SQLite and still shows the practice.
- **Full incidents in the list.** Rejected: the History list and the desktop map need a summary only, and loading every incident's turns and places would be N+1 work for nothing.
- **camelCase JSON with Pydantic aliases and hand-written TS types.** Rejected: snake_case end to end, with frontend types generated from the OpenAPI document (`@hey-api/openapi-ts`, ADR 0008), so the contract can't drift.
- **Demo mode as a Vite build-time variable.** Rejected: `GET /api/v1/config` is the runtime source of truth. The server enforces it anyway, and the same frontend build runs in both modes.
- **Promote another vehicle when the default is deleted.** Rejected: the usual reason to delete the daily driver is a new car the driver is about to add, and promoting e.g. a spouse's car would only add a correction step. The incidents keep their history (`vehicle_id` → null, ADR 0001), and no default exists until the driver picks one or adds a vehicle.
- **No server guard against duplicate creates** (client button disable only). Rejected: a weak signal is the app's core constraint, so "response lost after the server committed" is the typical failure, not a rare one. A duplicate would split photos and AI turns across two incidents.
- **A full idempotency-key store** (separate table, TTL, payload fingerprint). Rejected as more than the MVP needs. See the light version under Consequences.

## Conventions

- **Prefix:** `/api/v1` for the product API. `GET /health` is unversioned, because it's for docker-compose and the tunnel, not for clients.
- **Status codes:**
  - 201 + `Location` + body on create; 200 on read, PUT and PATCH; 204 on DELETE.
  - 404 when the resource in the **path** is missing. 422 when the **body** or query is invalid, including an unknown `vehicle_id`.
  - 409 for state conflicts, including the sixth photo: the request is well-formed, only the incident's state forbids it.
  - 413 and 415 for photos, and 403 for file uploads in demo mode.
  - 502 and 504 for provider failures, and 503 when a dependency (Overpass, the DB) is down.
- **Errors:** RFC 9457 problem details (`type: about:blank`, `title`, `status`, `detail`, `instance`) plus the extension `reason` (a stable snake_case code the UI switches on) and, on 422, `errors[]` with `field` and `message`.
- **Wire format:** snake_case JSON, integer ids, ISO 8601 UTC timestamps with `Z`.
- **DTOs:** `VehicleCreate`, `VehicleUpdate`, `VehicleRead`, `IncidentCreate`, `IncidentPatch`, `IncidentSummary`, `IncidentRead`, `PhotoRead`, `AiTurnCreate`, `AiTurnRead`, `NearbyRequest`, `NearbyRead`, `ConfigRead`, `Problem`. They are not the DB rows.
- **CORS** allows only the configured frontend origins (`FRONTEND_ORIGINS`, comma-separated), never `*`.

## Endpoints

All paths are under `/api/v1` except `/health`. Every error is a problem response, and the `reason` is shown where it is set.

| Method & path | Body / query | Success | Errors (`reason`) |
|---|---|---|---|
| `GET /health` | – | 200 `{status: "ok"}` (runs `SELECT 1`) | 503 |
| `GET /config` | – | 200 `{demo_mode, vision_enabled, max_photos, max_photo_bytes, sample_photos: [{id, url, title, credit}]}` | – |
| `GET /sample-photos/{id}` | – | 200 file | 404 |
| `GET /vehicles` | – | 200 array, default first, then oldest first; no pagination | – |
| `POST /vehicles` | `VehicleCreate`: `name` required, the rest nullable, `is_default?` | 201 + `Location` `VehicleRead` | 422 |
| `GET /vehicles/{id}` | – | 200 `VehicleRead` | 404 |
| `PUT /vehicles/{id}` | `VehicleUpdate` (full representation) | 200 `VehicleRead` | 404, 422 |
| `DELETE /vehicles/{id}` | – | 204 | 404 |
| `GET /incidents` | `?status=open\|resolved`, `?vehicle_id`, `?limit=20` (max 100), `?offset=0` | 200 `{items: IncidentSummary[], total, limit, offset}`, newest first | 422 |
| `POST /incidents` | `IncidentCreate`: `{problem_type, vehicle_id\|null, note?, location?: {lat, lon, accuracy_m?}}`; header `Idempotency-Key?` | 201 + `Location` `IncidentRead`; **200** with the existing incident on a repeated key | 422 |
| `GET /incidents/{id}` | – | 200 `IncidentRead` | 404 |
| `PATCH /incidents/{id}` | any of `status`, `note`, `problem_type`, `location`, `vehicle_id` | 200 `IncidentRead` | 404, 422 |
| `DELETE /incidents/{id}` | – | 204, deleting photos (files too), AI turns, the nearby snapshot and the damage report | 404 |
| `POST /incidents/{id}/photos` | multipart `file`, or JSON `{sample_id}` | 201 `PhotoRead` `{id, url, content_type, width, height, created_at}` | 404, 409 `photo_limit`, 413 `photo_too_large`, 415 `unsupported_media_type`, 403 `demo_uploads_disabled`, 422 `unknown_sample` |
| `GET /photos/{id}` | – | 200 file | 404 |
| `DELETE /photos/{id}` | – | 204 | 404 |
| `POST /incidents/{id}/ai-turns` | `AiTurnCreate`: `{locale: "pl"\|"en", reply?: {option?, text?, skip?}}` | 201 `AiTurnRead` (a `question` or the `advice`), no `Location` | 404, 409 `advice_exists` / `no_open_question` / `reply_required` / `turn_in_progress`, 502 `provider_error` / `invalid_output`, 504 `timeout` |
| `POST /incidents/{id}/nearby` | `NearbyRequest`: `{radius_km}` (1–25) | 200 `NearbyRead` `{status: "found"\|"none", places[], radius_km, fetched_at}` (`places` shape below) | 404, 409 `no_location`, 503 `nearby_unavailable`, 422 |

The damage report's endpoints are in ADR 0009, which also adds `damage_report_status` to `IncidentSummary`.

- **`IncidentSummary`:** `id`, `problem_type`, `status`, `created_at`, `location {lat, lon}`, `location_label`, `vehicle_id`, `photo_count`, `has_advice`.
- **`IncidentRead`:** the incident fields plus `photos[]`, `ai_turns[]` (in `seq` order), `nearby` (null until the first successful lookup) and `location_label` (null until the location context is computed).

## Wire shapes settled in spec #43

- **Problem type wire values:** `flat_tyre`, `flat_battery`, `out_of_fuel`, `pothole_damage`, `other`.
- **Reply body in `AiTurnCreate`:** `reply` is `{option?: string, text?: string, skip?: bool}` with exactly one field set, otherwise 422. `text` has the same maximum length as `note`.
- **Nearby place in `NearbyRead.places[]`:** `{osm_type, osm_id, category, name|null, lat, lon, distance_m, phone|null, opening_hours|null}`. At most 20 places, sorted by distance. `opening_hours` is passed on only in the simple forms of the prototype rule: `24/7`, or the same hours every day (`Mo-Su HH:MM-HH:MM`). Anything else is `null`.
- **Desktop History map:** it needs no geo-bounds filter and no larger page size. It shows the pins of the loaded page of `GET /incidents`.

## Core flow (Start → Result)

1. App load: `GET /config` and `GET /vehicles`. The Start tile label follows the default vehicle, if there is one.
2. "Get help now": `POST /incidents` with a fresh `Idempotency-Key`. It returns at once, and the UI moves to the Result screen with the safety checklist showing.
3. In parallel:
   - `POST /incidents/{id}/photos` for each photo (or `{sample_id}` in demo mode);
   - `POST /incidents/{id}/nearby {radius_km: 5}`, only when the incident has a location. Without one, the UI shows its "no location" state itself and never triggers the 409.
4. Once every upload has succeeded or failed: `POST /incidents/{id}/ai-turns {locale}`.
5. If the turn is a question: `POST /incidents/{id}/ai-turns {locale, reply}`, at most twice, until the advice arrives.
6. "Try again" repeats the failed call. On `none`, "Search within 25 km" sends `POST /incidents/{id}/nearby {radius_km: 25}`.
7. Later: `PATCH /incidents/{id} {status: "resolved"}`. History uses `GET /incidents?status=…`, incident detail uses `GET /incidents/{id}`. Reopening an incident with no advice resumes at step 4 or 5.

## Consequences

- **Light idempotency on incident create only.** The client generates a UUID when "Get help now" is tapped and sends it as `Idempotency-Key` (the IETF httpapi draft header, so the create body stays a plain representation). It's stored in a nullable UNIQUE `idempotency_key` column on the incident: no separate key store and no TTL, because the key lives as long as the incident does.
  - A repeat with the same key returns the existing incident with 200. A race between two such requests is caught by the UNIQUE constraint and answered the same way.
  - The header is optional, so curl and the MCP server work without it.
  - The server doesn't compare payloads: the same key with a different body still returns the existing incident. The stricter alternative is 422 on a payload mismatch, worth adding if keys ever come from less careful clients.
  - Other endpoints don't need keys: AI turns have their 409 guards, and a duplicate photo is a manual delete. The client still disables the button while a request is in flight.
- **One turn at a time per incident.** An in-process `asyncio.Lock` per incident id answers a concurrent `ai-turns` request with 409 `turn_in_progress`. This assumes one uvicorn worker. With more workers, it becomes a lock row or `BEGIN IMMEDIATE` in SQLite. "Try again" after a failed turn sends `{locale}` only.
- **Reverse geocoding is lazy and off the create path.** `POST /incidents` never calls Nominatim, because "Get help now" must return at once. The first AI turn computes the location context (ADR 0004: ≤3 s, failure or timeout → `unknown`, never blocks the turn). Its result (`road_class`, `settlement`, `location_label`) is cached on the incident. A PATCH that changes `location` recomputes it inline under the same 3 s budget, which is acceptable because PATCH is not on the help-request path. A failure leaves the context `unknown` and the label null. The advice's inputs snapshot keeps the context it was answered for.
- **A PATCH that changes `location` also clears the nearby snapshot** (`nearby` → null), because its places were found around the old point. The UI runs the lookup again. Changing `problem_type` keeps it: one Overpass query covers every category, and the type only changes the preselected chips (ADR 0004).
- **Default vehicle rule.** A vehicle added while no default exists becomes the default, unless it's created with `is_default: false`. `is_default: true` on create or PUT unsets the old default in the same transaction. Deleting the default leaves none.
- **Nearby failures are errors, results are data.** A 503 keeps the previous snapshot. `found` and `none` are both successes. Demo mode never calls Overpass (recorded results, ADR 0004), so the demo and the video can't hit the failure path, and every replay scenario needs a recorded `found` result.
