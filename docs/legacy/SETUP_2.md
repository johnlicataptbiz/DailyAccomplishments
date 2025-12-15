# Activity Tracker Setup Guide

## Configuration

The tracker is configured via `config.json`:

- **Tracking starts**: 6:00 AM (configured in `daily_start_hour`)
- **Daily reset**: Midnight (configured in `reset_hour`)
- **Timezone**: America/Chicago (CST/CDT)
- **Running logs**: Stored in `logs/daily/`
- **Archives**: Older logs moved to `logs/archive/`

## Daily Log System

### How it works

1. **6:00 AM**: System initializes a new daily log file (`logs/daily/YYYY-MM-DD.jsonl`)
2. **Throughout the day**: Activity events are appended to the current log
3. **Midnight**: Yesterday's log is archived and a new log is prepared for tomorrow

### Log Format

Each daily log contains:
- **Metadata** (first line): date, start time, timezone, coverage window
- **Activity events** (subsequent lines): focus changes, app switches, browser visits

Example log entry:
```json
{"type": "metadata", "data": {"date": "2025-12-02", "start_time": "2025-12-02T06:00:00-06:00", "timezone": "America/Chicago"}}
{"type": "focus_change", "timestamp": "2025-12-02T08:30:15-06:00", "data": {"app": "Google Chrome", "window_title": "Project Dashboard", "duration_seconds": 300}}
```

## Automated Scheduling

### Option 1: macOS launchd (Recommended)

Create `~/Library/LaunchAgents/com.activitytracker.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.activitytracker.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/DailyAccomplishments/tools/daily_logger.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>6</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>0</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/activitytracker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/activitytracker.err</string>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.activitytracker.daily.plist
```

### Option 2: Cron

Add to your crontab (`crontab -e`):

```bash
# Initialize daily log at 6am
0 6 * * * cd /path/to/DailyAccomplishments && /usr/bin/python3 tools/daily_logger.py

# Midnight reset
0 0 * * * cd /path/to/DailyAccomplishments && /usr/bin/python3 tools/daily_logger.py
```

### Option 3: Manual

Run manually when needed:
```bash
cd /path/to/DailyAccomplishments
python3 tools/daily_logger.py
```

## Integration with Activity Tracker

To integrate with your existing tracker (running on macOS):

1. Import the daily logger in your tracker script:
```python
from tools.daily_logger import log_activity, initialize_daily_log, midnight_reset
```

2. Call `log_activity()` whenever you capture focus/activity:
```python
log_activity('focus_change', {
    'app': current_app,
    'window_title': current_title,
    'duration_seconds': duration
})
```

3. Schedule midnight reset in your daemon loop:
```python
if current_hour == 0 and current_minute == 0:
    midnight_reset()
```

## Generating Reports

Update `tools/generate_reports.py` to read from daily logs:

```python
from tools.daily_logger import read_daily_log, get_log_path
from datetime import datetime

date = datetime(2025, 12, 2)
events = read_daily_log(date)

# Process events and generate report
# ...
```

## Testing

Test the system:

```bash
# Initialize today's log
python3 tools/daily_logger.py

# Check the log was created
ls -la logs/daily/

# View log contents
cat logs/daily/$(date +%Y-%m-%d).jsonl
```

## Troubleshooting

- **Logs not created**: Check `config.json` exists and is valid JSON
- **Wrong timezone**: Update `timezone` in `config.json`
- **Permission errors**: Ensure `logs/` directory is writable
- **Cron not working**: Check cron logs: `grep CRON /var/log/system.log` (macOS)

## Next Steps

1. Set up automated scheduling (choose launchd or cron)
2. Integrate with your existing activity tracker
3. Update report generation to use daily logs
4. Test end-to-end: 6am start → activity capture → midnight reset
