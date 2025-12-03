#!/usr/bin/env python3
"""
Sync ActivityTracker reports to GitHub Pages.

Run this on your Mac to push today's report to your GitHub Pages dashboard.

Usage:
    python3 sync_to_github.py                    # Sync today
    python3 sync_to_github.py 2025-12-03         # Sync specific date
    python3 sync_to_github.py --setup            # First-time setup
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Paths on Mac
TRACKER_BASE = Path.home() / "Library" / "Application Support" / "ActivityTracker"
LOG_DIR = TRACKER_BASE / "logs"
REPORT_DIR = TRACKER_BASE / "reports"

# Your GitHub repo (update this path to where you cloned it)
REPO_PATH = Path.home() / "DailyAccomplishments"  # Adjust if different
GH_PAGES_PATH = REPO_PATH / "gh-pages"  # Or wherever your gh-pages worktree is


def seconds_to_hhmm(total: int) -> str:
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h:02d}:{m:02d}"


def load_jsonl_events(date_str: str) -> list[dict]:
    """Load events from JSONL log file."""
    log_path = LOG_DIR / f"{date_str}.jsonl"
    if not log_path.exists():
        print(f"No log file found: {log_path}")
        return []
    
    events = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def aggregate_events(events: list[dict]) -> dict:
    """Aggregate events into summary data."""
    total_seconds = 0
    by_app: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_hour: dict[int, int] = {}
    by_window: dict[tuple, int] = {}
    browser_domains: dict[str, int] = {}
    first_ts = None
    last_ts = None
    
    # Category mapping (from the Mac tracker)
    app_categories = {
        "Terminal": "Coding", "iTerm2": "Coding", "Visual Studio Code": "Coding",
        "Xcode": "Coding", "PyCharm": "Coding", "DataGrip": "Coding",
        "Google Chrome": "Research", "Safari": "Research", "Arc": "Research", "Firefox": "Research",
        "Slack": "Communication", "Messages": "Communication", "Mail": "Communication",
        "Calendar": "Meetings", "Zoom": "Meetings", "Microsoft Teams": "Meetings",
        "TextEdit": "Docs", "Notes": "Docs"
    }
    
    for event in events:
        seconds = int(event.get("seconds", 0) or 0)
        if seconds <= 0:
            continue
        
        total_seconds += seconds
        app = event.get("app", "Unknown")
        title = event.get("title", "")
        
        # Track by app
        by_app[app] = by_app.get(app, 0) + seconds
        
        # Track by category
        category = app_categories.get(app, "Other")
        by_category[category] = by_category.get(category, 0) + seconds
        
        # Track by window
        key = (app, title[:80] if title else "")
        by_window[key] = by_window.get(key, 0) + seconds
        
        # Track by hour
        start_str = event.get("start", "")
        if start_str:
            try:
                dt = datetime.fromisoformat(start_str)
                hour = dt.hour
                by_hour[hour] = by_hour.get(hour, 0) + seconds
                
                if first_ts is None or dt < first_ts:
                    first_ts = dt
                if last_ts is None or dt > last_ts:
                    last_ts = dt
            except ValueError:
                pass
        
        # Track browser domains
        url = event.get("url", "")
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain:
                    browser_domains[domain] = browser_domains.get(domain, 0) + 1
            except Exception:
                pass
    
    return {
        "total_seconds": total_seconds,
        "by_app": by_app,
        "by_category": by_category,
        "by_hour": by_hour,
        "by_window": by_window,
        "browser_domains": browser_domains,
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def generate_activity_report_json(date_str: str) -> dict:
    """Generate ActivityReport JSON in the dashboard format."""
    events = load_jsonl_events(date_str)
    if not events:
        return {}
    
    agg = aggregate_events(events)
    
    # Build the report structure matching dashboard.html expectations
    report = {
        "date": date_str,
        "overview": {
            "focus_time": seconds_to_hhmm(agg["total_seconds"]),
            "meetings_time": seconds_to_hhmm(agg["by_category"].get("Meetings", 0)),
            "appointments": 0,
            "coverage_window": (
                f"{agg['first_ts'].strftime('%H:%M')}–{agg['last_ts'].strftime('%H:%M')} CST"
                if agg["first_ts"] and agg["last_ts"] else "—"
            ),
        },
        "debug_appointments": {
            "appointments_today": [],
            "meetings_today": [],
        },
        "by_category": {
            cat: seconds_to_hhmm(sec)
            for cat, sec in sorted(agg["by_category"].items(), key=lambda x: x[1], reverse=True)
        },
        "top_apps": [
            {"name": app, "time": seconds_to_hhmm(sec)}
            for app, sec in sorted(agg["by_app"].items(), key=lambda x: x[1], reverse=True)[:10]
        ],
        "top_windows": [
            {"app": app, "title": title, "time": seconds_to_hhmm(sec)}
            for (app, title), sec in sorted(agg["by_window"].items(), key=lambda x: x[1], reverse=True)[:15]
        ],
        "hourly_focus": [
            {"hour": h, "time": seconds_to_hhmm(sec), "pct": f"{min(100, sec * 100 // 3600)}%"}
            for h, sec in sorted(agg["by_hour"].items())
        ],
        "browser": {
            "top_domains": [
                {"domain": dom, "visits": cnt}
                for dom, cnt in sorted(agg["browser_domains"].items(), key=lambda x: x[1], reverse=True)[:20]
            ]
        },
    }
    
    return report


def sync_report(date_str: str):
    """Sync a day's report to GitHub Pages."""
    print(f"Generating report for {date_str}...")
    
    report = generate_activity_report_json(date_str)
    if not report:
        print(f"No data for {date_str}")
        return False
    
    # Save locally in repo
    output_path = REPO_PATH / f"ActivityReport-{date_str}.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved: {output_path}")
    
    # Also copy to gh-pages if it exists
    gh_pages_output = GH_PAGES_PATH / f"ActivityReport-{date_str}.json"
    if GH_PAGES_PATH.exists():
        gh_pages_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved: {gh_pages_output}")
    
    return True


