#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs - DEBUG VERSION."""
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
BASE = Path(__file__).resolve().parents[1]
DEFAULT_DATE = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d')
JSONL_INPUT = BASE / 'logs' / 'daily' / f'{DEFAULT_DATE}.jsonl'
JSON_INPUT = BASE / f'ActivityReport-{DEFAULT_DATE}.json'
OUT_DIR = BASE
def hhmm_to_minutes(s):
    if not s or ':' not in s:
        return 0
    parts = s.split(':')
    try:
        h = int(parts[0])
        m = int(parts[1])
        return h*60 + m
    except Exception:
        return 0
def write_csv(path, rows, headers):
    print(f"Writing CSV to {path} with {len(rows)} rows")
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
def load_from_jsonl(jsonl_path: Path) -> dict:
    print(f"Loading from JSONL: {jsonl_path}")
    if not jsonl_path.exists():
        return None
    events = []
    metadata = None
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        print(f"Parsed event: {event.get('type', 'unknown')}")
                        if event.get('type') == 'metadata':
                            metadata = event.get('data', {})
                        else:
                            events.append(event)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        continue
        print(f"Loaded {len(events)} events, {len(metadata) if metadata else 0} metadata keys")
    except Exception as e:
        print(f"Error reading JSONL: {e}")
        return None
    # ... (rest of the function as in original, but add print after aggregation)
    print(f"Total focus seconds: {total_focus_seconds}, meeting seconds: {total_meeting_seconds}")
    print(f"Categories found: {list(category_seconds.keys())}")
    print(f"Hourly seconds sample: {hourly_seconds[:5]}...")  # First 5 hours
    return report
def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        data = load_data(date)
        print(f"Loaded data keys: {list(data.keys()) if data else 'None'}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # ... (rest of main as in original, but add prints in write_csv and chart sections)
    print('DEBUG: CSVs and charts written to', OUT_DIR)
if __name__ == '__main__':
    main()
