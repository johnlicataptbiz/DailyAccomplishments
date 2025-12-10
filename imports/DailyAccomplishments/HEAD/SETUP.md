# Setup Guide

Complete setup instructions for the Daily Accomplishments Tracker.

## Prerequisites

- **Python 3.9+** (required for `zoneinfo` module)
- **Git** (for cloning the repository)
- **SMTP Account** (optional, for email notifications)
- **Slack Webhook** (optional, for Slack notifications)

## Installation

### 1. Clone Repository

```bash
git clone https://gitlab.com/acttrack/DailyAccomplishments/DailyAccomplishments.git
cd DailyAccomplishments
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Optional dependencies for enhanced features
pip install matplotlib pillow requests
```

**Note**: The core system uses only Python standard library. Optional dependencies:
- `matplotlib` - For chart generation in reports (optional)
- `pillow` - For image processing (optional)
- `requests` - For Slack notifications (optional)

### 4. Copy Configuration

```bash
cp config.json.example config.json
```

## Configuration

Edit `config.json` with your settings:

### Timezone

Set your local timezone:

```json
{
  "tracking": {
    "timezone": "America/Chicago"
  }
}
```

Common timezones:
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`

### Tracking Hours

Define your daily coverage window:

```json
{
  "tracking": {
    "daily_start_hour": 5,
    "daily_start_minute": 0,
    "daily_end_hour": 23,
    "daily_end_minute": 59
  }
}
```

### Log Directories

Specify where logs are stored:

```json
{
  "tracking": {
    "log_directory": "logs/daily",
    "archive_directory": "logs/archive"
  }
}
```

### Analytics Thresholds

Customize analytics parameters:

```json
{
  "analytics": {
    "deep_work_threshold": 25,
    "idle_threshold_seconds": 300,
    "context_switch_cost": 60,
    "meeting_credit": 0.25
  }
}
```

**Parameters**:
- `deep_work_threshold`: Minimum minutes for a session to count as deep work (default: 25)
- `idle_threshold_seconds`: Gap in seconds to end a session (default: 300 = 5 minutes)
- `context_switch_cost`: Seconds lost per context switch (default: 60)
- `meeting_credit`: Fraction of meeting time counted as productive, 0-1 (default: 0.25)

### Email Notifications

Configure SMTP for email reports:

```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "use_tls": true,
      "username": "your-email@gmail.com",
      "password": "your-app-specific-password",
      "from_email": "your-email@gmail.com",
      "to_emails": ["recipient@example.com"]
    }
  }
}
```

**Gmail Setup**:
1. Enable 2-factor authentication
2. Generate app-specific password: https://myaccount.google.com/apppasswords
3. Use app password in config (not your regular password)

### Slack Notifications

Configure Slack webhook:

```json
{
  "notifications": {
    "slack_webhook": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
      "channel": "#productivity",
      "username": "Productivity Bot"
    }
  }
}
```

**Slack Setup**:
1. Go to https://api.slack.com/apps
2. Create new app or select existing
3. Enable Incoming Webhooks
4. Add webhook to workspace
5. Copy webhook URL to config

## Directory Structure

The system expects these directories:

```
DailyAccomplishments/
├── logs/
│   ├── daily/          # Daily event logs (YYYY-MM-DD.jsonl)
│   └── archive/        # Archived logs
├── reports/            # Generated reports (JSON and Markdown)
├── tools/              # Python modules
├── tests/              # Unit tests
├── config.json         # Your configuration
└── dashboard.html      # Web dashboard
```

Directories are created automatically when needed.

## Event Log Format

Daily logs are stored as JSONL (JSON Lines) files in `logs/daily/YYYY-MM-DD.jsonl`.

### Event Types

**Metadata** (log information):
```json
{"type": "metadata", "version": "1.0", "timezone": "America/Chicago"}
```

**Focus Change** (app usage):
```json
{
  "type": "focus_change",
  "timestamp": "2025-12-05T09:30:00-06:00",
  "data": {
    "app": "VS Code",
    "duration_seconds": 1800
  }
}
```

**App Switch** (context switch):
```json
{
  "type": "app_switch",
  "timestamp": "2025-12-05T10:15:00-06:00",
  "data": {
    "from_app": "VS Code",
    "to_app": "Chrome"
  }
}
```

**Window Change** (window switch):
```json
{
  "type": "window_change",
  "timestamp": "2025-12-05T10:20:00-06:00"
}
```

**Meeting** (meeting events):
```json
{
  "type": "meeting_start",
  "timestamp": "2025-12-05T14:00:00-06:00",
  "data": {"title": "Team Sync"}
}
```

```json
{
  "type": "meeting_end",
  "timestamp": "2025-12-05T14:30:00-06:00",
  "data": {"duration_seconds": 1800}
}
```

**Idle** (inactivity):
```json
{
  "type": "idle_start",
  "timestamp": "2025-12-05T12:00:00-06:00"
}
```

```json
{
  "type": "idle_end",
  "timestamp": "2025-12-05T12:15:00-06:00",
  "data": {"duration_seconds": 900}
}
```

## Running the Tracker

### Manual Logging

```python
from tools.daily_logger import write_event

