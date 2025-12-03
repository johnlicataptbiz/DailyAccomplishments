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
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or ""
    except Exception:
        return ""


def detect_project(app: str, title: str, url: str) -> str:
    """Detect project from app, title, or URL."""
    title_lower = (title or "").lower()
    url_lower = (url or "").lower()
    
    # Project detection rules
    if "physicaltherapybiz" in title_lower or "physicaltherapybiz" in url_lower:
        return "physicaltherapybiz.com"
    if "hubspot" in url_lower or "hubspot" in title_lower:
        return "Email/CRM"
    if "slack" in url_lower or "slack" in title_lower:
        return "Slack"
    if "facebook" in url_lower or "facebook" in title_lower:
        return "Facebook Community"
    if "gmail" in url_lower or "mail.google" in url_lower:
        return "Email/CRM"
    if "github" in url_lower or "github" in title_lower:
        return "GitHub"
    if "railway" in url_lower:
        return "Railway"
    if "grok" in url_lower:
        return "AI Research"
    if "aistudio.google" in url_lower or "chatgpt" in url_lower:
        return "AI Research"
    
    return ""


def aggregate_events(events: list[dict]) -> dict:
    """Aggregate events into summary data matching Mac tracker's rich format."""
    total_seconds = 0
    by_app: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_hour: dict[int, int] = {}
    by_window: dict[tuple, int] = {}
    by_project: dict[str, int] = {}
    browser_domains: dict[str, int] = {}
    browser_pages: dict[tuple, int] = {}  # (domain, title) -> visits
    first_ts = None
    last_ts = None
    
    # Category mapping (from the Mac tracker)
    app_categories = {
        "Terminal": "Coding", "iTerm2": "Coding", "Visual Studio Code": "Coding",
        "Code": "Coding", "Xcode": "Coding", "PyCharm": "Coding", "DataGrip": "Coding",
        "Google Chrome": "Research", "Safari": "Research", "Arc": "Research", "Firefox": "Research",
        "Slack": "Communication", "Messages": "Communication", "Mail": "Communication",
        "Calendar": "Meetings", "Zoom": "Meetings", "Microsoft Teams": "Meetings",
        "TextEdit": "Docs", "Notes": "Docs", "Preview": "Docs",
    }
    
    for event in events:
        seconds = int(event.get("seconds", 0) or 0)
        app = event.get("app", "Unknown")
        title = event.get("title", "") or ""
        url = event.get("url", "") or ""
        start_str = event.get("start", "")
        
        # Always process for browser stats even if seconds is 0
        if url:
            domain = extract_domain(url)
            if domain:
                browser_domains[domain] = browser_domains.get(domain, 0) + 1
                # Track page visits
                page_title = title[:80] if title else domain
                browser_pages[(domain, page_title)] = browser_pages.get((domain, page_title), 0) + 1
        
        if seconds <= 0:
            continue
        
        total_seconds += seconds
        
        # Track by app
        by_app[app] = by_app.get(app, 0) + seconds
        
        # Track by category - also check title for Slack in browser
        category = app_categories.get(app, "Other")
        if "slack" in title.lower() or "slack" in url.lower():
            category = "Communication"
        by_category[category] = by_category.get(category, 0) + seconds
        
        # Track by window (truncate title)
        window_title = title[:80] if title else ""
        key = (app, window_title)
        by_window[key] = by_window.get(key, 0) + seconds
        
        # Track by project
        project = detect_project(app, title, url)
        if project:
            by_project[project] = by_project.get(project, 0) + seconds
        
        # Track by hour
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
    
    return {
        "total_seconds": total_seconds,
        "by_app": by_app,
        "by_category": by_category,
        "by_hour": by_hour,
        "by_window": by_window,
        "by_project": by_project,
        "browser_domains": browser_domains,
        "browser_pages": browser_pages,
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def generate_activity_report_json(date_str: str) -> dict:
    """Generate ActivityReport JSON in the dashboard format with rich data."""
    events = load_jsonl_events(date_str)
    if not events:
        return {}
    
    agg = aggregate_events(events)
    
    # Build top domains list
    top_domains = [
        {"domain": dom, "visits": cnt}
        for dom, cnt in sorted(agg["browser_domains"].items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    # Build top pages list
    top_pages = [
        {"domain": dom, "title": title, "visits": cnt}
        for (dom, title), cnt in sorted(agg["browser_pages"].items(), key=lambda x: x[1], reverse=True)[:15]
    ]
    
    # Build the report structure matching dashboard.html expectations
    report = {
        "date": date_str,
        "overview": {
            "focus_time": seconds_to_hhmm(agg["total_seconds"]),
            "meetings_time": seconds_to_hhmm(agg["by_category"].get("Meetings", 0)),
            "appointments": 0,  # TODO: integrate with Slack/Calendar
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
        "by_project": {
            proj: seconds_to_hhmm(sec)
            for proj, sec in sorted(agg["by_project"].items(), key=lambda x: x[1], reverse=True)
        },
        "top_apps": {
            app: seconds_to_hhmm(sec)
            for app, sec in sorted(agg["by_app"].items(), key=lambda x: x[1], reverse=True)[:10]
        },
        "top_windows": {
            f"{app} — {title or '(no title)'}": seconds_to_hhmm(sec)
            for (app, title), sec in sorted(agg["by_window"].items(), key=lambda x: x[1], reverse=True)[:15]
        },
        "hourly_focus": [
            {"hour": h, "time": seconds_to_hhmm(sec), "pct": f"{min(100, sec * 100 // 3600)}%"}
            for h, sec in sorted(agg["by_hour"].items())
        ],
        "browser_highlights": {
            "top_domains": top_domains,
            "top_pages": top_pages,
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
    
    # Try to push gh-pages if it's a proper git worktree (not a submodule)
    gh_pages_git = GH_PAGES_PATH / ".git"
    if GH_PAGES_PATH.exists() and gh_pages_git.exists():
        # Check if it's a worktree (file) or submodule (directory)
        if gh_pages_git.is_file():
            # It's a proper worktree
            os.chdir(GH_PAGES_PATH)
            subprocess.run(["git", "add", "ActivityReport-*.json"], check=False)
            subprocess.run(["git", "commit", "-m", f"Auto-sync report {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=False)
            subprocess.run(["git", "push", "origin", "gh-pages"], check=False)
        else:
            print("Note: gh-pages is a submodule, skipping local push. Report will be synced via GitHub Actions.")
    
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
