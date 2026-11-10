# Roadside

Roadside assistant for drivers: the driver says what happened, gets calm step-by-step help and real nearby places, and can keep the incident documented for later. One app, two moments: stranded on the roadside (mobile) and reviewing at home (desktop).

## Language

**Driver**:
The single person using the app; there are no accounts in the MVP.
_Avoid_: user, customer, account

**Problem type**:
What happened, as one of the quick picks: flat tyre, flat battery, out of fuel, pothole damage, something else. For an electric vehicle, out of fuel means out of charge; it is the same problem type under another label. Flat battery always means the small starter battery, never the battery that drives an electric car.
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
Everything the assistant returned for one incident's help request: zero to two clarifying questions, each followed by the driver's reply, then the advice. It only grows; no part of it is ever rewritten, and the advice closes it. It may be missing or stop before the advice if the assistant failed or timed out, until a retry succeeds. Each part the assistant produced keeps the inputs it was produced from (problem type, note, vehicle facts, location context, local time), so a later edit to the incident cannot make it look wrong.
_Avoid_: AI response, response, result, conversation

**Clarifying question**:
A turn in which the assistant asks instead of advising: first one immediate "right now" safety step, then one question with two to four options. It is asked only when the answer would change the first steps, and at most twice per incident.
_Avoid_: follow-up, prompt

**Reply**:
The driver's response to a clarifying question: one of the options, a short free text, or "Just give me the steps", which skips further questions and asks for advice at once.
_Avoid_: answer (that word belongs to the AI answer)

**Advice**:
The final part of an AI answer: the diagnosis, the numbered steps, the "stop and call for help if" conditions and what the assistant saw in the photos. Nothing follows it.
_Avoid_: final answer, response, solution

**Diagnosis**:
The part of the advice that says what is probably wrong: the likely cause, how confident the assistant is (likely, possible, unsure) and up to two other possible causes.
_Avoid_: using it for the whole AI answer or the whole advice

**Location context**:
A coarse description of where the driver is, derived from the location: the kind of road (motorway or expressway, main road, local street) and the kind of place (city, town, village, countryside), each possibly unknown. It is what the assistant learns about the location; the assistant never sees the location itself.
_Avoid_: location, address, geocode

**Vehicle**:
One of the driver's cars, with the details the assistant relies on: name, model, year, fuel type, transmission, tyre size, spare wheel, wheel locks and where their key is, registration, assistance insurance. Only the name is required; any detail left empty is unknown, which is not the same as "none" (an unknown spare wheel is not "no spare wheel"). A driver may keep several (e.g. the family's cars).
_Avoid_: car, vehicle profile

**Vehicle facts**:
What the assistant is told about the vehicle chosen for a help request: everything on the Vehicle except the registration, the assistance phone number and the policy number. Assistance counts only when a phone number is known. The AI answer keeps the vehicle facts it was answered for.
_Avoid_: vehicle context, profile

**Default vehicle**:
The driver's daily driver: the vehicle a new help request uses unless the driver picks another. At most one vehicle is the default; there may be none. A vehicle added while there is no default becomes the default. Deleting the default leaves none until the driver picks one.
_Avoid_: favorite, primary, last used vehicle

**Safety checklist**:
Static, non-AI first steps shown immediately for a problem type, before and alongside any AI answer.
_Avoid_: instructions, tips, AI steps

**Nearby place**:
A real place from OpenStreetMap near the driver (tyre shop, fuel station, charging station, car repair), always labelled as map data, never produced by the model.
_Avoid_: suggestion, recommendation

**Damage report**:
A draft letter to the road manager describing pothole damage from an incident, written with the assistant's help and finished by the driver. An incident has at most one; it is a draft until the driver marks it sent. The driver's own details are added only when the letter leaves the app.
_Avoid_: claim, complaint

**Demo mode**:
The app running on pre-recorded real AI answers, so it always works without a model or key; the public deploy runs only in this mode.
_Avoid_: replay mode, mock mode, offline mode

**Public demo**:
The one public instance reviewers can try, always in demo mode; anything entered there is temporary and wiped nightly.
_Avoid_: production, live version, staging

### Screens

**Start screen**:
The mobile first screen: problem-type quick picks, optional photo and note, detected location.

**Result screen**:
The Incident viewed right after "Get help now": safety checklist first, then the AI answer, nearby places and "Mark resolved". It is the same place as Incident detail, seen at the moment of need.
_Avoid_: handoff (the prototype's working name for it)

**Incident detail**:
The same Incident viewed later, from History or on desktop: photos, location, AI notes and the damage report.
_Avoid_: incident page, result page

**History screen**:
The driver's list of past Incidents with their status, shown beside a map on desktop.
_Avoid_: incident list, log

**Vehicles screen**:
Where the driver adds, edits and removes vehicles and picks the default vehicle.
_Avoid_: vehicle profile screen