# Log a focus session
write_event({
    'type': 'focus_change',
    'data': {
        'app': 'VS Code',
        'duration_seconds': 1800
    }
})
```

### Automated Logging

Set up a cron job or background service to log events automatically. See your activity tracking tool's documentation for integration.

## Generating Reports

### Daily Report

```bash
# Today's report
python3 tools/auto_report.py

# Specific date
python3 tools/auto_report.py --date 2025-12-05

# Custom output directory
python3 tools/auto_report.py --output /path/to/reports
```

### Weekly Report

```bash
# This week (ending today)
python3 tools/auto_report.py --type weekly

# Specific week (ending on date)
python3 tools/auto_report.py --type weekly --date 2025-12-05
```

## Viewing Dashboard

### Start Web Server

```bash
python3 -m http.server 8000
```

### Open in Browser

Navigate to: http://localhost:8000/dashboard.html

### Using the Dashboard

- **Date Picker**: Select any date to view its report
- **Previous/Next**: Navigate between days
- **Charts**: Interactive Chart.js visualizations
- **Responsive**: Works on desktop and mobile

## Automation Setup

### Cron (Linux/macOS)

Edit crontab:

```bash
crontab -e
```

Add entries:

```bash
# Generate daily report at 11 PM
0 23 * * * cd /path/to/DailyAccomplishments && /path/to/python3 tools/auto_report.py

# Generate weekly report on Sunday at midnight
0 0 * * 0 cd /path/to/DailyAccomplishments && /path/to/python3 tools/auto_report.py --type weekly

# Send email notification at 11:05 PM
5 23 * * * cd /path/to/DailyAccomplishments && /path/to/python3 tools/notifications.py --email
```

### macOS LaunchAgent

Create `~/Library/LaunchAgents/com.dailyaccomplishments.report.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaccomplishments.report</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/DailyAccomplishments/tools/auto_report.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>23</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/path/to/DailyAccomplishments</string>
</dict>
</plist>
```

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
```

### systemd (Linux)

Create `/etc/systemd/system/daily-accomplishments.service`:

```ini
[Unit]
Description=Daily Accomplishments Report Generator
After=network.target

[Service]
Type=oneshot
User=youruser
WorkingDirectory=/path/to/DailyAccomplishments
ExecStart=/usr/bin/python3 tools/auto_report.py

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/daily-accomplishments.timer`:

```ini
[Unit]
Description=Daily Accomplishments Report Timer

[Timer]
OnCalendar=23:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl enable daily-accomplishments.timer
sudo systemctl start daily-accomplishments.timer
```

## Troubleshooting

### No Report Found

**Problem**: Dashboard shows "No report found"

**Solution**:
1. Check if log file exists: `ls logs/daily/YYYY-MM-DD.jsonl`
2. Generate report: `python3 tools/auto_report.py --date YYYY-MM-DD`
3. Verify output directory: `ls reports/`

### Timezone Mismatch

**Problem**: Events logged at wrong time

**Solution**:
1. Verify timezone in config.json: `"timezone": "America/Chicago"`
2. Check available timezones: `python3 -c "import zoneinfo; print(zoneinfo.available_timezones())"`
3. Update config and regenerate reports

### Charts Not Loading

**Problem**: Dashboard shows but charts are blank

**Solution**:
1. Check browser console for errors (F12)
2. Verify Chart.js CDN is accessible
3. Check report JSON has data: `cat reports/daily-report-YYYY-MM-DD.json`

### Email Not Sending

**Problem**: Email notification fails

**Solution**:
1. Verify SMTP credentials in config.json
2. For Gmail, use app-specific password (not regular password)
3. Check SMTP server and port (Gmail: smtp.gmail.com:587)
4. Enable "Less secure app access" or use OAuth2
5. Test with: `python3 tools/notifications.py --email`

### Slack Not Posting

**Problem**: Slack notification fails

**Solution**:
1. Verify webhook URL in config.json
2. Test webhook with curl:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test"}' \
     YOUR_WEBHOOK_URL
   ```
3. Check Slack app permissions
4. Verify channel exists and bot has access

### Import Errors

**Problem**: `ModuleNotFoundError` when running scripts

**Solution**:
1. Ensure you're in the project root directory
2. Check Python version: `python3 --version` (must be 3.9+)
3. Install optional dependencies: `pip install requests`
4. Use absolute imports or run as module: `python3 -m tools.auto_report`

## Next Steps

1. **Test the system**: Generate a sample report with example data
2. **Integrate tracking**: Connect your activity tracking tool
3. **Customize thresholds**: Adjust analytics parameters for your workflow
4. **Set up automation**: Configure cron jobs for nightly reports
5. **Enable notifications**: Set up email or Slack for daily summaries

See `README.md` for usage examples and `IMPROVEMENTS.md` for planned features.
