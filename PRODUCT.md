# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript (user's choice). Responsive web / PWA, mobile-first; desktop uses the same components with different layout and density. Backend: SQLite-backed API.

## Users

Drivers. Primary moment: stranded on the roadside, often at night, cold and stressed, one hand busy, weak signal; they want to know what to do next with minimal reading or typing. Secondary moment: the same person later at home on desktop or tablet, calmly reviewing incident history, finishing a damage report, managing their vehicle profile.

## Product Purpose

Roadside assistant: the driver says what happened (breakdown, flat tyre, battery, out of fuel, pothole damage, other), gets calm step-by-step AI help and what is nearby, and can document the incident (e.g. pothole damage, with a draft report to the road authority) for later. Success: the driver knows the one next step, and incidents are saved in usable form.

## Positioning

Combines an AI-guided diagnosis, real nearby places, and incident documentation (photos, location, draft damage report) in one flow, with honest separation of AI-generated content from real map data.

## Operating Context

- Mobile: roadside, night, weak signal, one-handed use.
- Desktop/tablet: later review of incident history on a map, incident detail with photos, location, AI notes and a draft report to the road authority.
- UI in Polish and English; i18n from day one, no hard-coded strings.
- Emergency number 112 must always be one tap away.

## Capabilities and Constraints

Confirmed:
- Mobile screens: Start (quick-pick tiles, photo, optional text, detected location), Result (AI diagnosis, numbered steps, safety notes, nearby map + list, save as incident), Vehicle profile (model, tyre size, spare wheel / wheel lock key, assistance insurance), Incident history (list with status).
- Desktop screens: History + map (list beside map, potholes as pins), Incident detail (photos, location, AI notes, draft damage report).
- AI diagnosis is an LLM call, provider-agnostic via an OpenAI-compatible interface (local Ollama or a free-tier API). AI output must be labelled as AI, show uncertainty, and never pose as emergency services.
- Demo mode replays pre-recorded real AI responses; used on the public deploy.
- Map and nearby places: OpenStreetMap (Leaflet tiles + Overpass API); labelled as real data, distinct from AI content.
- No auth in the MVP: single-user app. Vehicle profile and incidents persist in a SQLite backend (not per-account, not localStorage only).

Out of scope for MVP (roadmap): auth / multi-user, public transport suggestions, taxi / fuel delivery integrations, community pothole map as a separate feature.

Undecided: working product name (TBD); specific LLM provider/model; hosting/deploy target; how photos are stored.

## Brand Commitments

Working name TBD. Voice: short sentences, second person, reassuring ("Let's sort this out step by step.").

## Evidence on Hand

Only the design brief in DESIGN.md. No real users, data, recorded AI responses, or assets yet; none should be fabricated.

## Product Principles

1. Calm over alarm: lower the user's stress, never add to it.
2. One next step: every screen answers "what do I do now?".
3. Tap, don't type: quick picks and photos over text.
4. Honest AI: distinguish AI output from real data, show uncertainty, never pretend to be emergency services; 112 always one tap away.
5. One app, two moments: roadside and at-home share identity and components.

## Accessibility & Inclusion

Large touch targets (min 48px), high contrast, readable in the dark and usable one-handed under stress. Polish and English supported.
