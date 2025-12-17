#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs."""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
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

def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        # keep this tiny and dependency-free; urlparse is fine too but this is enough
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _load_config(explicit_config: dict | None) -> dict:
    if explicit_config is not None:
        return explicit_config

    try:
        config_path = BASE / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _get_category_priority(config: dict) -> list[str]:
    category_priority = config.get('analytics', {}).get('category_priority', []) if config else []
    if not category_priority:
        category_priority = ['Coding', 'Design', 'Documentation', 'Project Work', 'Research', 'Communication', 'Meetings', 'Other']
    return category_priority


def _get_category_mapping(config: dict) -> dict[str, list[str]]:
    mapping = config.get('analytics', {}).get('category_mapping', {}) if config else {}
    # normalize mapping values to lists
    out: dict[str, list[str]] = {}
    for cat, apps in mapping.items():
        if isinstance(apps, list):
            out[cat] = [str(a) for a in apps]
        elif apps:
            out[cat] = [str(apps)]
    return out


def _get_domain_mapping(config: dict) -> dict[str, str]:
    mapping = config.get('analytics', {}).get('domain_mapping', {}) if config else {}
    out: dict[str, str] = {}
    for domain, cat in mapping.items():
        if domain and cat:
            out[str(domain).lower()] = str(cat)
    return out


def categorize_event(event: dict, config: dict | None = None) -> str:
    """
    Categorize a raw activity event.
    Supports:
      - app-based mapping (analytics.category_mapping)
      - domain-based mapping (analytics.domain_mapping) for browser URLs
      - fallback heuristics via categorize_app()
    """
    app = str(event.get('app', '') or '')
    app_lower = app.lower()

    config = config or {}
    category_mapping = _get_category_mapping(config)
    for category, apps in category_mapping.items():
        for mapped in apps:
            if mapped and mapped.lower() in app_lower:
                return category

    # Domain mapping has priority for browser activity
    url = (event.get('data') or {}).get('url') if isinstance(event.get('data'), dict) else None
    domain = _extract_domain(str(url or ''))
    domain_mapping = _get_domain_mapping(config)
    if domain and domain in domain_mapping:
        return domain_mapping[domain]

    return categorize_app(app)


def _sweep_timeline(intervals: list[tuple[datetime, datetime, str, str]], category_priority: list[str]):
    """
    Convert possibly-overlapping intervals into a timeline with priority-based attribution.
    Returns: list of (start, end, category, label/app)
    """
    events: list[tuple[datetime, int, str, str]] = []
    for start, end, category, label in intervals:
        if end <= start:
            continue
        events.append((start, 1, category, label))
        events.append((end, -1, category, label))
    if not events:
        return []

    pr = {c.lower(): i for i, c in enumerate(category_priority)}
    events.sort(key=lambda x: (x[0], -x[1]))  # start before end at same timestamp
    active: list[tuple[datetime, str, str]] = []  # (start_time, category, label)

    def pick_winner():
        if not active:
            return None
        # priority then most-recent start wins ties
        return min(active, key=lambda t: (pr.get(t[1].lower(), 10_000), -t[0].timestamp()))

    current_time = events[0][0]
    timeline: list[tuple[datetime, datetime, str, str]] = []

    i = 0
    while i < len(events):
        t = events[i][0]
        if t > current_time:
            winner = pick_winner()
            if winner:
                seg_start = current_time
                seg_end = t
                _, cat, label = winner
                if timeline and timeline[-1][2] == cat and timeline[-1][3] == label and timeline[-1][1] == seg_start:
                    # extend last segment
                    timeline[-1] = (timeline[-1][0], seg_end, cat, label)
                else:
                    timeline.append((seg_start, seg_end, cat, label))
            current_time = t

        while i < len(events) and events[i][0] == t:
            _, typ, cat, label = events[i]
            if typ == 1:
                active.append((t, cat, label))
            else:
                # remove one matching active entry (best-effort)
                for j in range(len(active) - 1, -1, -1):
                    if active[j][1] == cat and active[j][2] == label:
                        active.pop(j)
                        break
            i += 1

    return timeline


def _build_deep_work_blocks(timeline: list[tuple[datetime, datetime, str, str]], threshold_minutes: int = 25, gap_tolerance_seconds: int = 60):
    threshold_seconds = threshold_minutes * 60
    blocks = []
    current_start = None
    current_end = None

    for start, end, category, _label in timeline:
        if category.lower() == 'meetings':
            continue
        if current_start is None:
            current_start, current_end = start, end
            continue

        gap = (start - current_end).total_seconds()
        if gap <= gap_tolerance_seconds:
            current_end = max(current_end, end)
            continue

        duration_seconds = int((current_end - current_start).total_seconds())
        if duration_seconds >= threshold_seconds:
            blocks.append({
                "start": current_start.strftime("%H:%M"),
                "end": current_end.strftime("%H:%M"),
                "duration": seconds_to_hhmm(duration_seconds),
                "seconds": duration_seconds,
                "minutes": int(duration_seconds / 60),
            })

        current_start, current_end = start, end

    if current_start is not None and current_end is not None:
        duration_seconds = int((current_end - current_start).total_seconds())
        if duration_seconds >= threshold_seconds:
            blocks.append({
                "start": current_start.strftime("%H:%M"),
                "end": current_end.strftime("%H:%M"),
                "duration": seconds_to_hhmm(duration_seconds),
                "seconds": duration_seconds,
                "minutes": int(duration_seconds / 60),
            })

    return blocks


