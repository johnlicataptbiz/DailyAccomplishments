# Quick Start Checklist

Use this checklist to get your Daily Accomplishments system up and running in minutes.

## Prerequisites ✅

- [ ] Python 3.10+ installed (`python3 --version`)
- [ ] Git repository cloned
- [ ] Virtual environment activated (optional but recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

## Installation (5 minutes)

- [ ] **Install dependencies**
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **Verify installation**
  ```bash
  python3 tools/auto_report.py --help
  ```
  Should show help message without errors.

## Test the System (5 minutes)

- [ ] **Run integration example**
  ```bash
  python3 examples/integration_example.py simple
  ```
  Expected: ✓ Events logged successfully!

- [ ] **Generate a test report**
  ```bash
  python3 tools/auto_report.py --date $(date +%Y-%m-%d)
  ```
  Expected: Report generated in `reports/` directory

- [ ] **View the dashboard**
  ```bash
  python3 -m http.server 8000 &
  open http://localhost:8000/dashboard.html  # macOS
  # or
  xdg-open http://localhost:8000/dashboard.html  # Linux
  ```
  Expected: Dashboard loads with today's data

## Integration (15 minutes)

### Option A: Test with Examples First

- [ ] **Run full example simulation**
  ```bash
  python3 examples/integration_example.py
  ```
  
- [ ] **View logged events**
  ```bash
  cat logs/daily/$(date +%Y-%m-%d).jsonl | jq
  ```

- [ ] **Generate and view report**
  ```bash
  python3 tools/auto_report.py
  open dashboard.html
  ```

### Option B: Integrate with Your Tracker

Follow `INTEGRATION_GUIDE.md` Section 2:

- [ ] **Add imports to your `activity_tracker.py`**
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent / 'tools'))
  from tracker_bridge import ActivityTrackerBridge
  
  bridge = ActivityTrackerBridge()
  ```

- [ ] **Add event logging**
  
  See `examples/integration_example.py` for code examples:
  - Application switches → `bridge.on_focus_change(app, title, duration)`
  - URL visits → `bridge.on_browser_visit(domain, url, title)`
  - Meetings → `bridge.on_meeting_start(name, duration)`
  - Idle time → `bridge.on_idle_end(idle_seconds)`

- [ ] **Test your integration**
  ```bash
  # Run your tracker for a few minutes
  python3 activity_tracker.py
  
  # Check logs
  cat logs/daily/$(date +%Y-%m-%d).jsonl | jq
  
  # Generate report
  python3 tools/auto_report.py
  ```

## Email Notifications (10 minutes)

- [ ] **Get Gmail app password**
  1. Go to https://myaccount.google.com/security
  2. Enable 2-Factor Authentication
  3. Search for "App Passwords"
  4. Generate password for "Mail"
  5. Copy 16-character password

- [ ] **Update `config.json`**
  ```json
  {
    "notifications": {
      "email": {
        "enabled": true,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-app-password-here",
        "from_email": "your-email@gmail.com",
        "to_emails": ["recipient@example.com"]
      }
    }
  }
  ```

- [ ] **Test email**
  ```bash
  python3 tools/notifications.py --email-only
  ```
  Expected: HTML email received with today's report

## Slack Integration (10 minutes)

- [ ] **Create Slack webhook**
  1. Go to https://api.slack.com/apps
  2. Create New App → From Scratch
  3. Name: "Productivity Bot"
  4. Enable Incoming Webhooks
  5. Add New Webhook to Workspace
  6. Select channel (e.g., #productivity)
  7. Copy webhook URL

- [ ] **Update `config.json`**
  ```json
  {
    "notifications": {
      "slack": {
        "enabled": true,
        "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "channel": "#productivity",
        "username": "Productivity Bot"
      }
    }
  }
  ```

- [ ] **Test Slack**
  ```bash
  python3 tools/notifications.py --slack-only
  ```
  Expected: Message appears in Slack channel with report summary

## Automation (10 minutes)

### macOS - launchd

- [ ] **Create report job**
  ```bash
  # Create file: ~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
  # See INTEGRATION_GUIDE.md for template
  
  launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
  ```

- [ ] **Create notification job**
  ```bash
  # Create file: ~/Library/LaunchAgents/com.dailyaccomplishments.notify.plist
  # See INTEGRATION_GUIDE.md for template
  
  launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.notify.plist
  ```

- [ ] **Verify jobs loaded**
  ```bash
  launchctl list | grep dailyaccomplishments
  ```

### Linux - cron

- [ ] **Edit crontab**
  ```bash
  crontab -e
  ```

- [ ] **Add jobs**
  ```cron
  # Generate report at 11:55 PM
  55 23 * * * /usr/bin/python3 /path/to/DailyAccomplishments/tools/auto_report.py
  
  # Send notifications at 11:58 PM
  58 23 * * * /usr/bin/python3 /path/to/DailyAccomplishments/tools/notifications.py
  ```

- [ ] **Verify cron jobs**
  ```bash
  crontab -l
  ```

## Deployment (Optional - 10 minutes)

### GitHub Pages

- [ ] **Copy files to gh-pages directory**
  ```bash
  cp dashboard.html gh-pages/
  cp -r reports gh-pages/
  ```

- [ ] **Commit and push**
  ```bash
  cd gh-pages
  git add .
  git commit -m "Update dashboard"
  git push origin gh-pages
  ```

- [ ] **Access online**
  ```
  https://YOUR-USERNAME.github.io/DailyAccomplishments/dashboard.html
  ```

## Verification

Run this complete test sequence:

```bash
# 1. Log some test events
python3 examples/integration_example.py

