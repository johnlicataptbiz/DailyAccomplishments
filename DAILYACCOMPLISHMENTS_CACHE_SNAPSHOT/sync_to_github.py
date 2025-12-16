#!/usr/bin/env python3
"""
Sync ActivityTracker reports to GitHub Pages.

Run this on your Mac to push today's report to your GitHub Pages dashboard.

This script intelligently detects uncommitted changes before attempting to commit
and push, providing clear feedback about what actions are being taken.

Features:
    - Detects uncommitted changes in both main repo and gh-pages worktree
    - Only commits when there are actual changes
    - Provides clear status messages for each operation
    - Handles git push failures gracefully

Usage:
    python3 sync_to_github.py                    # Sync today
    python3 sync_to_github.py 2025-12-03         # Sync specific date
    python3 sync_to_github.py --setup            # First-time setup
"""

import argparse
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

# Your GitHub repo (resolved relative to this script for portability)
REPO_PATH = Path(__file__).resolve().parents[1]
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


def extract_domain_from_title(title: str) -> str:
    """Extract domain from window title patterns like 'Page - Google Chrome - domain.com'."""
    if not title:
        return ""
    
    # Common patterns in Chrome window titles
    # Pattern: "Page Title - Google Chrome - profile" or "Page - Site Name"
    parts = title.split(" - ")
    
    # Look for known domains in the title
    domain_patterns = [
        (r'hubspot\.com', 'app.hubspot.com'),
        (r'grok\.com', 'grok.com'),
        (r'slack\.com', 'app.slack.com'),
        (r'gmail|mail\.google', 'mail.google.com'),
        (r'github\.com', 'github.com'),
        (r'railway\.', 'railway.com'),
        (r'facebook\.com', 'www.facebook.com'),
        (r'aistudio\.google', 'aistudio.google.com'),
        (r'chatgpt', 'chatgpt.com'),
        (r'aloware', 'talk.aloware.com'),
        (r'monday\.com', 'monday.com'),
        (r'google\.com/search|Google Search', 'google.com'),
        (r'youtube\.com', 'youtube.com'),
        (r'linkedin\.com', 'linkedin.com'),
    ]
    
    title_lower = title.lower()
    for pattern, domain in domain_patterns:
        if re.search(pattern, title_lower):
            return domain
    
    return ""


def extract_page_title(title: str) -> str:
    """Extract the actual page title from window title."""
    if not title:
        return ""
    
    # Remove common suffixes like "- Google Chrome - profile"
    parts = title.split(" - ")
    if len(parts) >= 1:
        # First part is usually the page title
        return parts[0].strip()[:60]
    return title[:60]


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
        
        # Extract domain from URL or window title
        domain = ""
        if url:
            domain = extract_domain(url)
        elif app in ("Google Chrome", "Safari", "Arc", "Firefox") and title:
            domain = extract_domain_from_title(title)
        
        # Track browser stats (count each event as a "visit")
        if domain:
            browser_domains[domain] = browser_domains.get(domain, 0) + 1
            page_title = extract_page_title(title) if title else domain
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


def check_for_changes(repo_path: Path) -> bool:
    """Check if there are uncommitted changes in the repository.
    
    Args:
        repo_path: Path to the git repository to check
        
    Returns:
        True if there are uncommitted changes (staged or unstaged), False otherwise
        
    Raises:
        FileNotFoundError: If the repository path does not exist
        subprocess.CalledProcessError: If git commands fail
    """
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    
    # Check both unstaged and staged changes
    result_unstaged = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=repo_path,
        capture_output=True,
        check=False  # Don't raise on non-zero exit (expected for changes)
    )
    result_staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_path,
        capture_output=True,
        check=False  # Don't raise on non-zero exit (expected for changes)
    )
    
    # Return codes: 0 = no changes, 1 = changes exist, >1 = error
    if result_unstaged.returncode > 1:
        raise subprocess.CalledProcessError(
            result_unstaged.returncode,
            ["git", "diff", "--quiet"],
            output=None,
            stderr=result_unstaged.stderr
        )
    if result_staged.returncode > 1:
        raise subprocess.CalledProcessError(
            result_staged.returncode,
            ["git", "diff", "--cached", "--quiet"],
            output=None,
            stderr=result_staged.stderr
        )
    
    return result_unstaged.returncode != 0 or result_staged.returncode != 0


