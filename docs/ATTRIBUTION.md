# Third-party agent skills

This repo vendors a few third-party agent skills so reviewers can see exactly which tools were used to build it. They are copied into the repo on purpose instead of being installed globally, and some are lightly adapted for this project. Each skill keeps its original license.

## Matt Pocock — `mattpocock/skills`

- **Source:** https://github.com/mattpocock/skills
- **License:** MIT, see [`.claude/skills/LICENSE-mattpocock-skills`](../.claude/skills/LICENSE-mattpocock-skills)
- **Location in this repo:** `.claude/skills/`
- **Version:** `code-review` and `grill-with-docs` are copied unmodified from plugin version 1.3.1, commit [`49dd158`](https://github.com/mattpocock/skills/commit/49dd158d1076134a641b33efb035946536778336)

| Skill                      | Role in this project                                                                                                   | Changes                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `wayfinder`                | Plans the work as a map of decision tickets on GitHub Issues                                                           | _Planned:_ route UI `prototype` tickets to Impeccable instead of `prototype` (see below) |
| `setup-matt-pocock-skills` | Configures the issue tracker (GitHub Issues) used by the other skills                                                  | None                                                                                     |
| `grill-with-docs`          | Entry point for a grilling session: loads `grilling` and `domain-modeling`, so decisions land in ADRs and `CONTEXT.md` | None                                                                                     |
| `grilling`                 | Resolves wayfinder decision tickets through a guided Q&A                                                               | None                                                                                     |
| `domain-modeling`          | Used alongside `grilling` to shape the domain model                                                                    | None                                                                                     |
| `research`                 | Resolves research tickets (e.g. external API capabilities)                                                             | None                                                                                     |
| `to-spec`                  | Collapses a cleared wayfinder map into one spec                                                                        | None                                                                                     |
| `to-tickets`               | Slices the spec into implementation tickets                                                                            | None                                                                                     |
| `implement`                | Implements a ticket                                                                                                    | None                                                                                     |
| `tdd`                      | Test-first workflow used by `implement`                                                                                | None                                                                                     |
| `code-review`              | Reviews a branch against the repo standards and the originating issue, in two subagents; run at the end of `implement` | None                                                                                     |

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

## Sample photos

Demo mode refuses uploads and offers these bundled photos instead (ADR 0002). Each is from Wikimedia Commons (the 1280 px rendition) or Flickr (the largest public size, 1024 px), re-encoded as JPEG without metadata. None shows a number plate or a face.

**Location in this repo:** `backend/app/assets/sample_photos/`

| File                   | Shows                                            | Original                                                                                                                 | Author          | License                                                         |
| ---------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | --------------- | --------------------------------------------------------------- |
| `flat_tyre.jpg`        | A flat front tyre                                | [Flat Tyre.jpg](https://commons.wikimedia.org/wiki/File:Flat_Tyre.jpg)                                                   | Pujanak         | Public domain (as marked on its Commons page)                   |
| `screw_in_tread.jpg`   | A screw in a tyre tread                          | [Flat Tire.jpg](https://commons.wikimedia.org/wiki/File:Flat_Tire.jpg)                                                   | Godstar23       | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)   |
| `pothole.jpg`          | A deep pothole                                   | [A pothole in Dilova Street in Kyiv.jpg](https://commons.wikimedia.org/wiki/File:A_pothole_in_Dilova_Street_in_Kyiv.jpg) | Роман Рябенко   | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)   |
| `empty_fuel_gauge.jpg` | A fuel gauge on empty with the low-fuel light on | [2003 Honda Civic fuel gauge empty.JPG](https://commons.wikimedia.org/wiki/File:2003_Honda_Civic_fuel_gauge_empty.JPG)   | BrokenSphere    | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| `rim_damage.jpg`       | A chipped alloy rim and a deflated tyre          | [Flat tyre and minor damage to alloy wheel](https://www.flickr.com/photos/10515323@N08/48546235531)                      | Hazel Nicholson | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)       |

The API also returns each photo's credit in `GET /api/v1/config` (`sample_photos[].credit`).

## Change log for vendored skills

Every change to a vendored skill is recorded here with a reason.

| Date | Skill | Change | Why |
| ---- | ----- | ------ | --- |
| —    | —     | —      | —   |
