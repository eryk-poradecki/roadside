# Demo mode follows the scenario, not the visitor: picked scenarios, a scenario location, read-only demo vehicles

In demo mode the visitor doesn't describe their own situation. They pick a **demo scenario**, and the scenario supplies everything the replay key and the recorded places depend on. The help request is the normal Start form, filled in and read-only. The visitor's geolocation is never asked for. The three seeded **demo vehicles** can't be edited or deleted. Decided in #121 and #124 (parent #43).

Before this, a visitor typed their own request and the app tried to match a recording. Most visitors missed one:
- a visitor who shared no location got `road_class: unknown`, which matched 1 of 8 scenarios;
- the default vehicle (the Octavia) is wrong for 4 scenarios;
- the sample photos have to match exactly.

On the public demo (ADR 0011), one visitor who edited a seeded car broke that car's scenarios for everyone until the nightly wipe. Every visitor could also see everyone's incidents in History, real geolocation included. Demo mode exists so reviewers can see the app work without a model, so it now leads with what was recorded instead of guessing at a match.

## Considered Options

- **The frontend sends a simulated location context** (`road_class`, `settlement`, `dark`) from the scenario. Rejected: the backend already finds the recorded context by the scenario key, so this would add an API field only demo mode uses, and the client could set the road class itself, against ADR 0004's "the server does the lookup".
- **The recorded context with no location** (#121's first option). Accepted at first, then replaced. It fixes the AI turns, but the map would still show a visitor in Berlin next to places recorded in Poznań, and the visitor's real position would still be stored on the shared demo.
- **A fixed placeholder location for any visitor** (#121's second option). Rejected: a fake position in the visitor's own incident. The scenario point used instead belongs to the scenario, like its note.
- **Free input next to the scenarios.** Rejected: free input misses most of the time, and the replay ignores the note, so a recorded answer could talk about a different situation from the one the visitor typed.
- **Accepting the shared mutable vehicles** (#124's first option), **restoring them on a schedule** (third option), or **one session per visitor** (fourth option). Rejected: the first leaves one visitor able to break the demo for a day, and the third leaves it broken between restarts. The fourth also fixes shared incidents, but it is far more work than a demo meant to run for about a week needs. With no geolocation, what visitors share is what they typed.
- **Locking the scenario fields of an incident in the backend.** Rejected: someone calling the API directly can only break their own incident, and they get the labelled fallback (ADR 0004). The frontend hides the controls.

## Consequences

- **Demo scenarios come from the backend.** `backend/app/demo_scenarios.py` holds the 8 scenarios of `docs/demo-scenarios.md`. Each has:
  - an id;
  - a title, a one-line summary and a note in each locale;
  - the problem type;
  - the vehicle profile (or none);
  - the situation;
  - the sample photo ids;
  - its public-road point (lat, lon, accuracy).

  The points move here from `backend/scripts/demo/scenarios.py`, which imports them; the time of day stays with the recording run. A test checks the module against the YAML blocks in the document.
- **A scenario lists only the locales it was recorded in.** In demo mode `GET /config` returns `demo_scenarios`, each with `locales`. These are worked out at startup from the committed recordings: a locale is listed when the scenario's first turn has a recording under its replay key. The picker shows only the scenarios listed for the current UI locale. A test checks that every listed scenario and locale replays. Today all 8 are recorded in both locales.
- **`GET /config` also returns `public_deploy`**, so the frontend knows when to say the data is shared.
- **No geolocation in demo mode.** The help request sends the scenario's point as the incident's location. Its context, label and nearby places are the scenario's recorded ones (ADR 0004, #58), so the map, nearby, the History map and the damage report all agree. The visitor's own position is never requested or stored.
- **The demo Start screen:**
  - a demo notice first ("a demo without a live AI model; feel free to browse; answers are pre-recorded for the scenarios below"), plus, when `public_deploy` is on, that anything entered is visible to other visitors until the nightly reset;
  - then the scenario list;
  - picking a scenario shows the normal Start form, filled in and read-only, with "Change scenario" and "Get help now";
  - there is no free input.
- **Incident detail in demo mode** hides:
  - changing the problem type, vehicle, situation or location;
  - adding or removing photos. The damage report's replay key includes every sample photo on the incident.

  Resolving, reopening, deleting, the nearby radius, and editing the damage report or marking it sent still work. The AI panel hides the free-text reply. An option with no recording gets the labelled fallback (ADR 0004).
- **Demo vehicles are marked and read-only.**
  - **Marker:** a nullable, unique `demo_profile` column (migration 0009) holds the profile id (`golf_2017`, `mini_ev_2021`, `octavia_2015`), and `VehicleRead` exposes it.
  - **Seeding:** demo mode adds every profile that has no row with its marker, not only into an empty table. A local volume seeded before this change keeps its unmarked copies next to the marked ones until `docker compose down -v`.
  - **Refused changes:** in every demo-mode stack, not only `PUBLIC_DEPLOY`, `PUT` on a demo vehicle answers **403 `demo_vehicle_read_only`** unless the only change is `is_default` (ADR 0005 sets the default through `PUT`), and `DELETE` always answers 403. This matches the 403 for uploads (ADR 0002).
  - **When demo mode is off,** the marked rows are ordinary vehicles.
  - **The default isn't protected:** it isn't in the replay key, and the scenario picks its own car.
- **The Vehicles screen in demo mode:**
  - a "Demo vehicle" label on the seeded cars, with no edit or delete;
  - a hint that the scenarios use the demo vehicles;
  - full CRUD for the visitor's own cars, which the scenarios don't use.
- **`/demo-check`** walks each scenario as the picker sends it: the scenario's point, never a visitor location. It also checks that editing a demo vehicle gets 403.
