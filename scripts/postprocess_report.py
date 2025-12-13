#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    if not date_str:
        raise SystemExit("Usage: python3 scripts/postprocess_report.py YYYY-MM-DD")

    repo = Path(__file__).parent.parent
    f = repo / f"ActivityReport-{date_str}.json"
    if not f.exists():
        raise SystemExit(f"Missing {f}")

    report = json.loads(f.read_text())
    ov = report.get("overview") or {}

    active = ov.get("active_time", "00:00")
    focus = ov.get("focus_time", "00:00")
    meetings = ov.get("meetings_time", "00:00")
    coverage = ov.get("coverage_window", "")

    # Keep prepared_for_manager aligned
    top_apps = report.get("top_apps") or {}
    top3 = ", ".join(list(top_apps.keys())[:3]) if top_apps else ""
    report["prepared_for_manager"] = [
        f"Active Time: {active}",
        f"Focus Time: {focus}",
        f"Meeting Time: {meetings}",
        f"Top Apps: {top3}" if top3 else "Top Apps: "
    ]

    # Keep executive_summary aligned, preserve extra lines (like Screen Time) if present
    extra = []
    if isinstance(report.get("executive_summary"), list) and len(report["executive_summary"]) > 2:
        extra = report["executive_summary"][2:]
    report["executive_summary"] = [
        f"Active: {active} | Focus: {focus}",
        f"Coverage: {coverage}",
        *extra
    ]

    f.write_text(json.dumps(report, indent=2))
    print(f"Postprocessed {f}")

if __name__ == "__main__":
    main()
