# Daily Accomplishments Tracker

A privacy-focused productivity analytics system that tracks focus sessions, deep work, interruptions, and meetings to help you understand and optimize your daily work patterns.

## Overview

The Daily Accomplishments Tracker analyzes your work activities to provide insights into:
- Deep work sessions (uninterrupted focus periods ≥25 minutes)
- Productivity scoring (0-100 with detailed components)
- Time spent by category (Coding, Research, Meetings, etc.)
- Interruption patterns and context switching costs
- Meeting efficiency and balance
- Optimal focus windows for scheduling deep work

## Features

- **Deep Work Detection**: Automatically identifies uninterrupted focus sessions ≥25 minutes
- **Productivity Scoring**: Comprehensive 0-100 score based on deep work, interruptions, and session quality
- **Category Tracking**: Categorizes time spent across Research, Coding, Meetings, Communication, Docs, and Other
- **Meeting Efficiency**: Analyzes meeting time vs. focus time ratio with recommendations
- **Focus Window Suggestions**: Identifies low-interruption time blocks for scheduling deep work
- **Daily & Weekly Reports**: Generate JSON and Markdown reports with detailed analytics
- **Static Dashboard**: Beautiful web dashboard with Chart.js visualizations
- **Email & Slack Notifications**: Automated report delivery via email or Slack webhooks
- **Privacy-Focused**: No sensitive data (window titles, URLs) stored - only app names and aggregated metrics

## Quick Start

### Prerequisites

- Python 3.9+ (for `zoneinfo` support)
- Optional: SMTP account for email notifications
- Optional: Slack webhook for Slack notifications

### Installation

```bash
# Clone the repository
git clone https://gitlab.com/acttrack/DailyAccomplishments/DailyAccomplishments.git
cd DailyAccomplishments

# Copy example config
cp config.json.example config.json

# Edit config.json with your timezone and settings
nano config.json

# Create required directories (already created if using git)
mkdir -p logs/daily logs/archive reports
```

## Usage

### Running the Tracker

Log events manually or via automated tracking:

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

### Generating Reports

```bash
# Generate today's report
python3 tools/auto_report.py

# Generate report for specific date
python3 tools/auto_report.py --date 2025-12-05

# Generate weekly report
python3 tools/auto_report.py --type weekly

# Custom output directory
python3 tools/auto_report.py --output custom/path
```

### Viewing the Dashboard

```bash
# Start a local web server
python3 -m http.server 8000

# Open in browser
# http://localhost:8000/dashboard.html
```

Use the date picker to navigate between days and view your productivity metrics.

### Sending Notifications

```bash
# Send email notification
python3 tools/notifications.py --email

# Send Slack notification
python3 tools/notifications.py --slack

# Send both
python3 tools/notifications.py --email --slack
```

## Configuration

Edit `config.json` to customize:

### Tracking Settings
- `timezone`: Your local timezone (e.g., "America/Chicago")
- `daily_start_hour` / `daily_end_hour`: Coverage window (default: 5:00 - 23:59)
- `log_directory`: Path for daily event logs (default: "logs/daily")
- `archive_directory`: Path for archived logs (default: "logs/archive")

### Analytics Thresholds
- `deep_work_threshold`: Minimum minutes for deep work session (default: 25)
- `idle_threshold_seconds`: Gap to end a session (default: 300)
- `context_switch_cost`: Seconds lost per interruption (default: 60)
- `meeting_credit`: Fraction of meeting time counted as productive (default: 0.25)

### Notifications
- **Email**: SMTP server, credentials, recipients
- **Slack**: Webhook URL, channel, username

### Integrations
- HubSpot, Aloware, Monday.com, Slack, Google Calendar (optional)

## Automation

### Cron Job (Linux/macOS)

Generate nightly reports at 11 PM:

```bash
0 23 * * * cd /path/to/DailyAccomplishments && python3 tools/auto_report.py
```

Generate weekly reports on Sunday:

```bash
0 0 * * 0 cd /path/to/DailyAccomplishments && python3 tools/auto_report.py --type weekly
```

### GitHub Actions

The included workflow (`.github/workflows/generate_reports.yml`) automatically:
- Generates daily reports at 11 PM UTC
- Deploys reports to GitHub Pages
- Runs on push to main branch

## Dashboard Features

- **Date Navigation**: Previous/Next buttons and date picker
- **Productivity Score**: Large hero display with component breakdown
- **Deep Work Sessions**: List of all sessions with duration, app, and quality scores
- **Category Breakdown**: Doughnut chart showing time distribution
- **Hourly Interruptions**: Bar chart of interruptions throughout the day
- **Meeting Efficiency**: Stats and recommendations
- **Focus Window Suggestions**: Optimal time blocks for scheduling deep work
- **Responsive Design**: Works on desktop and mobile

## Report Format

### JSON Structure

```json
{
  "date": "2025-12-05",
  "deep_work_sessions": [...],
  "interruption_analysis": {...},
  "productivity_score": {...},
  "category_trends": {...},
  "meeting_efficiency": {...},
  "focus_windows": [...]
}
```

### Markdown Format

Human-readable summary with:
- Overall score and rating
- Key metrics (focus time, deep work, interruptions, meetings)
- Deep work sessions list
- Time by category
- Interruption analysis
- Meeting efficiency
- Suggested focus windows

## Privacy

- **No window titles or URLs** are stored in logs or reports
- Only **app names** and **event types** are tracked
- **Aggregated metrics** suitable for sharing with teams
- All data stored locally (no cloud sync by default)

## Development

### Running Tests

```bash
python3 -m pytest tests/
```

### Adding New Categories

Edit `_categorize_app()` in `tools/analytics.py`:

```python
def _categorize_app(self, app_name):
    app_lower = app_name.lower()
    if 'your-app' in app_lower:
        return 'YourCategory'
    # ...
```

### Customizing Thresholds

Edit the `analytics` section in `config.json`:

```json
{
  "analytics": {
    "deep_work_threshold": 30,
    "idle_threshold_seconds": 600,
    "context_switch_cost": 90
  }
}
```

## Deployment

### Local

```bash
python3 -m http.server 8000
```

### GitHub Pages

Push to `main` branch - GitHub Actions will deploy automatically.

### Docker

```bash
docker build -t daily-accomplishments .
docker run -p 8000:8000 daily-accomplishments
```

### Cloud Platforms

Deploy to Railway, Heroku, or any platform supporting Python 3.9+.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests

See `IMPROVEMENTS.md` for planned enhancements.
