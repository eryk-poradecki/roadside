# Mobile UI prototype (reference only)

This is the throwaway prototype of the **Start** and **Result** screens. It runs on mock data, and every scenario is a URL query param. This branch is never merged. The build ticket starts from it and removes the mocks.

Decisions behind it: [Prototype: Result screen (mobile) with Impeccable](https://github.com/eryk-poradecki/roadside/issues/8) (see the resolution comment).

```sh
npm ci && npm run dev
```

## Scenarios

- Start screen: `?loc=detecting|found|weak|denied`, `?sheet=<tile>`, `?lang=pl|en`, `?demo=0`.
- Result screen: `?result=tyre|battery|fuel|pothole|other`, plus:
  - `&ai=ok|asking|answered-after-question|unsure|error|loading`
  - `&places=found|searching|none|unavailable|noloc` (default: searching, then found)
  - `&vehicle=full|noins|none`
  - `&resolved=1`
  - `&map=open`

Screenshots at 390 px width are in `prototype-screens/`.

## What to remove when building the real frontend

- `src/mock.ts` (scenario params and timings) and `src/mockAi.ts` (AI answers, vehicles, **sample** places). The places are invented, because live Overpass was unavailable during prototyping.
- The query-param shortcuts in `App.tsx` and `LocationBar.tsx`.
- "Placeholder copy" and "Prototype: sample places" notes in `i18n.ts`.

## What to keep

The visual tokens and component structure in `styles.css`, the PL/EN dictionaries, the icons (`icons.tsx`), the Leaflet map wrapper (`MiniMap.tsx`), and the layout of the screens.

Mocks are not the AI JSON contract. The contract is decided in *AI design*.
