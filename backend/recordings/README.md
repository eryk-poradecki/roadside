# Demo recordings

What demo mode replays (ADR 0004): one JSON file per recorded AI turn, plus `places/` with
the recorded location context and nearby places per scenario. A recording run
(`DEMO_MODE=false`, `LLM_RECORD=true`) writes here. The Docker image copies this directory,
so `docker compose up` replays whatever is committed; a turn with no recording gets the
labelled fallback.

The recordings themselves come with #63. This file also keeps the directory in git, so the
Dockerfile's `COPY recordings` works before then.
