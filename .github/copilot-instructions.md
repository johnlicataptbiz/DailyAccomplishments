# Daily Accomplishments Tracker — Agent Instructions

## Overview
Productivity tracking system: logs daily activities → generates JSON/Markdown reports → publishes static dashboard to GitHub Pages.

```
External tracker (macOS) → JSONL logs → JSON reports → Charts/CSVs → GitHub Pages
```

## Architecture

### Data Flow
| Stage | Path | Purpose |
|-------|------|---------|
| **Input** | `logs/daily/YYYY-MM-DD.jsonl` | Raw event logs (focus_change, app_switch, browser_visit, meeting_*) |
| **Canonical** | `ActivityReport-YYYY-MM-DD.json` | **Edit this** for manual corrections |
| **Generated** | `reports/daily-report-*.json/md` | Report copies + `*.csv`, `*.svg` charts |
| **Published** | `gh-pages/` | Git worktree → GitHub Pages |

### Key Tools
| Tool | Purpose |
|------|---------|
| `tools/tracker_bridge.py` | Integration API—use `ActivityTrackerBridge` class |
| `tools/daily_logger.py` | JSONL logging with file locking & validation |
| `tools/generate_reports.py` | Generate CSVs + SVG charts from reports |
| `scripts/generate_daily_json.py` | Convert JSONL logs → ActivityReport JSON |
| `tools/analytics.py` | Productivity scoring, deep work detection (25min threshold) |
| `tools/auto_report.py` | End-to-end: logs → report → notifications |

## Essential Commands

```bash
# Generate report from logs
python3 scripts/generate_daily_json.py 2025-12-01

# Regenerate charts/CSVs after editing JSON
python3 tools/generate_reports.py

# Local preview
python3 -m http.server 8000  # → http://localhost:8000/dashboard.html

# Full pipeline with notifications
python3 tools/auto_report.py --date 2025-12-01
```

## Data Conventions

### ActivityReport JSON (canonical format)
```json
{
  "overview": {
    "focus_time": "08:54",              // Always HH:MM format
    "meetings_time": "01:15",
    "appointments": 2,                   // Must match array length below
    "coverage_window": "08:00–20:45 CST" // Actual activity span, no artificial cutoffs
  },
  "debug_appointments": {
    "appointments_today": [{"name": "...", "time": "..."}],
    "meetings_today": [{"name": "...", "time": "08:00–08:15"}]
  },
  "by_category": {"Coding": "01:38", "Research": "03:54"},
  "hourly_focus": [{"hour": 12, "time": "00:36", "pct": "43%"}]
}
```

### JSONL Event Types
- `focus_change` — `{app, window_title, duration_seconds}`
- `app_switch` — `{from_app, to_app}`
- `browser_visit` — `{domain, url, page_title}`
- `meeting_start/end` — `{name, duration_seconds}`
- `idle_start/end` — Break detection

### Timezone
All timestamps: `America/Chicago` (CST/CDT). Configured in `config.json` → `tracking.timezone`.

## Critical Rules

1. **Never truncate `coverage_window`** — Must reflect actual first-to-last activity times
2. **Keep counts in sync** — `overview.appointments` = length of `debug_appointments.appointments_today`
3. **Always HH:MM format** — Never use decimal hours for durations
4. **Regenerate after edits**: `python3 tools/generate_reports.py && cp *.csv *.svg gh-pages/`

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
