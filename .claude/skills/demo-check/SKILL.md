---
name: demo-check
description: "Start the stack in demo mode and walk every demo scenario, reporting any replay miss or validation failure."
disable-model-invocation: true
---

Proves `docker compose up` replays every scenario in `docs/demo-scenarios.md` with no `no_recording` fallback: every locale, every recorded branch, both nearby radii, and the pothole report in both letter languages. The walker is `backend/scripts/demo_check.py`; it refuses an app that is not in demo mode and deletes what it creates.

## 1. Start the stack in demo mode

Compose reads `backend/.env`, which on the owner's machine may turn demo mode off. Layer an override that forces it back on:

```sh
printf 'services:\n  backend:\n    environment:\n      DEMO_MODE: "true"\n      LLM_RECORD: "false"\n      LLM_PROVIDER: openai_compatible\n' \
  | docker compose -f compose.yaml -f - up --build --detach --wait
```

Done when `curl -fsS http://localhost:8080/api/v1/config` shows `"demo_mode":true`.

## 2. Walk

```sh
make demo-check
```

Done when it exits 0: every row reads `ok`. A row with a reason (`no_recording`, `nearby_not_recorded`, `invalid_output`, an option not offered) names the walk to fix with `/record-replays`.

## 3. Stop

```sh
docker compose down
```

Plain `down` keeps the owner's data volume; the walk already deleted what it made.

Report the table to the owner, with the failing rows first.
