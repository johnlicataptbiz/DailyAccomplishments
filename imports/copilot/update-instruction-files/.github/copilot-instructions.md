# Daily Accomplishments — Copilot/Agent Instructions

Concise, actionable guide for AI coding agents in this repo. Focus on architecture, workflows, and project-specific rules.

## Big Picture Architecture
- **Data Flow:**
  - Event producers (see `examples/`, `mac_tracker_adapter.py`) write JSONL logs to `logs/daily/YYYY-MM-DD.jsonl`.
  - `tools/daily_logger.py` handles log writing, file locking, schema validation, and log rotation.
  - Analytics and reporting: `tools/analytics.py`, `tools/auto_report.py`, `tools/generate_reports.py`, and `scripts/generate_daily_json.py` process logs into canonical JSON (`ActivityReport-YYYY-MM-DD.json`), CSVs, and dashboard assets in `gh-pages/` and `reports/`.
  - The dashboard is served via `dashboard.html` (see also `gh-pages/`).

## Key Files & Directories
- `tools/daily_logger.py`: Log writing, file locking, schema, rotation, health checks
- `tools/tracker_bridge.py`: Integration API (`ActivityTrackerBridge`), deduplication (2s window)
- `tools/analytics.py`: Deep-work detection, scoring (25-min default)
- `tools/auto_report.py`, `scripts/generate_daily_json.py`: Report pipeline, CLI
- `examples/integration_example.py`: Minimal and full integration examples
- `config.json`: Timezone, daily window, notification creds

## Developer Workflows
- **Install dependencies:** `pip install -r requirements.txt` (Python 3.10+)
- **Run minimal example:** `python3 examples/integration_example.py simple` (writes to `logs/daily/<date>.jsonl`)
- **Generate canonical JSON:** `python3 scripts/generate_daily_json.py <YYYY-MM-DD>`
- **Full pipeline + notifications:** `python3 tools/auto_report.py --date <YYYY-MM-DD>`
- **Regenerate charts/CSVs:** `python3 tools/generate_reports.py` (copy outputs to `gh-pages/`)
- **Preview dashboard:** `python3 -m http.server 8000` and open `dashboard.html`

## Project Conventions & Gotchas
- Log format: JSONL in `logs/daily/`, first line is a `metadata` record
- `ActivityReport-YYYY-MM-DD.json` is canonical; edit requires re-running `tools/generate_reports.py`
- Timezone: default `America/Chicago` (see `config.json`), use `zoneinfo.ZoneInfo`
- Durations: always `HH:MM` format (never decimal hours)
- `coverage_window` must match actual activity span
- Deduplication: identical events within 2s ignored by bridge
- File locking/retries: only use `tools/daily_logger.py` for writes

## Integration API Example
```python
from tools.tracker_bridge import ActivityTrackerBridge
bridge = ActivityTrackerBridge()
bridge.on_focus_change("Terminal", "~/code", 120)
```
See `examples/integration_example.py` for more.

## When Modifying Code
- Validate pipeline: run `examples/integration_example.py`, then `tools/auto_report.py`, then preview dashboard
- Only update `gh-pages/` with generated assets (CSV/SVG/JSON)
- Keep `ActivityTrackerBridge` API stable (all methods return `bool`)

## Troubleshooting
| Issue | Fix |
|-------|-----|
| Charts not rendering | `pip install matplotlib` and re-run `tools/generate_reports.py` |
| gh-pages push issues | `git worktree list` to inspect `gh-pages/` worktree |
| 403 on push | Workflow needs `contents: write` permission |
| Missing logs | Check both `logs/daily/` and legacy `logs/activity-*.jsonl` |

---
If any section is unclear or incomplete, specify which area to expand (examples, edits, or testing steps).
