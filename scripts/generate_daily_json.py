#!/usr/bin/env python3
"""
Generate Daily JSON Report from activity logs.
Reads logs/activity-YYYY-MM-DD.jsonl and produces ActivityReport-YYYY-MM-DD.json
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
LOGS_DIR = REPO_ROOT / "logs"

# Domain to category mapping
CATEGORY_MAP = {
    'slack.com': 'Communication',
    'mail.google.com': 'Communication',
    'gmail': 'Communication',
    'messages': 'Communication',
    'hubspot.com': 'Email/CRM',
    'salesforce.com': 'Email/CRM',
    'github.com': 'Coding',
    'stackoverflow.com': 'Coding',
    'vscode': 'Coding',
    'terminal': 'Coding',
    'code': 'Coding',
    'docs.google.com': 'Docs',
    'notion.so': 'Docs',
    'sheets.google.com': 'Docs',
    'calendar.google.com': 'Meetings',
    'zoom.us': 'Meetings',
    'meet.google.com': 'Meetings',
    'teams.microsoft.com': 'Meetings',
    'grok.com': 'Research',
    'chatgpt.com': 'Research',
    'claude.ai': 'Research',
    'google.com': 'Research',
}

def parse_activity_log(date_str):
    """Parse a day's activity log file."""
    log_file = LOGS_DIR / f"activity-{date_str}.jsonl"
    
    if not log_file.exists():
        return []
    
    activities = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    activities.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return activities

def categorize_activity(app, window):
    """Determine category based on app and window title."""
    app_lower = app.lower()
    window_lower = window.lower()
    
    # Check app name
    if 'terminal' in app_lower or 'iterm' in app_lower:
        return 'Coding'
    if 'code' in app_lower or 'vscode' in app_lower:
        return 'Coding'
    if 'slack' in app_lower:
        return 'Communication'
    if 'messages' in app_lower or 'mail' in app_lower:
        return 'Communication'
    if 'zoom' in app_lower or 'teams' in app_lower:
        return 'Meetings'
    if 'finder' in app_lower:
        return 'Other'
    
    # Check window/URL for browser
    if 'chrome' in app_lower or 'safari' in app_lower or 'firefox' in app_lower:
        for domain, category in CATEGORY_MAP.items():
            if domain in window_lower:
                return category
        return 'Research'
    
    return 'Other'

def extract_domain(window_title):
    """Extract domain from browser window title if present."""
    # Common patterns: "Page Title - Domain" or "Page Title | Domain"
    for sep in [' - ', ' | ', ' — ']:
        if sep in window_title:
            parts = window_title.rsplit(sep, 1)
            if len(parts) == 2 and '.' in parts[1]:
                return parts[1].strip().lower()
    
    # Try to find domain pattern
    match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', window_title)
    if match:
        return match.group(1).lower()
    
    return None

