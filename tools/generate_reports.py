#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs - FIXED FOR COLLECTOR FORMAT."""
import json
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
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
def _load_category_settings(config: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, List[str]], List[str]]:
    """Return category mapping and priority settings from config if available."""
    mapping: Dict[str, List[str]] = {}
    priority: List[str] = []

    cfg = config
    if cfg is None:
        try:
            from tools.daily_logger import load_config  # type: ignore

            cfg = load_config()
        except Exception as e:
            print(f"Warning: Failed to load configuration from daily_logger: {e}", file=sys.stderr)
            cfg = {}

    if isinstance(cfg, dict):
        analytics_cfg = cfg.get('analytics', {}) or {}
        if isinstance(analytics_cfg, dict):
            category_mapping = analytics_cfg.get('category_mapping') or {}
            if isinstance(category_mapping, dict):
                # Normalize mapping to lists of strings
                mapping = {
                    str(cat): [str(item) for item in items]
                    for cat, items in category_mapping.items()
                    if isinstance(items, list)
                }
            category_priority = analytics_cfg.get('category_priority') or []
            if isinstance(category_priority, list):
                priority = [str(cat) for cat in category_priority]

    return mapping, priority


def _build_categorizer(mapping: Dict[str, List[str]], fallback_categorizer: Callable[[str], str]) -> Callable[[str], str]:
    """Create a categorization function using config mapping with heuristic fallback."""
    normalized_mapping: Dict[str, List[str]] = {
        cat: [item.lower() for item in items]
        for cat, items in mapping.items()
    }

    def categorize(app: str) -> str:
        app_lower = app.lower()
        for cat, items in normalized_mapping.items():
            for keyword in items:
                if keyword and keyword in app_lower:
                    return cat
        return fallback_categorizer(app)

    return categorize


def _build_priority_func(priority_list: List[str]) -> Callable[[str], int]:
    """Create priority resolver honoring config ordering with safe defaults."""
    if priority_list:
        ordering = {cat.lower(): idx for idx, cat in enumerate(priority_list)}

        def category_priority(cat: str) -> int:
            if not cat:
                return len(ordering) + 50
            return ordering.get(cat.lower(), len(ordering) + 10)

        return category_priority

    def default_priority(cat: str) -> int:
        # lower number = higher priority
        if not cat:
            return 100
        c = cat.lower()
        if 'code' in c or 'coding' in c:
            return 1
        if 'research' in c:
            return 2
        if 'communication' in c:
            return 3
        if 'other' in c:
            return 4
        if 'meetings' in c:
            return 100
        return 50

    return default_priority


