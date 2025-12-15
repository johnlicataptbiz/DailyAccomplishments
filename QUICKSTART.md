# Quick Start Guide

Get DailyAccomplishments running in under 10 minutes.

## Prerequisites

- Python 3.10+ (`python3 --version`)
- Git (for cloning)

## Installation

```bash
# Clone and install
git clone https://github.com/johnlicataptbiz/DailyAccomplishments.git
cd DailyAccomplishments
pip install -r requirements.txt
```

## Quick Test

```bash
# 1. Generate sample data
python3 examples/integration_example.py

# 2. Create a report
python3 tools/auto_report.py

# 3. View dashboard
python3 -m http.server 8000
# Open http://localhost:8000/dashboard.html
```

## Basic Integration

Add to your existing activity tracker:

```python
from tools.tracker_bridge import ActivityTrackerBridge

bridge = ActivityTrackerBridge()

# Log events
bridge.on_focus_change("VS Code", "main.py", 120)  # 2 minutes
bridge.on_browser_visit("github.com", "https://github.com", "GitHub")
bridge.on_meeting_start("Daily Standup", 900)  # 15 minutes
```

**See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for complete integration instructions.**

## Optional: Configure Notifications

### Email Reports

1. Get Gmail app password: https://myaccount.google.com/security → App Passwords
2. Update `config.json`:

```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "to_emails": ["recipient@example.com"]
    }
  }
}
```

3. Test: `python3 tools/notifications.py --email-only`

### Slack Integration

1. Create Slack webhook: https://api.slack.com/apps → Create App → Incoming Webhooks
2. Update `config.json`:

```json
{
  "notifications": {
    "slack": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
      "channel": "#productivity"
    }
  }
}
```

3. Test: `python3 tools/notifications.py --slack-only`

## Optional: Schedule Automated Reports

### macOS (launchd)

```bash
# Install the LaunchAgent (runs every 30 minutes by default)
bash scripts/install_launchagents.sh

# Or customize interval (e.g., every 15 minutes):
INTERVAL_SECONDS=900 bash scripts/install_launchagents.sh
```

### Linux (cron)

```bash
crontab -e
# Add: 55 23 * * * cd /path/to/DailyAccomplishments && python3 tools/auto_report.py
```

**See [docs/ops/HANDOFF.md](docs/ops/HANDOFF.md) for production automation details.**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Events not logging | Check `ls -la logs/daily/` and file permissions |
| Report fails | Verify logs exist: `cat logs/daily/YYYY-MM-DD.jsonl \| jq` |
| Dashboard blank | Check report exists: `ls reports/daily-report-*.json` |
| Email fails | Test SMTP: See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) |

## Next Steps

- **Customize**: Edit `config.json` for categories, thresholds, timezone
- **Automate**: Schedule daily reports (see above)
- **Integrate**: Add more data sources (see [ROADMAP.md](ROADMAP.md))
- **Deploy**: Host dashboard on GitHub Pages or Railway

## Documentation

- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Complete integration guide with examples
- [ROADMAP.md](ROADMAP.md) - Future features and planned integrations
- [docs/ops/HANDOFF.md](docs/ops/HANDOFF.md) - Production operations guide
- [examples/README.md](examples/README.md) - API reference and code examples

---

**Ready in 10 minutes** ✅ Start tracking your productivity today!