def push_to_github():
    """Commit and push to GitHub.
    
    This function stages ActivityReport JSON files and commits them if there are
    changes, then pushes to both main branch and gh-pages worktree (if present).
    It provides clear feedback about each operation.
    """
    print("\nPushing to GitHub...")
    
    # Push main branch
    # Stage the ActivityReport files
    subprocess.run(
        ["git", "add", "ActivityReport-*.json"],
        cwd=REPO_PATH,
        check=False
    )
    
    # Check if there are changes to commit
    try:
        if check_for_changes(REPO_PATH):
            print("Uncommitted changes detected, proceeding with commit...")
            result = subprocess.run(
                ["git", "commit", "-m", f"Auto-sync report {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                cwd=REPO_PATH,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✓ Changes committed successfully")
                # Try to push
                push_result = subprocess.run(
                    ["git", "push"],
                    cwd=REPO_PATH,
                    capture_output=True,
                    text=True
                )
                if push_result.returncode == 0:
                    print("✓ Pushed to main branch")
                else:
                    print(f"⚠ Push failed: {push_result.stderr}")
            else:
                print(f"⚠ Commit failed: {result.stderr}")
        else:
            print("No changes to commit in main branch")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Git command failed in main branch: {e}")
    except OSError as e:
        print(f"⚠ System error accessing main branch: {e}")
    
    # Try to push gh-pages if it's a proper git worktree (not a submodule)
    gh_pages_git = GH_PAGES_PATH / ".git"
    if GH_PAGES_PATH.exists() and gh_pages_git.exists():
        # Check if it's a worktree (file) or submodule (directory)
        if gh_pages_git.is_file():
            # It's a proper worktree
            subprocess.run(
                ["git", "add", "ActivityReport-*.json"],
                cwd=GH_PAGES_PATH,
                check=False
            )
            
            try:
                if check_for_changes(GH_PAGES_PATH):
                    print("Uncommitted changes detected in gh-pages, proceeding with commit...")
                    result = subprocess.run(
                        ["git", "commit", "-m", f"Auto-sync report {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                        cwd=GH_PAGES_PATH,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print("✓ Changes committed to gh-pages")
                        push_result = subprocess.run(
                            ["git", "push", "origin", "gh-pages"],
                            cwd=GH_PAGES_PATH,
                            capture_output=True,
                            text=True
                        )
                        if push_result.returncode == 0:
                            print("✓ Pushed to gh-pages branch")
                        else:
                            print(f"⚠ gh-pages push failed: {push_result.stderr}")
                    else:
                        print(f"⚠ gh-pages commit failed: {result.stderr}")
                else:
                    print("No changes to commit in gh-pages")
            except subprocess.CalledProcessError as e:
                print(f"⚠ Git command failed in gh-pages: {e}")
            except OSError as e:
                print(f"⚠ System error accessing gh-pages: {e}")
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
    parser = argparse.ArgumentParser(description="Sync ActivityTracker logs into DailyAccomplishments repo artifacts.")
    parser.add_argument("date", nargs="?", help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("--date", dest="date_flag", help="YYYY-MM-DD (overrides positional)")
    parser.add_argument("--setup", action="store_true", help="Show first-time setup instructions")
    parser.add_argument("--update-report", action="store_true", help="Update ActivityReport JSON only (skip git push)")
    parser.add_argument("--no-push", action="store_true", help="Do not git commit/push (implies --update-report)")
    args = parser.parse_args()

    if args.setup:
        setup()
        return 0

    date_str = args.date_flag or args.date or datetime.now().strftime("%Y-%m-%d")

    ok = sync_report(date_str)
    if not ok:
        return 1

    if args.no_push or args.update_report:
        return 0

    push_to_github()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
