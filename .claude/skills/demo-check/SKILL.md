---
name: demo-check
description: "Start the stack in demo mode and walk every demo scenario, reporting any replay miss or validation failure."
disable-model-invocation: true
---

Proves `docker compose up` replays the Start screen scenarios from `GET /config`: each offered locale and recorded branch, both nearby radii, and the pothole report in both letter languages. The walker (`backend/scripts/demo_check.py`) sends the catalogue's location, note, situation, photos and vehicle, found by `demo_profile`. It checks every documented scenario and locale is offered, so missing recordings cannot silently shrink the check.

It also verifies each demo vehicle refuses fact changes and deletion with 403 `demo_vehicle_read_only`, accepts changing only `is_default`, and restores the original default (including no default or a visitor's vehicle). It refuses an app outside demo mode and deletes the incidents it creates.

## 1. Start the stack in demo mode

Compose reads `backend/.env`, which on the owner's machine may turn demo mode off. Layer an override that forces it back on, under a project of its own: its fresh data volume is what a first visitor gets, seeded demo vehicles included, and the owner's volume is never touched. Port 8080 must be free, so stop the owner's stack first if it is up.

```sh
printf 'services:\n  backend:\n    environment:\n      DEMO_MODE: "true"\n      LLM_RECORD: "false"\n      LLM_PROVIDER: openai_compatible\n' \
  | docker compose -p roadside-demo-check -f compose.yaml -f - up --build --detach --wait
```

Done when `curl -fsS http://localhost:8080/api/v1/config` shows `"demo_mode":true` and `curl -fsS http://localhost:8080/api/v1/vehicles` lists the Octavia, Golf and MINI.

## 2. Walk

```sh
make demo-check
```

Done when it exits 0: every row reads `ok`. Exit 2 with "the demo vehicles are not seeded or were edited" means the stack didn't start on a fresh volume. A `/config is missing scenario` or `missing locales` error means first-turn recordings are missing; restore them with `/record-replays`. A vehicle error names the forbidden mutation or default change that failed. A row with a reason (`no_recording`, `nearby_not_recorded`, `invalid_output`, an option not offered) names the walk to fix with `/record-replays`.

## 3. Stop

```sh
docker compose -p roadside-demo-check down --volumes
```

`--volumes` removes only this project's throwaway volume, so the next check starts fresh.

Report the table to the owner, with the failing rows first.
