#!/usr/bin/env python3
"""
Import per-app usage from macOS Screen Time (KnowledgeC) for a given date and
optionally merge it into ActivityReport-YYYY-MM-DD.json.

Notes
- Requires Full Disk Access (FDA) for Terminal (or your shell) to read
  ~/Library/Application Support/Knowledge/knowledgeC.db
- Tries multiple query patterns as schema varies across macOS versions.

Usage
  python3 scripts/import_screentime.py --date YYYY-MM-DD --update-report \
      --repo ~/Desktop/DailyAccomplishments
"""

from __future__ import annotations

import os
import re
import sys
import json
import math
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple


KNOWLEDGEC = Path.home() / "Library/Application Support/Knowledge/knowledgeC.db"
LOCAL_TZ = ZoneInfo("America/Chicago")


@dataclass
class AppUsage:
    bundle_id: str
    app: str
    start: datetime
    end: datetime

    @property
    def seconds(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds())




def _union_foreground_minutes(usages: list[AppUsage]) -> int:
    """Compute foreground minutes by unioning overlapping intervals.

    Raw Screen Time segments can overlap or be duplicated across streams.
    Foreground time cannot exceed 24h/day, so we merge intervals first.
    """
    if not usages:
        return 0

    intervals = sorted([(u.start, u.end) for u in usages if u.end > u.start], key=lambda x: x[0])
    if not intervals:
        return 0

    merged = []
    cur_s, cur_e = intervals[0]
    for s2, e2 in intervals[1:]:
        if s2 <= cur_e:
            if e2 > cur_e:
                cur_e = e2
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s2, e2
    merged.append((cur_s, cur_e))

    total_seconds = sum((e - s).total_seconds() for s, e in merged)
    # round up to minutes, cap to 24h
    import math
    mins = int(math.ceil(total_seconds / 60.0))
    return max(0, min(24 * 60, mins))
def _copy_db_safely(src: Path) -> Optional[Path]:
    try:
        if not src.exists():
            return None
        tmp = Path(tempfile.mkstemp(suffix=".db")[1])
        os.close(0) if False else None  # silence linters
        shutil.copy2(src, tmp)
        return tmp
    except Exception:
        return None


def _ts_from_apple_epoch(val: float) -> datetime:
    # Apple epoch: 2001-01-01 00:00:00 UTC
    # Convert to aware UTC, then to local timezone for correct day/hour bucketing
    dt_utc = datetime(2001, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=float(val))
    return dt_utc.astimezone(LOCAL_TZ)


def _within_day(start: datetime, end: datetime, day0: datetime, day1: datetime) -> Tuple[datetime, datetime]:
    if start < day0:
        start = day0
    if end > day1:
        end = day1
    return start, end


