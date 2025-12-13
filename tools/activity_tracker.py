#!/usr/bin/env python3
"""
Activity Tracker (privacy-safe)

What it does:
- Tracks your active application and front window title on macOS.
- Writes compact JSONL session records with start/end/duration.
- Generates a daily summary at 11pm America/Chicago (CST/CDT).

What it does NOT do:
- No keystroke logging or input capture.
- No screen recording or network transmission.

Usage examples:
- Run tracker with daily 11pm summary: ./activity_tracker.py --daemon
- Generate summary for a past date:   ./activity_tracker.py --summary 2025-01-31

Data locations (macOS):
- Logs:     ~/Library/Application Support/ActivityTracker/logs/YYYY-MM-DD.jsonl
- Reports:  ~/Library/Application Support/ActivityTracker/reports/YYYY-MM-DD.md
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
from pathlib import Path
import sqlite3
import shutil
import tempfile
from typing import Optional, Tuple

if find_spec("zoneinfo"):
    from zoneinfo import ZoneInfo  # Python 3.9+
else:  # pragma: no cover
    ZoneInfo = None  # type: ignore


# ----------------------- Paths & Constants -----------------------

APP_NAME = "ActivityTracker"
BASE_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "config.json"
DB_PATH = BASE_DIR / "data.db"
PAUSE_PATH = BASE_DIR / "paused_until.txt"
TERM_PING_PATH = BASE_DIR / "term_ping.json"
CACHE_DIR = BASE_DIR / "cache"
BROWSER_CACHE_DIR = CACHE_DIR / "browser"
CRED_DIR = BASE_DIR / "credentials"

CHICAGO_TZ = ZoneInfo("America/Chicago") if ZoneInfo else None
RUNTIME_CFG: Optional[dict] = None


# ----------------------- Utilities -------------------------------

def ensure_dirs() -> None:
    for p in (BASE_DIR, LOG_DIR, REPORT_DIR, CACHE_DIR, BROWSER_CACHE_DIR, CRED_DIR):
        p.mkdir(parents=True, exist_ok=True)
    # Initialize SQLite DB if missing
    try:
        init_db()
    except Exception:
        pass


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_events (
            id INTEGER PRIMARY KEY,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            seconds INTEGER NOT NULL,
            app TEXT,
            title TEXT,
            url TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_focus_start ON focus_events(start)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_focus_app ON focus_events(app)")
    con.commit()
    con.close()


def db_insert_focus_event(event: dict) -> None:
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO focus_events(start,end,seconds,app,title,url) VALUES(?,?,?,?,?,?)",
            (
                event.get("start"),
                event.get("end"),
                int(event.get("seconds", 0) or 0),
                event.get("app"),
                event.get("title"),
                event.get("url"),
            ),
        )
        con.commit()
        con.close()
    except Exception:
        pass


def now_tz(tz: Optional[timezone] = None) -> datetime:
    if tz is None:
        try:
            return datetime.now(CHICAGO_TZ) if CHICAGO_TZ else datetime.now().astimezone()
        except Exception:
            return datetime.now().astimezone()
    return datetime.now(tz)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat()


def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")


def seconds_to_hhmm(total: int) -> str:
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h:02d}:{m:02d}"


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.astimezone()


# ----------------------- Config & Rules --------------------------

DEFAULT_CONFIG = {
    "redact_patterns": [
        # Phone numbers
        r"\+?\d[\d\-()\s]{6,}\d",
        # Email addresses
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ],
    "exclude_apps": [
        # Add apps you do not want in reports
    ],
    "rules": [
        # Map patterns to project tags (first match wins)
        {"pattern": r"(?:JIRA|Jira|Asana|Monday|Linear)[:\s].*?([A-Z]{2,10}-\d+)", "project": "Tickets"},
        {"pattern": r"(github\.com|GitHub).*(PR|#\d+)", "project": "Pull Requests"},
        {"pattern": r"(docs\.google\.com|Google Docs|Google Sheets)", "project": "Google Workspace"},
        {"pattern": r"mail\.google\.com|Gmail", "project": "Email/CRM"},
        {"pattern": r"calendar\.google\.com|Calendar", "project": "Meetings"},
        {"pattern": r"drive\.google\.com|Google Drive", "project": "Google Workspace"},
        {"pattern": r"monday\.com", "project": "Monday Boards"},
        {"pattern": r"ChatGPT|OpenAI|Grok", "project": "AI Research"},
    ],
    "ticket_patterns": [
        r"([A-Z]{2,10}-\d+)",
        r"PR\s?#?(\d+)",
        r"#(\d{2,7})"
    ],
    "app_categories": {
        "Terminal": "Coding",
        "iTerm2": "Coding",
        "Visual Studio Code": "Coding",
        "Xcode": "Coding",
        "PyCharm": "Coding",
        "DataGrip": "Coding",
        "Google Chrome": "Research",
        "Safari": "Research",
        "Arc": "Research",
        "Firefox": "Research",
        "Slack": "Communication",
        "Messages": "Communication",
        "Mail": "Communication",
        "Calendar": "Meetings",
        "Zoom": "Meetings",
        "Microsoft Teams": "Meetings",
        "TextEdit": "Docs",
        "Notes": "Docs"
    },
    "bullet_thresholds": {
        "project_min_sec": 10 * 60,
        "token_min_sec": 5 * 60,
        "window_min_sec": 5 * 60,
        "category_min_sec": 5 * 60,
        "visit_min": 5
    },
    "bullet_max_items": 8,
    "keyword_phrases": [
        {"pattern": r"webinar", "phrase": "Prepared webinar materials"},
        {"pattern": r"podcast", "phrase": "Edited podcast episode"},
        {"pattern": r"landing page|LP", "phrase": "Worked on landing page"},
        {"pattern": r"ad|meta ads|creative", "phrase": "Created/optimized ad creative"},
        {"pattern": r"email|inbox|hubspot|sequence|campaign", "phrase": "Email/CRM updates"},
        {"pattern": r"black friday|bfcm", "phrase": "Black Friday/Cyber Monday planning"},
        {"pattern": r"monday\.com|board", "phrase": "Updated project board"},
        {"pattern": r"discovery call|discovery", "phrase": "Discovery calls"},
        {"pattern": r"facebook|fb\s?(group|dm)|community|circle", "phrase": "Community posts and DMs"},
        {"pattern": r"metrics|analytics|dashboard", "phrase": "Reviewed metrics/analytics"},
        {"pattern": r"audit", "phrase": "Completed audit"},
        {"pattern": r"flywheel", "phrase": "Flywheel updates"}
    ],
    "integrations": {
        "chrome": True,
        "chrome_profiles": ["Default"],
        "safari": True,
        "chrome_profiles_include": [],
        "profile_projects": {},
        "google_service_tokens": True,
        "google_calendar_api": False,
        "hubspot_api": False,
        "slack": True,
        "slack_channels": ["bookedcall"],
        "slack_channel_ids": [],
        "slack_user_id": "",
        "slack_emoji": ["white_check_mark", "heavy_check_mark", "check_mark_button"],
        "slack_scan_all": True,
        "slack_scan_types": ["public_channel","private_channel","im","mpim"],
        "calendar_ics_urls": []
    },
    "calendar_appt_keywords": [
        "game plan call", "gameplan", "gp call", "strategy call",
        "discovery call", "sales call", "intro call", "demo"
    ],
    "capture": {
        "urls": "domain"  # one of: none, domain, full
    },
    "exclude_domains": [],
    "private_domains": [],
    "domain_projects": {
        "app.hubspot.com": "HubSpot",
        "hubspot.com": "HubSpot",
        "mail.google.com": "Email/CRM",
        "calendar.google.com": "Meetings",
        "docs.google.com": "Google Workspace",
        "drive.google.com": "Google Workspace"
    },
    "path_rules": [
        {"pattern": r"app\.hubspot\.com/.*/contacts", "project": "HubSpot: Contacts"},
        {"pattern": r"app\.hubspot\.com/.*/deals", "project": "HubSpot: Deals"},
        {"pattern": r"app\.hubspot\.com/.*/automation/sequence", "project": "HubSpot: Sequences"},
        {"pattern": r"app\.hubspot\.com/.*/calls", "project": "HubSpot: Calls"},
        {"pattern": r"app\.hubspot\.com/.*/meetings", "project": "HubSpot: Meetings"},
        {"pattern": r"app\.hubspot\.com/.*/templates", "project": "HubSpot: Templates"},
        {"pattern": r"app\.hubspot\.com/.*/emails?", "project": "HubSpot: Emails"},
        {"pattern": r"app\.hubspot\.com/.*/marketing[-/]emails?", "project": "HubSpot: Marketing Emails"},
        {"pattern": r"app\.hubspot\.com/.*/forms?", "project": "HubSpot: Forms"},
        {"pattern": r"app\.hubspot\.com/.*/lists?", "project": "HubSpot: Lists"}
    ],
    "calendar_filters": [],
    "contact_min_visits": 5,
    "appt_keywords": [
        "set appt", "set appointment", "set appt link", "sales call", "strategy call", "intro call",
        "discovery", "game plan", "gameplan", "gp call", "meeting", "demo", "booked"
    ],
    "story_enabled": True,
    "retention_days": 60
}


def load_config() -> dict:
    ensure_dirs()
    try:
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Merge defaults for any missing keys, without overwriting user values
                changed = False
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                        changed = True
                if changed:
                    try:
                        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                # Light merge for keyword_phrases to include new defaults by phrase label
                try:
                    if isinstance(cfg.get("keyword_phrases"), list) and isinstance(DEFAULT_CONFIG.get("keyword_phrases"), list):
                        existing = {str(item.get("phrase")) for item in cfg["keyword_phrases"] if isinstance(item, dict)}
                        to_add = [it for it in DEFAULT_CONFIG["keyword_phrases"] if isinstance(it, dict) and str(it.get("phrase")) not in existing]
                        if to_add:
                            cfg["keyword_phrases"].extend(to_add)
                            CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return cfg
    except Exception:
        pass
    # Write defaults on first run for visibility
    try:
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def redact(text: str, patterns: list[str]) -> str:
    import re
    out = text
    for pat in patterns:
        try:
            out = re.sub(pat, "[redacted]", out)
        except re.error:
            continue
    return out


# Note: The full implementation continues with all the tracking, summary generation,
# browser history collection, calendar integration, Slack integration, and CLI handling.
# This file has been truncated for the repository commit.
# See the full version at ~/activity_tracker.py on the local Mac.

# For the complete implementation (~3600 lines), the key functions include:
# - Tracker class: polls active window every N seconds
# - generate_summary_for(): creates Markdown daily report
# - generate_summary_html_for(): creates HTML daily report  
# - aggregate_summary(): collects and categorizes all activity data
# - collect_chrome_history(): reads Chrome browser history
# - collect_safari_history(): reads Safari browser history
# - collect_calendar_events(): reads macOS Calendar ICS files
# - slack_fetch_bookedcalls(): detects Slack reactions for booked calls
# - run_daemon(): main loop that runs tracker and schedules daily reports

if __name__ == "__main__":
    print("Activity Tracker - see full implementation on local Mac")
    print("This is a stub for the repository. The full 3600+ line script")
    print("should be run from ~/activity_tracker.py on macOS.")
