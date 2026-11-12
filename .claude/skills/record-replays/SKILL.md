---
name: record-replays
description: "Record the demo scenarios against a live model, review each recording against its good/bad examples, and commit only the approved ones."
disable-model-invocation: true
---

Records what demo mode replays (ADR 0004): AI turns, location context and nearby places, the scenario's light, and the pothole damage report drafts. The scenarios and their good/bad examples are `docs/demo-scenarios.md`; the runner is `backend/scripts/record_replays.py` (`--help`).

It runs on the owner's machine with the owner's login or key. **Ask the owner which provider to use and for any value you lack. Never invent or write credentials.**

## 1. Provider

The **CLI provider** (`claude -p`, `docs/cli-provider.md`) records the demo set, once the owner confirms its terms are cleared for this use; otherwise Gemini through `openai_compatible`. Pass the settings on the command line, where they beat `backend/.env`, so the owner's file stays as it is:

```sh
cd backend
export DEMO_MODE=false LLM_RECORD=true LLM_VISION=true LLM_MAX_IMAGES=3 \
  LLM_TIMEOUT_S=85 LLM_TURN_BUDGET_S=95 LOG_LEVEL=WARNING
# CLI:    LLM_PROVIDER=cli LLM_MODEL=           (empty: the CLI's default model)
# Gemini: LLM_PROVIDER=openai_compatible, LLM_BASE_URL/LLM_MODEL/LLM_API_KEY from the owner
```

Done when the owner has named the provider and the command line has every value it needs.

## 2. Record

```sh
uv run python -m scripts.record_replays --out <scratchpad>/run.md
```

It walks every scenario in-process, on a clock shifted to each scenario's time of day, and **reuses** every recording already present: only missing keys reach the model. Overpass is slow, so a full run takes minutes; run it in the background. The Markdown review goes to `--out` and stdout. Exit 1 means some walk is incomplete or the privacy scan found something.

## 3. Choose branch options

For a question scenario (#3, #7), the walk stops with **Needs a choice**: the question, its exact options, and the branch's `intent` and `option_meaning`. Pick the option that means the intent and write its **exact text** to `backend/recordings/branches/choices.json`:

```json
{"fuel_almost_at_station": {"en": {"safe_walk_to_station": "<exact option>"}}}
```

Rerun step 2. The first turn is reused, so the reply is recorded against the very question a visitor sees. If no option means the intent, the question itself failed review: re-record it (step 4). Done when no walk shows **Needs a choice** for a required branch.

## 4. Review every recording

Read every walk in the review against its scenario's good and bad examples and the "Recording and QA checklist" in `docs/demo-scenarios.md`. **Reject** a recording that is unsafe, overstates the photo, invents a place, phone, distance, cost or legal duty, gives LPG advice, answers in the wrong language, delays 112, or treats a parked car as roadside. A **Problem** line always blocks; a **Review** line (a first turn of the other kind, a settlement off the scenario's) needs judgement.

To re-record one: delete its file (the review names it beside each step), delete any replies under it, then rerun step 2. A re-recorded question changes its options: update `choices.json` from the new ones.

Done when every walk is complete, every recording is approved, and the privacy scan reads **Clean**.

## 5. Prune and commit

```sh
uv run python -m scripts.record_replays --prune --out <scratchpad>/final.md
```

A full run lists **orphans**, recordings no walk reached (an old question's replies, a stale key), and `--prune` deletes them. Then run the `/demo-check` skill. Commit `backend/recordings/` with a `feat:` message naming the provider, the model and the prompt version (every recording carries all three). Done when `/demo-check` passes and the commit holds no orphan.
