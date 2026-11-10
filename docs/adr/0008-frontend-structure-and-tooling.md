# Frontend structure, data layer and tooling

The frontend is a React 19 + Vite + TypeScript PWA, laid out layer-first like the backend (ADR 0007). The existing prototype moves into it and keeps its styling, icons, font and plain Leaflet. react-i18next replaces the prototype's hand-rolled dictionaries but keeps them typed. React Router gives one URL per screen, with one route per Incident for both the Result screen and Incident detail. TanStack Query owns server state, and the client and its types are generated from the backend's OpenAPI schema with `@hey-api/openapi-ts`. Every version below was checked against the npm registry on 2026-11-10 by resolving the whole set with `npm install --package-lock-only`. It resolves with no peer conflicts, and nothing is assumed.

## Considered Options

- **Feature-first folders** (`features/{help,incidents,vehicles}`), or **stay flat** like the prototype. Rejected: with five screens feature folders don't pay off, and a flat folder stops working once the API layer arrives. Chosen: **layer-first**, matching the backend, so the repo reads the same on both sides.
- **Keep the prototype's TS dictionaries + `LangContext`**, **JSON resource files with a key-parity test**, or **a shim around the dictionaries.** react-i18next is a kickoff decision. Chosen: **TS resource objects** registered through `CustomTypeOptions`. `pl` is typed as `typeof en`, so a missing key or a bad `t()` call fails `tsc`, with no extra test.
- **File-less screen state** (the prototype's `useState` switch). Rejected: no deep links, no Back button, and a reload in the middle of an AI answer loses the screen. **React Router data mode (loaders)** rejected too: data lives in TanStack Query, and two data layers would compete. Chosen: **React Router, declarative mode**.
- **Separate Result and Incident detail routes**, or a desktop component tree. Rejected: ADR 0001 creates the Incident at "Get help now", so the Result screen is the Incident viewed right after creation. Chosen: **one `/incidents/:id`** with responsive layout. DESIGN.md: one app, two moments.
- **Plain `fetch` + `useState`/`useEffect`.** Rejected: the core flow needs a create with an `Idempotency-Key`, uploads that must settle before the AI turn (ADR 0002), an AI turn of up to ~100 s, a nearby 503 that keeps the old snapshot (ADR 0005), and list invalidation after PATCH/DELETE. By hand, that means rewriting loading, error, retry and cache logic in every screen. Chosen: **TanStack Query v5**.
- **`openapi-typescript` + `openapi-fetch`.** The smallest types-only option, but `openapi-typescript` 7.13.0 has a non-optional peer `typescript ^5.x`, so `npm ci` fails against TS 6 without an `overrides` hack. **orval.** No TS peer, but its output is heavy and its generated hooks get in the way of custom flow logic. **Hand-written types.** Rejected: ADR 0005 promises types from OpenAPI, guarded by the drift job (ADR 0007). Chosen: **`@hey-api/openapi-ts`** with its fetch client and TanStack Query plugin. It is pre-1.0, so it's pinned to an exact version.
- **TypeScript 7** (the prototype's 7.0.2, the native Go port). Rejected for now: `typescript-eslint` 8.72.2 needs `typescript >=4.8.4 <6.1.0`, and the type-aware lint rules are the point. Chosen: **TypeScript `~6.0.3`**, the last release with the JS API. Move to 7 when `typescript-eslint` supports it.
- **ESLint 10.** `eslint-plugin-jsx-a11y` 6.10.2, the latest (Oct 2024), allows only ESLint ≤9, so ESLint 10 + jsx-a11y fails `npm ci`. Rejected alternatives: the `eslint-plugin-jsx-a11y-x` 0.2.0 fork (0.x, little known), or ESLint 10 with no a11y lint. A driver stranded at night makes accessibility a product requirement, not polish. Chosen: **ESLint 9.39.5** (still patched, Jul 2026) + **jsx-a11y 6.10.2**. Move to 10 when jsx-a11y supports it.
- **Biome** instead of ESLint + Prettier. One fast tool, but weaker type-aware and a11y coverage, and the kickoff names ESLint + Prettier. Rejected.
- **CSS Modules** or **Tailwind.** Rejected: the Impeccable design tokens already live in CSS custom properties, and a second styling system mid-week would split them. Chosen: **plain CSS**.
- **`react-leaflet`.** Rejected: it adds little for three maps, and mixing it with the prototype's imperative Leaflet would mean two map systems. Chosen: **plain Leaflet everywhere**, behind one map module.
- **A different tile provider for the dark map** (e.g. CARTO Dark Matter). Not needed: the prototype darkens the **standard OSM tiles** (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) with a CSS filter on the tile pane, so no second provider, attribution or set of terms comes in.
- **Manifest-only PWA**, or **runtime-caching incident data.** Manifest only gives no offline shell. Caching incidents moves toward the out-of-scope offline queue. Chosen: **precache the app shell only**.
- **React Compiler**, or **a global state library** (Zustand, Redux). Rejected: no measured need. Server state is TanStack Query. The help-sheet draft (problem type, photo, note) is local state in the Start screen until "Get help now".
- **A frontend coverage gate**, **snapshot tests.** Rejected, same reasoning as ADR 0007. Frontend tests are lighter than the backend ones on purpose.

## Consequences

### Versions (verified on npm, 2026-11-10)

Pinned with `~` (patch only), and exact where marked `=`. Node **24 LTS** (`.nvmrc`, `"engines": {"node": ">=24.15"}`, the floor set by jsdom 31 and react-router 8), with **npm** and a committed `package-lock.json`.

| Package | Version | Notes |
| --- | --- | --- |
| `react`, `react-dom` | 19.3.1 | from the prototype |
| `react-router` | 8.5.1 | declarative mode, Node ≥22.22 |
| `@tanstack/react-query` (+ `-devtools`, dev only) | 5.107.1 | |
| `i18next` / `react-i18next` | 27.1.1 / 18.0.1 | react-i18next peer accepts TS 5–7 |
| `i18next-browser-languagedetector` | 8.3.0 | |
| `leaflet` (+ `@types/leaflet`) | 1.9.4 | plain, no `react-leaflet` |
| `lucide-react` | 1.71.0 | |
| `@fontsource-variable/atkinson-hyperlegible-next` | 5.3.0 | |
| `typescript` | 6.0.3 | not 7.x: typescript-eslint peer `<6.1.0` |
| `vite` / `@vitejs/plugin-react` | 8.3.7 / 6.3.0 | |
| `eslint` / `@eslint/js` | 9.39.5 | not 10.x: jsx-a11y peer `≤9` |
| `typescript-eslint` | 8.72.2 | peer eslint `^8.57 \|\| ^9 \|\| ^10`, TS `<6.1` |
| `eslint-plugin-react-hooks` | 7.1.1 | |
| `eslint-plugin-jsx-a11y` | 6.10.2 | |
| `eslint-config-prettier` / `prettier` | 10.1.8 / 3.9.10 | |
| `@hey-api/openapi-ts` | =0.99.0 | pre-1.0, exact pin; TS peer `>=5.5.3 \|\| >=6.0.0` |
| `vite-plugin-pwa` | 2.0.0 | peer vite `…\|\| ^8`, workbox 7.4.1 |
| `vitest` | 5.1.0 | peer vite `^6.4 \|\| ^7 \|\| ^8` |
| `jsdom` | 31.0.0 | |
| `@testing-library/react` / `user-event` / `jest-dom` | 16.3.3 / 14.6.9 / 7.0.1 | |
| `msw` | 3.0.4 | |

Upgrades go through a PR that re-runs `npm ci` and `make check`.

### Layout

```
frontend/
  src/
    main.tsx            # QueryClientProvider, i18n init, RouterProvider
    routes.tsx          # route table
    screens/            # one per route: Start, History, IncidentScreen, Vehicles, VehicleForm
    components/         # AppShell, TabBar, EmergencyBar, Sheet, LocationBar, Nearby, …
      map/              # the only module that imports leaflet
    api/
      generated/        # @hey-api output, committed, excluded from lint/format
      client.ts         # base URL, ApiError, problem parsing
      incidents.ts …    # hand-written hooks that wrap generated query/mutation options
    i18n/               # index.ts, en.ts, pl.ts
    lib/                # geo (haversine, distance format), small pure helpers
    styles/             # tokens.css, base.css; component CSS sits next to its component
  test/                 # MSW handlers and fixtures, setup
```

The prototype's `mock.ts` and `mockAi.ts` are deleted. The real API replaces them in the app, and MSW handlers in tests.

### i18n

- `i18n/en.ts` is the source. `i18n/pl.ts` is typed `typeof en`. Both are bundled, with no lazy loading.
- Plurals use i18next's `Intl.PluralRules` suffixes (`_one`, `_few`, `_many`, `_other`) instead of the prototype's `plural()`.
- Detection order: `querystring` (`?lang=`), then `localStorage` (`lang`), then `navigator`, with fallback `en`. This is the prototype's `initialLang()`. `document.documentElement.lang` follows the language.
- The AI turn's `locale` (ADR 0004/0005) is `i18n.resolvedLanguage`.

### Routing and navigation

| Route | Screen | Tab bar |
| --- | --- | --- |
| `/` | Start | yes (Help) |
| `/incidents` | History (desktop: list beside map) | yes |
| `/incidents/:id` | Result right after creation, Incident detail later | no |
| `/vehicles` | Vehicles | yes |
| `/vehicles/new`, `/vehicles/:id` | Vehicle form | no |

- One `AppShell` layout route renders the tab bar on top-level screens only. Flow screens show Back and their own bottom dock. The 112 control is on every screen.
- Desktop uses the same routes, with the tabs as a sidebar or top navigation. Layout differs through CSS breakpoints, plus `useMediaQuery` only where structure differs (the map beside the list).
- The visual rules are in DESIGN.md "Navigation" and get shaped with Impeccable during the build.

### Data layer and errors

- `QueryClient` defaults: queries retry only on network errors and 5xx (max 2). Mutations don't retry, except `POST /incidents`, which is safe to repeat because of its `Idempotency-Key` (ADR 0005).
- Hand-written hooks carry the flow logic: a fresh `Idempotency-Key` per "Get help now", uploads settling before the first AI turn (ADR 0002), and invalidating the incident and the list after an AI turn, PATCH or DELETE.
- `GET /config` and `GET /vehicles` load at app start (ADR 0005 core flow). Config has `staleTime: Infinity`.
- Base URL: `VITE_API_BASE_URL` (ADR 0007), set to `http://localhost:8000` in dev and empty in the compose build (same-origin `/api`).
- The client throws one `ApiError` carrying the parsed RFC 9457 problem. The UI maps `reason` to `errors.<reason>`, falling back to `errors.generic`, and never shows the server's `detail`. A fetch that fails without a response becomes reason `offline` and feeds the offline banner.

### Codegen

- `npm run openapi` (and `make openapi`) regenerates `src/api/generated/` from the backend's exported `openapi.json`. The CI `openapi-drift` job (ADR 0007) runs it and fails on a diff.

### Map

- `components/map/` is the only importer of `leaflet`. It serves the 240 px preview, the full map and the desktop History map.
- Tiles: `https://tile.openstreetmap.org/{z}/{x}/{y}.png` by default. The URL comes from `VITE_TILE_URL`, so it can change without a code edit, as the policy recommends. Dark styling is the CSS filter on `.leaflet-tile-pane`, so markers and attribution stay unfiltered.
- The OSM tile usage policy (checked 2026-11-10) allows a low-traffic public demo, which is best effort with no SLA. Its rules here:
  - Attribution "© OpenStreetMap contributors" (PL: "© autorzy OpenStreetMap") links to `https://www.openstreetmap.org/copyright`. It stays **fully visible and unobstructed on both the inline and the full-screen map**: not under the bottom sheet or the dock, and not behind a toggle. On the full map it is rendered above the sheet.
  - No prefetching and no offline tile caching: the service worker doesn't touch tiles (below).
  - Never send a restrictive `Referrer-Policy`. Neither Leaflet's `referrerPolicy` nor nginx (ADR 0007, Pi deploy) may set `no-referrer`. The browser default is fine.
  - Optional, recommended: a "Report a map issue" link to `https://www.openstreetmap.org/fixthemap` next to the attribution on the full map.

### PWA

- `vite-plugin-pwa` with `generateSW`, `registerType: 'autoUpdate'`. The service worker is registered in production builds only, so dev and the Playwright run (ADR 0007) stay free of SW caching.
- Precache the app shell only, including the bundled i18n resources. `/api/*` and OSM tiles are network-only, so tile caching is left to the browser's HTTP cache.
- The manifest has the name, icons and `theme_color`/`background_color` from the design tokens, with `display: standalone`.
- No queued writes. An offline banner shows when a request fails with `offline`.

### Lint, format, types

- ESLint flat config:
  - `@eslint/js` recommended
  - `typescript-eslint` `strictTypeChecked` with `projectService`
  - `react-hooks` recommended
  - `jsx-a11y` recommended
  - `eslint-config-prettier` last
  - ignores `src/api/generated/`
- Prettier keeps the prototype's style: no semicolons, single quotes.
- `tsconfig`: `strict`, `noUncheckedIndexedAccess`.
- Hooks (ADR 0007 "frontend linters as local hooks"): Prettier and ESLint on staged files in `pre-commit`. `tsc --noEmit` and the tests run only in CI and `make check`, like mypy.

### Tests

- Vitest + jsdom + React Testing Library + `user-event` + `jest-dom`, with MSW at the network level, so tests run through the real generated client. Queries are by role or label, which doubles as an a11y check. Leaflet is mocked; Playwright covers the real map.
- Covered:
  - the core flow screens: tile → "Get help now" → checklist; an `ask` turn → reply → `answer`; a failed turn (`reason: timeout`) → "Try again"; Mark resolved
  - Vehicle form validation
  - Polish plurals (1, 2–4, 5, 12–14)
  - `lib/` utilities