def load_from_jsonl(jsonl_path: Path, config: Optional[Dict[str, Any]] = None) -> dict:
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
    mapping, priority_list = _load_category_settings(config)
    category_resolver = _build_categorizer(mapping)
    priority_func = _build_priority_func(priority_list)
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
    # Aggregate: build timeline intervals from successive events, then merge
    if len(events) < 2:
        print("Not enough events for duration calculation")
        return report
    events.sort(key=lambda e: e.get('timestamp', ''))

    # Build raw intervals from consecutive events. Each interval uses the previous
    # event's app and idle_seconds to determine whether it counts as active.
    raw_intervals = []
    prev = events[0]
    for event in events[1:]:
        t0 = prev.get('timestamp')
        t1 = event.get('timestamp')
        try:
            dt0 = datetime.fromisoformat(t0)
            dt1 = datetime.fromisoformat(t1)
        except Exception:
            prev = event
            continue
        duration = int((dt1 - dt0).total_seconds())
        data_section = prev.get('data', {}) if isinstance(prev.get('data', {}), dict) else {}
        app = prev.get('app') or data_section.get('app') or data_section.get('application') or 'Unknown'
        idle = prev.get('idle_seconds', 0) or data_section.get('idle_seconds', 0)
        if duration > 1 and (idle is None or int(idle) < 5):
            cat = category_resolver(app)
            raw_intervals.append({'start': dt0, 'end': dt1, 'secs': duration, 'app': app, 'category': cat})
            print(f"Interval {dt0.isoformat()} -> {dt1.isoformat()} ({duration}s) app={app} cat={cat}")
        prev = event

    if not raw_intervals:
        print("No active intervals found")
        return report

    # Merge intervals to create a timeline of non-overlapping active intervals
    raw_intervals.sort(key=lambda r: r['start'])
    merged = []
    cur = raw_intervals[0].copy()
    for r in raw_intervals[1:]:
        if r['start'] <= cur['end']:
            # overlapping; extend end if needed
            if r['end'] > cur['end']:
                cur['end'] = r['end']
        else:
            merged.append(cur)
            cur = r.copy()
    merged.append(cur)

    # Compute totals
    hourly_seconds = [0] * 24
    category_seconds = {}
    active_seconds = 0
    meeting_seconds = 0

    # Build a cleaned timeline by splitting on all interval boundaries and assigning
    # each small segment to a single category using a priority rule. This produces
    # deterministic attribution and allows deep-work detection to operate on a
    # reattributed timeline (meetings reattributed when foreground activity exists).
    boundaries = set()
    for r in raw_intervals:
        boundaries.add(r['start'])
        boundaries.add(r['end'])
    boundaries = sorted(boundaries)

    cleaned = []
    for i in range(len(boundaries) - 1):
        s = boundaries[i]
        e = boundaries[i+1]
        if e <= s:
            continue
        # find raw intervals that cover [s,e]
        covering = [r for r in raw_intervals if r['start'] <= s and r['end'] >= e]
        if not covering:
            continue
        # choose category by highest priority non-meeting coverer, else meeting
        chosen = None
        best_pr = 999
        for r in covering:
            pr = priority_func(r['category'])
            if pr < best_pr:
                best_pr = pr
                chosen = r['category']
        secs = int((e - s).total_seconds())
        cleaned.append({'start': s, 'end': e, 'secs': secs, 'category': chosen or 'Other', 'app': covering[0].get('app')})

    # Merge adjacent cleaned segments with same category
    merged_by_cat = []
    if cleaned:
        cur = cleaned[0].copy()
        for seg in cleaned[1:]:
            if seg['category'] == cur['category'] and seg['start'] == cur['end']:
                cur['end'] = seg['end']
                cur['secs'] += seg['secs']
            else:
                merged_by_cat.append(cur)
                cur = seg.copy()
        merged_by_cat.append(cur)

    # Recompute totals from cleaned/merged timeline
    hourly_seconds = [0] * 24
    category_seconds = {}
    active_seconds = 0
    meeting_seconds = 0
    for seg in merged_by_cat:
        secs = seg['secs']
        active_seconds += secs
        cat = seg.get('category', 'Other')
        category_seconds[cat] = category_seconds.get(cat, 0) + secs
        if cat and cat.lower() == 'meetings':
            meeting_seconds += secs
        # distribute into hourly buckets by overlap
        s = seg['start']
        e = seg['end']
        cursor = s
        from datetime import timedelta
        while cursor < e:
            hour_end = datetime(cursor.year, cursor.month, cursor.day, cursor.hour, 59, 59, tzinfo=cursor.tzinfo)
            if hour_end > e:
                hour_end = e
            overlap = int((hour_end - cursor).total_seconds()) + 1
            hourly_seconds[cursor.hour] += overlap
            cursor = hour_end + timedelta(seconds=1)

    # Export cleaned timeline segments into report for UI rendering
    timeline_export = []
    for seg in merged_by_cat:
        secs = seg['secs']
        mins = int(secs / 60)
        timeline_export.append({
            'start': seg['start'].strftime('%H:%M'),
            'end': seg['end'].strftime('%H:%M'),
            'seconds': secs,
            'minutes': mins,
            'category': seg.get('category', 'Other'),
            'app': seg.get('app') or ''
        })
    report['timeline'] = timeline_export

    # Active seconds = sum of merged intervals
    from datetime import timedelta
    for m in merged:
        secs = int((m['end'] - m['start']).total_seconds())
        active_seconds += secs
        # distribute into hourly buckets by overlap
        s = m['start']
        e = m['end']
        cursor = s
        while cursor < e:
            hour_end = datetime(cursor.year, cursor.month, cursor.day, cursor.hour, 59, 59, tzinfo=cursor.tzinfo)
            if hour_end > e:
                hour_end = e
            overlap = int((hour_end - cursor).total_seconds()) + 1
            hourly_seconds[cursor.hour] += overlap
            cursor = hour_end + timedelta(seconds=1)

    # Compute focus as active - meetings (simple attribution rule)
    total_focus_seconds = max(0, active_seconds - meeting_seconds)

    # Coverage window: from first merged start to last merged end
    coverage_start = merged[0]['start']
    coverage_end = merged[-1]['end']
    report['overview']['coverage_window'] = f"{coverage_start.strftime('%H:%M')}–{coverage_end.strftime('%H:%M')}"
    report['overview']['focus_time'] = seconds_to_hhmm(total_focus_seconds)
    report['overview']['meetings_time'] = seconds_to_hhmm(meeting_seconds)
    report['overview']['active_time'] = seconds_to_hhmm(active_seconds)

    # By-category from category_seconds
    for cat, secs in category_seconds.items():
        report['by_category'][cat] = seconds_to_hhmm(secs)

    max_seconds = max(hourly_seconds) if any(hourly_seconds) else 1
    for hour in range(24):
        secs = hourly_seconds[hour]
        report['hourly_focus'][hour]['time'] = seconds_to_hhmm(secs)
        report['hourly_focus'][hour]['pct'] = f"{int(100 * secs / max_seconds) if max_seconds else 0}%"

    # Detect deep work blocks from the cleaned/merged timeline: non-meeting contiguous segments >=25min
    deep_blocks = []
    threshold = 25 * 60
    current_block_start = None
    current_block_end = None
    for seg in merged_by_cat:
        if seg['category'] and seg['category'].lower() == 'meetings':
            # finalize any current block
            if current_block_start and (current_block_end - current_block_start).total_seconds() >= threshold:
                secs = int((current_block_end - current_block_start).total_seconds())
                deep_blocks.append({'start': current_block_start.strftime('%H:%M'), 'end': current_block_end.strftime('%H:%M'), 'duration': seconds_to_hhmm(secs), 'seconds': secs, 'minutes': int(secs/60)})
            current_block_start = None
            current_block_end = None
            continue
        # non-meeting segment
        if not current_block_start:
            current_block_start = seg['start']
            current_block_end = seg['end']
        else:
            # if contiguous (no gap) extend, else finalize and start new
            gap = (seg['start'] - current_block_end).total_seconds()
            if gap <= 60:
                current_block_end = seg['end']
            else:
                if (current_block_end - current_block_start).total_seconds() >= threshold:
                    secs = int((current_block_end - current_block_start).total_seconds())
                    deep_blocks.append({'start': current_block_start.strftime('%H:%M'), 'end': current_block_end.strftime('%H:%M'), 'duration': seconds_to_hhmm(secs), 'seconds': secs, 'minutes': int(secs/60)})
                current_block_start = seg['start']
                current_block_end = seg['end']
    # finalize tail
    if current_block_start and (current_block_end - current_block_start).total_seconds() >= threshold:
        secs = int((current_block_end - current_block_start).total_seconds())
        deep_blocks.append({'start': current_block_start.strftime('%H:%M'), 'end': current_block_end.strftime('%H:%M'), 'duration': seconds_to_hhmm(secs), 'seconds': secs, 'minutes': int(secs/60)})

    report['deep_work_blocks'] = deep_blocks
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
        # Ensure `overview.focus_time` exists: if generator was run from an existing
        # ActivityReport JSON that lacks `focus_time`, compute it from `hourly_focus`.
        overview = data.get('overview', {}) or {}
        if not overview.get('focus_time'):
            hf = data.get('hourly_focus', [])
            total_minutes = 0
            for item in hf:
                # items may be objects with a 'time' field or simple strings
                if isinstance(item, dict):
                    t = item.get('time', '00:00')
                else:
                    t = item or '00:00'
                total_minutes += hhmm_to_minutes(t)
            # convert minutes to seconds for seconds_to_hhmm
            overview['focus_time'] = seconds_to_hhmm(total_minutes * 60)
        data['overview'] = overview
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
