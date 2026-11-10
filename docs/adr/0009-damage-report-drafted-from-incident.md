# The damage report is drafted from the incident by one AI call, without a tool

A driver who hits a pothole can turn the incident into a **damage report**: a draft letter to the road manager describing the event and the damage. It is in the MVP. Without it the pothole tile has little to offer (there is no tyre to change), and the report is the payoff of the desktop "secondary moment" that `PRODUCT.md` and `DESIGN.md` build around. The backend renders the facts it already has into a per-locale template, and one schema-constrained model call writes only the narrative. The driver edits the text, copies or prints it, and marks it sent. It is listed in the README as one of the features. Nothing in the README or the demo is labelled a "creative twist": reviewers can judge which feature stands out.

## Considered Options

- **Stretch, README roadmap only.** Rejected: the pothole tile would just record an incident, and the desktop screens would have nothing to finish.
- **A `draft_damage_report` tool the model calls** (the kickoff plan). Rejected for the in-app flow: the driver has already decided they want a report, so the model has no choice to make (the same argument as ADR 0004). The tool survives only as a thin MCP wrapper over the same service.
- **Template only, no AI.** Rejected: it wastes the photos and the note, which the model can turn into a readable description of the damage.
- **A stored claimant profile** (name, address, bank account) on the server. Rejected: an unauthenticated public demo would hold personal data, and the backend has no need to see a bank account.
- **Inferring the road manager from OSM.** Rejected: Nominatim does not reliably return `ref` ([research #32](https://github.com/eryk-poradecki/roadside/issues/32)), and cities with county rights manage national roads inside their borders, so a confident guess would often be wrong.
- **Versioned drafts; a server-side PDF.** Rejected as more than the MVP needs.

## Consequences

- **Only for pothole damage.** A report can be created only when the incident's problem type is `pothole_damage` (422 `not_pothole_damage` otherwise). A flat-tyre incident shows a "Was this caused by a pothole?" hint that switches the type (PATCH, ADR 0005). Changing the type away later **keeps** the report; the gate applies only at creation.
- **What the model sees and returns.** The same fact set as an AI turn (ADR 0004): problem type, note, time of day, coarse location context, the non-sensitive vehicle block (ADR 0003), up to 3 photos when `LLM_VISION` is on, and the cause from the AI answer if one exists. It returns `{description, damage_summary}`, validated with Pydantic and one repair call, within the same turn budget. Registration, policy number and claimant details never reach the model.
- **One text body.** The backend renders a plain-text `body` from a per-locale template: date and time, location label and coordinates, vehicle (including registration, inserted by the template), the narrative, "N photos attached", and placeholders such as `[Your name]` and `[Addressee: road manager]`. The facts are snapshotted at generation. The body is free text the driver edits; the template is the only place the layout lives.
- **Language is chosen at generation**, defaulting to Polish, because the letter goes to a Polish authority while the UI may be in English.
- **Claimant details stay in the browser.** A "Your details" form (name, address, phone, bank account) fills the placeholders only when copying or printing. An optional "Remember on this device" keeps them in `localStorage`. The stored body keeps its placeholders.
- **The addressee is a placeholder plus a static help line**: national roads and expressways → GDDKiA, voivodeship roads → ZDW, others → the county or municipality road manager. This is a factual claim about Polish road administration, so its copy is marked **to verify against an official source**, under the same rule as the safety checklist, and verified in that pass.
- **Labelled as AI content.** The section reads "Drafted by the assistant — check before sending. Not legal advice; claim requirements may vary." The label stays after edits.
- **Lifecycle.** At most one report per incident, status `draft | sent`; only the driver marks it sent. Regenerate overwrites the body after a confirmation and resets the status to `draft`. Deleting the incident deletes the report (ADR 0001). Generation takes the same per-incident lock as AI turns.
- **Export.** Copy to clipboard (never cut) and a print stylesheet with the photos inline, so the browser's "Save as PDF" covers PDF (cuttable). The copied text only counts the photos; the driver attaches them.
- **Demo mode** replays a recorded draft per pothole scenario (the replay key and format follow ADR 0004).
- **Cut order.** Never cut: drafting, editing, copying and marking sent, in the Incident detail section (mobile too, same route). Cuttable, in the report's old place in the cut order: the print view, a dedicated desktop layout, and the MCP tool.

## Endpoints

Under `/api/v1`, following ADR 0005. The report is a singular sub-resource with no id of its own.

| Endpoint | Body / query | Success | Errors |
| --- | --- | --- | --- |
| `GET /incidents/{id}/damage-report` | – | 200 `DamageReportRead` `{status, locale, body, created_at, updated_at}` | 404 |
| `POST /incidents/{id}/damage-report` | `DamageReportCreate` `{locale: "pl"\|"en", replace?: bool}` | 201 `DamageReportRead`; **200** when `replace: true` overwrote an existing report (status back to `draft`) | 404, 409 `damage_report_exists` / `turn_in_progress`, 422 `not_pothole_damage`, 502 `provider_error` / `invalid_output`, 504 `timeout` |
| `PATCH /incidents/{id}/damage-report` | `DamageReportPatch` `{body?, status?}` | 200 `DamageReportRead` | 404, 422 |
| `DELETE /incidents/{id}/damage-report` | – | 204 | 404 |

A failed generation stores nothing. `IncidentSummary` gains `damage_report_status: null | "draft" | "sent"`, so History can show a "Report: draft/sent" chip.