# 2. Generate report
python3 tools/auto_report.py

# 3. View dashboard
python3 -m http.server 8000 &
open http://localhost:8000/dashboard.html

# 4. Send notifications (if configured)
python3 tools/notifications.py

# 5. Check everything worked
echo "✓ Test complete!"
```

Expected results:
- ✅ Events logged to `logs/daily/YYYY-MM-DD.jsonl`
- ✅ Report generated in `reports/daily-report-YYYY-MM-DD.json`
- ✅ Dashboard displays data with charts
- ✅ Email received (if configured)
- ✅ Slack message posted (if configured)

## Troubleshooting

### Events not logging?

```bash
# Check file permissions
ls -la logs/daily/

# Check for lock files
ls -la logs/daily/*.lock

# Run with verbose logging
python3 examples/integration_example.py 2>&1 | tee debug.log
```

### Report generation fails?

```bash
# Check logs exist
ls -la logs/daily/

# Verify JSONL format
cat logs/daily/YYYY-MM-DD.jsonl | jq

# Check Python dependencies
pip list | grep -E "(matplotlib|requests)"
```

### Dashboard not loading?

```bash
# Check report exists
ls -la reports/daily-report-*.json

# Check HTTP server running
lsof -i :8000

# View browser console
# Open dashboard, press F12, check Console tab for errors
```

### Email not sending?

```bash
# Test SMTP connection
python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('your-email@gmail.com', 'your-app-password')
print('✅ SMTP OK')
s.quit()
"
```

### Slack not posting?

```bash
# Test webhook
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test from Daily Accomplishments"}'
```

## Next Steps

Once everything is working:

1. **Customize Categories**
   - Edit `tools/analytics.py` → `CATEGORY_MAPPING`
   - Add your custom activity categories

2. **Adjust Thresholds**
   - Deep work threshold: `analytics.py` line ~250
   - Idle threshold: `idle_detection.py` line 25
   - Break recommendations: `idle_detection.py` line 210

3. **Schedule Regular Reports**
   - Daily: 11:55 PM (before midnight reset)
   - Weekly: Sunday 11:55 PM
   - Monthly: Last day of month

4. **Monitor and Optimize**
   - Review dashboard weekly
   - Check focus windows for deep work planning
   - Track productivity trends over time

## Resources

- **Complete Guide**: `INTEGRATION_GUIDE.md`
- **API Reference**: `examples/README.md`
- **Feature Overview**: `DELIVERY_SUMMARY.md`
- **Technical Details**: `IMPROVEMENTS.md`

## Support

Questions? Check:
1. Logs: `tail -f /tmp/dailyaccomplishments*.log`
2. Documentation in repository
3. Example code in `examples/`

---

## Summary Checklist

- [ ] Dependencies installed
- [ ] Integration tested with examples
- [ ] Dashboard working locally
- [ ] Email notifications configured (optional)
- [ ] Slack integration configured (optional)
- [ ] Automation scheduled (optional)
- [ ] GitHub Pages deployed (optional)

**All done!** 🎉 Your productivity tracking system is ready to use.

Start tracking: Run your integrated `activity_tracker.py` or use the bridge API directly.

View results: Generate daily reports and check the dashboard at the end of each day.

Get insights: Review focus windows, productivity scores, and time distribution to optimize your workflow.
