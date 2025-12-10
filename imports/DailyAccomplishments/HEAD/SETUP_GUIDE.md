# Daily Accomplishments Tracker - Setup Guide

Complete step-by-step setup instructions for getting started with the Daily Accomplishments Tracker.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.9 or higher** (required for `zoneinfo` module)
  - Check version: `python3 --version`
  - Download: https://www.python.org/downloads/
- **Git** (for cloning the repository)
- **Text editor** (for editing configuration files)
- **SMTP account** (optional, for email notifications)
- **Slack workspace** (optional, for Slack notifications)

## Step 1: Clone the Repository

```bash
git clone https://gitlab.com/acttrack/DailyAccomplishments/DailyAccomplishments.git
cd DailyAccomplishments
```

## Step 2: Create Required Directories

The tracker needs three directories to store logs and reports:

```bash
# Create reports directory (stores generated JSON and Markdown reports)
mkdir -p reports

# Create daily logs directory (stores daily event logs in JSONL format)
mkdir -p logs/daily

# Create archive directory (stores archived historical logs)
mkdir -p logs/archive
```

**Why these directories?**
- `reports/` - Stores generated daily and weekly reports in JSON and Markdown formats
- `logs/daily/` - Stores daily event logs (one JSONL file per day)
- `logs/archive/` - Stores archived logs for long-term retention

## Step 3: Configure the Tracker

### Copy the Example Configuration

```bash
cp config.json.example config.json
```

### Edit Your Configuration

Open `config.json` in your text editor and update the following settings:

#### Set Your Timezone

```json
{
  "tracking": {
    "timezone": "America/Chicago"
  }
}
```

Common timezones:
- `America/New_York` (Eastern Time)
- `America/Chicago` (Central Time)
- `America/Denver` (Mountain Time)
- `America/Los_Angeles` (Pacific Time)
- `Europe/London` (UK)
- `Europe/Paris` (Central European Time)
- `Asia/Tokyo` (Japan)

Find your timezone: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

#### Configure Tracking Hours (Optional)

Set your typical work hours:

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

#### Adjust Analytics Thresholds (Optional)

Customize how the tracker analyzes your productivity:

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

**Parameters explained:**
- `deep_work_threshold`: Minimum minutes for a session to count as deep work (default: 25)
- `idle_threshold_seconds`: Seconds of inactivity before ending a session (default: 300 = 5 minutes)
- `context_switch_cost`: Estimated seconds lost per context switch (default: 60)
- `meeting_credit`: Fraction of meeting time counted as productive, 0-1 (default: 0.25)

## Step 4: Run the Integration Example

Test your installation by running the integration example:

```bash
python3 examples/integration_example.py
```

This will:
1. Create sample event logs
2. Generate a test report
3. Verify all components are working correctly

**Expected output:**
```
✓ Sample events logged
✓ Report generated successfully
✓ Dashboard data ready
```

## Step 5: Generate Your First Report

Once you have some real event data logged, generate your first report:

```bash
# Generate today's report
python3 tools/auto_report.py

# Or generate a report for a specific date
python3 tools/auto_report.py --date 2025-12-05
```

**What gets generated:**
- `reports/daily-report-YYYY-MM-DD.json` - Machine-readable JSON report
- `reports/daily-report-YYYY-MM-DD.md` - Human-readable Markdown summary

## Step 6: View the Dashboard

Start a local web server to view the interactive dashboard:

```bash
python3 -m http.server 8000
```

Then open your browser to: **http://localhost:8000/dashboard.html**

**Dashboard features:**
- Date picker to view any day's report
- Previous/Next buttons for easy navigation
- Interactive charts showing productivity metrics
- Deep work sessions breakdown
- Interruption analysis
- Meeting efficiency stats
- Suggested focus windows

## Step 7: Set Up Notifications (Optional)

### Email Notifications

1. **For Gmail users:**
   - Enable 2-factor authentication on your Google account
   - Generate an app-specific password: https://myaccount.google.com/apppasswords
   - Use the app password (not your regular password) in the config

2. **Update config.json:**

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

3. **Test email notifications:**

