# An incident starts at the help request

> **Amended by [ADR 0004](0004-ai-turns-without-tools.md):** the AI answer is no longer a single write-once object. It is an append-only sequence of clarifying questions, replies and advice. Each stored part is immutable, and 409 Conflict applies to rewriting a stored part or adding a turn after the advice.

Tapping "Get help now" creates the incident (status `open`) and commits it before the AI runs; the AI answer is then generated and attached to it. There is no "Save as incident" step. Most drivers want the history kept, so a save button is an extra action for the common case. Keeping is the default, and the rare unwanted incident (an accidental tap, a test) is removed with a hard delete. Committing the incident first also means the help request survives a crash, a closed tab or a lost connection.

## Considered Options

- **Create on "Save as incident"**: "Get help now" is a stateless query. Rejected: an extra action for the common case, and the help request is lost if the app dies before the driver saves.
- **Create a `draft` at "Get help now", promote it on save**: Rejected: needs a draft status, a cleanup job for abandoned drafts, and still has the extra save action.

## Consequences

- **The AI answer is write-once.** It may be missing after a failure or timeout, and generating it is allowed while it is empty (the Result screen offers "Try again"). Once stored, a second write is refused with 409 Conflict. The AI answer keeps the inputs it was answered for (problem type, note, vehicle), so a later edit to the incident cannot make the answer look wrong.
- **Two statuses, `open` and `resolved`, with no transition table.** Only the driver changes the status, in either direction (reopening is allowed). The system never sets it, and the AI arriving or failing does not touch it. The server validates the enum and nothing else, because there is no transition to forbid. This is deliberate, not a missing state machine. The damage report keeps its own state, separate from the incident status.
- **Only the problem type is required.** Location, note, photos, vehicle and the AI answer are optional, because saving must work with no GPS fix and no AI. The server sets `created_at` and the initial status.
- **Delete semantics differ on purpose.** Deleting an incident deletes its photos (rows and files) and its damage report, because an incident's parts do not outlive it. Deleting a vehicle sets `incidents.vehicle_id` to NULL (`ON DELETE SET NULL`), because a driver may keep several vehicles and removing one must not erase its history.
