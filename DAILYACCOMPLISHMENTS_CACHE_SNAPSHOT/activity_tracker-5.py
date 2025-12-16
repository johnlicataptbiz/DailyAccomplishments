#!/usr/bin/env python3
"""
Activity Tracker (privacy-safe)

What it does:
- Tracks your active application and front window title on macOS.
- Writes compact JSONL session records with start/end/duration (running daily log).
- Generates a daily summary for a configurable window (default: 6am–midnight CST/CDT).

What it does NOT do:
- No keystroke logging or input capture.
- No screen recording or network transmission.

Usage examples:
- Run tracker with daily midnight summary: ./activity_tracker.py --daemon
- Generate summary for a past date:       ./activity_tracker.py --summary 2025-01-31

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
from pathlib import Path
import sqlite3
import shutil
import tempfile
from typing import Optional, Tuple

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
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
        {"pattern": r"physicaltherapybiz\.com|Project:\s*783", "project": "PTB: Project 783"},
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
    }
    ,
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
        "chrome_profiles_include": ["physicaltherapybiz"],
        "profile_projects": {"physicaltherapybiz": "PT Biz"},
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
    "calendar_filters": ["PT", "physicaltherapybiz", "PT Biz", "jack licata"],
    "contact_min_visits": 5,
    "appt_keywords": [
        "set appt", "set appointment", "set appt link", "sales call", "strategy call", "intro call",
        "discovery", "game plan", "gameplan", "gp call", "meeting", "demo", "booked"
    ],
    "story_enabled": True,
    "retention_days": 60,
    # Daily window configuration
    # Start hour inclusive (e.g., 6 means 06:00 local), end hour exclusive (e.g., 24 means midnight)
    "day_start_hour_local": 6,
    "day_end_hour_local": 24
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


# ----------------------- Pause/Resume ----------------------------

def get_paused_until() -> Optional[datetime]:
    try:
        s = PAUSE_PATH.read_text(encoding="utf-8").strip()
        if not s:
            return None
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.astimezone()
    except Exception:
        return None


def set_paused_minutes(minutes: int) -> None:
    until = now_tz(CHICAGO_TZ) + timedelta(minutes=max(1, minutes))
    PAUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAUSE_PATH.write_text(iso(until), encoding="utf-8")


def clear_pause() -> None:
    try:
        if PAUSE_PATH.exists():
            PAUSE_PATH.unlink()
    except Exception:
        pass


def get_idle_seconds() -> int:
    """Return approximate user idle seconds on macOS via IOHIDSystem.
    Falls back to 0 on error.
    """
    try:
        # HIDIdleTime is in nanoseconds
        out = subprocess.check_output(
            [
                "bash",
                "-lc",
                "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}'",
            ],
            text=True,
        ).strip()
        if not out:
            return 0
        ns = int(out)
        return int(ns / 1_000_000_000)
    except Exception:
        return 0


def extract_domain_from_title(title: str, app: str) -> Optional[str]:
    # Heuristics for Chrome/Safari-style titles; pick a token that looks like a domain
    # We avoid Chrome profile suffixes like "… - Google Chrome - Jack (physicaltherapybiz.com)".
    import re
    is_chrome = "Chrome" in (app or "") or app in ("Arc", "Brave Browser")
    # If this looks like a Chrome profile suffix at end (" - Name (domain)") then ignore parentheses domain
    if is_chrome and re.search(r"\s-\s[^-]+\s*\([^)]+\)\s*$", title):
        pass  # skip parentheses extraction
    else:
        m = re.search(r"\(([A-Za-z0-9.-]+\.[A-Za-z]{2,})\)\s*$", title)
        if m:
            return m.group(1)
    # Else find last dash-separated token that looks like a domain but ignore typical chrome suffix chunks
    parts = [p.strip() for p in title.split("-") if p.strip()]
    # Drop trailing chunk if it looks like a profile name like "Jack (domain)"
    if parts and re.search(r"\([^)]+\)$", parts[-1]):
        parts = parts[:-1]
    for token in reversed(parts):
        if re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", token):
            return token
    return None


def clean_title_for_display(app: str, title: str) -> str:
    """Strip Chrome profile suffix from titles for nicer Top Windows display."""
    import re
    if "Chrome" in (app or "") or app in ("Arc", "Brave Browser"):
        # Remove trailing " - Something (domain)" suffix which is likely a profile label
        return re.sub(r"\s-\s[^-]+\s*\([^)]+\)\s*$", "", title).strip()
    return title


def infer_editor_workspace(app: str, title: str) -> Optional[str]:
    """Heuristically extract a workspace/project from editor window titles.
    - VS Code often uses: "filename — workspace — Visual Studio Code" or "workspace — Visual Studio Code"
    - Xcode titles usually start with the project/workspace name
    """
    import re
    if not app or not title:
        return None
    t = title.strip()
    if app == "Visual Studio Code" or "Code" in app:
        # Try to fetch document path via accessibility (AXDocument)
        try:
            res = subprocess.run([
                "osascript", "-e",
                'tell application "System Events" to tell process "Visual Studio Code" to try\nget value of attribute "AXDocument" of window 1\non error\nreturn ""\nend try'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
            doc = (res.stdout or "").strip()
            if doc:
                # Sometimes returns file:/// path; normalize
                p = doc
                if p.startswith('file://'):
                    from urllib.parse import urlparse, unquote
                    u = urlparse(p)
                    p = unquote(u.path)
                repo = find_repo_name(Path(p))
                if repo:
                    return repo
                # fallback to folder name
                try:
                    return Path(p).parts[-2]
                except Exception:
                    pass
        except Exception:
            pass
        # Strip trailing "- Visual Studio Code"
        t = re.sub(r"\s-\sVisual Studio Code\s*$", "", t)
        # Prefer the middle chunk if pattern "file — workspace"
        parts = [p.strip() for p in re.split(r"\s[—-]\s", t) if p.strip()]
        if len(parts) >= 2:
            # last part might be file; try the second part as workspace
            cand = parts[-1]
            # If last looks like a filename, pick the one before it
            if re.search(r"\.[a-zA-Z0-9]{1,5}$", cand):
                cand = parts[-2]
            return cand
        return t
    if app == "Xcode":
        # Try AppleScript for active workspace/project
        try:
            res = subprocess.run([
                "osascript", "-e",
                'try\n tell application "Xcode" to name of active workspace document\n on error\n tell application "Xcode" to name of front window\n end try'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
            nm = (res.stdout or "").strip()
            if nm:
                return nm
        except Exception:
            pass
        # Fallback: titles like "MyApp — ..."
        parts = [p.strip() for p in re.split(r"\s[—-]\s", t) if p.strip()]
        if parts:
            return parts[0]
    return None


def log_path_for(date_local: datetime) -> Path:
    return LOG_DIR / (date_local.strftime("%Y-%m-%d") + ".jsonl")


def report_path_for(date_local: datetime) -> Path:
    return REPORT_DIR / (date_local.strftime("%Y-%m-%d") + ".md")


# ----------------------- Front App/Window ------------------------

def get_front_app_and_title() -> Tuple[str, str, Optional[str]]:
    """Returns (app_name, window_title) using AppleScript via osascript.

    Works on macOS without extra dependencies. Requires Accessibility permissions
    for Terminal (or the host app) under System Settings > Privacy & Security.
    """
    script = [
        "tell application \"System Events\"",
        "set frontApp to first process whose frontmost is true",
        "set appName to name of frontApp",
        "set winTitle to \"\"",
        "try",
        "\ttell frontApp",
        "\t\tif exists (window 1) then set winTitle to name of window 1",
        "\tend tell",
        "end try",
        "end tell",
        "return appName & \"||\" & winTitle",
    ]
    try:
        res = subprocess.run(
            ["osascript"] + sum((['-e', line] for line in script), []),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        out = res.stdout.strip()
        if "||" in out:
            app, title = out.split("||", 1)
            url = get_front_url_if_browser(app.strip())
            return app.strip(), title.strip(), url
        appname = out.strip()
        return appname, "", get_front_url_if_browser(appname)
    except subprocess.CalledProcessError:
        return "(unknown)", "", None
    except FileNotFoundError:
        # osascript not found (non-macOS)
        return "(unsupported)", "", None


def get_front_url_if_browser(app_name: str) -> Optional[str]:
    try:
        cfg = (RUNTIME_CFG or DEFAULT_CONFIG)
        mode = cfg.get("capture", {}).get("urls", "domain")
    except Exception:
        mode = "domain"
    if mode == "none":
        return None
    app = (app_name or "").strip()
    script = None
    if app in ("Google Chrome", "Chrome", "Arc", "Brave Browser"):
        script = 'tell application "Google Chrome" to get URL of active tab of front window'
    elif app == "Safari":
        script = 'tell application "Safari" to get URL of front document'
    if not script:
        return None
    try:
        res = subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        url = res.stdout.strip()
        if not url:
            return None
        from urllib.parse import urlparse
        dom = None
        try:
            dom = urlparse(url).hostname
        except Exception:
            dom = None
        # Respect domain exclusions and privacy
        try:
            exclude = set((RUNTIME_CFG or DEFAULT_CONFIG).get("exclude_domains", []) or [])
            private = set((RUNTIME_CFG or DEFAULT_CONFIG).get("private_domains", []) or [])
        except Exception:
            exclude = set(); private = set()

        if dom and dom in exclude:
            return None
        if dom and dom in private:
            return "(private)"

        if mode == "domain":
            return dom
        # full URL
        return url
    except Exception:
        return None


# ----------------------- Data Structures -------------------------

@dataclass
class Session:
    app: str
    title: str
    start: datetime
    url: Optional[str] = None

    def to_event(self, end: datetime) -> dict:
        dur = int((end - self.start).total_seconds())
        return {
            "start": iso(self.start),
            "end": iso(end),
            "seconds": dur,
            "app": self.app,
            "title": self.title,
            "url": self.url,
        }


# ----------------------- Tracker Core ----------------------------

class Tracker:
    def __init__(self, poll_seconds: int = 5, idle_threshold: int = 300, heartbeat_seconds: int = 120) -> None:
        self.poll_seconds = max(1, poll_seconds)
        self.idle_threshold = max(0, idle_threshold)
        self.heartbeat_seconds = max(30, heartbeat_seconds)
        self.current: Optional[Session] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_heartbeat: Optional[datetime] = None

    def stop(self) -> None:
        self._stop.set()

    def _write_event(self, event: dict) -> None:
        ts = datetime.fromisoformat(event["start"]).astimezone(CHICAGO_TZ) if CHICAGO_TZ else datetime.fromisoformat(event["start"]).astimezone()
        log_path = log_path_for(ts)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        # Mirror to SQLite for richer queries
        db_insert_focus_event(event)

    def _roll_current(self, end_time: datetime) -> None:
        if self.current is None:
            return
        if end_time <= self.current.start:
            return
        event = self.current.to_event(end_time)
        self._write_event(event)
        # Start a fresh segment continuing from end_time
        self.current = Session(self.current.app, self.current.title, end_time)

    def tick(self) -> None:
        app, title, url = get_front_app_and_title()
        now = now_tz(CHICAGO_TZ)
        # Pause mode: if paused, cut current at pause start and stop recording
        p_until = get_paused_until()
        if p_until and now < p_until:
            if self.current is not None and p_until > self.current.start:
                with self._lock:
                    self._roll_current(p_until)
                    self.current = None
            return
        # Idle detection: if user idle beyond threshold, cut current session at idle start
        if self.idle_threshold > 0:
            try:
                idle_sec = get_idle_seconds()
            except Exception:
                idle_sec = 0
            if idle_sec >= self.idle_threshold and self.current is not None:
                idle_since = now - timedelta(seconds=idle_sec)
                if idle_since > self.current.start:
                    with self._lock:
                        self._roll_current(idle_since)
                        self.current = None
                # Do not start a new session while idle
                return
        with self._lock:
            if self.current is None:
                self.current = Session(app, title, now, url)
                self._last_heartbeat = now
                return
            if app == self.current.app and title == self.current.title and (
                (self.current.url or None) == (url or None)
            ):
                # heartbeat: periodically persist long sessions even without focus change
                if self._last_heartbeat is None:
                    self._last_heartbeat = self.current.start
                if (now - self._last_heartbeat) >= timedelta(seconds=self.heartbeat_seconds):
                    self._roll_current(now)
                    self._last_heartbeat = now
                return  # no change
            # write previous session and start new one
            self._roll_current(now)
            self.current = Session(app, title, now, url)
            self._last_heartbeat = now

    def flush(self) -> None:
        with self._lock:
            if self.current is not None:
                self._roll_current(now_tz(CHICAGO_TZ))

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                # Never crash the tracker loop; proceed to sleep.
                pass
            self._stop.wait(self.poll_seconds)

    def split_at(self, dt: datetime) -> None:
        """Cut the current session at dt, writing a segment ending exactly at dt.
        After this, the session continues from dt with the same app/title.
        """
        with self._lock:
            self._roll_current(dt)


# ----------------------- Summary ---------------------------------

def load_events_for_date(date_local: datetime) -> list[dict]:
    path = log_path_for(date_local)
    events: list[dict] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                events.append(evt)
            except json.JSONDecodeError:
                continue
    return events


def generate_summary_for(date_local: datetime, cutoff_hour_local: Optional[int] = None) -> Path:
    """Generate a Markdown summary for the given local date.

    The window is defined by config day_start_hour_local → day_end_hour_local unless overridden.
    """
    cfg = load_config()
    if cutoff_hour_local is None:
        cutoff_hour_local = int(cfg.get("day_end_hour_local", 24))
    agg = aggregate_summary(date_local, cutoff_hour_local, cfg)

    # Prepare report (Markdown)
    lines: list[str] = []
    date_str = date_local.strftime("%Y-%m-%d")
    start_hr = int(cfg.get("day_start_hour_local", 6))
    end_hr = int(cfg.get("day_end_hour_local", 24))
    win_label = f"{start_hr:02d}:00–{('24:00' if end_hr == 24 else f'{end_hr:02d}:00')} CST/CDT"
    lines.append(f"Daily Accomplishments — {date_str} (window {win_label})")
    lines.append("")
    # Executive top-of-funnel (guarded)
    story = safe_synthesize_story(agg, cfg)
    if story.get("bullets"):
        lines.append("Executive summary:")
        for b in story.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")
    # Prepared for manager (compact accomplishments)
    mgr_bullets = synthesize_manager_bullets(agg, cfg)
    if mgr_bullets:
        lines.append("Prepared for manager:")
        for b in mgr_bullets:
            lines.append(f"- {b}")
        lines.append("")
    lines.append(f"Total focused time: {seconds_to_hhmm(agg['total_seconds'])}")
    if agg["first_ts"] and agg["last_ts"]:
        lines.append(
            f"Coverage window: {agg['first_ts'].strftime('%H:%M')}–{agg['last_ts'].strftime('%H:%M %Z')}"
        )
    else:
        lines.append("Coverage window: —")
    lines.append("")

    # Top apps
    lines.append("Top Apps:")
    if agg["by_app"]:
        for app, sec in sorted(agg["by_app"].items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"- {app}: {seconds_to_hhmm(sec)}")
    else:
        lines.append("- No data recorded")
    lines.append("")

    # Top windows
    lines.append("Top Windows:")
    if agg["by_window"]:
        for (app, title), sec in sorted(agg["by_window"].items(), key=lambda x: x[1], reverse=True)[:15]:
            title_disp = clean_title_for_display(app, title) if title else "(no title)"
            lines.append(f"- {app} — {title_disp}: {seconds_to_hhmm(sec)}")
    else:
        lines.append("- No data recorded")
    lines.append("")

    lines.append("Notes:")
    for n in synthesize_notes(agg, cfg) or ["—"]:
        lines.append(f"- {n}")
    # Google Workspace section in Markdown
    gws_services = agg.get("gws_by_service", {}) or {}
    gws_docs = agg.get("gws_by_doc", {}) or {}
    if gws_services or gws_docs:
        lines.append("")
        lines.append("Google Workspace:")
        if gws_services:
            for svc, sec in sorted(gws_services.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {svc}: {seconds_to_hhmm(sec)}")
        if gws_docs:
            top_docs = sorted(gws_docs.items(), key=lambda x: x[1], reverse=True)[:10]
            for (svc, doc), sec in top_docs:
                lines.append(f"- {svc} — {doc}: {seconds_to_hhmm(sec)}")
    lines.append("")
    lines.append(f"Raw log: {log_path_for(date_local)}")

    out_path = report_path_for(date_local)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def aggregate_summary(date_local: datetime, cutoff_hour_local: Optional[int] = None, cfg: Optional[dict] = None) -> dict:
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    assert tz is not None
    cfg = cfg or DEFAULT_CONFIG
    start_hr = int((cfg or {}).get("day_start_hour_local", 6))
    end_hr = int((cfg or {}).get("day_end_hour_local", 24)) if cutoff_hour_local is None else int(cutoff_hour_local)
    base_start = datetime(date_local.year, date_local.month, date_local.day, 0, 0, 0, tzinfo=tz)
    window_start = base_start + timedelta(hours=start_hr)
    cutoff = base_start + timedelta(hours=end_hr)

    events = load_events_for_date(date_local)

    total_seconds = 0
    by_app: dict[str, int] = {}
    by_window: dict[Tuple[str, str], int] = {}
    by_category: dict[str, int] = {}
    by_project: dict[str, int] = {}
    by_token: dict[str, int] = {}
    by_hour: dict[int, int] = {h: 0 for h in range(24)}
    gws_by_service: dict[str, int] = {}
    gws_by_doc: dict[Tuple[str, str], int] = {}
    email_by_subject: dict[str, int] = {}
    by_workspace: dict[str, int] = {}
    cal_meetings: list[tuple[str, datetime, datetime, list[str]]] = []
    cal_total_seconds = 0
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None

    cfg = cfg or DEFAULT_CONFIG
    exclude_apps = set(cfg.get("exclude_apps", []))
    app_categories: dict[str, str] = cfg.get("app_categories", {})

    # Prepare rule regexes
    import re
    rule_specs = cfg.get("rules", [])
    compiled_rules: list[Tuple[re.Pattern[str], str]] = []
    for rule in rule_specs:
        pat = rule.get("pattern")
        proj = rule.get("project") or rule.get("tag")
        if not pat or not proj:
            continue
        try:
            compiled_rules.append((re.compile(pat, re.IGNORECASE), str(proj)))
        except re.error:
            continue

    # URL path-based rules
    path_specs = cfg.get("path_rules", [])
    compiled_path_rules: list[Tuple[re.Pattern[str], str]] = []
    for rule in path_specs:
        pat = rule.get("pattern")
        proj = rule.get("project") or rule.get("tag")
        if not pat or not proj:
            continue
        try:
            compiled_path_rules.append((re.compile(pat, re.IGNORECASE), str(proj)))
        except re.error:
            continue

    # Ticket/token extraction regexes
    token_specs = cfg.get("ticket_patterns", [])
    compiled_tokens: list[re.Pattern[str]] = []
    for pat in token_specs:
        try:
            compiled_tokens.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            continue

    def classify_project(app: str, title: str) -> Optional[str]:
        text = f"{app} {title}"
        dom = extract_domain_from_title(title, app)
        if dom:
            text = text + f" {dom}"
        # Enrich with recent terminal repo hint
        repo_hint = read_recent_term_ping_repo()
        if repo_hint:
            text = text + f" {repo_hint}"
        for rx, proj in compiled_rules:
            if rx.search(text):
                return proj
        # Fallback to domain as project surrogate
        if dom:
            return dom
        # Else fallback to repo hint if present
        if repo_hint:
            return f"Repo: {repo_hint}"
        return None

    def add_hourly(seg_start: datetime, seg_end: datetime):
        # Bucket seconds by hour boundaries
        cur = seg_start
        while cur < seg_end:
            hour_end = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            chunk_end = min(hour_end, seg_end)
            sec = int((chunk_end - cur).total_seconds())
            by_hour[cur.hour] = by_hour.get(cur.hour, 0) + sec
            cur = chunk_end

    for evt in events:
        start = parse_iso(evt["start"]).astimezone(tz)  # type: ignore
        end = parse_iso(evt["end"]).astimezone(tz)      # type: ignore
        app = str(evt.get("app", ""))
        title = str(evt.get("title", ""))
        url = str(evt.get("url", "")) if evt.get("url") else ""

        if app in exclude_apps:
            continue

        seg_start = max(start, window_start)
        seg_end = min(end, cutoff)
        if seg_end <= seg_start:
            continue
        sec = int((seg_end - seg_start).total_seconds())
        total_seconds += sec
        by_app[app] = by_app.get(app, 0) + sec
        by_window[(app, title)] = by_window.get((app, title), 0) + sec
        cat = app_categories.get(app, "Other")
        by_category[cat] = by_category.get(cat, 0) + sec
        # Editor workspace inference
        ws = infer_editor_workspace(app, title)
        if ws:
            by_workspace[ws] = by_workspace.get(ws, 0) + sec
        # Prefer domain from URL when available for classification
        dom_from_url = None
        if url:
            try:
                from urllib.parse import urlparse
                dom_from_url = urlparse(url).hostname
            except Exception:
                dom_from_url = None
        # Domain exclusions and privacy handled above; include domain hint for classification
        proj = None
        # First: URL path-based rules if we have a URL
        if url:
            for rx, pj in compiled_path_rules:
                try:
                    if rx.search(url):
                        proj = pj
                        break
                except Exception:
                    pass
        if not proj:
            proj = classify_project(app, title if not dom_from_url else f"{title} ({dom_from_url})")
        if proj:
            by_project[proj] = by_project.get(proj, 0) + sec
        elif ws:
            by_project[f"Workspace: {ws}"] = by_project.get(f"Workspace: {ws}", 0) + sec
        # Google Workspace doc/service inference
        svc, docname = infer_google_from_title_url(title, url)
        if svc:
            gws_by_service[svc] = gws_by_service.get(svc, 0) + sec
            if docname:
                gws_by_doc[(svc, docname)] = gws_by_doc.get((svc, docname), 0) + sec
        # Gmail subject inference
        subj = infer_gmail_subject_from_title(title)
        if subj:
            email_by_subject[subj] = email_by_subject.get(subj, 0) + sec

        # tokens
        text = f"{app} {title}"
        dom = extract_domain_from_title(title, app)
        if dom:
            text = text + f" {dom}"
        for rx in compiled_tokens:
            try:
                found = rx.findall(text)
            except Exception:
                found = []
            if not found:
                continue
            # flatten tuples if any
            if found and isinstance(found[0], tuple):
                for tup in found:
                    token = " ".join([t for t in tup if t])
                    if token:
                        by_token[token] = by_token.get(token, 0) + sec
            else:
                for token in found:
                    if token:
                        by_token[token] = by_token.get(token, 0) + sec
        add_hourly(seg_start, seg_end)
        first_ts = seg_start if first_ts is None else min(first_ts, seg_start)
        last_ts = seg_end if last_ts is None else max(last_ts, seg_end)

    # Browser highlights (cached; counts only, not time)
    browser = collect_browser_history_cached(window_start, cutoff, cfg)

    # Calendar reconciliation (prefer Google API, fallback to local ICS)
    try:
        use_google = cfg.get("integrations", {}).get("google_calendar_api") and google_api_available() and GOOGLE_TOKEN_PATH.exists()
    except Exception:
        use_google = False
    try:
        if use_google:
            cal_meetings = google_fetch_events(window_start, cutoff, cfg)
        else:
            cal_meetings = collect_calendar_events(window_start, cutoff)
        # Merge remote ICS URLs if configured
        ics_urls = (cfg.get("integrations", {}).get("calendar_ics_urls") or [])
        if ics_urls:
            cal_meetings.extend(collect_remote_ics_events(ics_urls, window_start, cutoff))
        for title_m, s_m, e_m, _att in cal_meetings:
            seg_start = max(s_m, window_start)
            seg_end = min(e_m, cutoff)
            if seg_end > seg_start:
                cal_total_seconds += int((seg_end - seg_start).total_seconds())
                by_category["Meetings"] = by_category.get("Meetings", 0) + int((seg_end - seg_start).total_seconds())
    except Exception:
        cal_meetings = []

    # Contact visits from HubSpot titles
    contact_visits: dict[str, int] = {}
    try:
        for dom, title_p, count in browser.get("pages", []):
            if not dom or "hubspot" not in dom:
                continue
            nm = extract_contact_name(title_p or "")
            if nm:
                contact_visits[nm] = contact_visits.get(nm, 0) + int(count)
    except Exception:
        pass

    # Infer appointments for high-visit contacts using calendar titles
    inferred_appointments: list[dict] = []
    try:
        min_visits = int(cfg.get("contact_min_visits", 10))
        keywords = [s.lower() for s in cfg.get("appt_keywords", []) or []]
        high = [(n,v) for n,v in sorted(contact_visits.items(), key=lambda x: x[1], reverse=True) if v >= min_visits]
        kw_events = []
        for (title_m, s_m, e_m, _att) in cal_meetings:
            t_low = (title_m or "").lower()
            if any(k in t_low for k in keywords):
                kw_events.append((title_m, s_m, e_m))
        for name, visits in high:
            if visits < min_visits:
                continue
            first = name.split()[0].lower()
            match = None
            for (title_m, s_m, e_m, _att) in cal_meetings:
                t_low = (title_m or "").lower()
                if first in t_low or any(k in t_low for k in keywords):
                    match = (title_m, s_m, e_m)
                    break
            if not match and kw_events and len(high) == 1:
                # Fallback: single high-visit contact + at least one keyword meeting
                match = kw_events[0]
            if match:
                t, s, e = match
                inferred_appointments.append({
                    "name": name,
                    "visits": visits,
                    "calendar_title": t,
                    "start": iso(s),
                    "end": iso(e),
                })
    except Exception:
        pass

    # Calendar-based appointment inference (keyword titles)
    try:
        cal_kw = [s.lower() for s in cfg.get("calendar_appt_keywords", []) or []]
        existing_titles = set((a.get("calendar_title") or "") for a in inferred_appointments)
        for (title_m, s_m, e_m, _att) in cal_meetings:
            t_low = (title_m or "").lower()
            if any(k in t_low for k in cal_kw):
                # Try to extract a name after 'with '
                import re
                m = re.search(r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+|\s+[A-Z]\.){0,2})", title_m or "", re.IGNORECASE)
                name = m.group(1) if m else (title_m or "Appointment")
                if title_m not in existing_titles:
                    inferred_appointments.append({
                        "name": name,
                        "visits": contact_visits.get(name, 0),
                        "calendar_title": title_m,
                        "start": iso(s_m),
                        "end": iso(e_m),
                        "source": "calendar"
                    })
                    existing_titles.add(title_m)
    except Exception:
        pass

    # Slack booked calls (green check by you in #bookedcall)
    try:
        slack_items = slack_fetch_bookedcalls(window_start, cutoff, cfg)
        for it in slack_items:
            # Represent as an inferred appointment with [likely] confidence
            txt = it.get('text') or 'Booked call'
            inferred_appointments.append({
                "name": txt[:40],
                "visits": 0,
                "calendar_title": f"Slack: {it.get('channel')} ({it.get('emoji')})",
                "start": iso(day_start),
                "end": iso(day_start + timedelta(minutes=15)),
                "source": "slack"
            })
    except Exception:
        pass
    # Broader Slack activity scan (appointments/follow-ups authored by me)
    try:
        slack_act = slack_scan_activity(window_start, cutoff, cfg)
    except Exception:
        slack_act = []

    return {
        "total_seconds": total_seconds,
        "by_app": by_app,
        "by_window": by_window,
        "by_category": by_category,
        "by_project": by_project,
        "by_token": by_token,
        "by_hour": by_hour,
        "by_workspace": by_workspace,
        "gws_by_service": gws_by_service,
        "gws_by_doc": gws_by_doc,
        "email_by_subject": email_by_subject,
        "contact_visits": contact_visits,
        "inferred_appointments": inferred_appointments,
        "calendar_events": [(t, iso(s), iso(e), a) for (t, s, e, a) in cal_meetings],
        "calendar_total_seconds": cal_total_seconds,
        "slack_booked": slack_items if 'slack_items' in locals() else [],
        "slack_activity": slack_act,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "day_start": window_start,
        "cutoff": cutoff,
        "browser_by_domain": browser.get("by_domain", {}),
        "browser_pages": browser.get("pages", []),
        "browser_tokens": browser.get("tokens", {}),
        "profile_projects": cfg.get("integrations", {}).get("profile_projects", {}),
    }


def synthesize_manager_bullets(agg: dict, cfg: dict) -> list[str]:
    import re
    bt = cfg.get("bullet_thresholds", {})
    proj_min = int(bt.get("project_min_sec", 15 * 60))
    tok_min = int(bt.get("token_min_sec", 10 * 60))
    win_min = int(bt.get("window_min_sec", 10 * 60))
    cat_min = int(bt.get("category_min_sec", 10 * 60))
    max_items = int(cfg.get("bullet_max_items", 8))
    visit_min = int(bt.get("visit_min", 5))

    bullets: list[str] = []

    # Projects
    for proj, sec in sorted(agg.get("by_project", {}).items(), key=lambda x: x[1], reverse=True):
        if sec >= proj_min:
            bullets.append(f"Worked on {proj} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    # Profile-based browser signals → boost as bullets without inflating focus time
    prof_map: dict[str, str] = agg.get("profile_projects", {}) or {}
    browser_tokens = agg.get("browser_tokens", {}) or {}
    for k, v in sorted(browser_tokens.items(), key=lambda x: x[1], reverse=True):
        if not k.startswith("profile:"):
            continue
        prof = k.split(":", 1)[1]
        # Choose mapped project if profile name contains a configured key
        target = None
        for key, proj in prof_map.items():
            if key.lower() in prof.lower():
                target = proj; break
        if target:
            bullets.append(f"Browser activity in {target}")
            if len(bullets) >= max_items:
                return bullets

    # Domain-based browser signals mapped to projects
    dom_proj: dict[str, str] = cfg.get("domain_projects", {}) or {}
    for dom, cnt in sorted((agg.get("browser_by_domain", {}) or {}).items(), key=lambda x: x[1], reverse=True):
        target = None
        for key, proj in dom_proj.items():
            if dom.endswith(key):
                target = proj; break
        if target and cnt >= visit_min:
            bullets.append(f"{target} activity ({cnt} visits)")
            if len(bullets) >= max_items:
                return bullets

    # Meeting titles (top 2)
    cal_ev = []
    for (title, start_s, end_s, _att) in agg.get("calendar_events", []) or []:
        try:
            s = datetime.fromisoformat(start_s); e = datetime.fromisoformat(end_s)
            sec = int((e - s).total_seconds())
            cal_ev.append((title, sec))
        except Exception:
            continue
    for title, sec in sorted(cal_ev, key=lambda x: x[1], reverse=True)[:2]:
        if sec >= cat_min:
            bullets.append(f"Meeting: {title} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    # Inferred appointments from HubSpot + calendar
    for appt in (agg.get("inferred_appointments") or [])[:2]:
        name = appt.get("name")
        visits = int(appt.get("visits", 0))
        title = appt.get("calendar_title") or "Appointment"
        bullets.append(f"Set appointment with {name} — {title} (HubSpot {visits} visits)")
        if len(bullets) >= max_items:
            return bullets

    # Google Workspace documents/services
    gws_docs = agg.get("gws_by_doc", {}) or {}
    for (svc, doc), sec in sorted(gws_docs.items(), key=lambda x: x[1], reverse=True):
        if sec >= win_min:
            bullets.append(f"Edited {svc}: {doc} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    gws_services = agg.get("gws_by_service", {}) or {}
    for svc, sec in sorted(gws_services.items(), key=lambda x: x[1], reverse=True):
        if sec >= cat_min:
            bullets.append(f"{svc} activity ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    # Email subjects
    for subj, sec in sorted((agg.get("email_by_subject", {}) or {}).items(), key=lambda x: x[1], reverse=True):
        if sec >= tok_min:
            bullets.append(f"Email: {subj} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    # Tokens
    for tok, sec in sorted(agg.get("by_token", {}).items(), key=lambda x: x[1], reverse=True):
        if sec >= tok_min:
            bullets.append(f"Progress on {tok} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    # Categories
    for cat, sec in sorted(agg.get("by_category", {}).items(), key=lambda x: x[1], reverse=True):
        if sec < cat_min:
            continue
        if cat == "Meetings":
            bullets.append(f"Meetings ({seconds_to_hhmm(sec)})")
        elif cat == "Communication":
            bullets.append(f"Client/team communication ({seconds_to_hhmm(sec)})")
        elif cat == "Docs":
            bullets.append(f"Edited docs/spreadsheets ({seconds_to_hhmm(sec)})")
        elif cat == "Coding":
            bullets.append(f"Development work ({seconds_to_hhmm(sec)})")
        elif cat == "Research":
            bullets.append(f"Research and planning ({seconds_to_hhmm(sec)})")
        else:
            bullets.append(f"{cat} ({seconds_to_hhmm(sec)})")
        if len(bullets) >= max_items:
            return bullets

    # Keyword-based from top windows
    key_specs = cfg.get("keyword_phrases", [])
    compiled = []
    for spec in key_specs:
        pat = spec.get("pattern")
        phr = spec.get("phrase")
        if not pat or not phr:
            continue
        try:
            compiled.append((re.compile(pat, re.IGNORECASE), phr))
        except re.error:
            continue

    for (app, title), sec in sorted(agg.get("by_window", {}).items(), key=lambda x: x[1], reverse=True):
        if sec < win_min:
            continue
        text = f"{app} {title}"
        matched = False
        for rx, phr in compiled:
            if rx.search(text):
                bullets.append(f"{phr} ({seconds_to_hhmm(sec)})")
                matched = True
                break
        if matched and len(bullets) >= max_items:
            return bullets

    # If still sparse, add top apps
    for app, sec in sorted(agg.get("by_app", {}).items(), key=lambda x: x[1], reverse=True):
        if sec >= cat_min:
            bullets.append(f"Time in {app} ({seconds_to_hhmm(sec)})")
            if len(bullets) >= max_items:
                return bullets

    return bullets


def synthesize_notes(agg: dict, cfg: dict) -> list[str]:
    notes: list[str] = []
    # Calendar events
    for (title, start_s, end_s, attendees) in agg.get("calendar_events", [])[:6]:
        try:
            s = datetime.fromisoformat(start_s)
            e = datetime.fromisoformat(end_s)
            dur = seconds_to_hhmm(int((e - s).total_seconds()))
            who = ", ".join(attendees[:3]) if attendees else ""
            if who:
                notes.append(f"Meeting: {title} ({dur}) — {who}")
            else:
                notes.append(f"Meeting: {title} ({dur})")
        except Exception:
            continue
    # Top Google Workspace documents
    for (svc, doc), sec in sorted((agg.get("gws_by_doc", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:5]:
        notes.append(f"Worked on {svc}: {doc} ({seconds_to_hhmm(sec)})")
    # Domain project visits
    dom_proj: dict[str, str] = cfg.get("domain_projects", {}) or {}
    for dom, cnt in sorted((agg.get("browser_by_domain", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:5]:
        target = None
        for key, proj in dom_proj.items():
            if dom.endswith(key):
                target = proj; break
        if target:
            notes.append(f"{target} browsing: {dom} ({cnt} visits)")
    # Tokens
    for tok, sec in sorted((agg.get("by_token", {}) or {}).items(), key=lambda x: x[1], reverse=True)[:5]:
        if sec > 0:
            notes.append(f"Touched {tok} ({seconds_to_hhmm(sec)})")
    # Inferred appointments
    for appt in (agg.get("inferred_appointments") or [])[:5]:
        name = appt.get("name"); visits = int(appt.get("visits", 0)); title = appt.get("calendar_title") or "Appointment"
        notes.append(f"Set appointment with {name}: {title} (HubSpot {visits} visits)")
    return notes


# ----------------------- High-level Story ------------------------

def synthesize_story(agg: dict, cfg: dict) -> dict:
    """Produce a compact, top-of-funnel story and next-steps.
    Returns {headline: str, bullets: list[str], next_up: list[str]}
    """
    bullets: list[str] = []
    next_up: list[str] = []

    # 1) Outcomes first: appointments set, key meetings, Slack wins, key artifacts
    appts = agg.get("inferred_appointments") or []
    if appts:
        top = []
        for a in appts[:3]:
            nm = a.get("name")
            cf = confidence_appt(a, cfg)
            if nm:
                top.append(f"{nm} {cf}")
        bullets.append(f"Set {len(appts)} appt(s): " + ", ".join(top))

    # Key meetings (top 2 by duration)
    mtgs = []
    for (title, start_s, end_s, _att) in agg.get("calendar_events", []) or []:
        try:
            s = datetime.fromisoformat(start_s); e = datetime.fromisoformat(end_s)
            mtgs.append((title, int((e - s).total_seconds())))
        except Exception:
            continue
    for title, sec in sorted(mtgs, key=lambda x: x[1], reverse=True)[:2]:
        bullets.append(f"Meeting: {title} ({seconds_to_hhmm(sec)})")

    # Top artifacts (Docs/Sheets or Workspace)
    gdocs = sorted((agg.get("gws_by_doc") or {}).items(), key=lambda x: x[1], reverse=True)
    if gdocs:
        (svc, doc), sec = gdocs[0]
        bullets.append(f"Primary doc: {svc} — {doc} ({seconds_to_hhmm(sec)})")
    work = sorted((agg.get("by_workspace") or {}).items(), key=lambda x: x[1], reverse=True)
    if work:
        ws, sec = work[0]
        bullets.append(f"Coding workspace: {ws} ({seconds_to_hhmm(sec)})")

    # Slack highlights
    act = agg.get("slack_activity", []) or []
    ap_set = [x for x in act if x.get('kind') == 'appointment_set']
    if ap_set:
        bullets.append(f"Booked via Slack: {min(3,len(ap_set))} item(s)")
    # Email theme
    emails = sorted((agg.get("email_by_subject") or {}).items(), key=lambda x: x[1], reverse=True)
    if emails:
        subj, sec = emails[0]
        bullets.append(f"Email: {subj} ({seconds_to_hhmm(sec)})")

    # 2) Next up suggestions
    # Contacts with many visits but no matched appointment
    with_appt = {a.get("name") for a in appts}
    for name, visits in sorted((agg.get("contact_visits") or {}).items(), key=lambda x: x[1], reverse=True):
        if name in with_appt:
            continue
        if visits >= int(cfg.get("contact_min_visits", 5)):
            next_up.append(f"Follow up with {name} (HubSpot {visits} visits today)")
            if len(next_up) >= 3:
                break

    # Docs with meaningful time but not top outcome
    for (svc, doc), sec in gdocs[1:4]:
        if sec >= 5 * 60:
            next_up.append(f"Finish work on {svc}: {doc}")
            if len(next_up) >= 5:
                break

    # Meeting-derived actions
    for title, sec in sorted(mtgs, key=lambda x: x[1], reverse=True):
        if len(next_up) >= 5:
            break
        if any(k in (title or '').lower() for k in ["strategy", "game plan", "discovery", "sales", "intro"]):
            next_up.append(f"Send recap for '{title}'")

    # Slack-derived follow-ups
    for x in act:
        if x.get('kind') == 'follow_up' and len(next_up) < 5:
            t = x.get('text','')[:80]
            next_up.append(f"Slack follow-up: {t}")

    momentum = synthesize_carryover(agg, cfg)
    headline = build_headline(agg, appts, mtgs, momentum)
    return {"headline": headline, "bullets": bullets[:4], "next_up": next_up[:5], "momentum": momentum, "appts": appts}


def build_headline(agg: dict, appts: list, mtgs: list, momentum: dict) -> str:
    appt_n = len(appts)
    meet_n = len(mtgs)
    focus = seconds_to_hhmm(int(agg.get("total_seconds", 0)))
    parts = []
    if appt_n:
        parts.append(f"{appt_n} appt")
    if meet_n:
        parts.append(f"{meet_n} mtg")
    parts.append(f"focus {focus}")
    if momentum.get("week_appts"):
        parts.append(f"wk appt {momentum['week_appts']}")
    return " • ".join(parts)


def confidence_appt(appt: dict, cfg: dict) -> str:
    """Return confidence tag for inferred appointment: [solid], [likely], [weak]."""
    visits = int(appt.get("visits", 0))
    min_v = int(cfg.get("contact_min_visits", 5))
    title = (appt.get("calendar_title") or "").lower()
    keys = [s.lower() for s in cfg.get("appt_keywords", []) or []]
    has_kw = any(k in title for k in keys)
    score = 0
    if visits >= min_v: score += 1
    if visits >= min_v * 2: score += 1
    if has_kw: score += 1
    if score >= 3:
        return "[solid]"
    if score == 2:
        return "[likely]"
    return "[weak]"


def synthesize_carryover(agg: dict, cfg: dict) -> dict:
    """Look back over the previous 3 days and compute small momentum stats."""
    from datetime import date
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    today = agg.get("day_start", datetime.now(tz)).date() if isinstance(agg.get("day_start"), datetime) else datetime.now(tz).date()
    total_appts = 0
    try:
        for d in range(1, 4):
            day = datetime.combine(today - timedelta(days=d), datetime.min.time()).replace(tzinfo=tz)
            a = aggregate_summary(day, int(cfg.get("day_end_hour_local", 24)), cfg)
            total_appts += len(a.get("inferred_appointments", [])) if a else 0
    except Exception:
        pass
    return {"week_appts": total_appts}


def build_story_html_lists(agg: dict, cfg: dict) -> dict:
    s = synthesize_story(agg, cfg)
    # Compose Executive bullets with simple evidence for appointments
    exec_items: list[str] = []
    appt_names = {a.get('name'): a for a in s.get('appts', []) if a.get('name')}
    for b in s['bullets']:
        # enrich appointment bullet with evidence tooltips
        if b.startswith('Set ') and 'appt' in b:
            # Add a muted evidence span per contact
            ev = []
            for name, ap in appt_names.items():
                visits = int(ap.get('visits', 0))
                title = ap.get('calendar_title') or ''
                conf = confidence_appt(ap, cfg)
                tip = f"visits {visits} • {title}"
                ev.append(f"<span class=badge title='{html_escape(tip)}'>{html_escape(conf)}</span> {html_escape(name)}")
            if ev:
                exec_items.append(f"<li>{html_escape(b.split(':')[0])}: " + ", ".join(ev) + "</li>")
            else:
                exec_items.append(f"<li>{html_escape(b)}</li>")
        else:
            exec_items.append(f"<li>{html_escape(b)}</li>")

    client_items = exec_items[:3]
    next_up_items = [f"<li>{html_escape(n)}</li>" for n in s['next_up']]
    return {"exec": "".join(exec_items), "client": "".join(client_items), "next_up": "".join(next_up_items), "headline": s['headline']}


def html_escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')


def story_enabled(cfg: dict) -> bool:
    try:
        return bool(cfg.get("story_enabled", True))
    except Exception:
        return True


def redact_ics_url(u: str) -> str:
    # Hide private token portion of Google ICS URLs
    try:
        if 'private-' in u:
            pre, post = u.split('private-', 1)
            # Keep only first 4 chars of token and the suffix path
            token = post.split('/', 1)[0]
            suffix = '/' + post.split('/', 1)[1] if '/' in post else ''
            return pre + 'private-' + token[:4] + '…' + suffix
        return u
    except Exception:
        return u


def safe_synthesize_story(agg: dict, cfg: dict) -> dict:
    if not story_enabled(cfg):
        return {"headline": "", "bullets": [], "next_up": []}
    try:
        return synthesize_story(agg, cfg)
    except Exception:
        return {"headline": "", "bullets": [], "next_up": []}


def safe_build_story_html_lists(agg: dict, cfg: dict) -> dict:
    if not story_enabled(cfg):
        return {"exec": "", "client": "", "next_up": "", "headline": ""}
    try:
        return build_story_html_lists(agg, cfg)
    except Exception:
        return {"exec": "", "client": "", "next_up": "", "headline": ""}


def report_html_path_for(date_local: datetime) -> Path:
    return REPORT_DIR / (date_local.strftime("%Y-%m-%d") + ".html")


def chrome_time_to_dt(us_since_1601: int, tzinfo: Optional[timezone]) -> datetime:
    try:
        base = datetime(1601, 1, 1, tzinfo=timezone.utc)
        dt = base + timedelta(microseconds=int(us_since_1601))
        if tzinfo:
            return dt.astimezone(tzinfo)
        return dt.astimezone()
    except Exception:
        return now_tz(CHICAGO_TZ)


def list_chrome_history_files(cfg: dict) -> list[Path]:
    chrome_base = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    integ = cfg.get("integrations", {})
    profiles = integ.get("chrome_profiles", ["Default"]) or []
    include_filters = [s.lower() for s in integ.get("chrome_profiles_include", []) or []]
    history_paths: list[Path] = []
    for prof in profiles:
        p = chrome_base / prof / "History"
        if p.exists():
            if include_filters and not any(f in str(p.parent.name).lower() for f in include_filters):
                continue
            history_paths.append(p)
    if not history_paths:
        # Attempt to scan all profiles
        for sub in chrome_base.glob("*/History"):
            if sub.is_file():
                if include_filters and not any(f in str(sub.parent.name).lower() for f in include_filters):
                    continue
                history_paths.append(sub)
    return history_paths


def collect_chrome_history(day_start: datetime, cutoff: datetime, cfg: dict) -> dict:
    """Collect Chrome history visit counts within [day_start, cutoff].
    Returns dict with keys: by_domain (dict[str,int]), pages (list[tuple[str,str,int]]), tokens (dict[str,int])
    Note: Uses counts or inferred buckets; does not contribute to total time.
    """
    # Find profiles
    integ = cfg.get("integrations", {})
    include_filters = [s.lower() for s in integ.get("chrome_profiles_include", []) or []]
    history_paths = list_chrome_history_files(cfg)

    by_domain: dict[str, int] = {}
    page_counts: dict[tuple[str, str], int] = {}
    tokens: dict[str, int] = {}

    # Token regexes (reuse config)
    import re
    token_specs = cfg.get("ticket_patterns", [])
    compiled_tokens: list[re.Pattern[str]] = []
    for pat in token_specs:
        try:
            compiled_tokens.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            continue

    def add_tokens(text: str):
        for rx in compiled_tokens:
            try:
                found = rx.findall(text)
            except Exception:
                found = []
            if not found:
                continue
            if found and isinstance(found[0], tuple):
                for tup in found:
                    token = " ".join([t for t in tup if t])
                    if token:
                        tokens[token] = tokens.get(token, 0) + 1
            else:
                for token in found:
                    if token:
                        tokens[token] = tokens.get(token, 0) + 1

    # Time bounds in Chrome epoch (web microseconds since 1601 UTC)
    # Convert using inverse function; here we convert day_start/cutoff to Chrome microseconds
    def dt_to_chrome_us(dt: datetime) -> int:
        base = datetime(1601, 1, 1, tzinfo=timezone.utc)
        return int((dt.astimezone(timezone.utc) - base).total_seconds() * 1_000_000)

    start_us = dt_to_chrome_us(day_start)
    end_us = dt_to_chrome_us(cutoff)

    for hp in history_paths:
        try:
            with tempfile.NamedTemporaryFile(prefix="at_chrome_", suffix=".db", delete=True) as tf:
                shutil.copy2(hp, tf.name)
                con = sqlite3.connect(tf.name)
                cur = con.cursor()
                try:
                    cur.execute(
                        "SELECT v.visit_time, u.url, u.title FROM visits v JOIN urls u ON v.url = u.id WHERE v.visit_time BETWEEN ? AND ?",
                        (start_us, end_us),
                    )
                except sqlite3.OperationalError:
                    # Older schema; try basic urls range by last_visit_time
                    cur.execute(
                        "SELECT u.last_visit_time, u.url, u.title FROM urls u WHERE u.last_visit_time BETWEEN ? AND ?",
                        (start_us, end_us),
                    )
                rows = cur.fetchall()
                con.close()
        except Exception:
            continue

        profile_name = hp.parent.name  # directory name reflects the Chrome profile folder
        for visit_time, url, title in rows:
            try:
                from urllib.parse import urlparse
                dom = urlparse(url).hostname or ""
                dom = dom.lower()
            except Exception:
                dom = ""
            if dom:
                by_domain[dom] = by_domain.get(dom, 0) + 1
            title_str = str(title or "")
            if dom or title_str:
                page_counts[(dom, title_str)] = page_counts.get((dom, title_str), 0) + 1
            # Tokenize with URL and add google service tokens if enabled
            add_tokens(f"{title_str} {url}")
            if integ.get("google_service_tokens"):
                svc = classify_google_service(url or "")
                if svc:
                    tokens[svc] = tokens.get(svc, 0) + 1
            # Add profile tag token to allow profile->project mapping later
            tokens[f"profile:{profile_name}"] = tokens.get(f"profile:{profile_name}", 0) + 1

    # Build top pages list
    pages_sorted = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    pages = [(dom, title, count) for (dom, title), count in pages_sorted]

    return {"by_domain": by_domain, "pages": pages, "tokens": tokens}


def classify_google_service(url: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse
        u = urlparse(url)
        host = (u.hostname or '').lower()
        path = (u.path or '').lower()
    except Exception:
        return None
    if host.endswith('google.com'):
        if host.startswith('mail.'):
            return 'Gmail'
        if host.startswith('calendar.'):
            return 'Google Calendar'
        if host.startswith('drive.'):
            return 'Google Drive'
        if host.startswith('docs.'):
            if path.startswith('/spreadsheets'):
                return 'Google Sheets'
            if path.startswith('/document'):
                return 'Google Docs'
            if path.startswith('/presentation') or path.startswith('/presentations'):
                return 'Google Slides'
        return 'Google'
    return None


def infer_google_from_title_url(title: str, url: str) -> Tuple[Optional[str], Optional[str]]:
    """Infer Google Workspace service and document name from title/url.
    Returns (service, docname) where service in {Google Docs, Google Sheets, Google Slides, Gmail, Google Calendar, Google Drive, Google}.
    """
    svc = classify_google_service(url or "")
    t = title or ""
    import re
    # Strip trailing " - Google Chrome" if present
    t = re.sub(r"\s-\sGoogle Chrome\s*$", "", t)
    if not svc:
        if "Google Sheets" in t:
            svc = "Google Sheets"
        elif "Google Docs" in t:
            svc = "Google Docs"
        elif "Google Slides" in t:
            svc = "Google Slides"
        elif "Gmail" in t:
            svc = "Gmail"
        elif "Calendar" in t:
            svc = "Google Calendar"
        elif "Google Drive" in t:
            svc = "Google Drive"
    doc = None
    if svc in ("Google Sheets", "Google Docs", "Google Slides"):
        # Titles are like: "My Sheet - Google Sheets" or "Doc title - Google Docs"
        m = re.split(r"\s-\sGoogle\s+(?:Sheets|Docs|Slides)\s*$", t)
        if m and m[0]:
            doc = m[0].strip()
    return svc, doc


def infer_gmail_subject_from_title(title: str) -> Optional[str]:
    """Best-effort subject extraction from Gmail window titles.
    Examples: "Subject — Inbox — jack@domain.com — Gmail" or "Subject — jack@domain.com — Gmail".
    Returns None if title looks like generic Inbox/label.
    """
    if not title or "Gmail" not in title:
        return None
    import re
    t = re.sub(r"\s-\sGoogle Chrome\s*$", "", title)
    parts = [p.strip() for p in re.split(r"\s[—-]\s", t) if p.strip()]
    # Remove trailing parts like account and "Gmail"
    parts = [p for p in parts if p.lower() not in ("gmail",)]
    if not parts:
        return None
    # If first part is 'Inbox' or a label, skip
    if parts[0].lower() in ("inbox", "starred", "sent", "drafts"):
        return None
    # Heuristic: take the first remaining chunk as subject
    subj = parts[0]
    # Avoid very short tokens
    if len(subj) < 4:
        return None
    return subj


def extract_contact_name(title: str) -> Optional[str]:
    """Heuristic to pull a contact name from HubSpot page titles.
    Handles patterns like:
    - "Contacts | Brad Nelson – HubSpot"
    - "Brad Nelson - Contacts - HubSpot"
    - "Brad N. – HubSpot"
    - "Brad Nelson | HubSpot"
    """
    if not title:
        return None
    import re
    t = re.sub(r"\s-\sGoogle Chrome\s*$", "", title)
    # Strip trailing hubspot marker
    t = re.sub(r"\s[-—|]\s*HubSpot.*$", "", t, flags=re.IGNORECASE)
    # Drop sections like "Contacts"/"Contact"
    t = re.sub(r"\b(Contacts?|Contact Details?)\b", "", t, flags=re.IGNORECASE)
    # Split by separators and scan tokens for name-like patterns
    parts = re.split(r"\s[-—|]\s", t)
    parts = [p.strip() for p in parts if p.strip()]
    candidates = parts[:3]
    name_re = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+|\s+[A-Z]\.?){0,2})\b")
    for chunk in candidates:
        m = name_re.search(chunk)
        if not m:
            continue
        name = m.group(1).strip()
        if name.lower() in ("hubspot", "contact", "contacts"):
            continue
        # Avoid picking domain words
        if re.search(r"\.(com|io|net|org)$", name.lower()):
            continue
        return name
    return None


def list_browser_profiles() -> None:
    base = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    profiles = []
    if base.exists():
        for sub in sorted(base.iterdir()):
            if (sub / "History").exists():
                profiles.append(sub.name)
    print("Chrome profiles with History DB:")
    for name in profiles:
        print(f"- {name}")
    integ = (RUNTIME_CFG or DEFAULT_CONFIG).get("integrations", {})
    inc = integ.get("chrome_profiles_include", [])
    if inc:
        print(f"Include filters: {inc}")


def scan_browser_today() -> None:
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    now = now_tz(CHICAGO_TZ).astimezone(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = now
    data = collect_chrome_history(day_start, cutoff, RUNTIME_CFG or DEFAULT_CONFIG)
    print("Top domains today:")
    for dom, cnt in sorted(data.get("by_domain", {}).items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"- {dom}: {cnt}")


def autodetect_chrome_profile_today() -> Optional[str]:
    base = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    if not base.exists():
        return None
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    now = now_tz(CHICAGO_TZ).astimezone(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Iterate all History DBs and count visits today
    best = None
    best_count = -1
    for hist in base.glob("*/History"):
        if not hist.is_file():
            continue
        # Count quickly
        try:
            import sqlite3, tempfile, shutil
            with tempfile.NamedTemporaryFile(prefix="at_detect_", suffix=".db", delete=True) as tf:
                shutil.copy2(hist, tf.name)
                con = sqlite3.connect(tf.name)
                cur = con.cursor()
                # Bounds in Chrome epoch
                def dt_to_us(dt):
                    base1601 = datetime(1601,1,1,tzinfo=timezone.utc)
                    return int((dt.astimezone(timezone.utc) - base1601).total_seconds()*1_000_000)
                start_us = dt_to_us(day_start)
                end_us = dt_to_us(now)
                try:
                    cur.execute("SELECT COUNT(*) FROM visits WHERE visit_time BETWEEN ? AND ?", (start_us, end_us))
                except sqlite3.OperationalError:
                    cur.execute("SELECT COUNT(*) FROM urls WHERE last_visit_time BETWEEN ? AND ?", (start_us, end_us))
                row = cur.fetchone()
                con.close()
                cnt = int(row[0]) if row else 0
        except Exception:
            cnt = 0
        if cnt > best_count:
            best_count = cnt
            best = hist.parent.name
    return best


def prune_old_data(days: int) -> None:
    cutoff_dt = now_tz(CHICAGO_TZ) - timedelta(days=max(1, days))
    # Logs
    try:
        for p in LOG_DIR.glob("*.jsonl"):
            try:
                d = datetime.strptime(p.stem, "%Y-%m-%d")
                if d < cutoff_dt.replace(hour=0, minute=0, second=0, microsecond=0):
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass
    # Reports (.md/.html) daily files only
    try:
        for p in REPORT_DIR.glob("*.md"):
            try:
                d = datetime.strptime(p.stem, "%Y-%m-%d")
                if d < cutoff_dt:
                    p.unlink()
            except Exception:
                pass
        for p in REPORT_DIR.glob("*.html"):
            # weekly files start with 'weekly-'; skip
            if p.name.startswith("weekly-"):
                continue
            try:
                d = datetime.strptime(p.stem, "%Y-%m-%d")
                if d < cutoff_dt:
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass
    # Cache
    try:
        for p in BROWSER_CACHE_DIR.glob("*.json"):
            try:
                d = datetime.strptime(p.stem, "%Y-%m-%d")
                if d < cutoff_dt:
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass
    # SQLite
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("DELETE FROM focus_events WHERE end < ?", (iso(cutoff_dt),))
        con.commit(); con.close()
    except Exception:
        pass


def view_daily_terminal(day: datetime) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        rich_ok = True
    except Exception:
        rich_ok = False
    cfg = load_config()
    agg = aggregate_summary(day, int(cfg.get("day_end_hour_local", 24)), cfg)
    if not rich_ok:
        print(f"Date: {day.strftime('%Y-%m-%d')}")
        print(f"Focus: {seconds_to_hhmm(int(agg.get('total_seconds',0)))}")
        print("Top Projects:")
        for proj, sec in sorted((agg.get('by_project') or {}).items(), key=lambda x:x[1], reverse=True)[:8]:
            print(f"- {proj}: {seconds_to_hhmm(sec)}")
        print("Top Domains:")
        for dom, cnt in sorted((agg.get('browser_by_domain') or {}).items(), key=lambda x:x[1], reverse=True)[:8]:
            print(f"- {dom}: {cnt} visits")
        return
    c = Console()
    c.print(f"[bold]Daily Summary[/bold] — {day.strftime('%Y-%m-%d')}")
    t1 = Table(title="Top Projects")
    t1.add_column("Project"); t1.add_column("Time")
    for proj, sec in sorted((agg.get('by_project') or {}).items(), key=lambda x:x[1], reverse=True)[:8]:
        t1.add_row(proj, seconds_to_hhmm(sec))
    t2 = Table(title="By Category")
    t2.add_column("Category"); t2.add_column("Time")
    for cat, sec in sorted((agg.get('by_category') or {}).items(), key=lambda x:x[1], reverse=True)[:8]:
        t2.add_row(cat, seconds_to_hhmm(sec))
    t3 = Table(title="Top Domains (visits)")
    t3.add_column("Domain"); t3.add_column("Visits")
    for dom, cnt in sorted((agg.get('browser_by_domain') or {}).items(), key=lambda x:x[1], reverse=True)[:8]:
        t3.add_row(dom, str(cnt))
    c.print(t1)
    c.print(t2)
    c.print(t3)


def suggest_rules_today() -> None:
    cfg = load_config()
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    today = now_tz(CHICAGO_TZ).astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    agg = aggregate_summary(today, int(cfg.get("day_end_hour_local", 24)), cfg)
    known = set(cfg.get('domain_projects', {}).keys())
    exclude = set(cfg.get('exclude_domains', []))
    priv = set(cfg.get('private_domains', []))
    suggestions = []
    for dom, cnt in sorted((agg.get('browser_by_domain') or {}).items(), key=lambda x:x[1], reverse=True):
        if any(dom.endswith(k) for k in known) or dom in exclude or dom in priv:
            continue
        if cnt < 3:
            continue
        suggestions.append((dom, cnt))
    print("Suggested domain → project rules (copy/paste):")
    for dom, cnt in suggestions[:10]:
        proj = f"Custom: {dom}"
        print(f"activity_tracker.py label --project \"{proj}\" --pattern \"{dom}\"")


def parse_ics_datetime(val: str) -> Optional[datetime]:
    try:
        import re
        # TZID=America/Chicago:YYYYMMDDTHHMMSS
        m = re.match(r"TZID=([^:]+):(\d{8}T\d{6})", val)
        if m:
            tzname, dtstr = m.groups()
            tz = ZoneInfo(tzname) if ZoneInfo else None
            dt = datetime.strptime(dtstr, "%Y%m%dT%H%M%S")
            return (dt.replace(tzinfo=tz) if tz else dt.replace(tzinfo=timezone.utc)).astimezone(CHICAGO_TZ or datetime.now().astimezone().tzinfo)
        # UTC Z suffix
        m = re.match(r"(\d{8}T\d{6})Z", val)
        if m:
            dt = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            return dt.astimezone(CHICAGO_TZ or datetime.now().astimezone().tzinfo)
        # Local date-time
        m = re.match(r"(\d{8}T\d{6})", val)
        if m:
            dt = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=CHICAGO_TZ or datetime.now().astimezone().tzinfo)
            return dt
        # All-day date
        m = re.match(r"(\d{8})", val)
        if m:
            dt = datetime.strptime(m.group(1), "%Y%m%d").replace(tzinfo=CHICAGO_TZ or datetime.now().astimezone().tzinfo)
            return dt
    except Exception:
        return None
    return None


def collect_calendar_events(day_start: datetime, cutoff: datetime) -> list[tuple[str, datetime, datetime, list[str]]]:
    """Scan macOS Calendar ICS files and return events intersecting [day_start, cutoff].
    Each item: (summary, start_dt, end_dt, attendees)
    """
    events: list[tuple[str, datetime, datetime, list[str]]] = []
    cal_dir = Path.home() / "Library" / "Calendars"
    if not cal_dir.exists():
        return events
    # Look at recent ICS files to limit IO
    import glob
    pattern = str(cal_dir / "*" / "Events" / "*.ics")
    paths = glob.glob(pattern)
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    # Optional calendar name filters
    try:
        filters = [s.lower() for s in (RUNTIME_CFG or DEFAULT_CONFIG).get("calendar_filters", []) or []]
    except Exception:
        filters = []
    for p in paths:
        if filters:
            low = p.lower()
            if not any(f in low for f in filters):
                continue
        try:
            st = os.stat(p)
            # Skip very old items
            if (datetime.now(tz) - datetime.fromtimestamp(st.st_mtime, tz)) > timedelta(days=14):
                continue
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        # crude parse
        start_s = None; end_s = None; summary = None; attendees: list[str] = []
        for line in text.splitlines():
            if line.startswith("DTSTART"):
                _, val = line.split(":", 1)
                d = parse_ics_datetime(val.strip())
                if d: start_s = d
            elif line.startswith("DTEND"):
                _, val = line.split(":", 1)
                d = parse_ics_datetime(val.strip())
                if d: end_s = d
            elif line.startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):].strip()
            elif line.startswith("ATTENDEE") and ":mailto:" in line:
                try:
                    parts = line.split(":mailto:", 1)[1]
                    addr = parts.strip()
                    attendees.append(addr)
                except Exception:
                    pass
        if start_s and end_s and summary:
            # overlap with range?
            if end_s > day_start and start_s < cutoff:
                events.append((summary, start_s, end_s, attendees))
    return events


# ----------------------- Google Calendar API ---------------------

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
GOOGLE_TOKEN_PATH = CRED_DIR / "google_token.json"
GOOGLE_CLIENT_PATH = CRED_DIR / "google_client_secret.json"


def google_api_available() -> bool:
    try:
        import google.auth  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
    except Exception:
        return False
    return True


def google_auth_flow() -> bool:
    if not google_api_available():
        print("Google API libraries not installed. Try: pip install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return False
    if not GOOGLE_CLIENT_PATH.exists():
        print(f"Missing client secret: {GOOGLE_CLIENT_PATH}\nDownload OAuth 2.0 Client (Desktop) JSON and save here.")
        return False
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore
        creds = None
        if GOOGLE_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), GOOGLE_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CLIENT_PATH), GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)
            GOOGLE_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        print(f"Google auth OK. Token saved: {GOOGLE_TOKEN_PATH}")
        return True
    except Exception as e:
        print(f"Google auth error: {e}")
        return False


def google_fetch_events(day_start: datetime, cutoff: datetime, cfg: dict) -> list[tuple[str, datetime, datetime, list[str]]]:
    if not google_api_available() or not GOOGLE_TOKEN_PATH.exists():
        return []
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), GOOGLE_SCOPES)
        service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        # Get calendars and filter
        filt = [s.lower() for s in cfg.get("calendar_filters", []) or []]
        cal_ids: list[tuple[str, str]] = []  # (id, summary)
        page_token = None
        while True:
            cals = service.calendarList().list(pageToken=page_token).execute()
            for item in cals.get('items', []):
                summary = (item.get('summary') or '').lower()
                if not filt or any(f in summary for f in filt):
                    cal_ids.append((item['id'], item.get('summary', 'Calendar')))
            page_token = cals.get('nextPageToken')
            if not page_token:
                break
        time_min = day_start.isoformat()
        time_max = cutoff.isoformat()
        results: list[tuple[str, datetime, datetime, list[str]]] = []
        for cal_id, _sum in cal_ids or [('primary', 'Primary')]:
            events_result = service.events().list(calendarId=cal_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy='startTime').execute()
            for ev in events_result.get('items', []):
                title = ev.get('summary') or '(no title)'
                start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                end = ev.get('end', {}).get('dateTime') or ev.get('end', {}).get('date')
                if not start or not end:
                    continue
                sdt = datetime.fromisoformat(start.replace('Z','+00:00')) if 'T' in start else datetime.fromisoformat(start + 'T00:00:00').replace(tzinfo=CHICAGO_TZ)
                edt = datetime.fromisoformat(end.replace('Z','+00:00')) if 'T' in end else datetime.fromisoformat(end + 'T00:00:00').replace(tzinfo=CHICAGO_TZ)
                attendees = []
                for a in ev.get('attendees', []) or []:
                    mail = a.get('email')
                    if mail:
                        attendees.append(mail)
                results.append((title, sdt.astimezone(CHICAGO_TZ), edt.astimezone(CHICAGO_TZ), attendees))
        return results
    except Exception:
        return []


# ----------------------- HubSpot API (optional) ------------------

HUBSPOT_TOKEN_PATH = CRED_DIR / "hubspot_token.txt"
SLACK_TOKEN_PATH = CRED_DIR / "slack_token.txt"


def hubspot_token() -> Optional[str]:
    tok = os.environ.get('HUBSPOT_TOKEN')
    if tok:
        return tok.strip()
    try:
        return HUBSPOT_TOKEN_PATH.read_text(encoding='utf-8').strip()
    except Exception:
        pass
    # Try HubSpot CLI config (~/.hubspot/config.yml)
    try:
        cli_path = Path.home() / ".hubspot" / "config.yml"
        if cli_path.exists():
            t = cli_path.read_text(encoding='utf-8', errors='ignore')
            # naive scan for accessToken: <token>
            for line in t.splitlines():
                line = line.strip()
                if line.lower().startswith('accesstoken:'):
                    token = line.split(':', 1)[1].strip().strip('"')
                    if token:
                        return token
    except Exception:
        pass
    return None


# ----------------------- Slack (optional) ------------------------

def slack_token() -> Optional[str]:
    tok = os.environ.get('SLACK_TOKEN') or os.environ.get('SLACK_BOT_TOKEN') or os.environ.get('SLACK_USER_TOKEN')
    if tok:
        return tok.strip()
    try:
        return SLACK_TOKEN_PATH.read_text(encoding='utf-8').strip()
    except Exception:
        return None


def slack_api(method: str, params: dict) -> Optional[dict]:
    import requests  # type: ignore
    tok = slack_token()
    if not tok:
        return None
    try:
        r = requests.get(f"https://slack.com/api/{method}", headers={"Authorization": f"Bearer {tok}"}, params=params, timeout=6)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get('ok'):
            return None
        return data
    except Exception:
        return None


def slack_get_self_id() -> Optional[str]:
    # Allow override via config
    try:
        cfg = load_config()
        override = cfg.get('integrations', {}).get('slack_user_id')
        if override:
            return str(override)
    except Exception:
        pass
    data = slack_api('auth.test', {})
    if not data:
        return None
    return data.get('user_id')


def slack_get_channel_id(name: str) -> Optional[str]:
    # Try to find by name (without #)
    import requests  # type: ignore
    tok = slack_token()
    if not tok:
        return None
    cursor = None
    for _ in range(10):
        params = {"limit": 200, "types": "public_channel,private_channel"}
        if cursor:
            params['cursor'] = cursor
        data = slack_api('conversations.list', params)
        if not data:
            return None
        for ch in data.get('channels', []):
            if (ch.get('name') or '').lower() == name.lower().lstrip('#'):
                return ch.get('id')
        cursor = data.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    return None


def slack_fetch_bookedcalls(day_start: datetime, cutoff: datetime, cfg: dict) -> list[dict]:
    tok = slack_token()
    if not tok or not cfg.get('integrations', {}).get('slack'):
        return []
    integ = cfg.get('integrations', {})
    channel_names = integ.get('slack_channels', []) or []
    channel_ids_cfg = integ.get('slack_channel_ids', []) or []
    emojis = set(cfg.get('integrations', {}).get('slack_emoji', []) or ["white_check_mark"])  # names
    me = slack_get_self_id()
    if not me:
        return []
    results: list[dict] = []
    oldest = str(day_start.timestamp())
    latest = str(cutoff.timestamp())
    # Resolve all channels: explicit IDs + names
    to_scan: list[tuple[str,str]] = []  # (id, label)
    for cid in channel_ids_cfg:
        if cid:
            to_scan.append((cid, cid))
    for ch_name in channel_names:
        ch_id = slack_get_channel_id(ch_name)
        if ch_id:
            to_scan.append((ch_id, ch_name))
    for ch_id, label in to_scan:
        cursor = None
        for _ in range(20):
            params = {"channel": ch_id, "oldest": oldest, "latest": latest, "limit": 200, "inclusive": True}
            if cursor:
                params['cursor'] = cursor
            data = slack_api('conversations.history', params)
            if not data:
                break
            for msg in data.get('messages', []):
                for react in msg.get('reactions', []) or []:
                    name = react.get('name')
                    if name not in emojis:
                        continue
                    users = react.get('users', []) or []
                    if me in users:
                        txt = msg.get('text') or '(no text)'
                        ts = float(msg.get('ts') or 0.0)
                        results.append({"channel": label, "text": txt, "ts": ts, "emoji": name})
                        break
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
    return results


def slack_list_conversations(types: list[str]) -> list[tuple[str,str]]:
    # returns list of (id, name_or_id)
    convs: list[tuple[str,str]] = []
    cursor = None
    t = ",".join(types)
    for _ in range(20):
        params = {"limit": 200, "types": t}
        if cursor:
            params['cursor'] = cursor
        data = slack_api('conversations.list', params)
        if not data:
            break
        for ch in data.get('channels', []):
            cid = ch.get('id'); name = ch.get('name') or cid
            if cid:
                convs.append((cid, name))
        cursor = data.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    return convs


def slack_scan_activity(day_start: datetime, cutoff: datetime, cfg: dict) -> list[dict]:
    if not cfg.get('integrations', {}).get('slack'):
        return []
    tok = slack_token()
    if not tok:
        return []
    import re
    me = slack_get_self_id() or ''
    types = cfg.get('integrations', {}).get('slack_scan_types', ["public_channel","private_channel","im"]) or []
    convs = slack_list_conversations(types)
    oldest = str(day_start.timestamp()); latest = str(cutoff.timestamp())
    items: list[dict] = []
    # patterns
    appt_rx = re.compile(r"\b(set\s+(appt|appointment)|booked|scheduled|confirmed|game\s*plan|discovery|strategy|sales\s*call|demo)\b", re.I)
    follow_rx = re.compile(r"\b(follow\s*up|remind|todo|next\s*up|action\s*items?)\b", re.I)
    for cid, label in convs[:50]:
        cursor = None
        for _ in range(10):
            params = {"channel": cid, "oldest": oldest, "latest": latest, "limit": 200, "inclusive": True}
            if cursor:
                params['cursor'] = cursor
            data = slack_api('conversations.history', params)
            if not data:
                break
            for msg in data.get('messages', []) or []:
                user = msg.get('user') or msg.get('bot_id')
                txt = (msg.get('text') or '').strip()
                if not txt:
                    continue
                # authored-by-me signals
                if user == me:
                    kind = None
                    if appt_rx.search(txt):
                        kind = 'appointment_set'
                    elif follow_rx.search(txt):
                        kind = 'follow_up'
                    if kind:
                        items.append({"kind": kind, "text": txt, "channel": label, "ts": float(msg.get('ts') or 0.0)})
                # reaction-by-me already covered in bookedcalls
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
    return items


def hubspot_fetch_meetings(start: datetime, end: datetime) -> list[dict]:
    token = hubspot_token()
    if not token:
        return []


# ----------------------- Remote ICS (optional) -------------------

def collect_remote_ics_events(urls: list[str], day_start: datetime, cutoff: datetime) -> list[tuple[str, datetime, datetime, list[str]]]:
    import urllib.request
    events: list[tuple[str, datetime, datetime, list[str]]] = []
    for url in urls or []:
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                raw = resp.read()
            text = raw.decode('utf-8', errors='ignore')
        except Exception:
            continue
        # crude parse of VEVENT blocks
        block: list[str] = []
        in_event = False
        for line in text.splitlines():
            line = line.strip()
            if line == 'BEGIN:VEVENT':
                in_event = True; block = []; continue
            if line == 'END:VEVENT':
                if block:
                    ev = parse_ics_block(block)
                    if ev:
                        title, s, e, att = ev
                        # Overlap filter
                        seg_start = max(s, day_start)
                        seg_end = min(e, cutoff)
                        if seg_end > seg_start:
                            events.append(ev)
                in_event = False; block = []; continue
            if in_event:
                block.append(line)
    return events


def parse_ics_block(lines: list[str]) -> Optional[tuple[str, datetime, datetime, list[str]]]:
    title = None; s = None; e = None; attendees: list[str] = []
    for ln in lines:
        try:
            if ln.startswith('SUMMARY:'):
                title = ln[len('SUMMARY:'):].strip()
            elif ln.startswith('DTSTART') and ':' in ln:
                _, val = ln.split(':', 1)
                ds = parse_ics_datetime(val)
                if ds: s = ds
            elif ln.startswith('DTEND') and ':' in ln:
                _, val = ln.split(':', 1)
                de = parse_ics_datetime(val)
                if de: e = de
            elif ln.startswith('ATTENDEE') and ':mailto:' in ln:
                attendees.append(ln.split(':mailto:',1)[1].strip())
        except Exception:
            continue
    if title and s and e:
        return title, s, e, attendees
    return None
    import requests  # type: ignore
    url = 'https://api.hubapi.com/crm/v3/objects/meetings/search'
    payload = {
        "filterGroups": [
            {"filters": [
                {"propertyName": "hs_lastmodifieddate", "operator": "GTE", "value": int(start.timestamp()*1000)},
                {"propertyName": "hs_lastmodifieddate", "operator": "LTE", "value": int(end.timestamp()*1000)}
            ]}
        ],
        "properties": ["hs_meeting_title", "hs_meeting_start_time", "hs_meeting_end_time"],
        "limit": 50
    }
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=6)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get('results', [])
    except Exception:
        return []


def record_terminal_ping(cwd: str) -> None:
    """Record last terminal working directory hint for project inference."""
    info = {
        "cwd": cwd,
        "repo": find_repo_name(Path(cwd)),
        "ts": iso(now_tz(CHICAGO_TZ)),
    }
    try:
        TERM_PING_PATH.write_text(json.dumps(info, indent=2), encoding="utf-8")
    except Exception:
        pass


def find_repo_name(path: Path) -> Optional[str]:
    try:
        p = path
        for _ in range(8):
            if (p / ".git").exists():
                return p.name
            if p.parent == p:
                break
            p = p.parent
    except Exception:
        return None
    return None


def read_recent_term_ping_repo(max_age_minutes: int = 20) -> Optional[str]:
    try:
        if not TERM_PING_PATH.exists():
            return None
        data = json.loads(TERM_PING_PATH.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data.get("ts", ""))
        if ts.tzinfo is None:
            ts = ts.astimezone()
        if now_tz(CHICAGO_TZ) - ts > timedelta(minutes=max_age_minutes):
            return None
        repo = data.get("repo")
        return str(repo) if repo else None
    except Exception:
        return None


def safari_time_to_dt(seconds_since_2001: float, tzinfo: Optional[timezone]) -> datetime:
    try:
        base = datetime(2001, 1, 1, tzinfo=timezone.utc)
        dt = base + timedelta(seconds=float(seconds_since_2001))
        return dt.astimezone(tzinfo or timezone.utc)
    except Exception:
        return now_tz(CHICAGO_TZ)


def collect_safari_history(day_start: datetime, cutoff: datetime, cfg: dict) -> dict:
    """Collect Safari history visit counts in the window [day_start, cutoff]."""
    db_path = Path.home() / "Library" / "Safari" / "History.db"
    if not db_path.exists():
        return {"by_domain": {}, "pages": [], "tokens": {}}

    by_domain: dict[str, int] = {}
    page_counts: dict[tuple[str, str], int] = {}
    tokens: dict[str, int] = {}

    # Token regexes
    import re
    token_specs = cfg.get("ticket_patterns", [])
    compiled_tokens: list[re.Pattern[str]] = []
    for pat in token_specs:
        try:
            compiled_tokens.append(re.compile(pat, re.IGNORECASE))
        except re.error:
            continue

    def add_tokens(text: str):
        for rx in compiled_tokens:
            try:
                found = rx.findall(text)
            except Exception:
                found = []
            if not found:
                continue
            if found and isinstance(found[0], tuple):
                for tup in found:
                    token = " ".join([t for t in tup if t])
                    if token:
                        tokens[token] = tokens.get(token, 0) + 1
            else:
                for token in found:
                    if token:
                        tokens[token] = tokens.get(token, 0) + 1

    # Bounds in Safari epoch seconds
    def dt_to_safari_seconds(dt: datetime) -> float:
        base = datetime(2001, 1, 1, tzinfo=timezone.utc)
        return (dt.astimezone(timezone.utc) - base).total_seconds()

    start_s = dt_to_safari_seconds(day_start)
    end_s = dt_to_safari_seconds(cutoff)

    try:
        with tempfile.NamedTemporaryFile(prefix="at_safari_", suffix=".db", delete=True) as tf:
            shutil.copy2(db_path, tf.name)
            con = sqlite3.connect(tf.name)
            cur = con.cursor()
            try:
                cur.execute(
                    "SELECT v.visit_time, i.url, i.title FROM history_visits v JOIN history_items i ON v.history_item = i.id WHERE v.visit_time BETWEEN ? AND ?",
                    (start_s, end_s),
                )
            except sqlite3.OperationalError:
                # Fallback: older schema variants
                cur.execute(
                    "SELECT i.visit_count, i.url, i.title FROM history_items i WHERE i.visit_count > 0",
                )
            rows = cur.fetchall()
            con.close()
    except Exception:
        rows = []

    for when_val, url, title in rows:
        try:
            from urllib.parse import urlparse
            dom = urlparse(url or "").hostname or ""
            dom = dom.lower()
        except Exception:
            dom = ""
        if dom:
            by_domain[dom] = by_domain.get(dom, 0) + 1
        title_str = str(title or "")
        if dom or title_str:
            page_counts[(dom, title_str)] = page_counts.get((dom, title_str), 0) + 1
        add_tokens(f"{title_str} {url}")

    pages_sorted = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    pages = [(dom, title, count) for (dom, title), count in pages_sorted]
    return {"by_domain": by_domain, "pages": pages, "tokens": tokens}


def collect_browser_history_cached(day_start: datetime, cutoff: datetime, cfg: dict) -> dict:
    """Cache merged Chrome+Safari results per day to reduce CPU and IO.
    Cache key incorporates history mtimes and include filters.
    """
    try:
        BROWSER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = day_start.strftime("%Y-%m-%d")
        cache_path = BROWSER_CACHE_DIR / f"{key}.json"

        # Fingerprint: list of Chrome history mtimes + Safari mtime + include filters
        chrome_files = list_chrome_history_files(cfg)
        c_mtimes = [str(int(p.stat().st_mtime)) for p in chrome_files if p.exists()]
        saf = Path.home() / "Library" / "Safari" / "History.db"
        s_mtime = str(int(saf.stat().st_mtime)) if saf.exists() else "0"
        integ = cfg.get("integrations", {})
        include_filters = integ.get("chrome_profiles_include", []) or []
        fingerprint = {
            "c": c_mtimes,
            "s": s_mtime,
            "inc": include_filters,
            "ver": 1,
        }

        if cache_path.exists():
            try:
                obj = json.loads(cache_path.read_text(encoding="utf-8"))
                if obj.get("fingerprint") == fingerprint:
                    return obj.get("data", {"by_domain": {}, "pages": [], "tokens": {}})
            except Exception:
                pass

        # Build fresh and write cache
        merged = {"by_domain": {}, "pages": [], "tokens": {}}
        if integ.get("chrome"):
            ch = collect_chrome_history(day_start, cutoff, cfg)
            for k, v in ch.get("by_domain", {}).items():
                merged["by_domain"][k] = merged["by_domain"].get(k, 0) + int(v)
            merged["pages"].extend(ch.get("pages", []))
            for k, v in ch.get("tokens", {}).items():
                merged["tokens"][k] = merged["tokens"].get(k, 0) + int(v)
        if integ.get("safari"):
            sf = collect_safari_history(day_start, cutoff, cfg)
            for k, v in sf.get("by_domain", {}).items():
                merged["by_domain"][k] = merged["by_domain"].get(k, 0) + int(v)
            merged["pages"].extend(sf.get("pages", []))
            for k, v in sf.get("tokens", {}).items():
                merged["tokens"][k] = merged["tokens"].get(k, 0) + int(v)

        try:
            cache_path.write_text(json.dumps({"fingerprint": fingerprint, "data": merged}), encoding="utf-8")
        except Exception:
            pass
        return merged
    except Exception:
        return {"by_domain": {}, "pages": [], "tokens": {}}

def generate_summary_html_for(date_local: datetime, cutoff_hour_local: Optional[int] = None) -> Path:
    cfg = load_config()
    if cutoff_hour_local is None:
        cutoff_hour_local = int(cfg.get("day_end_hour_local", 24))
    agg = aggregate_summary(date_local, cutoff_hour_local, cfg)
    date_str = date_local.strftime("%Y-%m-%d")
    # Build story once with safeguards/flag
    story = safe_build_story_html_lists(agg, cfg)

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    top_apps = "".join(
        f"<li><strong>{esc(app)}</strong>: {seconds_to_hhmm(sec)}</li>"
        for app, sec in sorted(agg["by_app"].items(), key=lambda x: x[1], reverse=True)[:10]
    ) or "<li>No data recorded</li>"

    # Redact sensitive bits in titles for presentation
    redact_pats = cfg.get("redact_patterns", [])
    def red(s: str) -> str:
        return esc(redact(s, redact_pats))

    top_windows = "".join(
        f"<li>{esc(app)} — {red(clean_title_for_display(app, title)) if title else '(no title)'}: {seconds_to_hhmm(sec)}</li>"
        for (app, title), sec in sorted(agg["by_window"].items(), key=lambda x: x[1], reverse=True)[:15]
    ) or "<li>No data recorded</li>"

    by_cat_html = "".join(
        f"<li><strong>{esc(cat)}</strong>: {seconds_to_hhmm(sec)}</li>"
        for cat, sec in sorted(agg["by_category"].items(), key=lambda x: x[1], reverse=True)
    ) or "<li>No data</li>"

    by_proj_html = "".join(
        f"<li><strong>{esc(proj)}</strong>: {seconds_to_hhmm(sec)}</li>"
        for proj, sec in sorted(agg["by_project"].items(), key=lambda x: x[1], reverse=True)[:12]
    ) or "<li>No projects detected</li>"

    # Build Digital Footprint tables
    apps_rows = "".join(
        f"<tr><td>{esc(app)}</td><td class=rt>{seconds_to_hhmm(sec)}</td></tr>"
        for app, sec in sorted(agg.get("by_app", {}).items(), key=lambda x: x[1], reverse=True)[:10]
    ) or "<tr><td colspan=2>—</td></tr>"

    domain_rows = "".join(
        f"<tr><td>{esc(dom)}</td><td class=rt>{cnt}</td></tr>"
        for dom, cnt in sorted(agg.get("browser_by_domain", {}).items(), key=lambda x: x[1], reverse=True)[:25]
    ) or "<tr><td colspan=2>—</td></tr>"

    def _trunc(text: str, n: int = 80) -> str:
        return text if len(text) <= n else text[: n - 1] + "…"

    windows_rows = "".join(
        f"<tr><td><span class=\"truncate\" title=\"{esc((clean_title_for_display(app, title) if title else '(no title)'))}\">{esc(_trunc(clean_title_for_display(app, title) if title else '(no title)'))}</span></td><td class=rt>{seconds_to_hhmm(sec)}</td></tr>"
        for (app, title), sec in sorted(agg.get("by_window", {}).items(), key=lambda x: x[1], reverse=True)[:25]
    ) or "<tr><td colspan=2>—</td></tr>"

    # Suggested tasks: from projects, tokens, and focused windows (build plain items)
    sugg_items: list[str] = []
    for proj, sec in sorted(agg["by_project"].items(), key=lambda x: x[1], reverse=True):
        if sec >= 15 * 60:
            sugg_items.append(f"Progress on {proj} — {seconds_to_hhmm(sec)}")

    for tok, sec in sorted(agg.get("by_token", {}).items(), key=lambda x: x[1], reverse=True):
        if sec >= 10 * 60:
            sugg_items.append(f"Touched {tok} — {seconds_to_hhmm(sec)}")

    count = 0
    for (app, title), sec in sorted(agg["by_window"].items(), key=lambda x: x[1], reverse=True):
        if sec < 10 * 60:
            continue
        plain_title = clean_title_for_display(app, title) if title else '(no title)'
        sugg_items.append(f"Focused on {app} — {plain_title} — {seconds_to_hhmm(sec)}")
        count += 1
        if count >= 8:
            break
    if sugg_items:
        def escattr(s: str) -> str:
            return s.replace("'","&#39;").replace('"','&quot;')
        sugg_html = "".join(
            f"<li><span class=truncate title='{escattr(i)}'>{esc(i)}</span> "
            f"<button class=\"btn\" onclick=\"addTodo('{escattr(i)}')\">+ Add to To‑Do</button></li>"
            for i in sugg_items
        )
    else:
        sugg_html = "<li>No suggestions yet — more focused time will surface items.</li>"

    coverage = (
        f"{agg['first_ts'].strftime('%H:%M')}–{agg['last_ts'].strftime('%H:%M %Z')}"
        if agg["first_ts"] and agg["last_ts"] else "—"
    )

    # Hourly bars (0-23)
    max_hour_sec = max(agg["by_hour"].values()) if agg["by_hour"] else 0
    def hour_bar(h: int) -> str:
        sec = agg["by_hour"].get(h, 0)
        pct = (sec / max_hour_sec * 100) if max_hour_sec else 0
        label = f"{h:02d}"
        dur = seconds_to_hhmm(sec)
        return f"<div class=hb><div class=hbL>{label}</div><div class=hbB><div class=hbF style=\"width:{pct:.0f}%\"></div></div><div class=hbT>{dur}</div></div>"

    hourly_html = "".join(hour_bar(h) for h in range(24))

    # Google Workspace section
    gws_services = agg.get("gws_by_service", {}) or {}
    gws_docs = agg.get("gws_by_doc", {}) or {}
    gws_service_html = "".join(
        f"<li><strong>{esc(svc)}</strong>: {seconds_to_hhmm(sec)}</li>"
        for svc, sec in sorted(gws_services.items(), key=lambda x: x[1], reverse=True)
    ) or "<li>No activity</li>"
    gws_docs_html = "".join(
        f"<li>{esc(svc)} — {esc(doc)}: {seconds_to_hhmm(sec)}</li>"
        for (svc, doc), sec in sorted(gws_docs.items(), key=lambda x: x[1], reverse=True)[:15]
    ) or "<li>No documents</li>"

    # Build Prepared for Manager section (compact bullets)
    top_projects = sorted(agg["by_project"].items(), key=lambda x: x[1], reverse=True)
    top_projects_str = ", ".join(
        f"{proj} ({seconds_to_hhmm(sec)})" for proj, sec in top_projects[:3]
    ) or "—"

    # Merge tokens from tracker and browser
    merged_tokens: dict[str, int] = {}
    for d in (agg.get("by_token", {}), agg.get("browser_tokens", {})):
        for k, v in d.items():
            merged_tokens[k] = merged_tokens.get(k, 0) + int(v)
    top_tokens = sorted(merged_tokens.items(), key=lambda x: x[1], reverse=True)
    top_tokens_str = ", ".join(
        f"{tok} ({seconds_to_hhmm(sec)})" for tok, sec in top_tokens[:3]
    ) or "—"

    top_apps_str = ", ".join(
        f"{app} ({seconds_to_hhmm(sec)})" for app, sec in sorted(agg["by_app"].items(), key=lambda x: x[1], reverse=True)[:3]
    ) or "—"

    prepared_lines = [
        f"- Total focused time: {seconds_to_hhmm(agg['total_seconds'])} (Coverage: {coverage})",
        f"- Top projects: {top_projects_str}",
        f"- Key tickets: {top_tokens_str}",
        f"- Top apps: {top_apps_str}",
    ]
    prepared_text = "\n".join(prepared_lines)

    prepared_html = "".join(f"<li>{esc(line[2:])}</li>" for line in prepared_lines)

    # Build consolidated Key Activity Summary (for stakeholders)
    def trunc(s: str, n: int = 48) -> str:
        return (s if len(s) <= n else s[: max(0, n - 1)] + "…") if s else s

    # Overall summary
    overall_line = f"Total Focused Time: {seconds_to_hhmm(int(agg.get('total_seconds',0)))} (Coverage: {coverage})"

    # Appointments set (confidence) and meetings attended (top 2)
    appts = agg.get("inferred_appointments", []) or []
    appt_names = []
    for a in appts[:3]:
        nm = (a.get("name") or "Appointment").strip()
        cf = confidence_appt(a, cfg)
        appt_names.append(f"{cf} {nm}")
    appt_line = f"Appointments Set ({len(appts)}): " + ", ".join(appt_names) if appts else "Appointments Set (0)"

    mtgs = []
    for (t, s, e, _att) in agg.get("calendar_events", []) or []:
        try:
            sd = datetime.fromisoformat(s); ed = datetime.fromisoformat(e)
            sec = int((ed - sd).total_seconds())
            mtgs.append((t or "(untitled)", sec))
        except Exception:
            continue
    mtgs = sorted(mtgs, key=lambda x: x[1], reverse=True)[:2]
    mtg_line = "Meetings Attended ({}): ".format(len(agg.get("calendar_events", []) or []))
    if mtgs:
        mtg_line += ", ".join(f"{trunc(t)} ({seconds_to_hhmm(sec)})" for t, sec in mtgs)
    else:
        mtg_line += "—"

    # Time allocation: top projects and applications
    time_projects_line = f"Top Projects: {top_projects_str or '—'}"
    time_apps_line = f"Top Applications: {top_apps_str or '—'}"

    # Key output: primary document (top Google Workspace doc)
    primary_doc_line = "Primary Document: —"
    if gws_docs:
        (svc0, doc0), sec0 = sorted(gws_docs.items(), key=lambda x: x[1], reverse=True)[0]
        primary_doc_line = f"Primary Document: {svc0} — {trunc(doc0)} ({seconds_to_hhmm(sec0)})"

    # Next up: take first two items from synthesized story
    story_obj = safe_synthesize_story(agg, cfg)
    nxt = story_obj.get("next_up", []) or []
    next_line = "Next Up: " + (" / ".join(trunc(i, 60) for i in nxt[:2]) if nxt else "—")

    key_lines = [
        overall_line,
        appt_line,
        mtg_line,
        time_projects_line,
        time_apps_line,
        primary_doc_line,
        next_line,
    ]
    key_summary_html = "".join(f"<li>{esc(l)}</li>" for l in key_lines)

    # Overview metrics
    meetings_sec = int(agg.get("calendar_total_seconds", 0) or 0)
    focus_sec = int(agg.get("total_seconds", 0) or 0)
    appt_n = len(agg.get("inferred_appointments", []) or [])
    proj_n = len(agg.get("by_project", {}) or {})
    windows_count = len(agg.get("by_window", {}) or {})
    pages_count = len(agg.get("browser_pages", []) or [])

    # Project mini-table (heuristic: match tokens to docs/windows)
    import re as _re
    def _tokens(p: str):
        return [_t.lower() for _t in _re.findall(r"[A-Za-z0-9]{3,}", p)]
    def _best_doc(p: str):
        toks = _tokens(p); best = None
        for (svc, doc), sec in (agg.get("gws_by_doc") or {}).items():
            dlow = (doc or '').lower()
            if any(t in dlow for t in toks):
                if not best or sec > best[2]: best = (svc, doc, sec)
        return best
    def _best_window(p: str):
        toks = _tokens(p); best = None
        for (app, title), sec in (agg.get("by_window") or {}).items():
            tlow = (title or '').lower()
            if any(t in tlow for t in toks):
                if not best or sec > best[2]: best = (app, title, sec)
        return best
    proj_table_rows = []
    for proj, sec in sorted((agg.get("by_project") or {}).items(), key=lambda x: x[1], reverse=True)[:10]:
        d = _best_doc(proj)
        w = _best_window(proj)
        dtxt = f"{esc(d[0])} — {esc(d[1])}" if d else "—"
        wtxt = esc(clean_title_for_display(w[0], w[1])) if w else "—"
        proj_table_rows.append(f"<tr><td>{esc(proj)}</td><td>{seconds_to_hhmm(sec)}</td><td>{dtxt}</td><td>{wtxt}</td></tr>")
    proj_table_html = "".join(proj_table_rows) or "<tr><td colspan=4>—</td></tr>"

    # Manager accomplishments bullets
    mgr_bullets = synthesize_manager_bullets(agg, cfg)
    mgr_html = "".join(f"<li>{esc(b)}</li>" for b in mgr_bullets) or "<li>—</li>"
    client_html = "".join(f"<li>{esc(b)}</li>" for b in mgr_bullets[:3]) or "<li>—</li>"

    # Counts used for UI summaries/collapses
    pages_count = len(agg.get("browser_pages", []) or [])
    windows_count = len(agg.get("by_window", {}) or {})

    # Debug: appointments
    def _fmt_time(s: str) -> str:
        try:
            dt = datetime.fromisoformat(s)
            return dt.strftime('%H:%M')
        except Exception:
            return s
    cvis = sorted((agg.get("contact_visits") or {}).items(), key=lambda x: x[1], reverse=True)[:5]
    cvis_html = "".join(f"<li>{esc(name)}: {cnt} visits</li>" for name, cnt in cvis) or "<li>—</li>"
    mtg_list = []
    for (title, s, e, _att) in agg.get("calendar_events", []) or []:
        mtg_list.append((title or '', _fmt_time(s), _fmt_time(e)))
    mtg_html = "".join(f"<li>{esc(t)} ({esc(s)}–{esc(e)})</li>" for t, s, e in mtg_list[:6]) or "<li>—</li>"
    slack_items = agg.get("slack_booked", []) or []
    slack_html = "".join(f"<li>[{esc(it.get('channel',''))}] {esc((it.get('text') or '')[:80])}</li>" for it in slack_items[:6]) or "<li>—</li>"

    # Counts used for UI summaries/collapses
    pages_count = len(agg.get("browser_pages", []) or [])
    windows_count = len(agg.get("by_window", {}) or {})

    # Debug: Appointments (collapsed)
    def fmt_dt(s: str) -> str:
        try:
            dt = datetime.fromisoformat(s)
            return dt.strftime('%H:%M')
        except Exception:
            return s
    cvis = sorted((agg.get("contact_visits") or {}).items(), key=lambda x: x[1], reverse=True)[:5]
    cvis_html = "".join(f"<li>{esc(name)}: {cnt} visits</li>" for name, cnt in cvis) or "<li>—</li>"
    kw = [k for k in (load_config().get('appt_keywords', []) if callable(locals().get('load_config')) else [])]
    mtg = []
    for (title, s, e, _att) in agg.get("calendar_events", []) or []:
        t = title or ''
        mtg.append((t, fmt_dt(s), fmt_dt(e)))
    mtg_html = "".join(f"<li>{esc(t)} ({esc(s)}–{esc(e)})</li>" for t, s, e in mtg[:6]) or "<li>—</li>"
    slack_items = agg.get("slack_booked", []) or []
    slack_html = "".join(f"<li>[{esc(it.get('channel',''))}] {esc((it.get('text') or '')[:80])}</li>" for it in slack_items[:6]) or "<li>—</li>"

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Daily Accomplishments — {esc(date_str)}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; color: #1f2937; background:#fff; }}
    body.dark {{ background:#0b1220; color:#e5e7eb; }}
    h1 {{ font-size: 20px; margin: 0 0 8px; }}
    .meta {{ color: #6b7280; margin-bottom: 16px; }}
    body.dark .meta {{ color:#9ca3af; }}
    h2 {{ font-size: 16px; margin: 20px 0 8px; }}
    ul {{ margin: 0 0 12px 18px; }}
    .muted {{ color: #9ca3af; }}
    .time {{ font-variant-numeric: tabular-nums; }}
    .foot {{ margin-top: 20px; font-size: 12px; color: #6b7280; }}
    code {{ background: #f3f4f6; padding: 0 4px; border-radius: 4px; }}
    body.dark code {{ background:#111827; color:#d1d5db; }}
    .toolbar {{ display:flex; gap:8px; margin-bottom:12px; }}
    .btn {{ font-size:12px; padding:6px 10px; border-radius:6px; border:1px solid #cbd5e1; background:#fff; color:#111827; cursor:pointer; }}
    body.dark .btn {{ background:#0f172a; color:#e5e7eb; border-color:#293241; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .hb {{ display:flex; align-items:center; gap:8px; margin:2px 0; }}
    .hbL {{ width:32px; text-align:right; opacity:.7; font-size:12px; }}
    .hbB {{ flex:1; background:#e5e7eb; height:10px; border-radius:6px; overflow:hidden; }}
    body.dark .hbB {{ background:#1f2937; }}
    .hbF {{ height:100%; background:#2563eb; }}
    body.dark .hbF {{ background:#60a5fa; }}
    .hbT {{ width:48px; text-align:left; opacity:.7; font-size:12px; }}
    .cards {{ display:grid; grid-template-columns: repeat(4, minmax(120px,1fr)); gap:12px; margin: 12px 0 4px; }}
    .card {{ border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; }}
    body.dark .card {{ border-color:#1f2937; }}
    .card .v {{ font-size:18px; font-variant-numeric: tabular-nums; }}
    .card .k {{ color:#6b7280; font-size:12px; }}
    .toc {{ display:flex; flex-wrap:wrap; gap:10px; margin: 8px 0; }}
    .chip {{ font-size:12px; padding:4px 8px; border-radius:999px; border:1px solid #cbd5e1; cursor:pointer; }}
    body.dark .chip {{ border-color:#293241; }}
    .badge {{ display:inline-block; padding:1px 6px; margin-right:4px; border-radius:10px; font-size:11px; background:#e5e7eb; }}
    body.dark .badge {{ background:#1f2937; }}
    table.ptable {{ width:100%; border-collapse: collapse; margin:8px 0; }}
    table.ptable th, table.ptable td {{ border:1px solid #e5e7eb; padding:6px 8px; text-align:left; }}
    body.dark table.ptable th, body.dark table.ptable td {{ border-color:#1f2937; }}
    @media print {{
      body {{ background:#fff; color:#000; }}
      .toolbar, .toc, .btn {{ display:none !important; }}
      .badge {{ border:1px solid #000; background:#fff; }}
      code {{ background:#eee; color:#000; }}
    }}
  </style>
  <script>
    (function() {{
      const key = 'at-theme';
      function apply(theme){{
        document.body.classList.toggle('dark', theme === 'dark');
      }}
      function load(){{ return localStorage.getItem(key) || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }}
      function save(t){{ localStorage.setItem(key, t); }}
      window.toggleTheme = function(){{ const cur = load(); const next = cur==='dark'?'light':'dark'; apply(next); save(next); }};
      window.copyPrepared = function(){{
        try {{
          const txt = document.getElementById('pm-text')?.textContent || '';
          navigator.clipboard.writeText(txt);
        }} catch (e) {{}}
      }};
      window.copyList = function(id){{ try {{ const ul=document.getElementById(id); if(!ul) return; const t=[...ul.querySelectorAll('li')].map(li=>li.textContent.trim()).join('\n'); navigator.clipboard.writeText(t); }} catch(e){{}} }};
      window.addTodo = function(text){{ try {{ const k='todos-'+'{esc(date_str)}'; const cur=JSON.parse(localStorage.getItem(k)||'[]'); cur.push(text); localStorage.setItem(k, JSON.stringify(cur)); alert('Added to To‑Do'); }} catch(e){{}} }};
      window.noteAdd = function(){{ const el=document.getElementById('note-input'); if(!el) return; const v=el.value.trim(); if(!v) return; const ul=document.getElementById('notes-list'); if(!ul) return; const li=document.createElement('li'); li.textContent=v; ul.appendChild(li); try{{ const k='notes-'+'{esc(date_str)}'; const cur=JSON.parse(localStorage.getItem(k)||'[]'); cur.push(v); localStorage.setItem(k, JSON.stringify(cur)); }}catch(e){{}} el.value=''; }};
      document.addEventListener('DOMContentLoaded', function(){{ apply(load()); try{{ const k='notes-'+'{esc(date_str)}'; const arr=JSON.parse(localStorage.getItem(k)||'[]'); const ul=document.getElementById('notes-list'); if(ul) arr.forEach(t=>{{ const li=document.createElement('li'); li.textContent=t; ul.appendChild(li); }}); }}catch(e){{}} }});
    }})();
  </script>
</head>
<body>
  <a id="top"></a>
  <div class="toolbar">
    <button class="btn" onclick="toggleTheme()">Toggle Dark Mode</button>
  </div>
  <h1>Daily Accomplishments — {esc(date_str)} (window {int(cfg.get('day_start_hour_local', 6)):02d}:00–{('24:00' if int(cfg.get('day_end_hour_local', 24)) == 24 else f"{int(cfg.get('day_end_hour_local', 24)):02d}:00")} CST/CDT)</h1>
  <div class="cards">
    <div class="card"><div class="v">{seconds_to_hhmm(focus_sec)}</div><div class="k">Focus</div></div>
    <div class="card"><div class="v">{seconds_to_hhmm(meetings_sec)}</div><div class="k">Meetings</div></div>
    <div class="card"><div class="v">{appt_n}</div><div class="k">Appointments</div></div>
    <div class="card"><div class="v">{proj_n}</div><div class="k">Projects</div></div>
  </div>
  <div class="toc">
    <a class="chip" href="#exec">Exec</a>
    <a class="chip" href="#next">Next Up</a>
    <a class="chip" href="#proj">Projects</a>
    <a class="chip" href="#gws">GWS</a>
    <a class="chip" href="#browser">Browser</a>
    <a class="chip" href="#apps">Apps</a>
    <a class="chip" href="#windows">Windows</a>
    <a class="chip" href="#notes">Notes</a>
  </div>
  <h2 id="summary">Key Activity Summary <button class="btn" onclick="copyList('key-summary')">Copy Summary</button></h2>
  <ul id="key-summary">
    {key_summary_html}
  </ul>
  <h2>Accomplishments Today</h2>
  <ul>
    {mgr_html}
  </ul>
  <div class="meta">
    <div>Total focused time: <span class="time">{seconds_to_hhmm(agg['total_seconds'])}</span></div>
    <div>Coverage window: {coverage}</div>
  </div>
  <div class="grid">
    <div>
      <h2>By Category</h2>
      <ul>{by_cat_html}</ul>
      <h2>By Project</h2>
      <ul>{by_proj_html}</ul>
      <h2>Google Workspace</h2>
      <h3>By Service</h3>
      <ul>{gws_service_html}</ul>
      <h3>Top Documents</h3>
      <ul>{gws_docs_html}</ul>
      <h2>Browser Highlights</h2>
      <h3>Top Domains (by visits)</h3>
      <ul>
        {''.join(f'<li><strong>{esc(dom)}</strong>: {cnt} visits</li>' for dom, cnt in sorted(agg.get('browser_by_domain', {}).items(), key=lambda x: x[1], reverse=True)[:25]) or '<li>No data</li>'}
      </ul>
      <h3>Top Pages (by visits)</h3>
      <ul>
        {''.join(f'<li>{esc(title)} <span class="muted">({esc(dom)})</span>: {cnt} visits</li>' for dom, title, cnt in agg.get('browser_pages', [])[:10]) or '<li>No data</li>'}
      </ul>
    </div>
    <div>
      <h2>Hourly Focus</h2>
      {hourly_html}
    </div>
  </div>
  <h2>AI Task Suggestions <button class="btn" onclick="copyList('next-list')">Copy</button></h2>
  <ul id="next-list">
    {sugg_html}
  </ul>
  <h2>Next Up <button class="btn" onclick="copyList('next-list')">Copy</button></h2>
  <ul id="next-list">
    {story['next_up'] or '<li>—</li>'}
  </ul>
  <h2>Digital Footprint</h2>
  <h3>Top Apps</h3>
  <table class="ptable"><thead><tr><th>Application</th><th class=rt>Time</th></tr></thead><tbody>{apps_rows}</tbody></table>
  <h3>Top Domains</h3>
  <table class="ptable"><thead><tr><th>Domain</th><th class=rt>Visits</th></tr></thead><tbody>{domain_rows}</tbody></table>
  <h3>Top Windows</h3>
  <details>
    <summary>Show Top Windows ({len(agg.get('by_window', {}))})</summary>
    <table class="ptable"><thead><tr><th>Window/Document</th><th class=rt>Time</th></tr></thead><tbody>{windows_rows}</tbody></table>
  </details>
  <h2 id="notes">Notes <button class="btn" onclick="noteAdd()">+ Add Note</button></h2>
  <input id="note-input" class="input" placeholder="Type a note and press + Add Note" style="margin:6px 0; width:100%;" />
  <ul id="notes-list">
    {''.join(f'<li>{esc(n)}</li>' for n in synthesize_notes(agg, cfg))}
  </ul>
  <details>
    <summary>System & Audit Data</summary>
    <h3>Contact Visits (top)</h3>
    <ul>{cvis_html}</ul>
    <h3>Meetings (today)</h3>
    <ul>{mtg_html}</ul>
    <h3>Slack Booked (checks by you)</h3>
    <ul>{slack_html}</ul>
  </details>
  <h2>Confidence Legend</h2>
  <ul>
    <li>[solid]: high evidence (HubSpot visits well above threshold + meeting keyword)</li>
    <li>[likely]: medium evidence (visits over threshold and/or meeting keyword)</li>
    <li>[weak]: low evidence (borderline signals)</li>
  </ul>
  <div class="foot">Raw log: <code>{esc(str(log_path_for(date_local)))}</code></div>
</body>
</html>
"""

    out = report_html_path_for(date_local)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def try_generate_pdf(html_path: Path) -> Optional[Path]:
    try:
        import shutil
        wk = shutil.which("wkhtmltopdf")
        if not wk:
            print("wkhtmltopdf not found; skipping PDF export.")
            return None
        pdf_path = html_path.with_suffix('.pdf')
        subprocess.run([wk, str(html_path), str(pdf_path)], check=False)
        if pdf_path.exists():
            print(f"PDF written to: {pdf_path}")
            return pdf_path
    except Exception:
        pass
    return None


