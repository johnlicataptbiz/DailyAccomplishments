# Handoff: Daily Accomplishments — Quick Start for Next Session

This is a fast onboarding for picking up where we left off. It summarizes setup, what’s implemented, what’s next, and the most important commands.

## Overview
- Purpose: Track daily activity and present a compelling story via a web dashboard.
- Key parts:
  - Data sources: Screen Time (KnowledgeC), Browser History (Chrome/Safari), Slack, Monday, HubSpot, Google Calendar, Aloware.
  - Pipeline: reporter job → generate daily JSON → enrich with Screen Time + Browser → charts/CSVs → archive → push to GitHub.
  - UI: dashboard.html (single-page; Chart.js + custom UI).

## Environment
- Python: `python3 --version` → 3.13.x
- Venv: `~/Desktop/DailyAccomplishments/.venv`
- Activate venv:
  - `source ~/Desktop/DailyAccomplishments/.venv/bin/activate`
- Install deps (already installed):
  - `pip install -r requirements.txt` (or `pip install matplotlib requests`)

## Paths and Clones
- Working clone for UI/dev: `~/Desktop/DailyAccomplishments` (has logs symlink to home clone)
- “Live” clone used by LaunchAgents: `~/DailyAccomplishments` (collector/reporter write here)
- Logs symlink: `~/Desktop/DailyAccomplishments/logs -> ~/DailyAccomplishments/logs`

## Automation (macOS LaunchAgents)
- Collector (active): `com.dailyaccomplishments.collector` → writes `~/DailyAccomplishments/logs/activity-YYYY-MM-DD.jsonl`
- Reporter (active, every 15min): `com.dailyaccomplishments.reporter` → generates reports/charts, archives, pushes via SSH
- Legacy daemon: `com.activitytracker.daemon` (disabled)
- Check: `launchctl list | egrep 'dailyaccomplishments|activitytracker'`

## Privacy
- Config path(s):
  - Desktop: `~/Desktop/DailyAccomplishments/config.json`
  - Home: `~/DailyAccomplishments/config.json`
- Structure:
  ```json
  {
    "privacy": {
      "mode": "exclude", // or "anonymize"
      "blocked_domains": ["..."],
      "blocked_keywords": ["..."]
    }
  }
  ```
- Behavior: applies to Screen Time (by bundle/app label) and Browser History (domain/title). Exclude removes rows; anonymize keeps time under “Private”.

## What’s Implemented
- Screen Time importer (KnowledgeC `/app/usage`) with privacy filters.
- Browser History importer (Chrome/Safari) with privacy filters and coverage union.
- Top Apps aggregation from Screen Time (HH:MM strings; friendly app names).
- Deep Work derivation (contiguous ≥ 25 min; small gaps ≤ 5 min) with category/app labels.
- Dashboard improvements:
  - Hero: Focus/Meetings with 7-day baselines (deltas), Coverage, Deep Work Blocks, Privacy pill.
  - Deep Work chips with longest-block trophy and tooltips.
  - Integration Highlights grid (Slack, Monday, HubSpot, Calendar, Aloware KPIs).

## Open Items (Priority)
1) Home clone rebase conflict (ActivityReport-2025-12-03.json)
- If you want local to match remote:
  ```bash
  cd ~/DailyAccomplishments
  git checkout --theirs ActivityReport-2025-12-03.json
  git add ActivityReport-2025-12-03.json
  git rebase --continue
  ```
- Then regenerate:
  ```bash
  source ~/Desktop/DailyAccomplishments/.venv/bin/activate
  python ~/Desktop/DailyAccomplishments/scripts/import_screentime.py --date 2025-12-03 --update-report --repo ~/DailyAccomplishments
  python ~/Desktop/DailyAccomplishments/tools/generate_reports.py 2025-12-03
  ```

2) Railway deployment (build failing)
- Plan: add Dockerfile with static server (Nginx or Node `serve`), ensure `index.html`, `ActivityReport-*.json`, and `reports/*` are served; handle base path if used.
- After Dockerfile PR, configure Railway to build and serve static.

3) UI next passes
- Integration Highlights: add top lists per integration (e.g., Monday boards, Slack channels, HubSpot deals).
- Hourly overlay: show Calendar meetings on top of focus bars + legend.
- Trends: add 7-day sparklines for Focus/Meetings/Tasks/Msgs.

## Most-Used Commands
- Generate reports for a date (Desktop clone):
  ```bash
  source ~/Desktop/DailyAccomplishments/.venv/bin/activate
  python ~/Desktop/DailyAccomplishments/tools/generate_reports.py 2025-12-02
  ```
- Import Screen Time & merge:
  ```bash
  python ~/Desktop/DailyAccomplishments/scripts/import_screentime.py --date 2025-12-02 --update-report --repo ~/Desktop/DailyAccomplishments
  ```
- Import Browser History & merge:
  ```bash
  python ~/Desktop/DailyAccomplishments/scripts/import_browser_history.py --date 2025-12-02 --update-report --repo ~/Desktop/DailyAccomplishments
  ```
- Run reporter once (home clone):
  ```bash
  bash ~/DailyAccomplishments/scripts/cron_report_and_push.sh
  ```

## Logs & Debugging
- Reporter logs: `~/DailyAccomplishments/logs/reporter.out.log` (and `.err.log`)
- Collector logs: `~/DailyAccomplishments/logs/activity-YYYY-MM-DD.jsonl`
- KnowledgeC exists: `~/Library/Application Support/Knowledge/knowledgeC.db`
- If Screen Time importer returns 0 records: re-check Full Disk Access for Terminal; we’re using `/app/usage` stream.

## Files Most Recently Updated
- UI: `dashboard.html`
- Importers: `scripts/import_screentime.py`, `scripts/import_browser_history.py`
- Reporter: `scripts/cron_report_and_push.sh`, `scripts/archive_outputs.sh`
- Roadmap: `FUTURE_UPDATES.md`

## “Start Here” (Next Session)
1) Resolve home rebase (or confirm it’s done) and regenerate 12-03.
2) Add Dockerfile for Railway and push; verify a successful build.
3) Implement Integration Highlights v2 (mini lists) and Hourly meetings overlay.

---
Owner: jacklicataptbiz | Updated: 2025-12-04
