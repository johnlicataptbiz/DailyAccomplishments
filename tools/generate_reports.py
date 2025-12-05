#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs - FIXED FOR COLLECTOR FORMAT."""
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
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        print(f"Loaded {len(events)} events")
    except Exception as e:
        print(f"Error reading JSONL: {e}")
        return None
    # Aggregate for collector format: calculate durations from timestamps, categorize apps
    # Use the JSONL filename (YYYY-MM-DD) as the canonical report date when available.
    date_str = jsonl_path.stem if jsonl_path and jsonl_path.exists() else DEFAULT_DATE
    report = {
        'date': date_str,
        'overview': {
            'focus_time': '00:00',
            'meetings_time': '00:00',
            'appointments': 0,
            'projects_count': 0,
            'coverage_window': '06:00–23:59'
        },
        'by_category': {},
        'browser_highlights': {'top_domains': [], 'top_pages': []},
        'hourly_focus': []
    }
    # Initialize hourly buckets
    for hour in range(24):
        report['hourly_focus'].append({
            'hour': hour,
            'time': '00:00',
            'pct': '0%'
        })
    # Aggregate: sort by timestamp, calculate durations
    if len(events) < 2:
        print("Not enough events for duration calculation")
        return report
    events.sort(key=lambda e: e.get('timestamp', ''))
    hourly_seconds = [0] * 24
    category_seconds = {}
    total_focus_seconds = 0
    prev_timestamp = None
    for event in events:
        timestamp = event.get('timestamp', '')
        # Support both collector formats: data may be nested under 'data'
        data_section = event.get('data', {}) if isinstance(event.get('data', {}), dict) else {}
        app = event.get('app') or data_section.get('app') or data_section.get('application') or 'Unknown'
        idle = event.get('idle_seconds', 0) or data_section.get('idle_seconds', 0)
        try:
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour
        except:
            hour = 0
        if prev_timestamp:
            duration = int((dt - datetime.fromisoformat(prev_timestamp)).total_seconds())
            # Ignore idle time > 5s or very short durations
            if duration > 1 and idle < 5:
                total_focus_seconds += duration
                hourly_seconds[hour] += duration
                category = categorize_app(app)
                category_seconds[category] = category_seconds.get(category, 0) + duration
                print(f"Aggregated {duration}s to hour {hour}, category {category}")
        prev_timestamp = timestamp
    print(f"Total focus seconds: {total_focus_seconds}, categories: {list(category_seconds.keys())}")
    # Fill report
    report['overview']['focus_time'] = seconds_to_hhmm(total_focus_seconds)
    for cat, secs in category_seconds.items():
        report['by_category'][cat] = seconds_to_hhmm(secs)
    max_seconds = max(hourly_seconds) if hourly_seconds else 1
    for hour in range(24):
        secs = hourly_seconds[hour]
        report['hourly_focus'][hour]['time'] = seconds_to_hhmm(secs)
        report['hourly_focus'][hour]['pct'] = f"{int(100 * secs / max_seconds) if max_seconds else 0}%"
    return report
