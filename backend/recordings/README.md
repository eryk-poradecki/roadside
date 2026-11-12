# Demo recordings

What demo mode replays (ADR 0004), made from the scenarios in `docs/demo-scenarios.md` by the
`/record-replays` skill and checked by `/demo-check` (#63):

- one JSON file per recorded AI turn or damage report draft, named by its replay key, each
  naming its provider, model and prompt version;
- `places/`: per scenario, the recorded location context and label, whether it was dark, and
  the nearby places at 5 and 25 km;
- `branches/choices.json`: the exact option chosen for each clarifying-question branch.

The Docker image copies this directory, so `docker compose up` replays whatever is committed;
a turn with no recording gets the labelled fallback. No recording holds the recorded point, a
registration, a policy number or the driver's phone: the recording run scans for them.
