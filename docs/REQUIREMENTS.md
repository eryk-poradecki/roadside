# Task requirements & acceptance checklist

Requirements of the Xelerit recruitment task, paraphrased from the task email and the candidate webinar (9 Nov 2026). **Every item marked "Required" must be met before submitting.** Use this file as the final acceptance checklist.

## Deadline & submission

- [ ] **Required:** send the public GitHub repo link + full name to the company email by **15 Nov 2026, 23:59**.
- [ ] **Required:** repository is **public**.

## Application

- [ ] **Required:** a small but working **full-stack web app (MVP)** related to **transport**.
- [ ] **Required:** backend API supports **basic CRUD** operations for the chosen functionality.
- [ ] **Required:** frontend communicates smoothly with the API. **CORS configured.**
- [ ] **Required:** database is **in-memory or SQLite**, so no external DB server has to be set up.
- [ ] **Required:** frontend and backend are **separated** (separate folders in the repo).
- Expected: intuitive, pleasant UX/UI.
- Expected: a **"creative twist"**, i.e. one small but clever, distinctive feature. Their examples: transport recommendation based on weather, carbon-footprint comparison, eco points. Small beats complex.
- Optional, but a clear plus: an **AI feature** in the app (one well-designed prompt, a simple agent, or a few cooperating agents). What counts is the idea, its usefulness and understanding it, not its complexity.
- Optional, small plus: a **deployed** version.
- Should be an original idea, not a rewrite/adaptation of an existing platform.

## What reviewers evaluate

1. **Architecture & organisation:** logical layering, FE/BE separation.
2. **Code quality & readability:** good practices on both server and client.
3. **API design:** correct REST endpoints, smooth FE↔BE communication.
4. **UX/UI:** turning the idea into a working, good-looking interface.
5. **Creative twist.**
6. **AI workflow:** said at the webinar to weigh **as much as the app itself**. They look at agent instruction files, custom skills/commands, defined subagents, how the work and environment are organised. Whether code was hand-written or generated doesn't matter; documenting _how_ AI was used does. Commit history is not reviewed.

## README.md (required sections)

- [ ] Short description of the app and its features.
- [ ] Technical description: technologies used, notable solutions.
- [ ] Clear **step-by-step** instructions to run it locally, for **both API and frontend**.
- [ ] Short description of **how AI tools were used** (which tools, for what; the webinar also asked for example prompts).

## Demo video

- [ ] **Required:** a short video (**.gif or .mp4**) showing the app working, **added to the repository**. Keep the file small enough for GitHub (well under 100 MB).
- Length: a few minutes at most; 3–5 min is the upper bound, shorter is fine.
- Voice-over is optional (a small plus if in English); **subtitles are appreciated**.

## Agent configuration

- [ ] **Required:** commit any agent instruction files used (e.g. `AGENTS.md`, `CLAUDE.md`, rules files, custom instructions, skills, subagents).

## Context from the webinar (not formal requirements)

- Tech: any stack. Their frontends are mostly React / Angular (some Next.js, Vue); backends mostly Java / Python / C#, but others are accepted.
- Interviews include technical questions about the project and general topics (OOP, databases), partly in English. English communication is assessed alongside technical skills.
- They are "AI native" and mainly use Claude; heavy, disciplined AI use is expected.