```bash
python3 tools/notifications.py --email
```

### Slack Notifications

1. **Create a Slack webhook:**
   - Go to https://api.slack.com/apps
   - Create a new app or select an existing one
   - Enable "Incoming Webhooks"
   - Add webhook to your workspace
   - Copy the webhook URL

2. **Update config.json:**

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

3. **Test Slack notifications:**

```bash
python3 tools/notifications.py --slack
```

## Step 8: Set Up Automation (Optional)

Automate daily report generation using cron (Linux/macOS) or Task Scheduler (Windows).

### Linux/macOS (cron)

Edit your crontab:

```bash
crontab -e
```

Add these lines:

```bash
# Generate daily report at 11 PM
0 23 * * * cd /path/to/DailyAccomplishments && python3 tools/auto_report.py

# Generate weekly report on Sunday at midnight
0 0 * * 0 cd /path/to/DailyAccomplishments && python3 tools/auto_report.py --type weekly

# Send email notification at 11:05 PM (after report generation)
5 23 * * * cd /path/to/DailyAccomplishments && python3 tools/notifications.py --email
```

**Important:** Replace `/path/to/DailyAccomplishments` with the actual path to your installation.

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create a new task
3. Set trigger: Daily at 11:00 PM
4. Set action: Run `python3 tools/auto_report.py`
5. Set working directory: Your DailyAccomplishments folder

## Troubleshooting

### Problem: "No report found" in dashboard

**Solution:**
1. Check if log file exists: `ls logs/daily/YYYY-MM-DD.jsonl`
2. Generate report: `python3 tools/auto_report.py --date YYYY-MM-DD`
3. Verify reports directory: `ls reports/`

### Problem: "Log file not found" error

**Solution:**
1. Run the integration example first: `python3 examples/integration_example.py`
2. Ensure directories exist: `mkdir -p logs/daily logs/archive reports`
3. Check if tracker is running and logging events

### Problem: Timezone mismatch (events at wrong time)

**Solution:**
1. Verify timezone in `config.json`
2. List available timezones: `python3 -c "import zoneinfo; print(sorted(zoneinfo.available_timezones()))"`
3. Update config and regenerate reports

### Problem: Email not sending

**Solution:**
1. For Gmail, use app-specific password (not regular password)
2. Verify SMTP settings: `smtp.gmail.com:587`
3. Check that TLS is enabled: `"use_tls": true`
4. Test with: `python3 tools/notifications.py --email`

### Problem: Slack notification fails

**Solution:**
1. Verify webhook URL is correct
2. Test webhook with curl:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test"}' \
     YOUR_WEBHOOK_URL
   ```
3. Check that channel exists and bot has access

### Problem: Charts not loading in dashboard

**Solution:**
1. Check browser console for errors (press F12)
2. Verify Chart.js CDN is accessible
3. Check report JSON has data: `cat reports/daily-report-YYYY-MM-DD.json`

### Problem: Import errors or module not found

**Solution:**
1. Ensure you're in the project root directory
2. Check Python version: `python3 --version` (must be 3.9+)
3. Install optional dependencies: `pip install requests matplotlib pillow`

## Next Steps

Now that you're set up, here's what to do next:

1. **Integrate with your activity tracker** - Connect your time tracking tool to log events
2. **Customize analytics thresholds** - Adjust parameters to match your workflow
3. **Review daily reports** - Check your productivity metrics each evening
4. **Identify patterns** - Look for trends in your focus windows and interruptions
5. **Optimize your schedule** - Use focus window suggestions to plan deep work
6. **Share insights** - Use email/Slack notifications to share progress with your team

## Additional Resources

- **README.md** - Full documentation and usage examples
- **SETUP.md** - Detailed setup instructions
- **IMPROVEMENTS.md** - Planned features and enhancements
- **examples/integration_example.py** - Sample integration code
- **tests/** - Unit tests for all components

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs in `logs/daily/`
3. Run tests: `python3 -m pytest tests/`
4. Check the GitLab issues: https://gitlab.com/acttrack/DailyAccomplishments/DailyAccomplishments/-/issues

Happy tracking! 📊
