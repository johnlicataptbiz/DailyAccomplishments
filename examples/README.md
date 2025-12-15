# Integration Examples

This directory contains practical examples showing how to integrate the Daily Accomplishments tracking system with your existing activity tracker.

## Files

### `integration_example.py`

Complete working examples demonstrating the integration API.

**Features:**
- ✅ Application switch tracking with deduplication
- ✅ Browser URL visit logging
- ✅ Meeting/calendar integration
- ✅ Idle detection and break recommendations
- ✅ Focus session tracking
- ✅ Manual time entry logging

## Quick Start

### Minimal Example (3 lines)

```bash
python3 integration_example.py simple
```

This demonstrates the absolute minimum code needed:

```python
from tools.tracker_bridge import ActivityTrackerBridge

bridge = ActivityTrackerBridge()
bridge.on_focus_change("Terminal", "~/code", 120)  # 2 minutes
bridge.on_browser_visit("github.com", "https://github.com", "GitHub")
```

**Output:**
```
✓ Events logged successfully!
  Location: logs/daily/2025-12-02.jsonl
```

### Full Example (Simulated Day)

```bash
python3 integration_example.py
```

This simulates a full workday with various event types:

**Events logged:**
- 09:00 — Start work in VS Code
- 09:15 — Research documentation (Safari + URL)
- 09:30 — Back to coding
- 10:15 — Slack check (interruption)
- 10:20 — Deep work session (2 hours)
- 12:30 — Lunch break (idle detection)
- 14:00 — Team meeting
- 14:20 — Documentation writing

**Output:**
```
[09:00] Starting work...
📱 App: VS Code — main.py — DailyAccomplishments

[09:15] Researching documentation...
📱 App: Safari — Python Documentation
🌐 URL: docs.python.org — datetime — Basic date and time types

... (full day simulation)

Next steps:
  1. Generate report: python3 tools/auto_report.py
  2. View dashboard: open dashboard.html
  3. Send notifications: python3 tools/notifications.py
```

## Integration API Reference

### ActivityTrackerBridge

The main bridge class for logging events.

#### Methods

**`on_focus_change(app: str, window_title: str, duration_seconds: int)`**
- Log when user focuses on an application
- `app`: Application name (e.g., "VS Code", "Safari")
- `window_title`: Current window/document title
- `duration_seconds`: How long the app had focus
- Returns: `bool` (success)

**`on_app_switch(from_app: str, to_app: str)`**
- Log when user switches between applications
- `from_app`: Previous application
- `to_app`: New application
- Returns: `bool` (success)

**`on_window_change(app: str, window_title: str)`**
- Log window title changes within an app
- `app`: Application name
- `window_title`: New window title
- Returns: `bool` (success)

**`on_browser_visit(domain: str, url: str, page_title: Optional[str])`**
- Log browser page visits
- `domain`: Domain name (e.g., "github.com")
- `url`: Full URL
- `page_title`: Page title (optional)
- Returns: `bool` (success)

**`on_meeting_start(name: str, scheduled_duration: Optional[int])`**
- Log when a meeting starts
- `name`: Meeting title
- `scheduled_duration`: Duration in seconds (optional)
- Returns: `bool` (success)

**`on_meeting_end(name: str, duration_seconds: int)`**
- Log when a meeting ends
- `name`: Meeting title
- `duration_seconds`: Actual duration
- Returns: `bool` (success)

**`on_idle_start()`**
- Log when user becomes idle
- Returns: `bool` (success)

**`on_idle_end(idle_duration_seconds: int)`**
- Log when user returns from idle
- `idle_duration_seconds`: How long idle
- Returns: `bool` (success)

**`on_manual_entry(description: str, duration_seconds: int, category: Optional[str])`**
- Log manual time entry (for completed tasks/sessions)
- `description`: What was done
- `duration_seconds`: How long it took
- `category`: Category (e.g., "Development", "Writing")
- Returns: `bool` (success)

### IdleDetector

Cross-platform idle time detection.

#### Methods

**`get_idle_seconds() -> Optional[int]`**
- Get current system idle time in seconds
- Returns: `int` seconds idle, or `None` if unavailable

