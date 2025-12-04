# Daily Accomplishments — Copilot / Agent Instructions

Short, actionable guide for AI coding agents working in this repo. Focus on where to read, what to run, and project-specific rules.

- **Big picture**: Event producers (examples/activity_tracker, mac_adapter) write JSONL logs → `tools/daily_logger.py` manages daily JSONL (`logs/daily/YYYY-MM-DD.jsonl`) → analytics (`tools/analytics.py`) and report generators (`scripts/generate_daily_json.py`, `tools/generate_reports.py`, `tools/auto_report.py`) produce `ActivityReport-YYYY-MM-DD.json`, `reports/` and static assets under `gh-pages/`.

- **Key files to read first**:
  - `tools/daily_logger.py` — file locking, schema validation, log rotation, health checks
  - `tools/tracker_bridge.py` — integration API (use `ActivityTrackerBridge`) and deduplication (2s window)
  - `tools/analytics.py` — deep-work detection and scoring (25-min default)
  - `tools/auto_report.py` & `scripts/generate_daily_json.py` — report pipeline and CLI
  - `examples/integration_example.py` — minimal (3-line) and full integration examples
  - `config.json` — runtime knobs (timezone, daily window, notification creds)

- **Developer workflows / commands** (most common):
  - Install deps: `pip install -r requirements.txt` (Python 3.10+)
  - Run minimal example: `python3 examples/integration_example.py simple` (writes `logs/daily/<date>.jsonl`)
  - Generate canonical JSON: `python3 scripts/generate_daily_json.py <YYYY-MM-DD>`
  - Full pipeline + notifications: `python3 tools/auto_report.py --date <YYYY-MM-DD>`
  - Regenerate charts/CSVs: `python3 tools/generate_reports.py` then copy outputs to `gh-pages/` for pages
  - Preview dashboard: `python3 -m http.server 8000` → open `dashboard.html`

- **Project conventions & gotchas (do not change lightly):**
  - Preferred log format: JSONL in `logs/daily/` with a `metadata` record as first line.
  - `ActivityReport-YYYY-MM-DD.json` is treated as the canonical/manual-correction file; editing it requires re-running `tools/generate_reports.py` to regenerate charts.
  - Timezone default: `America/Chicago` (check `config.json`); use `zoneinfo.ZoneInfo` for parsing.
  - Durations in outputs use `HH:MM` format (never decimal hours).
  - `coverage_window` must reflect actual first-to-last activity — avoid truncating it.
  - Deduplication: identical events within 2 seconds are ignored by the bridge.
  - File locking and retries are implemented in `tools/daily_logger.py`; avoid introducing concurrent write paths that bypass it.

- **Integration examples agents can use**:
  - Minimal (3 lines):
    ```py
    from tools.tracker_bridge import ActivityTrackerBridge
    bridge = ActivityTrackerBridge()
    bridge.on_focus_change("Terminal", "~/code", 120)
    ```
  - Use `examples/integration_example.py` for a simulated day to validate pipeline end-to-end.

- **When modifying code**:
  - Run the example and pipeline locally: `examples/integration_example.py` → `tools/auto_report.py` → `python3 -m http.server 8000` to verify dashboard.
  - Update `gh-pages/` only with generated assets (CSV/SVG/JSON) — `gh-pages` is a published worktree.
  - Keep public API stable: methods on `ActivityTrackerBridge` (on_focus_change, on_app_switch, on_browser_visit, on_meeting_start/end, on_idle_start/end, on_manual_entry) return `bool` for success/failure; callers expect that.

- **Troubleshooting quick tips**:
  - Charts not rendering: `pip install matplotlib` and re-run `tools/generate_reports.py`.
  - gh-pages push issues: run `git worktree list` to inspect the `gh-pages/` worktree.
  - Missing logs: check both `logs/daily/` and legacy `logs/activity-*.jsonl`.

If any part of this is unclear or you want the agent to expand a specific section (examples, typical edits, or testing steps), tell me which area to expand.

## Integration API

```python
from tools.tracker_bridge import ActivityTrackerBridge
bridge = ActivityTrackerBridge()
bridge.on_focus_change("VS Code", "main.py", 120)  # 2 min duration
bridge.on_browser_visit("github.com", "https://github.com", "GitHub")
bridge.on_meeting_start("Standup", 900)  # 15 min scheduled
```
Events auto-deduplicate within 2-second windows. See `examples/integration_example.py`.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Charts fail | `pip install matplotlib` |
| gh-pages errors | `git worktree list` to verify; VS Code warnings safe to ignore |
| 403 on push | Workflow needs `contents: write` permission |
| Missing data | Check both `logs/daily/` and `logs/activity-*.jsonl` |
