# How I used AI to build Roadside

This is how I worked with AI on this project: planning, decisions, implementation and checking
the result. How the app itself uses a model is in the [README](README.md) and the
[ADRs](docs/adr/).

## 1. Planning in a regular chat

I started in a regular Claude chat: "I got this assignment, I have a few ideas, help me pick one
and get started." I described each idea in detail and asked for pros, cons and how well each
fit the requirements. The two that lost:

- a navigation app that uses live traffic data to tell you whether your bus is late and whether
  you'd still make it if you left now. It's less creative, and a lot to build for a short MVP;
- a flat-hunting app that ranks homes by how well connected they are to your workplace, your
  family and the places you visit often, by every mode of transport. One flat might have a
  great bike route straight to work but awkward buses, so it's worse when it rains. It would
  depend on transit data that differs from city to city and on maps that may be weak on bike
  routes: too many things could go wrong for an MVP.

Once I had picked Roadside, the deadline worried me more than the idea. I had plenty I wanted to
show, both in the app (desktop and mobile, AI features, an MCP server, integrations with maps
and places) and around it (an installable PWA, CI, Docker, and a public demo deployed on my own
server). I used the same chat to set the scope: what the MVP needs, and what can be cut if
something takes longer than planned or doesn't work. Out of that chat came the kickoff document that the next step started from.

## 2. Mapping and grilling