**`is_break_recommended() -> bool`**
- Check if a break is recommended based on focus time
- Returns: `bool`

## Integrating with Your Existing Tracker

### Step 1: Add Import

At the top of your `activity_tracker.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'tools'))
from tracker_bridge import ActivityTrackerBridge

bridge = ActivityTrackerBridge()
```

### Step 2: Log Events

Wherever you detect events in your existing code:

```python
# When app changes
def on_application_change(app_name, window_title, duration):
    # Your existing code here...
    
    # Add this line:
    bridge.on_focus_change(app_name, window_title, duration)

# When URL changes (for browsers)
def on_url_change(url, title):
    from urllib.parse import urlparse
    # Your existing code here...
    
    # Add this:
    domain = urlparse(url).netloc
    bridge.on_browser_visit(domain, url, title)

# When meetings start
def on_meeting_detected(title, duration):
    # Your existing code here...
    
    # Add this:
    bridge.on_meeting_start(title, scheduled_duration=duration)
```

### Step 3: Test

Run your tracker and verify logs:

```bash
# Run your tracker
python3 activity_tracker.py

# Check logs are being created
cat logs/daily/$(date +%Y-%m-%d).jsonl | jq

# Generate report
python3 tools/auto_report.py

# View dashboard
open dashboard.html
```

## Automatic Deduplication

The bridge automatically handles deduplication:

```python
# This will log
bridge.on_focus_change("VS Code", "main.py", 60)

# This will be ignored (duplicate within 2 seconds)
bridge.on_focus_change("VS Code", "main.py", 60)

time.sleep(3)

# This will log (more than 2 seconds later)
bridge.on_focus_change("VS Code", "main.py", 60)
```

## Error Handling

All methods return `bool` for success/failure:

```python
success = bridge.on_focus_change("VS Code", "main.py", 60)
if not success:
    print("Warning: Failed to log event")
    # Your error handling here...
```

## Event Types in JSONL

Events are stored in JSONL format in `logs/daily/YYYY-MM-DD.jsonl`:

```json
{"type": "focus_change", "timestamp": "2025-12-02T09:00:00-06:00", "data": {"app": "VS Code", "window_title": "main.py", "duration_seconds": 120}}
{"type": "app_switch", "timestamp": "2025-12-02T09:15:00-06:00", "data": {"from_app": "VS Code", "to_app": "Safari"}}
{"type": "browser_visit", "timestamp": "2025-12-02T09:15:05-06:00", "data": {"domain": "github.com", "url": "https://github.com", "page_title": "GitHub"}}
{"type": "meeting_start", "timestamp": "2025-12-02T14:00:00-06:00", "data": {"name": "Daily Standup", "scheduled_duration_seconds": 900}}
{"type": "idle_end", "timestamp": "2025-12-02T12:30:00-06:00", "data": {"idle_duration_seconds": 1800}}
{"type": "manual_entry", "timestamp": "2025-12-02T16:00:00-06:00", "data": {"description": "Development - Focus Session", "duration_seconds": 7200, "category": "Development"}}
```

## Next Steps

After integrating:

1. **Generate Reports**: `python3 tools/auto_report.py`
2. **View Dashboard**: Open `dashboard.html` in browser
3. **Set Up Notifications**: Configure email/Slack in `config.json`
4. **Automate**: Schedule daily reports with launchd/cron

See `INTEGRATION_GUIDE.md` for complete setup instructions.

## Testing

Verify integration is working:

```bash
# 1. Run the example
python3 examples/integration_example.py

# 2. Check logs were created
ls -la logs/daily/

# 3. View logged events
cat logs/daily/$(date +%Y-%m-%d).jsonl | jq

# 4. Generate report
python3 tools/auto_report.py

# 5. Open dashboard
python3 -m http.server 8000
open http://localhost:8000/dashboard.html
```

## Support

For detailed integration instructions, see:
- `INTEGRATION_GUIDE.md` — Complete setup guide
- `docs/design/IMPROVEMENTS.md` — Technical architecture
- `tools/tracker_bridge.py` — Full API source code
