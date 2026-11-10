# Triage labels

Minimal label vocabulary for this project. It was written by hand because the `triage` skill isn't used here: this is a solo project with no incoming issue queue to triage. Only the labels the planning/implementation flow actually applies are listed.

| Label             | Meaning                                                                                 | Applied by                                            |
| ----------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `ready-for-agent` | Fully specified, so an agent can pick it up and implement it without further questions. | `to-spec`, `to-tickets`                               |
| `ready-for-human` | Needs a human decision or manual action before (or instead of) agent work.              | Manually, when a ticket turns out to be blocked on me |

Wayfinder's own labels (`wayfinder:map`, `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, `wayfinder:task`) are documented in `docs/agents/issue-tracker.md`.

## Creating the labels

```bash
gh label create ready-for-agent --color 0E8A16 --description "Fully specified; an agent can implement it"
gh label create ready-for-human --color FBCA04 --description "Needs a human decision or manual action"
```
