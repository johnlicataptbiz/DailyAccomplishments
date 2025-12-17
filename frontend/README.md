# Today Brief (Daily Accomplishments)

A single-page React + TypeScript dashboard that renders the Daily Accomplishments "Today Brief" experience. It loads the latest `ActivityReport-<DATE>.json`, generates Slack-ready headline bullets, and exposes proof receipts and inline editing tools (rename, merge, hide) with localStorage persistence.

## Scripts

```bash
npm install          # install dependencies
npm run dev          # run Vite dev server (http://localhost:5173/#/today)
npm run build        # type-check + production build to dist/
npm run preview      # serve the built app locally
```

## Data loading
- Fetches from `/reports/<DATE>/ActivityReport-<DATE>.json` (falls back to `/ActivityReport-<DATE>.json`).
- If today’s file is missing, the UI automatically tries yesterday’s report and displays a fallback badge.

## Editing & UX
- Copy-to-clipboard for Slack bullets.
- Merge multiple bullets into a new headline, with summed durations and combined proof.
- Hide/noise filtering plus reset-to-default option.
- Proof drawers show deep work/timeline evidence when available.

## Deployment
`railway-start.sh` copies `frontend/dist` into the Flask `site/` directory during container startup so the SPA is served at `/` alongside static reports.
