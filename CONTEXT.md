# Roadside

Roadside assistant for drivers: the driver says what happened, gets calm step-by-step help and real nearby places, and can keep the incident documented for later. One app, two moments: stranded on the roadside (mobile) and reviewing at home (desktop).

## Language

**Driver**:
The single person using the app; there are no accounts in the MVP.
_Avoid_: user, customer, account

**Problem type**:
What happened, as one of the quick picks: flat tyre, flat battery, out of fuel, pothole damage, something else.
_Avoid_: tile (that is the UI control that picks it), category, incident type

**Incident**:
One roadside event, starting the moment the driver asks for help ("Get help now"): problem type, optionally a vehicle, location, note, photos, the nearby places shown, and the AI answer once it arrives. The incident outlives a deleted vehicle; its photos and damage report do not outlive the incident. Every help request is an incident; there is no separate "save" step, and unwanted ones are deleted.
_Avoid_: case, event, ticket, report, draft

**Photo**:
A picture the driver attaches to an incident, up to five, each added or removed on its own and never edited. Photos taken at the help request may be seen by the assistant; photos added later document the incident (e.g. for a damage report) and do not change the AI answer.
_Avoid_: image, attachment, picture

**Sample photo**:
A bundled, freely licensed photo the driver can attach in demo mode instead of uploading their own; once attached it is an ordinary photo of that incident.
_Avoid_: demo image, stock photo

**Open** / **Resolved**:
The two statuses of an incident. Every incident starts open; only the driver changes it, marking it resolved when the situation is sorted or reopening it.
_Avoid_: closed, done, archived

**AI answer**:
Everything the assistant returned for one incident's help request. It is a record of what the assistant said and never changes once stored; it may be missing if the assistant failed or timed out, until a retry succeeds. It keeps the inputs it was answered for (problem type, note, vehicle), so a later edit to the incident cannot make it look wrong.
_Avoid_: AI response, response, result

**Diagnosis**:
The part of an AI answer that says what is probably wrong, next to the steps and the stated uncertainty.
_Avoid_: using it for the whole AI answer

**Vehicle**:
One of the driver's cars, with the details the assistant relies on: model, tyre size, spare wheel, wheel lock key, assistance insurance. A driver may keep several (e.g. the family's cars).
_Avoid_: car, vehicle profile

**Default vehicle**:
The driver's daily driver: the vehicle a new help request uses unless the driver picks another. At most one vehicle is the default; there may be none.
_Avoid_: favorite, primary, last used vehicle

**Safety checklist**:
Static, non-AI first steps shown immediately for a problem type, before and alongside any AI answer.
_Avoid_: instructions, tips, AI steps

**Nearby place**:
A real place from OpenStreetMap near the driver (tyre shop, fuel station, car repair, towing), always labelled as map data, never produced by the model.
_Avoid_: suggestion, recommendation

**Damage report**:
A draft document to the road authority describing pothole damage from an incident.
_Avoid_: claim, complaint

**Demo mode**:
The app running on pre-recorded real AI answers, so it always works without a model or key; the public deploy runs only in this mode.
_Avoid_: replay mode, mock mode, offline mode

### Screens

**Start screen**:
The mobile first screen: problem-type quick picks, optional photo and note, detected location.

**Result screen**:
The mobile screen after "Get help now": safety checklist first, then the AI answer, nearby places and "Mark resolved".
_Avoid_: handoff (the prototype's working name for it)

**Vehicles screen**:
Where the driver adds, edits and removes vehicles and picks the default vehicle.
_Avoid_: vehicle profile screen
