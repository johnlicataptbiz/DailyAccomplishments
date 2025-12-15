## Copilot / AI agent guidance — DailyAccomplishments (concise)

Purpose: quick, repo-specific rules to get an AI coding agent productive. Keep changes small, verifiable, and reversible.

Big picture
- Data flow: trackers → `tools/tracker_bridge.py` → `tools/daily_logger.py` (newline JSONL in `logs/daily/YYYY-MM-DD.jsonl`) → `tools/analytics.py` → `tools/auto_report.py` → `reports/` + `gh-pages/` dashboard. See `README.md` "Data Flow".

Key files to read first
- `config.json` / `config.json.example` (timezone, analytics settings)
- `tools/tracker_bridge.py`, `tools/daily_logger.py`, `tools/analytics.py`, `tools/auto_report.py`
- `activity_tracker.py`, `mac_tracker_adapter.py`, `tracker_bridge.py`, `tracker_cli.py` (collection adapters)
- `gh-pages/dashboard.html`, `reports/`, and `ActivityReport-*.json` (UI contract)

Quick dev commands (most useful)
- Install deps: `pip install -r requirements.txt`
- Smoke ingest: `python3 examples/integration_example.py` (generates sample `logs/daily/*.jsonl`)
- Generate reports: `python3 tools/auto_report.py` or `./generate_reports.sh`
- Serve dashboard locally: `python -m http.server -d gh-pages 8000` and open `/dashboard.html`
- Run tests: `pytest`

Project-specific conventions (do not change lightly)
- Event format: newline-delimited JSONL under `logs/daily/` — tools assume this exact shape.
- Timezone default: `America/Chicago` (check `config.json` before changing date logic).
- Category mapping & priority: `config.json` keys `analytics.category_mapping` and `analytics.category_priority` drive attribution in `tools/analytics.py`.
- CSV artifacts may contain trailing whitespace (handled by repo config). Prefer non-binary outputs (SVG charts) and avoid committing new binary images.

Verification & smoke tests
- Quick end-to-end: run `python3 examples/integration_example.py` then `python3 tools/auto_report.py` and inspect `reports/daily-report-*.json` and `gh-pages/dashboard.html`.
- Before changing aggregation/visualization: run `./verify_installation.py` and `pytest`.

Integrations & external dependencies
- Notifications: `tools/notifications.py` (SMTP, Slack webhooks) — examples in `examples/`.
- Calendar, browser, and macOS knowledgeC adapters live in `mac_tracker_adapter.py`, `tracker_bridge.py`.
- Charting requires system libs (e.g., freetype) — see `Dockerfile` and `requirements.txt` for runtime requirements.

Deploy / hosting notes
- `gh-pages/` must expose `reports/*.json` or the UI falls back to raw GitHub URLs (see `docs/RAILWAY_DEPLOY.md`).
- ActivityReport-*.json files are the contract the frontend expects; preserve their schema when changing report generation.

Git & patch discipline (required)
- Make small, focused change-sets. Show `git diff` after edits and stage only intended paths: `git add path/to/file` (never `git add -A`).
- When asked to prove changes, include raw command outputs (this repo requires reproducible verification).

Secrets & credentials
- `credentials/` is gitignored. Do not add secrets to `config.json`; use env vars or the `credentials/` pattern.

If something here is unclear or you want a small patch walkthrough (e.g., `tools/analytics.py`), tell me which area to expand.
## Copilot / AI agent guidance — concise reference

This file gives quickly-actionable rules for an AI coding agent working on DailyAccomplishments. Keep edits small, verifiable, and reproducible.

- Big picture: data flows from trackers → `tools/tracker_bridge.py` → `tools/daily_logger.py` (JSONL files in `logs/daily/`) → `tools/analytics.py` → `tools/auto_report.py` → `reports/` + `gh-pages/` dashboard. See `README.md` "Data Flow" and `tools/` for examples.
- Key files to read first: `config.json`, `config.json.example`, `tools/tracker_bridge.py`, `tools/daily_logger.py`, `tools/analytics.py`, `tools/auto_report.py`, `gh-pages/dashboard.html`, `README.md` (top-level).
- Local dev commands (most useful):
  - Install deps: `pip install -r requirements.txt`
  - Run example ingestion: `python3 examples/integration_example.py`
  - Generate a report: `python3 tools/auto_report.py`
  - Serve dashboard: `python3 -m http.server 8000` and open `/dashboard.html`
  - Backfill: `python3 scripts/backfill_reports.py --start 2025-12-01 --end 2025-12-31`
- Conventions specific to this repo:
  - Event storage: newline-delimited JSONL in `logs/daily/YYYY-MM-DD.jsonl` (tools expect this format).
  - CSV files may contain trailing whitespace (handled by .gitattributes) — do not strip blindly in bulk.
  - Charts: prefer SVG outputs; avoid committing new binary images.
  - Timezone default: `America/Chicago` — verify conversions when editing analytics or report code.
  - Category configuration lives in `config.json` (`analytics.category_mapping` and `analytics.category_priority`) and drives overlap attribution logic in `tools/analytics.py`.