def aggregate_range(start_date: datetime, end_date: datetime, cfg: dict) -> dict:
    agg_total: Optional[dict] = None
    d = start_date
    while d <= end_date:
        a = aggregate_summary(d, 24, cfg)
        if agg_total is None:
            agg_total = a
        else:
            # Sum numeric dicts
            for k in ["total_seconds"]:
                agg_total[k] = agg_total.get(k, 0) + a.get(k, 0)
            for k in ["by_app","by_window","by_category","by_project","by_token","by_hour","by_workspace","gws_by_service","gws_by_doc","email_by_subject","browser_by_domain"]:
                dst = agg_total.get(k, {})
                for kk, vv in a.get(k, {}).items():
                    dst[kk] = dst.get(kk, 0) + vv
                agg_total[k] = dst
            # Merge arrays
            agg_total.setdefault("browser_pages", []).extend(a.get("browser_pages", []))
            agg_total.setdefault("calendar_events", []).extend(a.get("calendar_events", []))
            agg_total.setdefault("inferred_appointments", []).extend(a.get("inferred_appointments", []))
        d = d + timedelta(days=1)
    if agg_total is None:
        agg_total = aggregate_summary(start_date, 24, cfg)
    agg_total["day_start"] = start_date
    agg_total["cutoff"] = end_date + timedelta(days=1)
    return agg_total


