# Integration Guide: Daily Accomplishments Tracker

This guide shows you **exactly how** to integrate the new robust tracking system with your existing `activity_tracker.py`, configure notifications, and use the web dashboard.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Integrating with Existing Tracker](#integrating-with-existing-tracker)
3. [Email Notifications Setup](#email-notifications-setup)
4. [Slack Integration Setup](#slack-integration-setup)
5. [Using the Web Dashboard](#using-the-web-dashboard)
6. [Automated Report Scheduling](#automated-report-scheduling)
7. [Complete Workflow Example](#complete-workflow-example)

---

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install -r requirements.txt

# Verify Python version (3.10+)
python3 --version
```

### Test the System

```bash
# Generate a test report
python3 tools/auto_report.py --date 2025-12-01

# Open the dashboard
open dashboard.html  # macOS
# or
xdg-open dashboard.html  # Linux
```

---

## Daily Window & Reset

This system tracks each day from 6:00 AM to midnight (local time) and performs a reset at midnight.

- Start: 06:00 local (America/Chicago by default)
- Reset: 00:00 local (midnight)
- Running log: JSONL at `logs/daily/YYYY-MM-DD.jsonl`

You can change these in `config.json`:

```json
{
  "tracking": {
    "daily_start_hour": 6,
    "daily_start_minute": 0,
    "reset_hour": 0,
    "reset_minute": 0,
    "timezone": "America/Chicago"
  },
  "report": {
    "coverage_start": "06:00",
    "coverage_end": "24:00"
  }
}
```

Note: If you prefer a different window, update the `tracking.*` and `report.coverage_*` values accordingly.

---

## Integrating with Existing Tracker

Your existing `activity_tracker.py` (3600 lines) can send events to the new system using `tracker_bridge.py`.

### Step 1: Import the Bridge

Add this to the top of your `activity_tracker.py`:

```python
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from tracker_bridge import ActivityTrackerBridge

# Initialize the bridge
bridge = ActivityTrackerBridge()
```

### Step 2: Log Application Switches

Find where your tracker detects application changes and add:

```python
# When application changes
def on_application_change(app_name, window_title):
    """Called when active application changes."""
    bridge.log_application_switch(
        application=app_name,
        window_title=window_title
    )
    # ... your existing code ...
```

### Step 3: Log URL Visits (for browsers)

```python
# When browser URL changes
def on_url_change(url):
    """Called when browser URL changes."""
    # Extract domain
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    bridge.log_url_visit(
        url=url,
        domain=domain,
        title=current_window_title  # your code to get title
    )
    # ... your existing code ...
```

### Step 4: Log Meetings

```python
# When a meeting starts
def on_meeting_start(meeting_info):
    """Called when a meeting starts."""
    bridge.log_meeting(
        title=meeting_info['title'],
        duration_seconds=meeting_info.get('duration', 0),
        attendees=meeting_info.get('attendees', []),
        platform=meeting_info.get('platform', 'Unknown')  # Zoom, Teams, etc.
    )
```

### Step 5: Log Idle Detection

```python
# Use the built-in idle detector
from idle_detection import IdleDetector

idle_detector = IdleDetector(threshold_seconds=300)  # 5 minutes

# In your main loop
def check_idle():
    """Check for idle time."""
    idle_seconds = idle_detector.get_idle_time()
    
    if idle_seconds >= 300:  # 5 minutes idle
        bridge.log_idle_detection(
            idle_duration=idle_seconds
        )
```

### Step 6: Log Focus Sessions

```python
# When user completes a deep work session
def on_focus_session_complete(duration_minutes, category):
    """Called when a focus session completes."""
    bridge.log_focus_session(
        duration_minutes=duration_minutes,
        category=category,
        interruption_count=get_interruption_count()  # your code
    )
```

### Complete Integration Example

Here's a complete example showing how to integrate:

```python
#!/usr/bin/env python3
"""
activity_tracker.py - Enhanced with DailyAccomplishments integration
"""

import sys
from pathlib import Path

# Add tools directory
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from tracker_bridge import ActivityTrackerBridge
from idle_detection import IdleDetector

class EnhancedActivityTracker:
    def __init__(self):
        # Your existing initialization
        self.current_app = None
        self.current_url = None
        
        # New: Initialize bridge
        self.bridge = ActivityTrackerBridge()
        self.idle_detector = IdleDetector(threshold_seconds=300)
        
    def track_application(self, app_name, window_title):
        """Track application switch with deduplication."""
        if app_name != self.current_app:
            # Log to new system
            self.bridge.log_application_switch(
                application=app_name,
                window_title=window_title
            )
            
            # Your existing tracking
            self.current_app = app_name
            # ... rest of your code ...
    
    def track_browser_url(self, url, title):
        """Track browser URL with deduplication."""
        from urllib.parse import urlparse
        
        if url != self.current_url:
            domain = urlparse(url).netloc
            
            # Log to new system
            self.bridge.log_url_visit(
                url=url,
                domain=domain,
                title=title
            )
            
            # Your existing tracking
            self.current_url = url
            # ... rest of your code ...
    
    def check_idle(self):
        """Check for idle time."""
        idle_seconds = self.idle_detector.get_idle_time()
        
        if idle_seconds >= 300:  # 5 minutes
            self.bridge.log_idle_detection(idle_duration=idle_seconds)
            
            # Check if break is recommended
            if self.idle_detector.is_break_recommended():
                print("🎯 Break recommended! You've been focused for a while.")
    
    def run(self):
        """Main tracking loop."""
        while True:
            # Your existing application tracking
            app_info = self.get_active_application()  # your code
            self.track_application(app_info['name'], app_info['title'])
            
            # Your existing browser tracking
            if app_info['name'] in ['Safari', 'Chrome', 'Firefox']:
                url = self.get_browser_url()  # your code
                self.track_browser_url(url, app_info['title'])
            
            # New: Check idle time
            self.check_idle()
            
            # Sleep interval
            time.sleep(5)

if __name__ == '__main__':
    tracker = EnhancedActivityTracker()
    tracker.run()
```

---

## Email Notifications Setup

### Step 1: Get Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication (required)
3. Go to **App Passwords** (search for it in settings)
4. Select **Mail** and **Mac** (or other device)
5. Click **Generate**
6. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 2: Update config.json

Edit `config.json`:

```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "abcd efgh ijkl mnop",  // Your app password
      "from_email": "your-email@gmail.com",
      "to_emails": ["recipient@example.com", "manager@example.com"]
    }
  }
}
```

### Step 3: Test Email Sending

```bash
# Send today's report via email
python3 tools/notifications.py --email-only

# Send specific date
python3 tools/notifications.py --date 2025-12-01 --email-only
```

You should receive an HTML email with:
- Productivity score and rating
- Deep work vs context switching breakdown
- Top 3 productive sessions
- Category distribution
- Focus window recommendations

---

## Slack Integration Setup

### Step 1: Create Incoming Webhook

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **Create New App** → **From Scratch**
3. Name it **Productivity Bot**, select your workspace
4. Click **Incoming Webhooks** → **Activate Incoming Webhooks**
5. Click **Add New Webhook to Workspace**
6. Select channel (e.g., `#productivity`)
7. Copy the webhook URL (e.g., `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`)

### Step 2: Update config.json

```json
{
  "notifications": {
    "slack": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
      "channel": "#productivity",
      "username": "Productivity Bot"
    }
  }
}
```

### Step 3: Test Slack Notification

```bash
# Send to Slack only
python3 tools/notifications.py --slack-only

# Send to both email and Slack
python3 tools/notifications.py
```

Your Slack message will include:
- 📊 Productivity score with color coding
- ⏱️ Deep work hours
- 🎯 Focus time percentage
- 🔄 Interruption count
- 🏆 Top 3 sessions
- 📈 Category breakdown

---

## Using the Web Dashboard

### Step 1: Generate Report Data

```bash
# Generate today's report
python3 tools/auto_report.py

# Generate specific date
python3 tools/auto_report.py --date 2025-12-01
```

This creates `reports/daily-report-YYYY-MM-DD.json`.

### Step 2: Start Local Server

```bash
# Start HTTP server
python3 -m http.server 8000

# Dashboard available at:
# http://localhost:8000/dashboard.html
```

### Step 3: Open Dashboard

Open `http://localhost:8000/dashboard.html` in your browser.

### Dashboard Features

1. **Date Selector**: Choose any date to view historical reports
2. **Auto-Refresh**: Dashboard updates every 5 minutes
3. **Stats Grid**:
   - Productivity Score (0-100)
   - Deep Work Hours
   - Focus Time %
   - Interruptions count
4. **Hourly Interruptions Chart**: Bar chart showing interruption patterns
5. **Category Distribution**: Doughnut chart of time by category
6. **Session List**: All work sessions with quality scores
7. **Focus Windows**: Recommended time blocks for deep work

### Publishing to GitHub Pages

If you want a permanent URL:

```bash
# Copy dashboard and reports to gh-pages directory
cp dashboard.html gh-pages/
cp -r reports gh-pages/

# Commit and push
cd gh-pages
git add .
git commit -m "Update dashboard with latest reports"
git push origin gh-pages

# Access at:
# https://YOUR-USERNAME.github.io/DailyAccomplishments/dashboard.html
```

---

## Automated Report Scheduling

### macOS (launchd)

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
        <integer>0</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/tmp/dailyaccomplishments.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/dailyaccomplishments.error.log</string>
</dict>
</plist>
```

Load the job:

```bash
launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
```

### Schedule Notifications (12:02 AM daily)

Create `~/Library/LaunchAgents/com.dailyaccomplishments.notify.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaccomplishments.notify</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/DailyAccomplishments/tools/notifications.py</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>2</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/tmp/dailyaccomplishments_notify.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/dailyaccomplishments_notify.error.log</string>
</dict>
</plist>
```

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.notify.plist
```

### Linux (cron)

```bash
# Edit crontab
crontab -e

# Add these lines:
# Generate report at midnight
0 0 * * * /usr/bin/python3 /path/to/DailyAccomplishments/tools/auto_report.py

# Send notifications at 12:02 AM
2 0 * * * /usr/bin/python3 /path/to/DailyAccomplishments/tools/notifications.py
```

---

## Complete Workflow Example

Here's the complete end-to-end workflow:

### Morning (6:00 AM)

1. **Tracker Starts**: Your `activity_tracker.py` begins logging
2. **Bridge Integration**: Events flow to `daily_logger.py` via `tracker_bridge.py`
3. **JSONL Logging**: All events saved to `logs/daily/YYYY-MM-DD.jsonl`

### Throughout the Day

1. **Application Switches**: Logged automatically
2. **URL Visits**: Browser activity tracked
3. **Meetings**: Calendar events recorded
4. **Idle Detection**: Breaks tracked every 5 minutes
5. **Focus Sessions**: Deep work periods identified

### Midnight Reset (12:00 AM)

1. **Auto Report Generation**: `auto_report.py` runs via launchd/cron
2. **Analytics Processing**: 
   - Deep work calculation
   - Productivity scoring
   - Interruption analysis
   - Focus window recommendations
3. **Report Output**:
   - JSON: `reports/daily-report-2025-12-01.json`
   - Markdown: `reports/daily-report-2025-12-01.md`

### Notification (11:58 PM)

1. **Email Sent**: HTML report to your inbox
2. **Slack Message**: Summary posted to `#productivity`
3. **Dashboard Update**: Web dashboard shows new data

### Next Morning

1. **Review Dashboard**: Open `dashboard.html` to see yesterday's stats
2. **Check Focus Windows**: Plan today's deep work using recommendations
3. **Track Progress**: Compare to previous days

---

## Troubleshooting

### Email Not Sending

```bash
# Test SMTP connection
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('✅ SMTP connection successful')
server.quit()
"
```

**Common Issues**:
- ❌ "Username and Password not accepted" → Generate new app password
- ❌ "SMTPAuthenticationError" → Enable 2FA in Google Account
- ❌ "Connection refused" → Check firewall settings

### Slack Webhook Not Working

```bash
# Test webhook
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test message from Daily Accomplishments"}'
```

**Common Issues**:
- ❌ "invalid_payload" → Check JSON formatting in config
- ❌ "channel_not_found" → Verify channel exists and bot has access

### Dashboard Not Loading

**Check**:
1. Report exists: `ls reports/daily-report-*.json`
2. HTTP server running: `lsof -i :8000`
3. Browser console: Press F12, check for errors
4. Date format: Must be `YYYY-MM-DD`

### Bridge Not Logging Events

```bash
# Check log file exists
ls -la logs/daily/

# Verify write permissions
touch logs/daily/test.jsonl && rm logs/daily/test.jsonl

# Check for lock files
ls -la logs/daily/*.lock
```

---

## Advanced Configuration

### Custom Categories

Edit category mappings in `analytics.py`:

```python
CATEGORY_MAPPING = {
    'Development': ['VS Code', 'Terminal', 'GitHub'],
    'Communication': ['Slack', 'Email', 'Zoom'],
    'Research': ['Safari', 'Chrome', 'Documentation'],
    # Add your custom categories
    'Learning': ['Udemy', 'YouTube', 'Coursera'],
}
```

### Adjust Deep Work Threshold

Default is 25 minutes. To change:

```python
# In analytics.py, line ~250
def detect_deep_work_sessions(self, sessions, min_duration=25):
    # Change min_duration to your preference (in minutes)
```

### Custom Idle Threshold

```python
# In your tracker integration
idle_detector = IdleDetector(threshold_seconds=600)  # 10 minutes instead of 5
```

---

## Support

For issues:
1. Check logs: `tail -f /tmp/dailyaccomplishments*.log`
2. Review documentation: `IMPROVEMENTS.md`
3. Inspect JSONL: `cat logs/daily/YYYY-MM-DD.jsonl | jq`

---

**You're all set!** 🎉

Your productivity tracking system is now:
- ✅ Integrated with your existing tracker
- ✅ Sending email and Slack notifications
- ✅ Displaying beautiful web dashboards
- ✅ Running automated daily reports
- ✅ Providing actionable insights
