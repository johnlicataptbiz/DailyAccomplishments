# Daily Accomplishments Tracker

> **A robust, production-ready activity tracking and productivity analytics system**

Automatically track your daily activities, analyze productivity patterns, and get actionable insights through beautiful dashboards and automated notifications.

## ✨ Features

### 🛡️ **Robust & Reliable**
- **Error Handling**: File locking, JSON validation, automatic backups, self-healing
- **Data Integrity**: Health checks, corruption detection, automatic repair
- **Cross-Platform**: macOS, Linux, Windows support
- **Timezone-Aware**: Accurate timestamps with configurable timezone

### 📊 **Analytics & Insights**
- **Deep Work Detection**: Identify focused work sessions (25+ minutes)
- **Productivity Scoring**: 0-100 scale with quality ratings
- **Interruption Analysis**: Track context switches and distractions
- **Focus Windows**: AI-recommended time blocks for deep work
- **Category Breakdown**: Automatic categorization by activity type

### 🖥️ **Web Dashboard**
- **Interactive Charts**: Chart.js visualizations (hourly interruptions, category distribution)
- **Real-Time Stats**: Productivity score, deep work hours, focus time %, interruptions
- **Session List**: All work sessions with quality indicators
- **Auto-Refresh**: Updates every 5 minutes
- **Historical Data**: Date picker for past reports

### 📧 **Notifications**
- **Email**: Beautiful HTML reports via SMTP (Gmail)
- **Slack**: Rich block-based messages with emoji indicators
- **Automated**: Schedule daily/weekly delivery
- **Smart Summaries**: Top sessions, category breakdown, focus recommendations

### 🔗 **Easy Integration**
- **Bridge API**: Drop-in integration for existing trackers
- **Event Types**: App switches, URL visits, meetings, idle time, focus sessions
- **Deduplication**: Automatic filtering of duplicate events (2-second window)
- **Simple API**: Just 3 lines of code to start logging

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/johnlicataptbiz/DailyAccomplishments.git
cd DailyAccomplishments

# Install dependencies
pip install -r requirements.txt

# Run example
python3 examples/integration_example.py simple
```

### Generate Your First Report

```bash
# Log some test events
python3 examples/integration_example.py

# Generate report
python3 tools/auto_report.py

# View dashboard
python3 -m http.server 8000
open http://localhost:8000/dashboard.html
```

### Smoke-test Railway (static paths)

```bash
bash scripts/smoke_railway.sh https://dailyaccomplishments.up.railway.app
```

### Integration (3 Lines)

```python
from tools.tracker_bridge import ActivityTrackerBridge