def load_from_jsonl(jsonl_path: Path, config: dict | None = None) -> dict:
    """Load and convert JSONL log to report format with interval merging."""
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

    config = _load_config(config)
    category_priority = _get_category_priority(config)
    
    # Convert events to report format with timeline reconstruction.
    # Supports two JSONL shapes:
    #  - "typed" events: {"type": "focus_change", "timestamp": "...", "data": {...}}
    #  - "raw samples": {"timestamp": "...", "app": "...", "idle_seconds": 0, "data": {...}}
    report = {
        'date': metadata.get('date') if metadata else DEFAULT_DATE,
        'overview': {
            'active_time': '00:00',
            'focus_time': '00:00',
            'meetings_time': '00:00',
            'appointments': 0,
            'projects_count': 0,
            'coverage_window': metadata.get('coverage_start', '06:00') + '–' + metadata.get('coverage_end', '23:59') if metadata else '06:00–23:59'
        },
        'by_category': {},
        'browser_highlights': {'top_domains': [], 'top_pages': []},
        'hourly_focus': [],
        'timeline': [],
        'deep_work_blocks': [],
    }
    
    # Initialize hourly buckets
    for hour in range(24):
        report['hourly_focus'].append({
            'hour': hour,
            'time': '00:00',
            'pct': '0%'
        })
    
    # Build intervals for sweep-line attribution.
    # Format: (start_dt, end_dt, category, label/app)
    intervals: list[tuple[datetime, datetime, str, str]] = []
    
    # If "typed" events exist, build intervals from those. Otherwise, treat events as raw samples.
    has_typed = any(isinstance(e, dict) and 'type' in e for e in events)
    if has_typed:
        for event in events:
            event_type = event.get('type')
            data = event.get('data', {}) if isinstance(event.get('data'), dict) else {}
            timestamp = event.get('timestamp', '')

            try:
                dt = datetime.fromisoformat(timestamp)
            except Exception:
                continue

            if event_type == 'focus_change':
                duration = int(data.get('duration_seconds', 0) or 0)
                if duration > 0:
                    app = str(data.get('app', '') or '')
                    category = categorize_event({'app': app, 'data': data}, config)
                    end_dt = dt + timedelta(seconds=duration)
                    intervals.append((dt, end_dt, category, app))
            elif event_type == 'meeting_end':
                duration = int(data.get('duration_seconds', 0) or 0)
                if duration > 0:
                    end_dt = dt
                    start_dt = dt - timedelta(seconds=duration)
                    intervals.append((start_dt, end_dt, 'Meetings', str(data.get('title', 'Meeting') or 'Meeting')))
    else:
        samples: list[tuple[datetime, dict]] = []
        for event in events:
            timestamp = event.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp)
            except Exception:
                continue
            samples.append((dt, event))

        samples.sort(key=lambda x: x[0])
        if samples:
            # Interpret samples as point-in-time observations that last until the next sample.
            # The final sample has no implied duration (avoids off-by-one minute in tests).
            for idx in range(len(samples) - 1):
                dt, event = samples[idx]
                next_dt = samples[idx + 1][0]
                if next_dt <= dt:
                    continue
                idle = int(event.get('idle_seconds', 0) or 0)
                if idle >= int((next_dt - dt).total_seconds()):
                    continue

                app = str(event.get('app', '') or '')
                category = categorize_event(event, config)
                intervals.append((dt, next_dt, category, app))

            report['date'] = samples[0][0].date().isoformat()
            report['overview']['coverage_window'] = f"{samples[0][0].strftime('%H:%M')}–{samples[-1][0].strftime('%H:%M')}"
    
    # Attribute overlaps via sweep-line, producing a concrete timeline.
    intervals.sort(key=lambda x: x[0])
    timeline_segments = _sweep_timeline(intervals, category_priority)

    report['timeline'] = [
        {
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "minutes": int((end - start).total_seconds() / 60),
            "category": category,
            "label": label,
        }
        for start, end, category, label in timeline_segments
        if end > start
    ]

    report['deep_work_blocks'] = _build_deep_work_blocks(timeline_segments)

    # Aggregate by category and hour (use attributed timeline, not raw intervals)
    hourly_seconds = [0] * 24
    category_seconds: dict[str, int] = {}
    meeting_seconds = 0
    focus_seconds = 0
    active_seconds = 0

    for start, end, category, _label in timeline_segments:
        duration_secs = int((end - start).total_seconds())
        active_seconds += duration_secs
        if category.lower() == 'meetings':
            meeting_seconds += duration_secs
        else:
            focus_seconds += duration_secs

        category_seconds[category] = category_seconds.get(category, 0) + duration_secs
        
        # Distribute *focus* across hours (exclude meetings for hourly focus)
        if category.lower() != 'meetings':
            current = start
            while current < end:
                next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                segment_end = min(end, next_hour)
                segment_secs = int((segment_end - current).total_seconds())
                hourly_seconds[current.hour] += segment_secs
                current = segment_end
    
    # Convert to HH:MM format
    report['overview']['active_time'] = seconds_to_hhmm(active_seconds)
    report['overview']['focus_time'] = seconds_to_hhmm(focus_seconds)
    report['overview']['meetings_time'] = seconds_to_hhmm(meeting_seconds)
    
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
