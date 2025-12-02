#!/usr/bin/env python3
"""
Generate Daily JSON Report from activity logs.

Prefers logs/activity-YYYY-MM-DD.jsonl (collector output).
Falls back to logs/daily/YYYY-MM-DD.jsonl (legacy/event-style logs) if needed.
Outputs ActivityReport-YYYY-MM-DD.json at repo root.
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

def _normalize_event(obj: dict) -> dict | None:
    """Normalize various event schemas to a flat activity dict.

    Returns a dict with at least: timestamp (ISO), app (str), window (str or "").
    Optionally includes duration_seconds (float) if present in source.
    """
    # Flat schema: already has keys
    if all(k in obj for k in ("timestamp",)) and (
        ("app" in obj) or ("window" in obj)
    ):
        return {
            "timestamp": obj.get("timestamp"),
            "app": obj.get("app", "Unknown"),
            "window": obj.get("window", obj.get("window_title", "")),
            **({"duration_seconds": obj.get("duration_seconds")} if obj.get("duration_seconds") else {}),
        }

    # Legacy event schema: {"type": ..., "timestamp": ..., "data": {...}}
    if "timestamp" in obj and isinstance(obj.get("data"), dict):
        data = obj["data"]
        app = (
            data.get("app")
            or data.get("from_app")
            or data.get("to_app")
            or ("Manual Entry" if obj.get("type") == "manual_entry" else "Unknown")
        )
        window = (
            data.get("window_title")
            or data.get("window")
            or data.get("description", "")
        )
        out = {
            "timestamp": obj["timestamp"],
            "app": app,
            "window": window or "",
        }
        if isinstance(data.get("duration_seconds"), (int, float)):
            out["duration_seconds"] = float(data["duration_seconds"])
        return out

    return None


def parse_activity_log(date_str):
    """Parse a day's activity log file with fallback to legacy locations."""
    # Preferred collector output
    primary = LOGS_DIR / f"activity-{date_str}.jsonl"
    # Legacy/event-style logs
    fallback = LOGS_DIR / "daily" / f"{date_str}.jsonl"
    # Older legacy pattern
    fallback_alt = LOGS_DIR / "daily" / f"activity-{date_str}.jsonl"

    if primary.exists():
        log_file = primary
    elif fallback.exists():
        log_file = fallback
    elif fallback_alt.exists():
        log_file = fallback_alt
    else:
        print(f"No log file found for {date_str}")
        print(f"  Checked: {LOGS_DIR}/activity-{date_str}.jsonl")
        print(f"  Checked: {LOGS_DIR}/daily/{date_str}.jsonl")
        print(f"  Checked: {LOGS_DIR}/daily/activity-{date_str}.jsonl")
        return []

    print(f"Reading: {log_file}")

    activities = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            norm = _normalize_event(obj)
            if norm:
                activities.append(norm)

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
    
    # Process activities
    # Default interval if no explicit duration is available (5 seconds)
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
        # Use explicit duration if provided, else assume fixed sample interval
        dur_min = (
            float(activity.get("duration_seconds", 0)) / 60.0
            if activity.get("duration_seconds")
            else interval_minutes
        )

        app_time[app] += dur_min
        hourly_minutes[hour] += dur_min
        
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
        window_time[window_key] += dur_min
    
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
