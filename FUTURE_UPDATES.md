# Future Updates Roadmap

This document tracks planned improvements to the Daily Accomplishments dashboard and data pipeline. Items are organized so we can implement and ship in small, testable steps.

## Guiding Principles
- Story-first: lead with wins and outcomes, not raw stats.
- Multi-source truth: Screen Time, Browser History, Slack, Monday, HubSpot, Calendar, Aloware.
- Privacy-by-default: clear indicators and filters, no accidental exposure.
- Fast and accessible: instant load, keyboard-friendly, responsive.
- Incremental: each change should be independently valuable and safe to roll out.

## Phase 1 — Baseline & Screen Time (in progress)
- [x] Integrate Screen Time (KnowledgeC) into daily report
- [x] Add Top Applications from Screen Time to report and UI
- [x] Privacy filters (exclude/anonymize) for both Screen Time and browser history
- [x] Show “Privacy filters active” pill in UI when Private time exists
- [x] Add 7-day baseline for Focus and Meetings with up/down deltas in hero
- [x] Union coverage window across sources (Screen Time + Browser + existing)
- [ ] QA: verify top_apps and categories stay consistent day-to-day

Files touched: `scripts/import_screentime.py`, `scripts/import_browser_history.py`, `scripts/cron_report_and_push.sh`, `dashboard.html`.

## Phase 2 — Deep Work Timeline Overlay
Goal: Visualize contiguous focused blocks (>= 25 min) with labels.

- [ ] Extract deep work blocks from hourly_focus (detect contiguous >= 25 min)
- [ ] Render as chips or bars on the hourly timeline with category/app label
- [ ] Tooltip: start–end, total minutes, category
- [ ] Acceptance: visually distinct blocks align with reported focus minutes

Files: `tools/generate_reports.py` (optional), `dashboard.html` (render + styles).

## Phase 3 — Integration Highlights Grid
Goal: Surface actionable KPIs per integration.

- [ ] Slack: appointments set (names), messages sent/received, active channels
- [ ] Monday: tasks updated, top 3 boards, “wins” from Jack Set Calls
- [ ] HubSpot: calls/emails counts, top 3 deals (only those tagged as yours)
- [ ] Google Calendar: meetings attended (count + total mins)
- [ ] Aloware: call totals and talk time (when enabled)
- [ ] Acceptance: each card shows at-a-glance KPIs with short detail lists

Files: `dashboard.html` (analysis + render), data shaping in report if needed.

## Phase 4 — Trends & Sparklines (7-day)
Goal: Show trajectory for key metrics.

- [ ] 7-day sparklines: Focus, Meetings, Appointments, Messages, Tasks
- [ ] Week-over-week change badges
- [ ] Acceptance: quick scan shows progress or regression trends

Files: `dashboard.html` (fetch last 7 reports + mini charts).

## Phase 5 — Filters & Privacy Controls
Goal: Let users tailor the view without changing the underlying data.

- [ ] Category toggles (Coding, Research, Communication, Meetings, Private)
- [ ] Toggle “Show Private time” (on shows aggregate minute total only)
- [ ] Hourly overlays: show meetings on top of focus bars
- [ ] Acceptance: toggling updates bars and charts without reload

Files: `dashboard.html` (state + re-render), minor CSS.

## Phase 6 — Drilldowns & Reporting
Goal: Click-through exploration and shareable summaries.

- [ ] Click a category/app to see top hours and recent sessions/pages
- [ ] “Share summary” export (compact PNG/HTML section of hero + insights)
- [ ] Acceptance: useful drilldown in a single click, export looks clean

Files: `dashboard.html` (modals or expanders), small export utility.

## Phase 7 — Performance, Accessibility, Mobile
- [ ] Lazy-load secondary charts and lists
- [ ] Improve semantic structure, tab order, contrast
- [ ] Mobile layout tweaks (single column, stacked metrics)
- [ ] Acceptance: Lighthouse >= 90 performance/accessibility

Files: `dashboard.html` (layout + CSS), image sizing.

## Data & Pipeline Enhancements
- [ ] Nightly consolidated JSON for last 7 days to speed baselines
- [ ] Optional: hourly meetings overlay (Calendar -> report.hourly_meetings)
- [ ] Optional: deeper “top apps” normalization map

## Deployment — Railway (Fix + Permanent Link)
Goal: Reliable, shareable deployment that updates on push without breakage.

- [ ] Investigate failing Railway builds and capture logs
- [ ] Add Dockerfile for static hosting (Nginx or Node `serve`) with proper cache headers
- [ ] Add simple health endpoint and basePath handling if needed
- [ ] Configure Railway service environment to serve `index.html` and `ActivityReport-*.json`/`reports/*`
- [ ] Add `railway.json` or project config notes to repo
- [ ] Acceptance: successful build/deploy on push, stable URL, dashboard loads all assets

Files: `scripts/generate_daily_json.py`, `tools/generate_reports.py` (if needed).

## Open Questions
- Weights for “Impact Score” vs. productivity; ensure alignment with goals.
- Deep work threshold (25 vs. 30 vs. 45 min) and per-category heuristics.
- Which integrations are “authoritative” for appointments and closes?

## Rollout Plan
1. Ship Phase 2 (Deep Work overlay) behind a small flag in the UI.
2. Ship Phase 3 (Integration Highlights) – minimal KPIs first.
3. Ship Phase 4 (Trends) with Focus/Meetings only; expand later.
4. Ship Phase 5 (Filters) with category toggles and privacy switch.
5. Monitor load time and browser console; add feature flags as needed.

## Acceptance Checklist (per feature)
- [ ] User story stated in PR description
- [ ] Screenshots for desktop/mobile
- [ ] Privacy behavior validated (exclude/anonymize)
- [ ] Tested against empty and large (>1000 event) log files
- [ ] Passes `scripts/validate_schemas.py`
- [ ] Dashboard renders correctly with new data
- [ ] Team lead/stakeholder review
- [ ] QA sign-off
