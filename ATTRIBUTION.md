# Third-party agent skills

This repo vendors a few third-party agent skills so reviewers can see exactly which tools were used to build it. They are copied into the repo on purpose instead of being installed globally, and some are lightly adapted for this project. Each skill keeps its original license.

## Matt Pocock — `mattpocock/skills`

- **Source:** https://github.com/mattpocock/skills
- **License:** MIT, see [`.claude/skills/LICENSE-mattpocock-skills`](../.claude/skills/LICENSE-mattpocock-skills)
- **Location in this repo:** `.claude/skills/`

| Skill                      | Role in this project                                                  | Changes                                                                                  |
| -------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `wayfinder`                | Plans the work as a map of decision tickets on GitHub Issues          | _Planned:_ route UI `prototype` tickets to Impeccable instead of `prototype` (see below) |
| `setup-matt-pocock-skills` | Configures the issue tracker (GitHub Issues) used by the other skills | None                                                                                     |
| `grilling`                 | Resolves wayfinder decision tickets through a guided Q&A              | None                                                                                     |
| `domain-modeling`          | Used alongside `grilling` to shape the domain model                   | None                                                                                     |
| `research`                 | Resolves research tickets (e.g. external API capabilities)            | None                                                                                     |
| `to-spec`                  | Collapses a cleared wayfinder map into one spec                       | None                                                                                     |
| `to-tickets`               | Slices the spec into implementation tickets                           | None                                                                                     |
| `implement`                | Implements a ticket                                                   | None                                                                                     |
| `tdd`                      | Test-first workflow used by `implement`                               | None                                                                                     |

**Not vendored:** `prototype`. UI exploration uses Impeccable, so the project has a single design system instead of two competing ones.

## Paul Bakaus — Impeccable

- **Source:** https://github.com/pbakaus/impeccable · https://impeccable.style
- **License:** Apache 2.0, see [`.claude/skills/LICENSE-impeccable`](../.claude/skills/LICENSE-impeccable) and [`.claude/skills/NOTICE-impeccable.md`](../.claude/skills/NOTICE-impeccable.md). The installer ships no license file, so these were downloaded from the upstream repo. Impeccable builds on Anthropic's `frontend-design` skill.
- **Location in this repo:** `.claude/skills/impeccable/`, `.claude/agents/impeccable-*`, `.agents/skills/impeccable/`, `.codex/hooks.json`
- **Role:** design context (`PRODUCT.md`, `DESIGN.md`), shaping and building UI screens, design critique, plus a hook that runs an anti-pattern detector on UI file edits.
- **Note:** the detector's platform binary (`scripts/bin/`, ~22 MB) is gitignored. To restore it, run:

  ```bash
  npx impeccable install --providers=claude,codex --scope=project
  ```

## Change log for vendored skills

Every change to a vendored skill is recorded here with a reason.

| Date | Skill | Change | Why |
| ---- | ----- | ------ | --- |
| —    | —     | —      | —   |