def query_app_usage(db: Path, date_str: str) -> List[AppUsage]:
    # Use local timezone day bounds
    day0 = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    day1 = day0 + timedelta(days=1)
    results: List[AppUsage] = []

    if not db.exists():
        return results

    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    # Candidate queries across macOS versions
    queries = [
        # modern stream: /app/usage with bundle in ZVALUESTRING
        (
            "/app/usage",
            """
            SELECT
              ZOBJECT.ZVALUESTRING as bundle,
              ZOBJECT.ZSTARTDATE as start,
              ZOBJECT.ZENDDATE as end
            FROM ZOBJECT
            WHERE ZOBJECT.ZSTREAMNAME = '/app/usage'
              AND ZOBJECT.ZVALUESTRING IS NOT NULL
              AND ZOBJECT.ZSTARTDATE >= ? AND ZOBJECT.ZSTARTDATE < ?
            """,
        ),
        # runningboard process snapshots with bundle id in value string
        (
            "runningboard_value",
            """
            SELECT
              ZOBJECT.ZVALUESTRING as bundle,
              ZOBJECT.ZSTARTDATE as start,
              ZOBJECT.ZENDDATE as end
            FROM ZOBJECT
            WHERE ZOBJECT.ZSTREAMNAME = 'com.apple.runningboard.process'
              AND ZOBJECT.ZVALUESTRING IS NOT NULL
              AND ZOBJECT.ZSTARTDATE >= ? AND ZOBJECT.ZSTARTDATE < ?
            """,
        ),
        # runningboard with structured metadata bundle id
        (
            "runningboard_meta",
            """
            SELECT
              ZSTRUCTUREDMETADATA.ZBUNDLEID as bundle,
              ZOBJECT.ZSTARTDATE as start,
              ZOBJECT.ZENDDATE as end
            FROM ZOBJECT
            JOIN ZSTRUCTUREDMETADATA ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
            WHERE ZOBJECT.ZSTREAMNAME = 'com.apple.runningboard.process'
              AND ZSTRUCTUREDMETADATA.ZBUNDLEID IS NOT NULL
              AND ZOBJECT.ZSTARTDATE >= ? AND ZOBJECT.ZSTARTDATE < ?
            """,
        ),
        # older schema: application usage stream
        (
            "application_usage",
            """
            SELECT
              ZOBJECT.ZVALUESTRING as bundle,
              ZOBJECT.ZSTARTDATE as start,
              ZOBJECT.ZENDDATE as end
            FROM ZOBJECT
            WHERE ZOBJECT.ZSTREAMNAME = 'com.apple.applicationusage.state'
              AND ZOBJECT.ZVALUESTRING IS NOT NULL
              AND ZOBJECT.ZSTARTDATE >= ? AND ZOBJECT.ZSTARTDATE < ?
            """,
        ),
    ]

    # Convert day bounds to Apple epoch seconds (2001)
    apple_epoch_utc = datetime(2001, 1, 1, tzinfo=timezone.utc)
    # Convert local bounds to UTC seconds for DB filter
    day0_apple = (day0.astimezone(timezone.utc) - apple_epoch_utc).total_seconds()
    day1_apple = (day1.astimezone(timezone.utc) - apple_epoch_utc).total_seconds()

    for name, q in queries:
        try:
            cur.execute(q, (day0_apple, day1_apple))
            rows = cur.fetchall()
        except Exception:
            rows = []
        if rows:
            for bundle, start, end in rows:
                try:
                    start_dt = _ts_from_apple_epoch(start)
                    end_dt = _ts_from_apple_epoch(end)
                    start_dt, end_dt = _within_day(start_dt, end_dt, day0, day1)
                    if end_dt > start_dt and bundle:
                        results.append(AppUsage(bundle_id=str(bundle), app=str(bundle), start=start_dt, end=end_dt))
                except Exception:
                    continue
            break  # prefer first successful query

    conn.close()
    return results


def categorize_app(bundle_or_name: str) -> str:
    s = bundle_or_name.lower()
    if 'private' in s:
        return "Private"
    if any(x in s for x in ["code", "vscode", "terminal", "pycharm", "intellij", "xcode"]):
        return "Coding"
    if any(x in s for x in ["slack", "messages", "mail", "gmail", "outlook"]):
        return "Communication"
    if any(x in s for x in ["zoom", "teams", "meet."]):
        return "Meetings"
    if any(x in s for x in ["docs", "sheets", "notion", "word", "excel"]):
        return "Docs"
    if any(x in s for x in ["chrome", "safari", "firefox", "browser"]):
        return "Research"
    return "Other"


def friendly_app_name(bundle_id: str) -> str:
    b = (bundle_id or '').lower()
    mapping = {
        'com.google.chrome': 'Google Chrome',
        'com.apple.safari': 'Safari',
        'org.mozilla.firefox': 'Firefox',
        'com.microsoft.vscode': 'VS Code',
        'com.apple.terminal': 'Terminal',
        'com.apple.mobileSMS'.lower(): 'Messages',
        'com.apple.mail': 'Mail',
        'com.apple.textedit': 'TextEdit',
        'com.apple.finder': 'Finder',
        'com.tinyspeck.slackmacgap': 'Slack',
        'com.apple.systempreferences': 'System Settings',
    }
    for key, val in mapping.items():
        if key in b:
            return val
    return bundle_id


