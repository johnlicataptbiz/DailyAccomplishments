#!/usr/bin/env python3
"""
Import meetings from an ICS calendar file for a given date and merge into
ActivityReport-YYYY-MM-DD.json as debug_appointments.meetings_today.

No external dependencies; handles common DTSTART/DTEND formats:
  - DTSTART:20251202T170000Z
  - DTSTART;TZID=America/Chicago:20251202T110000

Assumptions:
  - If TZID is present, treat timestamp as local to that TZID. If absent and ends
    with 'Z', treat as UTC and convert to LOCAL_TZ.
  - Otherwise, treat as LOCAL_TZ naive local time.

Usage:
  python3 scripts/import_calendar_ics.py --date YYYY-MM-DD --ics /path/to/calendar.ics \
      --update-report --repo ~/Desktop/DailyAccomplishments
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Chicago")


def parse_ics_datetime(line: str, tzid: str | None) -> datetime | None:
    # Extract raw timestamp (after ':')
    if ':' not in line:
        return None
    raw = line.split(':', 1)[1].strip()
    # Normalize seconds
    fmt_candidates = ["%Y%m%dT%H%M%S", "%Y%m%dT%H%M"]
    if raw.endswith('Z'):
        raw_noz = raw[:-1]
        for fmt in fmt_candidates:
            try:
                dt = datetime.strptime(raw_noz, fmt).replace(tzinfo=timezone.utc)
                return dt.astimezone(LOCAL_TZ)
            except ValueError:
                pass
        return None
    # Has TZID; treat as local to TZID
    if tzid:
        tz = None
        try:
            tz = ZoneInfo(tzid)
        except Exception:
            tz = LOCAL_TZ
        for fmt in fmt_candidates:
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=tz).astimezone(LOCAL_TZ)
            except ValueError:
                pass
        return None
    # No Z and no TZID: assume local time
    for fmt in fmt_candidates:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=LOCAL_TZ)
        except ValueError:
            pass
    return None


def load_meetings_from_ics(ics_path: Path, day: datetime) -> list[tuple[datetime, datetime, str]]:
    if not ics_path.exists():
        return []
    text = ics_path.read_text(errors='ignore')
    events = []
    for block in re.split(r"\nBEGIN:VEVENT\n", text)[1:]:
        chunk = block.split("\nEND:VEVENT", 1)[0]
        tzid = None
        m = re.search(r"^DTSTART(;TZID=([^:\n]+))?:.*$", chunk, re.MULTILINE)
        n = re.search(r"^DTEND(;TZID=([^:\n]+))?:.*$", chunk, re.MULTILINE)
        s = re.search(r"^SUMMARY:(.*)$", chunk, re.MULTILINE)
        if m:
            tzid = m.group(2) or None
            dt_start = parse_ics_datetime(m.group(0), tzid)
        else:
            dt_start = None
        if n:
            tzid2 = n.group(2) or tzid
            dt_end = parse_ics_datetime(n.group(0), tzid2)
        else:
            dt_end = None
        title = (s.group(1).strip() if s else 'Meeting')
        if dt_start and dt_end and dt_end > dt_start:
            # Keep events that intersect the target local day
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            if not (dt_end <= day_start or dt_start >= day_end):
                a = max(dt_start, day_start)
                b = min(dt_end, day_end)
                events.append((a, b, title))
    return events


def merge_into_report(repo: Path, date_str: str, meetings: list[tuple[datetime, datetime, str]]):
    report_path = repo / f"ActivityReport-{date_str}.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
    else:
        report = {"date": date_str}

    def fmt(dt: datetime) -> str:
        return f"{dt.hour:02d}:{dt.minute:02d}"

    # Build mt list
    mt = [{"name": title, "time": f"{fmt(a)}–{fmt(b)}"} for a, b, title in meetings]

    # Merge with any existing meetings_today; union overlapping
    prev = report.get('debug_appointments', {}).get('meetings_today', [])
    def parse_range(r: str):
        parts = re.split(r"[–—-]", r.replace(' ', ''))
        if len(parts) != 2:
            return None
        def to_min(s):
            h, m = s.split(':'); return int(h)*60+int(m)
        return to_min(parts[0]), to_min(parts[1])

    intervals = []
    for item in prev:
        rng = parse_range(item.get('time', ''))
        if rng:
            s, e = rng; intervals.append((s, e))
    for a, b, _ in meetings:
        intervals.append((a.hour*60+a.minute, b.hour*60+b.minute))
    intervals.sort()
    merged = []
    for s, e in intervals:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)
    # Back to mt list
    final = [{"name": "Meeting", "time": f"{s//60:02d}:{s%60:02d}–{e//60:02d}:{e%60:02d}"} for s, e in merged]
    dbg = report.setdefault('debug_appointments', {})
    dbg['meetings_today'] = final

    report_path.write_text(json.dumps(report, indent=2))
    print(f"Updated {report_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=False)
    ap.add_argument('--ics', required=False)
    ap.add_argument('--update-report', action='store_true')
    ap.add_argument('--repo', default=str(Path.home() / 'Desktop' / 'DailyAccomplishments'))
    args = ap.parse_args()

    date_str = args.date or datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
    day = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=LOCAL_TZ)
    ics_path = Path(args.ics) if args.ics else (Path(args.repo) / 'credentials' / 'calendar.ics')

    meetings = load_meetings_from_ics(ics_path, day)
    print(f"Found {len(meetings)} ICS meetings for {date_str}")
    if args.update_report:
        merge_into_report(Path(args.repo), date_str, meetings)

if __name__ == '__main__':
    main()