- Integrations and deploy hooks to be aware of:
  - Notifications: `tools/notifications.py` (email via SMTP, Slack webhook). Tests/examples under `examples/` and `README.md`.
  - Hosted static site: `gh-pages/` is used for dashboard publishing and must include `reports/*.json` or fallbacks to raw GitHub URLs (see `docs/RAILWAY_DEPLOY.md`).
- Git/patch discipline (required):
  - Make small, single-feature change-sets. Show `git diff` after edits. Stage only intended files: `git add <paths>` (never `git add -A`).
  - For any git/network step paste raw command output when requested. Keep commits focused and reversible.
- Testing and verification pointers:
  - Use `examples/integration_example.py` for smoke tests and `tools/auto_report.py` to validate report generation end-to-end.
  - When changing parsing/aggregation, run a short synthetic day via the example and inspect `reports/daily-report-*.json` and `logs/daily/*.jsonl`.
- Safety and secrets:
  - Credentials live in `credentials/` (gitignored). Never add secrets to code or `config.json`; use environment variables where possible.

If anything in this concise guide is unclear or you want more examples (e.g., a small patch walkthrough for `tools/analytics.py`), tell me which area to expand.
# GitHub Copilot Instructions for DailyAccomplishments

## Project Overview

DailyAccomplishments is a production-ready productivity tracking and analytics system that automatically logs activity events, generates insights, and provides visualizations through a web dashboard.

### Purpose
- Track daily activities from multiple sources
- Analyze productivity patterns and deep work sessions
- Generate automated reports with visualizations
- Provide actionable insights via dashboard and notifications

### Current Integrations
- **Screen Time**: macOS KnowledgeC database (app usage)
- **Browser History**: Chrome/Safari browsing activity
- **Google Calendar**: Meeting and event tracking
- **Slack**: Team communication (notification posting)

### Planned Integrations (see ROADMAP.md)
- **HubSpot**: CRM activity tracking
 # GitHub Copilot instructions — DailyAccomplishments

Keep guidance short, actionable, and repository-specific. The items below are patterns and commands an AI coding agent should follow to be productive here.

1. Big picture
  - Data collectors & adapters: `mac_tracker_adapter.py`, `tracker_bridge.py`, `tracker_cli.py`, `activity_tracker.py` produce raw events and JSON reports (`ActivityReport-YYYY-MM-DD.json`).
  - Processing & tools: `tools/`, `analyze_branches.py`, `extract_diff.py`, `generate_reports.sh` transform data into CSVs and SVG charts saved under `reports/` and `gh-pages/`.
  - Dashboard & hosting: static UI under `gh-pages/` and `dashboard/`; gh-pages must continue to expose ActivityReport JSON fallbacks (see `docs/RAILWAY_DEPLOY.md`).

2. Key files & examples (search these when changing behavior)
  - `config.json` — canonical runtime settings (timezone default: America/Chicago).
  - `credentials/` — never commit; use env vars for CI.
  - `ActivityReport-*.json`, `reports/`, `gh-pages/dashboard.html` — primary UX/outputs. Treat them as the contract the UI expects.

3. Developer workflows (commands you should run / recommend)
  - Local server for dashboard: `python -m http.server -d gh-pages 8000` or use Docker:
    - `docker build -t daily-accomplishments .`
    - `docker run -p 8000:8000 daily-accomplishments`
  - Regenerate reports: `./generate_reports.sh` then open `gh-pages/dashboard.html`.
  - Tests: run `pytest` (project includes `pytest.ini` and `tests/`).

4. Project-specific conventions
  - Keep diffs small and focused; the repo enforces a disciplined patch workflow (stage exact files only).
  - CSVs may contain trailing whitespace — `.gitattributes` allows it. Avoid normalizing CSV whitespace in bulk commits.
  - Visual artifacts should be SVG (see `generate_charts.sh` / `tools/`); do not add new binary images in PRs.
  - Timezone and daily-cutoff logic live in `activity_tracker.py`/`tools/` — update tests when changing cutoff behavior.

5. Integrations & external dependencies
  - Integrations documented in `INTEGRATION_GUIDE.md` (Google Calendar, Slack, macOS KnowledgeC). Use `config.json` toggles and `credentials/` for secrets.
  - Docker and system libs (freetype for matplotlib) are required for chart generation — see `Dockerfile` and `requirements.txt`.

6. Git + CI expectations for automated agents
  - Never run a sweeping `git add -A`. Stage precise paths: `git add path/to/file`.
  - Provide exact command outputs when claiming changes (follow repo's verification checklist). When proposing changes, include the minimal `git diff` for review.

7. Safety checks before edits
  - Run `./verify_installation.py` and `pytest` if modifying processors or visualization code.
  - If changing public-facing artifacts in `gh-pages/`, ensure `ActivityReport-*.json` fallback URLs still work.

8. Examples to copy into PR descriptions
  - How to build/run locally: `docker build -t daily-accomplishments . && docker run -p 8000:8000 daily-accomplishments`
  - How to regenerate outputs: `./generate_reports.sh && python -m http.server -d gh-pages 8000`

If any area is unclear or you'd like more examples (unit tests, a sample Docker-based dev script, or a checklist for dashboard changes), tell me which part to expand.
