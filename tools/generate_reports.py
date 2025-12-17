#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs."""
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv

BASE = Path(__file__).resolve().parents[1]
# Try to read from JSONL log first, fallback to JSON
DEFAULT_DATE = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d')
JSONL_INPUT = BASE / 'logs' / 'daily' / f'{DEFAULT_DATE}.jsonl'
JSON_INPUT = BASE / f'ActivityReport-{DEFAULT_DATE}.json'
# OUT_DIR will be set based on the date being processed
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
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)

def load_from_jsonl(jsonl_path: Path) -> dict:
    """Load and convert JSONL log to report format with interval merging"""
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
                        if event.get('type') == 'metadata':
                            metadata = event.get('data', {})
                        else:
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error reading JSONL: {e}")
        return None
    
    # Convert events to report format with timeline reconstruction
    report = {
        'date': metadata.get('date') if metadata else DEFAULT_DATE,
        'overview': {
            'focus_time': '00:00',
            'meetings_time': '00:00',
            'appointments': 0,
            'projects_count': 0,
            'coverage_window': metadata.get('coverage_start', '06:00') + '–' + metadata.get('coverage_end', '23:59') if metadata else '06:00–23:59'
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
    
    # Build timeline with intervals to merge overlaps
    # Format: (start_time, end_time, category, app)
    intervals = []
    total_meeting_seconds = 0
    
    for event in events:
        event_type = event.get('type')
        data = event.get('data', {})
        timestamp = event.get('timestamp', '')
        
        try:
            dt = datetime.fromisoformat(timestamp)
        except:
            continue
        
        if event_type == 'focus_change':
            duration = data.get('duration_seconds', 0)
            if duration > 0:
                app = data.get('app', '')
                category = categorize_app(app)
                end_dt = dt + __import__('datetime').timedelta(seconds=duration)
                intervals.append((dt, end_dt, category))
        
        elif event_type in ['meeting_start', 'meeting_end']:
            if event_type == 'meeting_end':
                duration = data.get('duration_seconds', 0)
                total_meeting_seconds += duration
    
    # Sort intervals by start time
    intervals.sort(key=lambda x: x[0])
    
    # Merge overlapping intervals and attribute by category priority
    # Load category priority from config if available
    try:
        config_path = BASE / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                category_priority = config.get('analytics', {}).get('category_priority', [])
        else:
            category_priority = []
    except:
        category_priority = []
    
    if not category_priority:
        category_priority = ['Coding', 'Design', 'Documentation', 'Project Work', 'Research', 'Communication', 'Meetings', 'Other']
    
    # Merge overlapping intervals with priority-based attribution
    merged_intervals = []
    for start, end, category in intervals:
        # Check for overlaps and merge
        overlaps = []
        non_overlaps = []
        for i, (m_start, m_end, m_cat) in enumerate(merged_intervals):
            if start < m_end and end > m_start:
                overlaps.append(i)
            else:
                non_overlaps.append((m_start, m_end, m_cat))
        
        if not overlaps:
            # No overlap, add as-is
            merged_intervals.append((start, end, category))
        else:
            # Merge with overlapping intervals using priority
            all_cats = [category] + [merged_intervals[i][2] for i in overlaps]
            # Pick highest priority category
            priority_cat = min(all_cats, key=lambda c: category_priority.index(c) if c in category_priority else 999)
            
            # Compute merged time range
            all_starts = [start] + [merged_intervals[i][0] for i in overlaps]
            all_ends = [end] + [merged_intervals[i][1] for i in overlaps]
            merged_start = min(all_starts)
            merged_end = max(all_ends)
            
            # Rebuild merged_intervals without overlapped items
            merged_intervals = non_overlaps + [(merged_start, merged_end, priority_cat)]
    
    # Aggregate by category and hour
    hourly_seconds = [0] * 24
    category_seconds = {}
    total_focus_seconds = 0
    
    for start, end, category in merged_intervals:
        duration_secs = int((end - start).total_seconds())
        total_focus_seconds += duration_secs
        category_seconds[category] = category_seconds.get(category, 0) + duration_secs
        
        # Distribute across hours
        current = start
        while current < end:
            next_hour = current.replace(minute=0, second=0, microsecond=0) + __import__('datetime').timedelta(hours=1)
            segment_end = min(end, next_hour)
            segment_secs = int((segment_end - current).total_seconds())
            hourly_seconds[current.hour] += segment_secs
            current = segment_end
    
    # Convert to HH:MM format
    report['overview']['focus_time'] = seconds_to_hhmm(total_focus_seconds)
    report['overview']['meetings_time'] = seconds_to_hhmm(total_meeting_seconds)
    
    # Fill category distribution
    for cat, secs in category_seconds.items():
        report['by_category'][cat] = seconds_to_hhmm(secs)
    
    # Fill hourly focus
    max_seconds = max(hourly_seconds) if hourly_seconds else 1
    for hour in range(24):
        secs = hourly_seconds[hour]
        report['hourly_focus'][hour]['time'] = seconds_to_hhmm(secs)
        report['hourly_focus'][hour]['pct'] = f"{int(100 * secs / max_seconds) if max_seconds else 0}%"
    
    return report

def seconds_to_hhmm(seconds: int) -> str:
    """Convert seconds to HH:MM format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

def categorize_app(app: str) -> str:
    """Simple app categorization"""
    app_lower = app.lower()
    
    if any(word in app_lower for word in ['chrome', 'firefox', 'safari', 'browser']):
        return 'Research'
    elif any(word in app_lower for word in ['code', 'terminal', 'iterm', 'pycharm', 'intellij']):
        return 'Coding'
    elif any(word in app_lower for word in ['slack', 'zoom', 'teams', 'meet']):
        return 'Meetings'
    elif any(word in app_lower for word in ['mail', 'outlook', 'gmail', 'messages']):
        return 'Communication'
    elif any(word in app_lower for word in ['word', 'excel', 'sheets', 'docs', 'notion']):
        return 'Docs'
    else:
        return 'Other'

def load_data(date: str = None) -> dict:
    """Load data from JSONL or JSON file"""
    if date:
        jsonl_path = BASE / 'logs' / 'daily' / f'{date}.jsonl'
        json_path = BASE / f'ActivityReport-{date}.json'
    else:
        jsonl_path = JSONL_INPUT
        json_path = JSON_INPUT
    
    # Try JSONL first
    if jsonl_path.exists():
        data = load_from_jsonl(jsonl_path)
        if data:
            return data
    
    # Fallback to JSON
    if json_path.exists():
        print(f"Loading from JSON: {json_path}")
        return json.loads(json_path.read_text())
    
    raise FileNotFoundError(f"No data found for date {date or DEFAULT_DATE}")

def main():
    """Main entry point"""
    # Support command line argument for date
    date = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        data = load_data(date)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine output directory with date subdirectory
    report_date = data.get('date') or date or DEFAULT_DATE
    global OUT_DIR
    OUT_DIR = BASE / 'reports' / report_date
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Saving outputs to {OUT_DIR}")

    # Hourly focus CSV
    hf = data.get('hourly_focus', [])
    hf_rows = []
    for item in hf:
        time_str = item.get('time', '00:00')
        minutes = hhmm_to_minutes(time_str)
        # Cap minutes at 60 per hour (the data appears to show cumulative or scaled values)
        # We'll use the percentage to derive actual minutes if time exceeds 60
        pct_str = item.get('pct', '0%').rstrip('%')
        try:
            pct = int(pct_str)
        except:
            pct = 0
        # If minutes > 60, use percentage-based calculation relative to max of 60
        if minutes > 60:
            minutes = min(60, int(60 * pct / 100))
        hf_rows.append([item.get('hour'), time_str, item.get('pct'), minutes])
    write_csv(OUT_DIR / 'hourly_focus.csv', hf_rows, ['hour', 'time', 'pct', 'minutes'])

    # Top domains CSV
    domains = data.get('browser_highlights', {}).get('top_domains', [])
    dom_rows = [[d.get('domain'), d.get('visits')] for d in domains]
    write_csv(OUT_DIR / 'top_domains.csv', dom_rows, ['domain', 'visits'])

    # Category distribution CSV
    cats = data.get('by_category', {})
    cat_rows = []
    for k, v in cats.items():
        cat_rows.append([k, v, hhmm_to_minutes(v)])
    write_csv(OUT_DIR / 'category_distribution.csv', cat_rows, ['category', 'time', 'minutes'])

    # Generate charts (matplotlib)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as e:
        print('matplotlib required to generate charts:', e)
        return

    # Hourly bar chart
    # Use the date from the data, falling back to the CLI arg or default
    title_date = data.get('date') or date or DEFAULT_DATE
    hours = [int(x.get('hour', 0)) for x in hf]
    # Apply same capping logic as CSV: if minutes > 60, use percentage-based calc
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
    plt.savefig(OUT_DIR / 'hourly_focus.png')
    plt.savefig(OUT_DIR / 'hourly_focus.svg')
    plt.close()

    # Category pie chart
    labels = [r[0] for r in cat_rows]
    sizes = [r[2] for r in cat_rows]
    if any(sizes):
        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title(f'Time by Category — {title_date}')
        plt.tight_layout()
        plt.savefig(OUT_DIR / 'category_distribution.png')
        plt.savefig(OUT_DIR / 'category_distribution.svg')
        plt.close()

    print('CSVs and charts written to', OUT_DIR)

if __name__ == '__main__':
    main()
