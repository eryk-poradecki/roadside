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
One roadside event the driver chose to keep: problem type, location, optional photo and note, and what the assistant said.
_Avoid_: case, event, ticket, report

**Vehicle profile**:
The driver's car details the assistant relies on: model, tyre size, spare wheel, wheel lock key, assistance insurance.
_Avoid_: car, vehicle settings

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
The mobile screen after "Get help now": safety checklist first, then the AI answer, nearby places and "save as incident".
_Avoid_: handoff (the prototype's working name for it)
