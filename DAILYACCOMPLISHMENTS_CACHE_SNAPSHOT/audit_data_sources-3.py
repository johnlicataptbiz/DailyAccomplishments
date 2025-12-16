#!/usr/bin/env python3
"""CLI auditor: show per-hour contributions and source summaries for a date.

Behavior:
- Try `logs/daily/<date>.jsonl` (preferred) and aggregate by event timestamps and `source` fields.
- Fallback to `ActivityReport-<date>.json` or `reports/daily-report-<date>.json` and report hourly_focus + integration summaries.

This is intentionally conservative: when raw JSONL isn't available we derive per-hour focus from the report's `hourly_focus` array and surface other integration totals (Slack, Monday, HubSpot, browser).
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def parse_args():
    p = argparse.ArgumentParser(description='Audit data sources for a given date')
    p.add_argument('--date', '-d', help='Date YYYY-MM-DD', required=False)
    return p.parse_args()


def try_paths(date):
    cwd = Path.cwd()
    candidates = [cwd / 'logs' / 'daily' / f'{date}.jsonl',
                  cwd / f'ActivityReport-{date}.json',
                  cwd / 'reports' / f'daily-report-{date}.json']
    return candidates


def read_jsonl(path: Path):
    results = []
    with path.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except Exception:
                # tolerate malformed lines
                continue
    return results


def aggregate_from_jsonl(events):
    # Per-hour minutes (from focus events) and counts per source
    per_hour_mins = defaultdict(int)
    source_counts = defaultdict(int)

    for e in events:
        src = e.get('source') or e.get('origin') or e.get('type') or 'unknown'
        source_counts[src] += 1

        # If event has timestamp and duration use it
        ts = e.get('timestamp') or e.get('time') or e.get('when')
        dur = e.get('duration') or e.get('seconds') or e.get('minutes')
        if ts and dur:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                h = dt.hour
                # assume duration in seconds if > 300 else minutes
                if isinstance(dur, (int, float)):
                    sec = int(dur)
                    if sec > 600:  # likely seconds
                        mins = sec // 60
                    else:
                        # ambiguous — treat >=60 as seconds
                        mins = sec // 60 if sec >= 60 else int(dur)
                else:
                    # string like '00:12'
                    if isinstance(dur, str) and ':' in dur:
                        hh, mm = dur.split(':')[:2]
                        mins = int(hh) * 60 + int(mm)
                    else:
                        mins = 0
                per_hour_mins[h] += mins
            except Exception:
                continue

    return per_hour_mins, source_counts


def summarize_report(report):
    lines = []
    # Hourly focus
    hourly = report.get('hourly_focus', [])
    per_hour = {h['hour']: h.get('time', '00:00') for h in hourly}

    lines.append('\nPer-hour focus (from report):')
    lines.append('Hour | Minutes')
    lines.append('-----|--------')
    for h in range(0, 24):
        t = per_hour.get(h, '00:00')
        hh = 0
        if t and t != '00:00':
            try:
                hh = int(t.split(':')[0]) * 60 + int(t.split(':')[1])
            except Exception:
                hh = 0
        lines.append(f'{h:02d}:00 | {hh}')

    # Integrations summary
    lines.append('\nIntegration Totals (best-effort):')
    # Slack
    slack = report.get('slack', {}).get('stats', {})
    lines.append(f"Slack messages (sent/recv): {slack.get('total_sent', 0)}/{slack.get('total_received', 0)}")

    # Monday
    monday = report.get('monday', {})
    lines.append(f"Monday items updated: {monday.get('items_updated', 0)}")

    # HubSpot
    hub = report.get('hubspot', {})
    lines.append(f"HubSpot deals today: {len(hub.get('deals', []) if isinstance(hub, dict) else [])}")

    # Browser
    browser = report.get('browser_highlights', {})
    top_domains = browser.get('top_domains', [])
    lines.append(f"Top domain visits (sum): {sum(d.get('visits', 0) for d in top_domains)}")

    # Meetings & appointments
    meetings = report.get('debug_appointments', {}).get('meetings_today', [])
    appts = report.get('debug_appointments', {}).get('appointments_today', [])
    lines.append(f"Meetings: {len(meetings)}  Appointments: {len(appts)}")

    return '\n'.join(lines)


def main():
    args = parse_args()
    date = args.date or datetime.now().strftime('%Y-%m-%d')

    paths = try_paths(date)
    jsonl_path, activity_path, reports_path = paths

    if jsonl_path.exists():
        events = read_jsonl(jsonl_path)
        per_hour, sources = aggregate_from_jsonl(events)

        print(f'Loaded {len(events)} events from {jsonl_path}')
        print('\nPer-hour minutes (from raw events):')
        for h in range(0, 24):
            print(f'{h:02d}:00 - {per_hour.get(h, 0)} min')

        print('\nEvent counts by source:')
        for s, c in sorted(sources.items(), key=lambda x: -x[1]):
            print(f'  {s}: {c}')
        return

    # Fallback to ActivityReport
    if activity_path.exists():
        with activity_path.open('r', encoding='utf-8') as fh:
            report = json.load(fh)
        print(f'Loaded ActivityReport from {activity_path}\n')
        print(summarize_report(report))
        return

    if reports_path.exists():
        with reports_path.open('r', encoding='utf-8') as fh:
            report = json.load(fh)
        print(f'Loaded report from {reports_path}\n')
        print(summarize_report(report))
        return

    print('No data found for', date)


if __name__ == '__main__':
    main()
