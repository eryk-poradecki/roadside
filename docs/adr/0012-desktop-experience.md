# Desktop is the "at home" moment: a sidebar shell, no dock, and 112 only where an emergency is plausible

Desktop is how most reviewers first see the app, and its moment is reviewing at home, not being stranded (DESIGN.md: one app, two moments). From 1024 px wide, the app uses a desktop layout. It has the same routes, tokens and components as mobile, but a different shell. Below 1024 px everything, tablets included, gets the mobile layout unchanged. Desktop is designed and checked at 1280, 1440 and 1920 px and must read as a desktop app, not a stretched tablet. Decided in #111.

## Decisions

- **One breakpoint, 1024 px**, used for the shell, the 112 rules and every two-column layout (it replaces #77's 900 px). There is no tablet tier.
- **A sidebar on every route** (wordmark, Help / History / Vehicles, language switch) replaces the bottom tab bar. Flow screens (incident, report, edit, vehicle form) keep their Back link, and the sidebar highlights the section they belong to.
- **No dock on desktop, and no dock action.** The Result screen's "Call <insurer>" becomes a normal row in the incident's vehicle area: "Assistance: <insurer> · <phone>" (a `tel:` link, with the policy number when there is one). It shows only while the incident is open, and only if the **incident's own vehicle** (`vehicle_id`, with its current data, never the default vehicle) has an assistance phone. No vehicle, or a deleted one, means no row.
- **No global 112 on desktop.** This is a deliberate exception to DESIGN.md's "112 stays on every screen". 112 appears only:
  - in the incident header while the incident is **open**, as a normal `tel:112` link. If the AI answer is urgent, that link takes the urgent style and the urgent banner gets its own inline "Call 112";
  - inside the Start screen's trial column, which keeps its mobile behaviour.
  Nobody uses a laptop for the roadside moment, so a permanent emergency control there only adds noise. Mobile keeps the rule unchanged. **Don't "fix" desktop back to a global 112.**
- **Start screen on desktop:** a QR code ("In a real roadside moment you'd use your phone, so scan to open it there") beside "Or try it here", the normal flow in a narrow column. The QR code encodes `window.location.origin`, is generated in the browser, and is **hidden on localhost and private IPs**, where a phone couldn't reach the address. In the QR code's place there is then a short "How it works at the roadside" panel: three steps (pick what happened, safety steps at once, AI advice plus real nearby places from map data) and a hint that on a phone it opens full screen, so try the browser's device mode. Either way the page has two parts: the left panel and the trial column. The help sheet opens as a centred modal, and "Get help now" leads to the full desktop Result.
- **Width:** desktop uses the width the way desktop apps do: two columns where the content has two parts, about 70ch for running text. There is no single fixed cap; exact widths are chosen during the build. Depth comes from existing tokens only. A new colour or gradient needs a DESIGN.md change.
- **Report screen:** the letter takes the larger left column, with the details, the road manager and the actions on the right. The letter is a plain `<textarea>` that behaves like a normal text editor (text cursor, drag and double-click selection, standard shortcuts, tall or auto-growing). No touch-oriented styles (`user-select`, `touch-action`) apply at desktop widths.
- **Vehicles** stays a single column, with field groups in two columns in the vehicle form. Incident edit is one form at about 70ch.

## Considered Options

- **A quiet 112 row in the sidebar or header.** Rejected: it is a global emergency control in a context where no emergency happens, and the "try it here" column already shows the real mobile behaviour.
- **A breakpoint at 900 px**, as in #77. Rejected: a 900 to 1024 px window is a tablet or a narrow laptop window, which gets more from the mobile layout.
- **A master–detail Vehicles screen** (list beside the form). Rejected for now: nested routing plus an unsaved-changes state, for little gain.
- **An in-app phone-frame preview in demo mode.** Cut: the QR code and the trial column already show both moments.