bridge = ActivityTrackerBridge()
bridge.on_focus_change("VS Code", "main.py", 120)  # 2 minutes
```

**That's it!** Events are now logged to `logs/daily/YYYY-MM-DD.jsonl`

## ✨ Advanced Features

### Timeline-Based Aggregation
- **High-Fidelity Reporting**: Instead of bucketing events into hourly chunks, the system now constructs a precise timeline of your activity. It intelligently merges overlapping events and re-attributes time based on activity priority (e.g., coding in the foreground during a meeting).
- **Accurate Metrics**: This results in highly accurate `focus_time`, `meetings_time`, and `active_time` calculations.

### SVG Activity Timeline
- **Visual Overview**: The dashboard now features a dynamic SVG timeline visualization that shows your entire day at a glance.
- **Color-Coded Categories**: Each activity segment is color-coded by category (Coding, Research, Meetings, etc.) for easy identification.
- **Deep Work Overlay**: Contiguous deep work sessions are highlighted as a translucent overlay, making it easy to spot your most productive periods.

### Configurable Category Priority
- **Flexible Attribution**: You can now control how overlapping activities are attributed by defining a priority order for categories.
- **Easy Configuration**: Simply edit the `category_priority` array in your `config.json` file. The generator will use this order to decide which activity "wins" when overlaps occur.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | Step-by-step checklist (45 minutes to complete setup) |
| **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** | Complete integration guide with code examples |
| **[examples/README.md](examples/README.md)** | API reference and integration examples |
| **[DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md)** | Feature overview and what was delivered |
| **[IMPROVEMENTS.md](IMPROVEMENTS.md)** | Technical architecture and design decisions |

## 🎯 Use Cases

### For Individual Developers
- Track coding sessions and productivity
- Identify optimal focus times
- Minimize context switching
- Review daily/weekly progress

### For Teams
- Share productivity reports via Slack
- Identify meeting overhead
- Optimize team schedules
- Track project time allocation

### For Managers
- Automated daily email summaries
- Productivity trend analysis
- Focus time vs. meeting time balance
- Data-driven schedule optimization

## 📊 Dashboard Preview

```
┌─────────────────────────────────────────────────────────┐
│  Daily Productivity Report                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Score: 85/100 (Excellent)                           │
│  ⏱️  Deep Work: 4h 30min                                │
│  🎯 Focus Time: 65%                                     │
│  🔄 Interruptions: 12                                   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Hourly Interruptions          Category Distribution   │
│  [Bar Chart]                   [Doughnut Chart]        │
├─────────────────────────────────────────────────────────┤
│  Sessions                                               │
│  • 09:00-11:30 Development (95 quality)                │
│  • 14:00-16:00 Writing (88 quality)                    │
│  • 16:30-17:30 Research (75 quality)                   │
└─────────────────────────────────────────────────────────┘
```

## 🔔 Notification Examples

### Email (HTML)
- Gradient header with branding
- Stats grid with icons
- Top 3 productive sessions
- Category breakdown with percentages
- Focus window recommendations

### Slack (Rich Blocks)
```
📊 Daily Productivity Report — December 2, 2025

Score: 85/100 (Excellent) 🎉
⏱️ Deep Work: 4h 30min
🎯 Focus Time: 65%
🔄 Interruptions: 12

🏆 Top Sessions:
1. 09:00-11:30 (2.5h) — Development • Quality: 95
2. 14:00-16:00 (2h) — Writing • Quality: 88
3. 16:30-17:30 (1h) — Research • Quality: 75
```

## 🏗️ Architecture

### Core Modules (3,000+ lines of Python)

- **`daily_logger.py`** (380 lines): Robust JSONL logging with error handling
- **`tracker_bridge.py`** (220 lines): Integration API with deduplication
- **`analytics.py`** (600 lines): Productivity analytics engine
- **`idle_detection.py`** (400 lines): Cross-platform idle monitoring
- **`auto_report.py`** (300 lines): Automated report generation
- **`notifications.py`** (500 lines): Email and Slack delivery
- **`dashboard.html`** (400 lines): Interactive web UI with Chart.js

### Data Flow

```
Your Tracker
    ↓
tracker_bridge.py (deduplication)
    ↓
daily_logger.py (JSONL storage)
    ↓
analytics.py (productivity scoring)
    ↓
auto_report.py (JSON + Markdown)
    ↓
┌─────────────┬──────────────┐
│  dashboard  │ notifications│
│  (Chart.js) │ (Email/Slack)│
└─────────────┴──────────────┘
```

## 🔧 Configuration

Edit `config.json`:

```json
{
  "tracking": {
    "daily_start_hour": 6,
    "timezone": "America/Chicago",
    "enable_running_log": true
  },
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "to_emails": ["recipient@example.com"]
    },
    "slack": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/services/...",
      "channel": "#productivity"
    }
  }
}
```

## 📝 Event Types

| Event Type | Description | API Method |
|------------|-------------|------------|
| **focus_change** | User focuses on application | `on_focus_change(app, title, duration)` |
| **app_switch** | Switch between applications | `on_app_switch(from_app, to_app)` |
| **window_change** | Window title changes | `on_window_change(app, title)` |
| **browser_visit** | Browser page visit | `on_browser_visit(domain, url, title)` |
| **meeting_start** | Meeting begins | `on_meeting_start(name, duration)` |
| **meeting_end** | Meeting ends | `on_meeting_end(name, duration)` |
| **idle_start** | User becomes idle | `on_idle_start()` |
| **idle_end** | User returns from idle | `on_idle_end(idle_seconds)` |
| **manual_entry** | Manual time entry | `on_manual_entry(desc, duration, category)` |

## 🎨 Customization

### Categories

Edit `tools/analytics.py`:

```python
CATEGORY_MAPPING = {
    'Development': ['VS Code', 'Terminal', 'GitHub'],
    'Communication': ['Slack', 'Email', 'Zoom'],
    'Research': ['Safari', 'Chrome', 'Documentation'],
    # Add your custom categories
    'Learning': ['Udemy', 'YouTube', 'Coursera'],
}
```

### Deep Work Threshold

```python
# In analytics.py, line ~250
def detect_deep_work_sessions(self, sessions, min_duration=25):
    # Change min_duration (default: 25 minutes)
