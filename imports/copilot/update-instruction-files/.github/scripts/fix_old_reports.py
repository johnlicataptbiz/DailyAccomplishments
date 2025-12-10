#!/usr/bin/env python3
"""Backfill missing `overview.focus_time` and minimal overview fields for older reports.

Usage: python3 .github/scripts/fix_old_reports.py 2025-11-27 2025-11-28
"""
import sys
import json
from pathlib import Path


def parse_hhmm(s):
    if not s or not isinstance(s, str):
        return 0
    parts = s.split(":")
    if len(parts) != 2:
        return 0
    try:
        h = int(parts[0])
        m = int(parts[1])
        return h * 60 + m
    except Exception:
        return 0


def fmt_hhmm(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def fix_report(path: Path):
    j = json.loads(path.read_text())
    # compute sum of hourly_focus times
    total_min = 0
    hf = j.get("hourly_focus", [])
    for item in hf:
        if isinstance(item, dict) and "time" in item:
            total_min += parse_hhmm(item.get("time"))
        elif isinstance(item, str):
            total_min += parse_hhmm(item)
        elif isinstance(item, (int, float)):
            # assume minutes
            total_min += int(item)

    overview = j.get("overview", {})
    if "focus_time" not in overview:
        overview["focus_time"] = fmt_hhmm(total_min)
    if "meetings_time" not in overview:
        overview["meetings_time"] = overview.get("meetings_time", "00:00")
    if "appointments" not in overview:
        overview["appointments"] = overview.get("appointments", 0)
    if "projects_count" not in overview:
        overview["projects_count"] = overview.get("projects_count", 0)
    j["overview"] = overview

    # write back
    path.write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n")
    print(f"Patched {path}")


def main(argv):
    if len(argv) < 2:
        print("Usage: fix_old_reports.py <date> [date ...]")
        return 2
    for d in argv[1:]:
        p = Path("reports") / d / f"ActivityReport-{d}.json"
        if not p.exists():
            print(f"Missing report file: {p}")
            continue
        fix_report(p)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