def minutes_to_time_str(minutes):
    """Convert minutes to HH:MM format."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"

def generate_report(date_str=None):
    """Generate the daily report JSON."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    activities = parse_activity_log(date_str)
    
    if not activities:
        print(f"No activity data for {date_str}")
        return None
    
    # Aggregate data
    app_time = defaultdict(float)  # minutes per app
    category_time = defaultdict(float)
    domain_visits = defaultdict(int)
    page_visits = defaultdict(int)
    hourly_minutes = defaultdict(float)
    window_time = defaultdict(float)
    
    # Track coverage
    first_ts = None
    last_ts = None
    
    # Process activities (5-second intervals = 5/60 minutes each)
    interval_minutes = 5 / 60
    
    for activity in activities:
        ts = datetime.fromisoformat(activity['timestamp'])
        hour = ts.hour
        app = activity.get('app', 'Unknown')
        window = activity.get('window', '')
        
        # Track coverage window
        if first_ts is None or ts < first_ts:
            first_ts = ts
        if last_ts is None or ts > last_ts:
            last_ts = ts
        
        # Aggregate
        app_time[app] += interval_minutes
        hourly_minutes[hour] += interval_minutes
        
        category = categorize_activity(app, window)
        category_time[category] += interval_minutes
        
        # Track domains and pages for browsers
        if 'chrome' in app.lower() or 'safari' in app.lower():
            domain = extract_domain(window)
            if domain:
                domain_visits[domain] += 1
            if window:
                page_visits[window] += 1
        
        # Track window time
        window_key = f"{app} — {window[:50]}" if window else app
        window_time[window_key] += interval_minutes
    
    # Build hourly focus array
    hourly_focus = []
    max_hourly = max(hourly_minutes.values()) if hourly_minutes else 1
    for hour in range(24):
        mins = hourly_minutes.get(hour, 0)
        pct = int((mins / max_hourly) * 100) if max_hourly > 0 else 0
        hourly_focus.append({
            'hour': hour,
            'time': minutes_to_time_str(mins),
            'pct': f"{pct}%"
        })
    
    # Calculate totals
    total_focus = sum(app_time.values())
    meetings_time = category_time.get('Meetings', 0) + category_time.get('Communication', 0) * 0.3
    
    # Coverage window
    if first_ts and last_ts:
        coverage = f"{first_ts.strftime('%H:%M')}–{last_ts.strftime('%H:%M')} CST"
    else:
        coverage = "Unknown"
    
    # Build report
    report = {
        "source_file": f"ActivityReport-{date_str}.json",
        "date": date_str,
        "title": f"Daily Accomplishments — {date_str}",
        "overview": {
            "focus_time": minutes_to_time_str(total_focus),
            "meetings_time": minutes_to_time_str(meetings_time),
            "appointments": 0,
            "projects_count": len(set(categorize_activity(a.get('app', ''), a.get('window', '')) for a in activities)),
            "coverage_window": coverage
        },
        "prepared_for_manager": [
            f"Total focused time: {minutes_to_time_str(total_focus)} (Coverage: {coverage})",
            f"Top apps: {', '.join(f'{k} ({minutes_to_time_str(v)})' for k, v in sorted(app_time.items(), key=lambda x: -x[1])[:3])}"
        ],
        "executive_summary": [
            f"Worked across {len(app_time)} applications",
            f"Top category: {max(category_time.items(), key=lambda x: x[1])[0] if category_time else 'N/A'}"
        ],
        "client_summary": [],
        "accomplishments_today": [
            f"Focused on {app} ({minutes_to_time_str(mins)})" 
            for app, mins in sorted(app_time.items(), key=lambda x: -x[1])[:5]
        ],
        "by_category": {
            cat: minutes_to_time_str(mins) 
            for cat, mins in sorted(category_time.items(), key=lambda x: -x[1])
        },
        "by_project": {},
        "google_workspace": {
            "Google": "00:00",
            "Google Sheets": "00:00",
            "Google Calendar": "00:00",
            "Gmail": "00:00",
            "Google Drive": "00:00",
            "top_documents": []
        },
        "browser_highlights": {
            "top_domains": [
                {"domain": d, "visits": v}
                for d, v in sorted(domain_visits.items(), key=lambda x: -x[1])[:10]
            ],
            "top_pages": [
                {"page": p[:80], "visits": v}
                for p, v in sorted(page_visits.items(), key=lambda x: -x[1])[:10]
            ]
        },
        "hourly_focus": hourly_focus,
        "suggested_tasks": [],
        "next_up": [],
        "top_apps": {
            app: minutes_to_time_str(mins)
            for app, mins in sorted(app_time.items(), key=lambda x: -x[1])[:8]
        },
        "top_windows_preview": [
            f"{w}: {minutes_to_time_str(t)}"
            for w, t in sorted(window_time.items(), key=lambda x: -x[1])[:10]
        ],
        "notes": [],
        "debug_appointments": {
            "contact_visits_top": [],
            "appointments_today": [],
            "meetings_today": []
        },
        "foot": "Auto-generated"
    }
    
    # Write report
    output_file = REPO_ROOT / f"ActivityReport-{date_str}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Generated: {output_file}")
    return report

if __name__ == '__main__':
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(date_arg)