def load_privacy_config(repo_path: Path) -> Dict[str, str]:
    defaults = {
        "mode": "exclude",
        "blocked_domains": [],  # not used here
        "blocked_keywords": [
            "porn", "xxx", "nsfw", "onlyfans", "xvideos", "xnxx",
            "redtube", "youporn", "pornhub", "brazzers", "camgirl",
            "camwhores", "hentai"
        ],
    }
    candidates = [repo_path / 'config.json', Path.home() / 'DailyAccomplishments' / 'config.json']
    for c in candidates:
        try:
            if c.exists():
                cfg = json.loads(c.read_text())
                p = cfg.get('privacy') or {}
                return {
                    "mode": p.get('mode', defaults['mode']),
                    "blocked_domains": p.get('blocked_domains', defaults['blocked_domains']),
                    "blocked_keywords": p.get('blocked_keywords', defaults['blocked_keywords']),
                }
        except Exception:
            continue
    return defaults


def is_unsavory_app(name_or_bundle: str, privacy: Dict[str, str]) -> bool:
    s = (name_or_bundle or '').lower()
    return any(kw in s for kw in (privacy.get('blocked_keywords') or []))


def minutes_to_time_str(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def add_hhmm(a: str, minutes: int) -> str:
    if not a or ":" not in a:
        base = 0
    else:
        try:
            hh, mm = a.split(":")
            base = int(hh) * 60 + int(mm)
        except Exception:
            base = 0
    return minutes_to_time_str(base + minutes)


def merge_into_activity_report(date_str: str, usages: List[AppUsage], repo_path: Path) -> Path:
    report_file = repo_path / f"ActivityReport-{date_str}.json"
    if report_file.exists():
        report = json.loads(report_file.read_text())
    else:
        report = {
            "source_file": f"ActivityReport-{date_str}.json",
            "date": date_str,
            "title": f"Daily Accomplishments — {date_str}",
            "overview": {
                "focus_time": "00:00",
                "coverage_window": "",
            },
            "browser_highlights": {"top_domains": [], "top_pages": []},
            "by_category": {},
            "hourly_focus": [],
            "timeline": [],
            "deep_work_blocks": [],
        }

    if not isinstance(report.get("timeline"), list):
        report["timeline"] = []
    if not isinstance(report.get("deep_work_blocks"), list):
        report["deep_work_blocks"] = []
    ov = report.setdefault("overview", {})
    if "focus_time" not in ov:
        ov["focus_time"] = "00:00"
    if "coverage_window" not in ov:
        ov["coverage_window"] = ""
    if not isinstance(report.get("browser_highlights"), dict):
        report["browser_highlights"] = {"top_domains": [], "top_pages": []}
    else:
        bh = report["browser_highlights"]
        if not isinstance(bh.get("top_domains"), list):
            bh["top_domains"] = []
        if not isinstance(bh.get("top_pages"), list):
            bh["top_pages"] = []

    # Hourly minutes and top apps from app usage
    hourly = [0] * 24
    by_cat_minutes: Dict[str, int] = {}
    app_minutes: Dict[str, int] = {}
    if usages:
        day0 = datetime.strptime(date_str, "%Y-%m-%d")
        for u in usages:
            start = u.start
            end = u.end
            while start < end:
                next_hour = (start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
                segment_end = min(end, next_hour)
                dur = int((segment_end - start).total_seconds() // 60)
                if dur > 0:
                    hourly[start.hour] += dur
                    cat = categorize_app(u.bundle_id or u.app)
                    by_cat_minutes[cat] = by_cat_minutes.get(cat, 0) + dur
                    # aggregate top apps by friendly name
                    app_label = friendly_app_name(u.bundle_id or u.app)
                    app_minutes[app_label] = app_minutes.get(app_label, 0) + dur
                start = segment_end

    # Merge categories using union semantics (avoid additive double counting)
    def parse_hhmm(s: str) -> int:
        try:
            hh, mm = str(s or '00:00').split(':')
            return int(hh) * 60 + int(mm)
        except Exception:
            return 0

    # Prefer Screen Time totals when report focus_time is missing or clearly lower.
    if app_minutes:
        total_usage_minutes = sum(app_minutes.values())
        ov = report.setdefault("overview", {})
        existing_focus = parse_hhmm(ov.get("focus_time", "00:00"))
        if total_usage_minutes > existing_focus:
            ov["focus_time"] = minutes_to_time_str(total_usage_minutes)
    existing = report.get('by_category') or {}
    # If existing looks clearly corrupted (sum >> 24h), reset and prefer Screen Time
    existing_total = sum(parse_hhmm(v) for v in existing.values())
    if existing_total > 24 * 60:
        merged = {}
    else:
        merged = dict(existing)
    for cat, mins in by_cat_minutes.items():
        prev = parse_hhmm(merged.get(cat, '00:00'))
        merged[cat] = minutes_to_time_str(max(prev, mins))
    report['by_category'] = merged

    # Merge hourly_focus (union per hour, cap at 60)
    # Merge hourly_focus as union per hour (keep existing collector minutes, add Screen Time where higher)
    existing_hf = report.get('hourly_focus') or [{"hour": h, "time": "00:00", "pct": "0%"} for h in range(24)]
    merged_hf = []
    for h in range(24):
        # Existing minutes from report (collector)
        cur_m = 0
        try:
            t = str(existing_hf[h].get('time', '00:00'))
            hh, mm = t.split(':')
            cur_m = int(hh) * 60 + int(mm)
        except Exception:
            cur_m = 0
        st_m = min(60, max(0, int(hourly[h])))
        merged_m = min(60, max(cur_m, st_m))
        merged_hf.append({"hour": h, "time": minutes_to_time_str(merged_m), "pct": "0%"})
    report['hourly_focus'] = merged_hf

    # Merge top apps (HH:MM strings)
    if app_minutes:
        top = sorted(app_minutes.items(), key=lambda x: -x[1])[:12]
        report['top_apps'] = {name: minutes_to_time_str(mins) for name, mins in top}

    # Derive deep work blocks (>='+str(25)+' min continuous) from usage segments
    def to_min(dt: datetime) -> int:
        return dt.hour * 60 + dt.minute

    def fmt_hhmm(m: int) -> str:
        return f"{m//60:02d}:{m%60:02d}"

    allowed_cats = {"Coding", "Research", "Docs", "Private"}
    segments = []
    for u in usages:
        cat = categorize_app(u.bundle_id or u.app)
        segments.append({
            'start': u.start,
            'end': u.end,
            'cat': cat,
            'app': friendly_app_name(u.bundle_id or u.app)
        })
    segments.sort(key=lambda s: s['start'])

    deep_blocks = []
    cur_start = None
    cur_end = None
    cur_minutes = 0
    cur_cat_totals: Dict[str, int] = {}
    cur_app_totals: Dict[str, int] = {}

    def flush_block():
        nonlocal cur_start, cur_end, cur_minutes, cur_cat_totals, cur_app_totals
        if cur_start and cur_end and cur_minutes >= 25:
            label_cat = max(cur_cat_totals.items(), key=lambda x: x[1])[0] if cur_cat_totals else 'Other'
            label_app = max(cur_app_totals.items(), key=lambda x: x[1])[0] if cur_app_totals else 'Unknown'
            deep_blocks.append({
                'start': fmt_hhmm(to_min(cur_start)),
                'end': fmt_hhmm(to_min(cur_end)),
                'minutes': cur_minutes,
                'category': label_cat,
                'label': label_app
            })
        cur_start = None
        cur_end = None
        cur_minutes = 0
        cur_cat_totals = {}
        cur_app_totals = {}

    # Build blocks: contiguous segments with small gaps (<=5 min) and allowed categories
    last_end = None
    for s in segments:
        if s['cat'] not in allowed_cats:
            flush_block()
            last_end = None
            continue
        seg_mins = max(0, int((s['end'] - s['start']).total_seconds() // 60))
        if seg_mins == 0:
            continue
        if cur_start is None:
            cur_start = s['start']
            cur_end = s['end']
            cur_minutes = seg_mins
            cur_cat_totals[s['cat']] = cur_cat_totals.get(s['cat'], 0) + seg_mins
            cur_app_totals[s['app']] = cur_app_totals.get(s['app'], 0) + seg_mins
        else:
            gap = 0 if last_end is None else int((s['start'] - last_end).total_seconds() // 60)
            if gap <= 5:
                # continue block
                cur_end = s['end']
                cur_minutes += seg_mins
                cur_cat_totals[s['cat']] = cur_cat_totals.get(s['cat'], 0) + seg_mins
                cur_app_totals[s['app']] = cur_app_totals.get(s['app'], 0) + seg_mins
            else:
                flush_block()
                cur_start = s['start']
                cur_end = s['end']
                cur_minutes = seg_mins
                cur_cat_totals = {s['cat']: seg_mins}
                cur_app_totals = {s['app']: seg_mins}
        last_end = s['end']
    flush_block()

    if deep_blocks:
        # Keep top 8 blocks by minutes
        deep_blocks.sort(key=lambda x: -x['minutes'])
        report['deep_work'] = deep_blocks[:8]

    # Derive meeting intervals from Screen Time segments categorized as 'Meetings',
    # and heuristically detect Slack Huddles (long contiguous Slack foreground usage).
    # This provides overlay ranges when dedicated calendar data is absent.
    try:
        def merge_intervals(items, gap_limit_min=5):
            items = sorted(items, key=lambda s: s['start'])
            out = []
            cur_s = None
            cur_e = None
            last = None
            for it in items:
                if cur_s is None:
                    cur_s, cur_e = it['start'], it['end']
                    last = it['end']
                else:
                    gap = int((it['start'] - last).total_seconds() // 60)
                    if gap <= gap_limit_min:
                        cur_e = max(cur_e, it['end'])
                    else:
                        out.append((cur_s, cur_e))
                        cur_s, cur_e = it['start'], it['end']
                    last = it['end']
            if cur_s and cur_e:
                out.append((cur_s, cur_e))
            return out

        # Zoom/Teams explicit 'Meetings' category
        meet_raw = [s for s in segments if s.get('cat') == 'Meetings']
        merged_meet = merge_intervals(meet_raw)

        # Heuristic: Slack Huddles — long contiguous Slack usage (>= 15 min), small gaps allowed
        slack_raw = [s for s in segments if (s.get('app') or '').lower() == 'slack']
        merged_slack = merge_intervals(slack_raw, gap_limit_min=3)
        slack_meet = [(a, b) for (a, b) in merged_slack if int((b - a).total_seconds() // 60) >= 15]

        # Combine and normalize
        combined = sorted(merged_meet + slack_meet, key=lambda x: x[0])
        # Merge overlaps between the two sets
        normalized = []
        for s,e in combined:
            if not normalized:
                normalized.append([s,e])
            else:
                ps,pe = normalized[-1]
                if s <= pe:
                    normalized[-1][1] = max(pe, e)
                else:
                    normalized.append([s,e])

        if normalized:
            def fmt_dt(dt: datetime) -> str:
                return f"{dt.hour:02d}:{dt.minute:02d}"
            mt = [{
                'name': 'Meeting',
                'time': f"{fmt_dt(a)}–{fmt_dt(b)}"
            } for a, b in normalized if b > a]
            dbg = report.setdefault('debug_appointments', {})
            dbg['meetings_today'] = mt
    except Exception:
        pass

    # Update overview focus_time and meetings_time heuristically from Screen Time
    # We prefer not to double-count other sources; take the max of existing and derived.
    def parse_hhmm(s: str) -> int:
        try:
            hh, mm = str(s or '00:00').split(':')
            return int(hh) * 60 + int(mm)
        except Exception:
            return 0
    if usages:
        ov = report.setdefault('overview', {})
        # Derive Screen Time minutes by category we just calculated (avoid double counting existing data)
        st_meeting_mins = int(by_cat_minutes.get('Meetings', 0))
        st_focus_mins = int(sum(v for k, v in by_cat_minutes.items() if k != 'Meetings'))

        # Update focus_time to at least Screen Time focus minutes
        cur_focus_mins = parse_hhmm(ov.get('focus_time', '00:00'))
        if st_focus_mins > cur_focus_mins:
            ov['focus_time'] = minutes_to_time_str(st_focus_mins)

        # Update meetings_time to at least Screen Time meetings minutes
        cur_meet_mins = parse_hhmm(ov.get('meetings_time', '00:00'))
        if st_meeting_mins > cur_meet_mins:
            ov['meetings_time'] = minutes_to_time_str(st_meeting_mins)

    # Merge coverage window
    def parse_cov(s: str) -> Tuple[Optional[int], Optional[int]]:
        m = re.findall(r"(\d{2}:\d{2})", s or "")
        if len(m) >= 2:
            def to_min(x):
                p = x.split(":"); return int(p[0])*60+int(p[1])
            return to_min(m[0]), to_min(m[1])
        return (None, None)

    def fmt_cov(a: int, b: int) -> str:
        def f(m):
            return f"{m//60:02d}:{m%60:02d}"
        return f"{f(a)}–{f(b)}"

    if usages:
        cov_start = min(u.start for u in usages)
        cov_end = max(u.end for u in usages)
        u_start = cov_start.hour * 60 + cov_start.minute
        u_end = cov_end.hour * 60 + cov_end.minute
        ov = report.setdefault('overview', {})
        e_start, e_end = parse_cov(ov.get('coverage_window', ''))
        if e_start is None or e_end is None:
            ov['coverage_window'] = fmt_cov(u_start, u_end)
        else:
            ov['coverage_window'] = fmt_cov(min(e_start, u_start), max(e_end, u_end))

    # Executive summary note
    exec_sum = report.setdefault('executive_summary', [])
    if usages:
        total_min = _union_foreground_minutes(usages)
        summary = f"Screen Time: ~{total_min} min foreground app usage"
        if summary not in exec_sum:
            exec_sum.append(summary)

    report_file.write_text(json.dumps(report, indent=2))
    print(f"Updated {report_file}")
    return report_file


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Import Screen Time (KnowledgeC) app usage")
    ap.add_argument("--date", required=False, help="YYYY-MM-DD; defaults to today")
    ap.add_argument("--db", help="Path to knowledgeC.db", default=str(KNOWLEDGEC))
    ap.add_argument("--update-report", action="store_true", help="Merge into ActivityReport JSON")
    ap.add_argument("--repo", default=os.path.expanduser("~/Desktop/DailyAccomplishments"))
    args = ap.parse_args()

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    src = Path(args.db)
    tmp = _copy_db_safely(src)
    if not tmp:
        print("Could not access knowledgeC.db. Grant Full Disk Access to Terminal and retry.")
        print("System Settings > Privacy & Security > Full Disk Access > enable Terminal")
        sys.exit(2)

    try:
        usages = query_app_usage(tmp, date_str)
    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}")
        print("Likely TCC/FDA issue. Grant Full Disk Access to Terminal and retry.")
        sys.exit(2)
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass

    print(f"Found {len(usages)} usage records for {date_str}")
    total_min = _union_foreground_minutes(usages)
    print(f"Approx foreground minutes: ~{total_min}")
    if usages[:5]:
        print("Sample:")
        for u in usages[:5]:
            print(f"  {u.bundle_id} {u.start.strftime('%H:%M')}–{u.end.strftime('%H:%M')} ({int(math.ceil(u.seconds/60))}m)")

    if args.update_report:
        repo = Path(args.repo)
        privacy = load_privacy_config(repo)
        filtered: List[AppUsage] = []
        for u in usages:
            label = u.bundle_id or u.app
            if is_unsavory_app(label, privacy):
                if privacy.get('mode') == 'anonymize':
                    filtered.append(AppUsage(bundle_id='private', app='Private', start=u.start, end=u.end))
                else:
                    continue
            else:
                filtered.append(u)
        merge_into_activity_report(date_str, filtered, repo)


if __name__ == "__main__":
    main()