def seconds_to_hhmm(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"
def categorize_app(app: str) -> str:
    app_lower = app.lower()
    if any(word in app_lower for word in ['chrome', 'firefox', 'safari']):
        return 'Research'
    elif any(word in app_lower for word in ['code', 'terminal', 'iterm']):
        return 'Coding'
    elif any(word in app_lower for word in ['slack', 'zoom']):
        return 'Meetings'
    elif any(word in app_lower for word in ['mail', 'messages']):
        return 'Communication'
    else:
        return 'Other'
def load_data(date: str = None) -> dict:
    if date:
        jsonl_path = BASE / 'logs' / 'daily' / f'{date}.jsonl'
        json_path = BASE / f'ActivityReport-{date}.json'
    else:
        jsonl_path = JSONL_INPUT
        json_path = JSON_INPUT
    if jsonl_path.exists():
        data = load_from_jsonl(jsonl_path)
        if data:
            return data
    if json_path.exists():
        print(f"Loading from JSON: {json_path}")
        return json.loads(json_path.read_text())
    raise FileNotFoundError(f"No data found for date {date or DEFAULT_DATE}")
def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        data = load_data(date)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # Ensure outputs are placed under reports/<date>/ as canonical location
    date_str = data.get('date') or date or DEFAULT_DATE
    out_dir = BASE / 'reports' / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write canonical ActivityReport JSON into reports/<date>/
    try:
        (out_dir / f'ActivityReport-{date_str}.json').write_text(json.dumps(data, indent=2))
        # Also write the dashboard fallback name
        (out_dir / f'daily-report-{date_str}.json').write_text(json.dumps(data, indent=2))
        print(f"Wrote canonical ActivityReport JSON to {out_dir}")
    except Exception as e:
        print(f"Failed to write ActivityReport JSON to {out_dir}: {e}")

    # Hourly focus CSV
    hf = data.get('hourly_focus', [])
    hf_rows = []
    for item in hf:
        time_str = item.get('time', '00:00')
        minutes = hhmm_to_minutes(time_str)
        pct_str = item.get('pct', '0%').rstrip('%')
        try:
            pct = int(pct_str)
        except:
            pct = 0
        if minutes > 60:
            minutes = min(60, int(60 * pct / 100))
        hf_rows.append([item.get('hour'), time_str, item.get('pct'), minutes])
    write_csv(out_dir / f'hourly_focus-{date_str}.csv', hf_rows, ['hour', 'time', 'pct', 'minutes'])
    # Top domains CSV
    domains = data.get('browser_highlights', {}).get('top_domains', [])
    dom_rows = [[d.get('domain'), d.get('visits')] for d in domains]
    write_csv(out_dir / f'top_domains-{date_str}.csv', dom_rows, ['domain', 'visits'])
    # Category distribution CSV
    cats = data.get('by_category', {})
    cat_rows = []
    for k, v in cats.items():
        cat_rows.append([k, v, hhmm_to_minutes(v)])
    write_csv(out_dir / f'category_distribution-{date_str}.csv', cat_rows, ['category', 'time', 'minutes'])
    # Generate charts
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        print("Matplotlib imported")
    except Exception as e:
        print('matplotlib required to generate charts:', e)
        return
    # Hourly bar chart
    title_date = data.get('date') or date or DEFAULT_DATE
    hours = [int(x.get('hour', 0)) for x in hf]
    minutes = []
    for x in hf:
        m = hhmm_to_minutes(x['time'])
        if m > 60:
            pct_str = x.get('pct', '0%').rstrip('%')
            try:
                pct = int(pct_str)
                m = min(60, int(60 * pct / 100))
            except:
                m = min(60, m)
        minutes.append(m)
    plt.figure(figsize=(10,4))
    plt.bar(hours, minutes, color='#2563eb')
    plt.xlabel('Hour')
    plt.ylabel('Focused minutes')
    plt.title(f'Hourly Focus — {title_date}')
    plt.xticks(hours)
    plt.tight_layout()
    plt.savefig(out_dir / f'hourly_focus-{title_date}.png')
    plt.savefig(out_dir / f'hourly_focus-{title_date}.svg')
    plt.close()
    print(f"Hourly chart saved for {title_date}")
    # Category pie chart
    labels = [r[0] for r in cat_rows]
    sizes = [r[2] for r in cat_rows]
    if any(sizes):
        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title(f'Time by Category — {title_date}')
        plt.tight_layout()
        plt.savefig(out_dir / f'category_distribution-{title_date}.png')
        plt.savefig(out_dir / f'category_distribution-{title_date}.svg')
        plt.close()
        print(f"Category chart saved for {title_date}")
    else:
        print(f"No category data for {title_date}")
    print('CSVs and charts written to', out_dir)
if __name__ == '__main__':
    main()
