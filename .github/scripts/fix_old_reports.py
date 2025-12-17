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

def _default_hourly_focus():
    return [{"hour": h, "time": "00:00", "pct": "0%"} for h in range(24)]


def _normalize_hourly_focus(hf):
    """
    Return a 24-item hourly_focus list.

    Accepts legacy shapes:
      - [] / missing
      - list of strings ("HH:MM")
      - list of numbers (minutes)
      - list of dicts with hour/time
      - list of dicts without hour (position-based)
    """
    out = _default_hourly_focus()
    if not isinstance(hf, list) or not hf:
        return out

    # First pass: honor explicit "hour" when present.
    used_by_hour = set()
    for item in hf:
        if not isinstance(item, dict):
            continue
        hour = item.get("hour")
        try:
            hour_i = int(hour)
        except Exception:
            continue
        if 0 <= hour_i <= 23:
            out[hour_i] = item
            used_by_hour.add(hour_i)

    # Second pass: fill remaining by position for items without an explicit hour.
    pos = 0
    for item in hf:
        if isinstance(item, dict) and "hour" in item:
            continue
        while pos < 24 and pos in used_by_hour:
            pos += 1
        if pos >= 24:
            break
        out[pos] = item if isinstance(item, dict) else {"hour": pos, "time": item, "pct": "0%"}
        used_by_hour.add(pos)
        pos += 1

    # Final pass: ensure each entry is a dict with an hour.
    for i in range(24):
        item = out[i]
        if isinstance(item, dict):
            # Ensure hour is present and normalized
            item.setdefault("hour", i)
            # Normalize time: accept numeric minutes, numeric-strings, or HH:MM
            t = item.get("time")
            if isinstance(t, (int, float)):
                item["time"] = fmt_hhmm(int(t))
            elif isinstance(t, str):
                ts = t.strip()
                # pure digits -> minutes value
                if ts.isdigit():
                    item["time"] = fmt_hhmm(int(ts))
                else:
                    # leave as-is (expecting HH:MM); fallback to 00:00 if unparsable
                    if parse_hhmm(ts) == 0 and ts not in ("00:00", "0:00", "0"):
                        item["time"] = "00:00"
                    else:
                        item["time"] = ts
            else:
                item["time"] = "00:00"

            # Normalize pct to a percent string
            p = item.get("pct")
            if isinstance(p, (int, float)):
                try:
                    item["pct"] = f"{int(p)}%"
                except Exception:
                    item["pct"] = "0%"
            elif isinstance(p, str):
                ps = p.strip()
                if ps.endswith("%"):
                    item["pct"] = ps
                elif ps.isdigit():
                    item["pct"] = f"{ps}%"
                else:
                    item["pct"] = "0%"
            else:
                item["pct"] = "0%"

            out[i] = item
        elif isinstance(item, str):
            out[i] = {"hour": i, "time": item, "pct": "0%"}
        elif isinstance(item, (int, float)):
            out[i] = {"hour": i, "time": fmt_hhmm(int(item)), "pct": "0%"}
        else:
            out[i] = {"hour": i, "time": "00:00", "pct": "0%"}

    return out


def fix_report(path: Path):
    j = json.loads(path.read_text())
    # Ensure schema-required hourly_focus shape exists before computing totals.
    j["hourly_focus"] = _normalize_hourly_focus(j.get("hourly_focus"))
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
    if "coverage_window" not in overview:
        # Prefer an explicit placeholder over silently fabricating coverage.
        overview["coverage_window"] = ""
    if "meetings_time" not in overview:
        overview["meetings_time"] = overview.get("meetings_time", "00:00")
    if "appointments" not in overview:
        overview["appointments"] = overview.get("appointments", 0)
    if "projects_count" not in overview:
        overview["projects_count"] = overview.get("projects_count", 0)
    j["overview"] = overview

    # Ensure schema-required top-level fields exist.
    if "timeline" not in j or not isinstance(j.get("timeline"), list):
        j["timeline"] = []
    if "deep_work_blocks" not in j or not isinstance(j.get("deep_work_blocks"), list):
        j["deep_work_blocks"] = []

    # Ensure browser_highlights is present with list-shaped fields.
    bh = j.get("browser_highlights")
    if not isinstance(bh, dict):
        bh = {}
    if "top_domains" not in bh or not isinstance(bh.get("top_domains"), list):
        bh["top_domains"] = []
    if "top_pages" not in bh or not isinstance(bh.get("top_pages"), list):
        bh["top_pages"] = []
    j["browser_highlights"] = bh

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