I've used grilling sessions for a long time, and I like Matt Pocock's
[skills](https://github.com/mattpocock/skills), so I used them here. `/wayfinder` turned the
kickoff document into a [map of tickets](https://github.com/eryk-poradecki/roadside/issues/4):
research questions (Overpass, Nominatim, local and hosted models), a UI prototype, and one
grilling ticket per open decision. `/grill-with-docs` then took each grilling ticket through
its decision tree, one round of questions at a time, until nothing was left open. Every
decision went into an [ADR](docs/adr/) and the terms into [CONTEXT.md](CONTEXT.md). `/to-spec`
then collapsed the map into [one spec](https://github.com/eryk-poradecki/roadside/issues/43),
and `/to-tickets` cut that into small implementation tickets with their dependencies.

When I wasn't sure about an answer, I took the question back to the planning chat for a reality
check. It went both ways:

- **More robust.** In the API grilling ([#12](https://github.com/eryk-poradecki/roadside/issues/12)),
  the agent recommended no server-side guard against a duplicate "Get help now", just a disabled
  button. I thought that was wrong for an app built around a weak signal, but I didn't know
  whether full idempotency logic was needed. After weighing it in the chat, I went with a light
  version of server-side protection, limited to incident creation: a weak signal is the app's
  core constraint, so a response lost after the server committed is the typical failure. That
  became an `Idempotency-Key` stored on the incident itself, with no separate key store
  ([ADR 0005](docs/adr/0005-rest-conventions-and-endpoints.md)).
- **Less work.** For the shared public demo
  ([#124](https://github.com/eryk-poradecki/roadside/issues/124)), one session per visitor was
  the clean fix, but far more work than a demo meant to run for about a week needs. Read-only
  demo vehicles solved the real problem instead
  ([ADR 0013](docs/adr/0013-demo-mode-follows-the-scenario.md)).

## 3. Implementation

With the spec and tickets in place, every ticket went through the same loop: a new session,
`/implement issue #N`, answer the agent's questions, a short manual QA pass, review the PR,
merge, and a new session for the next ticket. `/implement` works test-first with `/tdd` and
ends with `/code-review`, which checks the branch against the repo's standards and against the
ticket, in two separate subagents.

My prompts were short, because the context lives in the repo, not in the prompts: in
[AGENTS.md](AGENTS.md) (which [CLAUDE.md](CLAUDE.md) points to), [CONTEXT.md](CONTEXT.md), the
ADRs and the skills. A typical pair of sessions looked like this:

> `/grill-with-docs` start a grilling session for issue #13 → answering the questions → shared
> understanding, resolve the issue ([ADR 0001](docs/adr/0001-incident-starts-at-help-request.md))
>
> *new session* → `/implement issue #49` → "found a bug: … fix it" → "good, open a PR"

I used Claude Code for most of the work: Opus 5.5 for most tickets, and Fable 5.2 for the early
grilling and architecture, which I tried while it was available on my plan for its launch week.
Codex (6.1 Sol, low reasoning) took the smaller tickets when I was close to my Claude limits. The
low setting was probably too low: it made small UI mistakes, like a sticky header added to
History that hid the offline banner behind it, missing gaps between buttons, or not following
the design decisions closely. I caught most of them reviewing the changes, before the PR.

For the UI I tried [Impeccable](https://impeccable.style), a newer design skill: it keeps the
design context in [PRODUCT.md](PRODUCT.md) and [DESIGN.md](DESIGN.md), and I used it for the
first prototype and later polish passes.

The demo's AI answers were recorded through the Claude Code CLI with `claude-opus-5-5`, using
the project's `/record-replays` skill, and checked with `/demo-check`.

## 4. Quality control

After every bigger change I tested the new feature and its edge cases by hand, and before the
video I did a full pass on desktop and on a phone, in demo and live mode, in both languages.
Most of what I found wasn't caught by tests: it was in what the agents claimed, or in what
nobody had thought of.

**Coding agents**

- **A broken promise.** ADR 0010 says the safety checklist works offline. The checklist only
  appeared after the server had saved the incident, so offline the driver never saw it. Found in
  the QA pass, fixed with an offline view of the checklist and 112
  ([#146](https://github.com/eryk-poradecki/roadside/issues/146)).
- **Side effects.** In demo mode, a failed damage report request wiped the Nearby section
  ([#143](https://github.com/eryk-poradecki/roadside/issues/143)), and opening the full-screen
  map turned the whole screen black.
- **A design flaw only a running demo showed.** Visitors who didn't share a location matched a
  recorded answer in 1 of 8 scenarios, and one visitor editing a seeded car broke its scenarios
  for everyone ([#121](https://github.com/eryk-poradecki/roadside/issues/121),
  [#124](https://github.com/eryk-poradecki/roadside/issues/124)). Demo mode was redesigned
  around picked scenarios ([ADR 0013](docs/adr/0013-demo-mode-follows-the-scenario.md)).

**The app's model**

These were fixed in the prompt (a new prompt version each time) and, where possible, with a new
rule in the eval script:

- "If it's LPG, try switching to petrol" for cars that weren't LPG at all
  ([#90](https://github.com/eryk-poradecki/roadside/issues/90)).
- A push start suggested where it didn't apply, found while reading the recordings
  ([#102](https://github.com/eryk-poradecki/roadside/issues/102)).
- "See Nearby below for a tow truck", when Nearby has no towing category
  ([#106](https://github.com/eryk-poradecki/roadside/issues/106)).
- Hazard lights, vest and triangle for a car in a parking lot. This was really a product gap,
  and it led to the "parked" option ([#93](https://github.com/eryk-poradecki/roadside/issues/93)).

The eval script's rule checks catch the mechanical cases, but passing them didn't mean an
answer was good. So before committing the demo recordings, I reviewed each one, with an agent's
help, against the good and bad examples in [docs/demo-scenarios.md](docs/demo-scenarios.md).

## 5. What was hard

**Scope.** The hardest part was choosing a scope that shows a lot of what I wanted to show in
the time we had: backend and frontend, a database, CI, a deployment, an MCP server, AI. It also
had to stay reasonable, so I wouldn't end up perfecting the Pi deployment while the app itself
wasn't in good shape. That's why the optional tickets carry a cut order: `[cut 1]` (the MCP
server) was the first to drop, as the least valuable, and `[cut 7]` (vision on photos) the last,
as the most valuable for the MVP. In the end every tier was built, `[cut 1]` included, so the
cut order was a safety net I didn't need.

**Agents reading the docs differently from me.** The offline checklist above is one case.
Another is the ticket for this very document
([#66](https://github.com/eryk-poradecki/roadside/issues/66)): the agent that wrote it read
"AI usage" as model evaluation results and a gallery of prompts, while I meant how I worked.

**Several agents at once.** The demo-mode tickets
([#130](https://github.com/eryk-poradecki/roadside/issues/130)–[#135](https://github.com/eryk-poradecki/roadside/issues/135))
were split so they didn't touch the same files, which let several agents work on them in
parallel git worktrees and their PRs merge cleanly. The remaining friction was keeping the local
`main` in sync across the worktrees.

## Where the agent configuration lives

- [AGENTS.md](AGENTS.md): shared instructions for Claude Code and Codex. [CLAUDE.md](CLAUDE.md)
  just includes it.
- [CONTEXT.md](CONTEXT.md) and [docs/adr/](docs/adr/): the domain language and the decisions the
  agents work from. [docs/agents/](docs/agents/) describes the issue tracker and labels.
- [.claude/skills/](.claude/skills/): every skill used, vendored so you don't have to look them
  up. Codex sees the same skills through links in [.agents/skills/](.agents/skills/). Sources
  and licences are in [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md). `record-replays` and
  `demo-check` are this project's own.
- [.claude/agents/](.claude/agents/) and `.agents/skills/impeccable/agents/`: Impeccable's
  subagents.
- [.claude/hooks/](.claude/hooks/) with [.claude/settings.json](.claude/settings.json), and
  [.codex/hooks.json](.codex/hooks.json): format every file an agent edits.
- [.pre-commit-config.yaml](.pre-commit-config.yaml), the [Makefile](Makefile) (`make check`)
  and [CI](.github/workflows/ci.yml): the same quality gates for agents and for me.