```

### Idle Threshold

```python
# In idle_detection.py, line 25
def __init__(self, idle_threshold_seconds: int = 300):
    # Change threshold (default: 5 minutes)
```

## ⏰ Automation

### macOS (launchd)

```bash
# Schedule daily report at 11:55 PM
~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
launchctl load ~/Library/LaunchAgents/com.dailyaccomplishments.report.plist
```

### Linux (cron)

```bash
# Edit crontab
crontab -e

# Add daily jobs
55 23 * * * python3 /path/to/tools/auto_report.py
58 23 * * * python3 /path/to/tools/notifications.py
```

See `INTEGRATION_GUIDE.md` for complete launchd/cron templates.

## 🌐 Deployment

### Local Dashboard

```bash
python3 -m http.server 8000
open http://localhost:8000/dashboard.html
```

### GitHub Pages

```bash
cp dashboard.html gh-pages/
cp -r reports gh-pages/
cd gh-pages && git push origin gh-pages
# Access at: https://YOUR-USERNAME.github.io/DailyAccomplishments/
```

## 🧪 Testing

Run the test suite:

```bash
# Simple integration test
python3 examples/integration_example.py simple

# Full day simulation
python3 examples/integration_example.py

# Verify logs
cat logs/daily/$(date +%Y-%m-%d).jsonl | jq

# Generate report
python3 tools/auto_report.py

# Test notifications (if configured)
python3 tools/notifications.py --email-only
python3 tools/notifications.py --slack-only
```

## 🐛 Troubleshooting

### Events Not Logging?

```bash
# Check file permissions
ls -la logs/daily/

# Check for errors
tail -f /tmp/dailyaccomplishments*.log
```

### Dashboard Not Loading?

```bash
# Check report exists
ls -la reports/daily-report-*.json

# Verify HTTP server
lsof -i :8000

# Check browser console (F12)
```

### Notifications Failing?

```bash
# Test email
python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('email', 'password')
print('✅ Email OK')
s.quit()
"

# Test Slack
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test"}'
```

## 📦 Requirements

- Python 3.10+
- matplotlib 3.10+
- requests 2.32+
- Modern web browser (for dashboard)

## 🤝 Contributing

This is a personal productivity tracking system, but feel free to fork and customize for your needs.

## 📄 License

MIT License - See LICENSE file for details

## 🎯 Project Status

**Production Ready** ✅

- ✅ 3,000+ lines of production code
- ✅ Comprehensive error handling
- ✅ Full documentation
- ✅ Working examples
- ✅ Automated testing
- ✅ Cross-platform support

## 📞 Support

For questions or issues:
1. Check documentation in repository
2. Review example code in `examples/`
3. Check troubleshooting sections in guides

---

**Ready to optimize your productivity?** Start with [QUICKSTART.md](QUICKSTART.md) 🚀

## Production automation (macOS launchd)
If you are running the scheduled publisher on macOS via launchd, the canonical operations doc is:

  HANDOFF.md

The expected launchd label is:

  com.dailyaccomplishments.reporter
