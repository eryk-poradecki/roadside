# Design Brief

> Name: Roadside. A roadside assistant for drivers: describe what happened, get calm step-by-step help and what's nearby; document incidents (e.g. pothole damage) for later.

## Users & context of use

**Primary moment (mobile):** a driver stuck on the roadside — often at night, cold, stressed, one hand busy, weak signal. They don't want to read or type much; they want to know _what to do next_.

**Secondary moment (desktop/tablet):** the same person at home, later, calmly reviewing incident history, finishing a damage report, managing their vehicle profile.

Both are **the same app**: same visual language, same components. Desktop changes **layout and density**, not mood or identity.

## Design principles

1. **Calm over alarm.** The user is already stressed; the UI should lower the temperature. No flashing, no red-everywhere, no warning-sign aesthetics.
2. **One next step.** Every screen answers "what do I do now?" with one clear primary action.
3. **Tap, don't type.** Quick-pick tiles (flat tyre, battery, out of fuel, pothole damage, other), photo instead of description, free text optional.
4. **Readable in the dark.** Dark theme by default, high contrast, large touch targets (min 48px), generous spacing.
5. **Honest AI.** Clearly show what comes from AI vs. real data (map places). Show uncertainty; never pretend to be emergency services. Emergency number (112) always one tap away.

## Visual direction

- **Mood:** a well-designed navigation/car dashboard at night — quiet, competent, trustworthy.
- **Avoid:** road-sign / reflective-vest aesthetics, driving-school website look, purple gradients, generic SaaS cards, emoji-heavy UI.
- **Color:** deep graphite/near-black neutrals; **one warm accent** (e.g. soft amber) used sparingly for primary actions and the user's location — not as a "warning" theme. Semantic red only for genuine danger/emergency.
- **Typography:** one clean, highly legible sans with good numerals; clear hierarchy; avoid default Inter look-alike styling.
- **Shape & motion:** soft but not bubbly corners; minimal, purposeful motion (state changes, loading the AI answer), nothing decorative.
- **Map:** muted, dark map style so markers and the accent stand out.

## Screens

**Mobile**

1. Start — "What happened?" quick-pick tiles + photo + optional text; location detected.
2. Result — AI diagnosis, numbered steps, safety notes, "nearby" (map + list: tyre shop, fuel, etc.), ending with "Mark resolved" (every help request is already an incident, ADR 0001).
3. Vehicle profile — model, tyre size, spare wheel / wheel lock key, assistance insurance.
4. Incident history — list with status.

**Desktop**

1. History + map — incidents list next to a map (potholes visible as pins).
2. Incident detail — photos, location, AI notes, draft damage report to road authority.

## Navigation

- **One app shell, bottom tab bar with three tabs:** Help (Start), History, Vehicles. Not a hamburger menu: hidden navigation costs an extra tap and hurts discoverability.
- **The tab bar shows only on top-level screens** (Start, History, Vehicles). Flow screens (the help sheet, Result, Incident detail, the vehicle form) hide it and use Back plus their own bottom dock. **The 112 control stays on every screen.**
- **On Start, 112 must not become a second full-height bottom row.** Put it either in a compact bar directly above the tab bar or in the content above the tiles. Pick one, and show both in the prototype only if it's unclear.
- **Desktop:** same routes. The tabs become a sidebar or top navigation, with the same components in a different layout (one app, two moments).
- **Result and Incident detail are the same route** (`/incidents/:id`): Result is the incident viewed right after creation, and History links to the same place.
- **Routes:** `/` (Start), `/incidents` (History), `/incidents/:id` (Result / detail), `/vehicles`, `/vehicles/new`, `/vehicles/:id`. See ADR 0008.
- **Map attribution** ("© OpenStreetMap contributors", linked) stays fully visible on the inline and the full-screen map, never under the sheet or the dock.

## Content & tone

- Short sentences, second person, reassuring: "Let's sort this out step by step."
- UI available in **Polish and English** (i18n from day one; no hard-coded strings).

## Out of scope for MVP (roadmap)

Public transport suggestions, taxi / fuel delivery integrations, community pothole map as a separate feature.