def generate_weekly_html(end_date: Optional[datetime] = None, days: int = 7) -> Path:
    cfg = load_config()
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    end = (end_date or now_tz(CHICAGO_TZ)).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days-1)
    agg = aggregate_range(start, end, cfg)
    # Reuse daily HTML generator bits via story/html list builders
    def esc(s: str) -> str:
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    story = build_story_html_lists(agg, cfg)
    date_str = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weekly Roll-up — {esc(date_str)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; color: #1f2937; }}
    .muted {{ color: #6b7280; }}
    .badge {{ display:inline-block; padding:1px 6px; margin-right:4px; border-radius:10px; font-size:11px; background:#e5e7eb; }}
  </style>
  <meta name="generator" content="ActivityTracker" />
  <meta http-equiv="refresh" content="0; url=#top">
</head>
<body>
  <a id="top"></a>
  <h1>Weekly Roll-up — {esc(date_str)}</h1>
  <div class="muted">{esc(story['headline'])}</div>
  <h2>Executive Summary</h2>
  <ul>{story['exec']}</ul>
  <h2>Next Up</h2>
  <ul>{story['next_up'] or '<li>—</li>'}</ul>
</body>
</html>
"""
    out = REPORT_DIR / (f"weekly-{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


# ----------------------- Scheduler (midnight) --------------------

def seconds_until_next_midnight_chicago(ref: Optional[datetime] = None) -> float:
    tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
    now_local = (ref or now_tz(CHICAGO_TZ)).astimezone(tz)
    # Next midnight is tomorrow at 00:00 local
    tomorrow = (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (tomorrow - now_local).total_seconds()


def run_daemon(poll_seconds: int) -> None:
    ensure_dirs()
    tracker = Tracker(poll_seconds=poll_seconds)

    stop_event = threading.Event()

    def handle_signal(signum, frame):  # type: ignore
        stop_event.set()
        tracker.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Tracking thread
    t = threading.Thread(target=tracker.run, name="activity-tracker", daemon=True)
    t.start()

    # Scheduler loop (generate at midnight)
    try:
        while not stop_event.is_set():
            to_wait = max(1.0, seconds_until_next_midnight_chicago())
            stop_event.wait(to_wait)
            if stop_event.is_set():
                break

            # Cut current session at exactly midnight (Chicago) and generate summary for the prior day
            now_local = now_tz(CHICAGO_TZ)
            # We woke at (or extremely near) midnight; cut at current timestamp
            cut_at = now_local.replace(microsecond=0)

            tracker.split_at(cut_at)

            # Generate yesterday's report (Markdown and HTML) and open HTML
            today_local = now_tz(CHICAGO_TZ).date()
            y = today_local - timedelta(days=1)
            day = datetime(y.year, y.month, y.day)
            md_report = generate_summary_for(day)
            html_report = generate_summary_html_for(day)
            print(f"[ActivityTracker] Generated reports: {md_report} | {html_report}")
            try:
                subprocess.run(["open", str(html_report)], check=False)
            except Exception:
                pass
    finally:
        tracker.flush()


# ----------------------- CLI ------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Privacy-safe activity tracker for macOS.")
    sub = parser.add_subparsers(dest="cmd")

    # Main flags (no subcommand)
    parser.add_argument("--daemon", action="store_true", help="Run tracker and schedule daily midnight summary.")
    parser.add_argument("--summary", metavar="YYYY-MM-DD", help="Generate summary for a specific date.")
    parser.add_argument("--html", action="store_true", help="With --summary, also generate HTML; alone does nothing.")
    parser.add_argument("--cutoff", type=int, help="Override cutoff hour (local) for daily summary (default: config day_end_hour_local)")
    parser.add_argument("--pdf", action="store_true", help="With --summary/--html or weekly, also generate PDF if wkhtmltopdf is available.")
    parser.add_argument("--poll", type=int, default=5, help="Polling interval in seconds (default: 5).")
    parser.add_argument("--idle", type=int, default=300, help="Idle threshold seconds to pause tracking (default: 300). 0 disables idle detection.")
    parser.add_argument("--heartbeat", type=int, default=120, help="Write a session segment at least this often (default: 120s).")

    # label subcommand
    p_label = sub.add_parser("label", help="Add a project rule: pattern -> project")
    p_label.add_argument("--project", required=True, help="Project name for matches.")
    p_label.add_argument("--pattern", required=True, help="Regex to match titles/URLs/domains.")

    # pause/resume/status
    p_pause = sub.add_parser("pause", help="Pause tracking for N minutes")
    p_pause.add_argument("minutes", type=int, nargs="?", default=30, help="Minutes to pause (default 30)")
    sub.add_parser("resume", help="Resume tracking now")
    sub.add_parser("status", help="Show tracker pause status")

    # ping from terminal/editor to provide cwd/repo hint
    p_ping = sub.add_parser("ping", help="Record current working directory (from shell hook)")
    p_ping.add_argument("--cwd", required=True)

    # domain management
    p_dom = sub.add_parser("domain", help="Manage exclude/private domains")
    g = p_dom.add_mutually_exclusive_group(required=True)
    g.add_argument("--private-add")
    g.add_argument("--private-remove")
    g.add_argument("--exclude-add")
    g.add_argument("--exclude-remove")

    # browser diagnostics
    sub.add_parser("browser-profiles", help="List detected Chrome profile folders")
    sub.add_parser("browser-scan", help="Show top browser domains today (respects include filters)")
    sub.add_parser("browser-autodetect", help="Auto-detect the active Chrome profile today and update config")

    # weekly roll-up
    p_week = sub.add_parser("weekly", help="Generate a weekly roll-up ending on the given date (default today)")
    p_week.add_argument("--end", metavar="YYYY-MM-DD", help="Week end date (default: today)")
    p_week.add_argument("--days", type=int, default=7, help="Number of days to include (default 7)")

    # prune old data
    p_prune = sub.add_parser("prune", help="Prune old logs/reports/DB/cache by retention_days (or --days)")
    p_prune.add_argument("--days", type=int, help="Override retention_days in config")

    # view daily in terminal (rich if available)
    p_view = sub.add_parser("view", help="View daily summary in terminal")
    p_view.add_argument("--date", metavar="YYYY-MM-DD", help="Date to view (default today)")

    # suggest rules from unlabeled patterns
    sub.add_parser("suggest", help="Suggest classification rules from unlabeled domains/titles")
    # share sanitized HTML to Desktop
    p_share = sub.add_parser("share", help="Write sanitized HTML copy to Desktop")
    p_share.add_argument("--date", metavar="YYYY-MM-DD", help="Date to share (default today)")

    # Google & HubSpot integrations setup
    sub.add_parser("google-auth", help="Run OAuth flow for Google Calendar API (stores token locally)")
    p_hs = sub.add_parser("hubspot-set-token", help="Save HubSpot private app token to credentials")
    p_hs.add_argument("--token", required=True)
    p_ics_add = sub.add_parser("calendar-add-ics", help="Add a remote ICS URL to integrations.calendar_ics_urls")
    p_ics_add.add_argument("--url", required=True)
    p_ics_add.add_argument("--name", help="Optional label to remember what this is")
    sub.add_parser("calendar-list-ics", help="List configured ICS URLs (redacted)")
    sub.add_parser("hubspot-import-cli-token", help="Import OAuth token from HubSpot CLI (~/.hubspot/config.yml) into credentials")
    p_slack = sub.add_parser("slack-set-token", help="Save Slack token (user or bot) to credentials")
    p_slack.add_argument("--token", required=True)
    sub.add_parser("slack-scan", help="Scan Slack for booked calls in the daily window and print them")

    args = parser.parse_args(argv)

    ensure_dirs()
    # Load config early and keep available for URL capture policy
    global RUNTIME_CFG
    RUNTIME_CFG = load_config()

    # Handle subcommands
    if args.cmd == "label":
        cfg = RUNTIME_CFG or load_config()
        rules = cfg.setdefault("rules", [])
        rules.append({"pattern": args.pattern, "project": args.project})
        try:
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            print(f"Added rule: /{args.pattern}/ -> {args.project}")
        except Exception as e:
            print(f"Failed to write config: {e}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "pause":
        set_paused_minutes(int(args.minutes))
        print(f"Paused until {get_paused_until()}")
        return 0
    if args.cmd == "resume":
        clear_pause()
        print("Resumed (pause cleared)")
        return 0
    if args.cmd == "status":
        pu = get_paused_until()
        if pu and now_tz(CHICAGO_TZ) < pu:
            print(f"Paused until {pu}")
        else:
            print("Active (not paused)")
        return 0
    if args.cmd == "ping":
        record_terminal_ping(args.cwd)
        print("ping recorded")
        return 0
    if args.cmd == "domain":
        cfg = RUNTIME_CFG or load_config()
        changed = False
        if args.private_add:
            lst = cfg.setdefault("private_domains", [])
            if args.private_add not in lst:
                lst.append(args.private_add); changed = True
        if args.private_remove:
            lst = cfg.setdefault("private_domains", [])
            if args.private_remove in lst:
                lst.remove(args.private_remove); changed = True
        if args.exclude_add:
            lst = cfg.setdefault("exclude_domains", [])
            if args.exclude_add not in lst:
                lst.append(args.exclude_add); changed = True
        if args.exclude_remove:
            lst = cfg.setdefault("exclude_domains", [])
            if args.exclude_remove in lst:
                lst.remove(args.exclude_remove); changed = True
        if changed:
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            print("domain list updated")
        else:
            print("no changes")
        return 0
    if args.cmd == "browser-profiles":
        list_browser_profiles()
        return 0
    if args.cmd == "browser-scan":
        scan_browser_today()
        return 0
    if args.cmd == "browser-autodetect":
        name = autodetect_chrome_profile_today()
        if name:
            cfg = RUNTIME_CFG or load_config()
            integ = cfg.setdefault("integrations", {})
            integ["chrome_profiles_include"] = [name]
            cps = set(integ.get("chrome_profiles", []) or [])
            cps.add(name)
            integ["chrome_profiles"] = sorted(cps)
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            print(f"Selected Chrome profile: {name}")
        else:
            print("Could not detect an active profile today.")
        return 0
    
    if args.cmd == "prune":
        cfg = RUNTIME_CFG or load_config()
        days = int(args.days or cfg.get("retention_days", 60))
        prune_old_data(days)
        print(f"Pruned data older than {days} days.")
        return 0

    if args.cmd == "view":
        date_str = args.date or now_tz(CHICAGO_TZ).strftime("%Y-%m-%d")
        try:
            d = parse_date(date_str)
        except ValueError:
            print("Invalid --date format. Use YYYY-MM-DD.", file=sys.stderr)
            return 2
        view_daily_terminal(d)
        return 0

    if args.cmd == "suggest":
        suggest_rules_today()
        return 0

    if args.cmd == "share":
        date_str = args.date or now_tz(CHICAGO_TZ).strftime("%Y-%m-%d")
        try:
            d = parse_date(date_str)
        except ValueError:
            print("Invalid --date format. Use YYYY-MM-DD.", file=sys.stderr)
            return 2
        html_path = report_html_path_for(d)
        if not html_path.exists():
            # generate if missing
            out_html = generate_summary_html_for(d)
            html_path = out_html
        try:
            raw = html_path.read_text(encoding='utf-8')
            # sanitize raw log paths
            import re
            cleaned = re.sub(r"Raw log: <code>.*?</code>", "Shared copy", raw)
            # replace absolute user paths
            cleaned = cleaned.replace(str(Path.home()), "~")
            dest = Path.home()/"Desktop"/f"ActivityReport-{date_str}.html"
            dest.write_text(cleaned, encoding='utf-8')
            print(f"Wrote sanitized report to: {dest}")
            try:
                subprocess.run(["open", str(dest)], check=False)
            except Exception:
                pass
            return 0
        except Exception as e:
            print(f"Failed to write shareable copy: {e}", file=sys.stderr)
            return 1

    if args.cmd == "google-auth":
        ok = google_auth_flow()
        return 0 if ok else 1

    if args.cmd == "hubspot-set-token":
        try:
            CRED_DIR.mkdir(parents=True, exist_ok=True)
            HUBSPOT_TOKEN_PATH.write_text(args.token.strip(), encoding='utf-8')
            print(f"Saved token to: {HUBSPOT_TOKEN_PATH}")
            return 0
        except Exception as e:
            print(f"Failed to save token: {e}", file=sys.stderr)
            return 1

    if args.cmd == "hubspot-import-cli-token":
        t = hubspot_token()
        if not t:
            print("No token found in env/credentials/HubSpot CLI config.")
            return 1
        try:
            HUBSPOT_TOKEN_PATH.write_text(t, encoding='utf-8')
            print(f"Imported token into: {HUBSPOT_TOKEN_PATH}")
            return 0
        except Exception as e:
            print(f"Failed to import token: {e}", file=sys.stderr)
            return 1

    if args.cmd == "calendar-add-ics":
        cfg = RUNTIME_CFG or load_config()
        integ = cfg.setdefault("integrations", {})
        urls = integ.setdefault("calendar_ics_urls", [])
        if args.url not in urls:
            urls.append(args.url)
            try:
                CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                label = args.name or "(no label)"
                print(f"Added ICS URL ({label})")
            except Exception as e:
                print(f"Failed to save ICS URL: {e}", file=sys.stderr)
                return 1
        else:
            print("ICS URL already present")
        return 0

    if args.cmd == "calendar-list-ics":
        cfg = RUNTIME_CFG or load_config()
        urls = (cfg.get("integrations", {}).get("calendar_ics_urls") or [])
        print("ICS URLs:")
        for u in urls:
            print(f"- {redact_ics_url(u)}")
        return 0

    if args.cmd == "slack-set-token":
        try:
            CRED_DIR.mkdir(parents=True, exist_ok=True)
            SLACK_TOKEN_PATH.write_text(args.token.strip(), encoding='utf-8')
            print(f"Saved Slack token to: {SLACK_TOKEN_PATH}")
            return 0
        except Exception as e:
            print(f"Failed to save Slack token: {e}", file=sys.stderr)
            return 1

    if args.cmd == "slack-scan":
        cfg = RUNTIME_CFG or load_config()
        tz = CHICAGO_TZ or datetime.now().astimezone().tzinfo
        today = now_tz(CHICAGO_TZ).astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        items = slack_fetch_bookedcalls(today, today + timedelta(hours=24), cfg)
        if not items:
            print("No Slack booked calls found today or token/channel not configured.")
            return 0
        print("Slack booked calls detected:")
        for it in items:
            print(f"- [{it.get('channel')}] {it.get('text')} ({it.get('emoji')})")
        return 0

    if args.summary:
        try:
            d = parse_date(args.summary)
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
            return 2
        cutoff = int(args.cutoff) if args.cutoff is not None else int((RUNTIME_CFG or load_config()).get("day_end_hour_local", 24))
        out = generate_summary_for(d, cutoff)
        print(f"Summary written to: {out}")
        if args.html:
            out_html = generate_summary_html_for(d, cutoff)
            print(f"HTML summary written to: {out_html}")
            if args.pdf:
                try_generate_pdf(out_html)
            try:
                subprocess.run(["open", str(out_html)], check=False)
            except Exception:
                pass
        return 0

    if args.daemon:
        # Construct tracker with CLI options by passing via environment variables
        # (daemon creates its own Tracker). For simplicity, override defaults globally here.
        Tracker.__init__  # no-op to satisfy linters
        def make_tracker():
            return Tracker(poll_seconds=args.poll, idle_threshold=args.idle, heartbeat_seconds=args.heartbeat)
        # Monkey-patch run_daemon to use our constructed tracker
        # Simpler: directly run a tracker with scheduler thread here
        ensure_dirs()
        tracker = make_tracker()
        stop_event = threading.Event()

        def handle_signal(signum, frame):  # type: ignore
            stop_event.set()
            tracker.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        t = threading.Thread(target=tracker.run, name="activity-tracker", daemon=True)
        t.start()

        try:
            while not stop_event.is_set():
                to_wait = max(1.0, seconds_until_next_midnight_chicago())
                stop_event.wait(to_wait)
                if stop_event.is_set():
                    break
                now_local = now_tz(CHICAGO_TZ)
                cut_at = now_local.replace(microsecond=0)
                tracker.split_at(cut_at)
                today_local = now_tz(CHICAGO_TZ).date()
                y = today_local - timedelta(days=1)
                day = datetime(y.year, y.month, y.day)
                md_report = generate_summary_for(day)
                html_report = generate_summary_html_for(day)
                print(f"[ActivityTracker] Generated reports: {md_report} | {html_report}")
                try:
                    subprocess.run(["open", str(html_report)], check=False)
                except Exception:
                    pass
        finally:
            tracker.flush()
        return 0

    if args.cmd == "weekly":
        end = None
        if args.end:
            try:
                end = parse_date(args.end)
            except ValueError:
                print("Invalid --end date format. Use YYYY-MM-DD.", file=sys.stderr)
                return 2
        out = generate_weekly_html(end_date=end, days=args.days)
        print(f"Weekly HTML written to: {out}")
        if args.pdf:
            try_generate_pdf(out)
        try:
            subprocess.run(["open", str(out)], check=False)
        except Exception:
            pass
        return 0

    # Default: run tracker interactively (foreground) without scheduler
    print("Running tracker (no scheduler). Press Ctrl+C to stop.")
    tracker = Tracker(poll_seconds=args.poll, idle_threshold=args.idle, heartbeat_seconds=args.heartbeat)

    def handle_signal(signum, frame):  # type: ignore
        tracker.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        tracker.run()
    finally:
        tracker.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