def push_to_github():
    """Commit and push to GitHub."""
    print("\nPushing to GitHub...")
    
    # Push main branch
    os.chdir(REPO_PATH)
    subprocess.run(["git", "add", "ActivityReport-*.json"], check=False)
    subprocess.run(["git", "commit", "-m", f"Auto-sync report {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=False)
    subprocess.run(["git", "push"], check=False)
    
    # Push gh-pages
    if GH_PAGES_PATH.exists():
        os.chdir(GH_PAGES_PATH)
        subprocess.run(["git", "add", "ActivityReport-*.json"], check=False)
        subprocess.run(["git", "commit", "-m", f"Auto-sync report {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=False)
        subprocess.run(["git", "push", "origin", "gh-pages"], check=False)
    
    print("\n✅ Done! Your report is now live at:")
    print("https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html")


def setup():
    """First-time setup instructions."""
    print("""
=== ActivityTracker → GitHub Sync Setup ===

1. Clone your repo (if not already):
   git clone https://github.com/johnlicataptbiz/DailyAccomplishments.git ~/DailyAccomplishments

2. Set up gh-pages worktree:
   cd ~/DailyAccomplishments
   git worktree add ../gh-pages-worktree gh-pages
   
   Then update GH_PAGES_PATH in this script to point to it.

3. Run this script daily:
   python3 ~/DailyAccomplishments/scripts/sync_to_github.py

4. Or add to crontab for auto-sync (runs every hour):
   crontab -e
   # Add this line:
   0 * * * * cd ~/DailyAccomplishments && python3 scripts/sync_to_github.py

Your dashboard will be live at:
https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html
""")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--setup":
            setup()
            return
        date_str = arg
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    if sync_report(date_str):
        push_to_github()


if __name__ == "__main__":
    main()
