#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON or JSONL logs - DEBUG VERSION.

This is a debug version of generate_reports.py that includes verbose logging
to help diagnose issues with report generation.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv

# Import the main functions from generate_reports
try:
    from tools.generate_reports import (
        load_data, 
        hhmm_to_minutes, 
        seconds_to_hhmm,
        load_from_jsonl,
        categorize_app
    )
    print("DEBUG: Successfully imported functions from generate_reports")
except ImportError as e:
    print(f"DEBUG: Failed to import from generate_reports: {e}")
    # Fallback to local directory if tools. import fails
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_reports import (
            load_data, 
            hhmm_to_minutes, 
            seconds_to_hhmm,
            load_from_jsonl,
            categorize_app
        )
        print("DEBUG: Successfully imported functions from current directory")
    except ImportError as e2:
        print(f"DEBUG: Failed to import from current directory: {e2}")
        sys.exit(1)

BASE = Path(__file__).resolve().parents[1]
DEFAULT_DATE = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d')

def write_csv_debug(path, rows, headers):
    """Write CSV with debug output."""
    print(f"DEBUG: Writing CSV to {path} with {len(rows)} rows")
    print(f"DEBUG: CSV headers: {headers}")
    if rows:
        print(f"DEBUG: First row: {rows[0]}")
        print(f"DEBUG: Last row: {rows[-1]}")
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
    print(f"DEBUG: CSV write complete for {path}")

def main():
    """Main debug report generation with verbose output."""
    print(f"DEBUG: Starting debug report generation at {datetime.now()}")
    print(f"DEBUG: BASE directory: {BASE}")
    print(f"DEBUG: DEFAULT_DATE: {DEFAULT_DATE}")
    
    date = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"DEBUG: Date argument: {date or 'None (using default)'}")
    
    try:
        print("DEBUG: Loading data...")
        data = load_data(date)
        print(f"DEBUG: Data loaded successfully")
        print(f"DEBUG: Data keys: {list(data.keys()) if data else 'None'}")
        print(f"DEBUG: Data overview: {data.get('overview', {})}")
        print(f"DEBUG: Categories: {list(data.get('by_category', {}).keys())}")
    except FileNotFoundError as e:
        print(f"DEBUG ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"DEBUG ERROR: Unexpected error loading data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Determine output directory
    date_str = data.get('date') or date or DEFAULT_DATE
    out_dir = BASE / 'reports' / date_str
    print(f"DEBUG: Output directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG: Output directory created/verified")
    
    # Write ActivityReport JSON
    try:
        overview = data.get('overview', {}) or {}
        if 'coverage_window' not in overview:
            overview['coverage_window'] = ''
        if not overview.get('focus_time'):
            hf = data.get('hourly_focus', [])
            total_minutes = 0
            for item in hf:
                if isinstance(item, dict):
                    t = item.get('time', '00:00')
                else:
                    t = item or '00:00'
                total_minutes += hhmm_to_minutes(t)
            # Convert minutes to seconds for seconds_to_hhmm (which expects seconds)
            overview['focus_time'] = seconds_to_hhmm(total_minutes * 60)
        data['overview'] = overview
        
        # Ensure schema-required fields
        if not isinstance(data.get('timeline'), list):
            data['timeline'] = []
        if not isinstance(data.get('deep_work_blocks'), list):
            data['deep_work_blocks'] = []
        bh = data.get('browser_highlights')
        if not isinstance(bh, dict):
            bh = {}
        if not isinstance(bh.get('top_domains'), list):
            bh['top_domains'] = []
        if not isinstance(bh.get('top_pages'), list):
            bh['top_pages'] = []
        data['browser_highlights'] = bh
        
        json_path = out_dir / f'ActivityReport-{date_str}.json'
        print(f"DEBUG: Writing ActivityReport JSON to {json_path}")
        json_path.write_text(json.dumps(data, indent=2))
        
        fallback_path = out_dir / f'daily-report-{date_str}.json'
        print(f"DEBUG: Writing fallback JSON to {fallback_path}")
        fallback_path.write_text(json.dumps(data, indent=2))
        
        print(f"DEBUG: JSON files written successfully")
    except Exception as e:
        print(f"DEBUG ERROR: Failed to write JSON: {e}")
        import traceback
        traceback.print_exc()
    
    # Hourly focus CSV
    print("DEBUG: Generating hourly focus CSV...")
    hf = data.get('hourly_focus', [])
    print(f"DEBUG: Found {len(hf)} hourly focus entries")
    hf_rows = []
    for item in hf:
        time_str = item.get('time', '00:00')
        minutes = hhmm_to_minutes(time_str)
        pct_str = item.get('pct', '0%').rstrip('%')
        try:
            pct = int(pct_str)
        except ValueError:
            pct = 0
        if minutes > 60:
            minutes = min(60, int(60 * pct / 100))
        hf_rows.append([item.get('hour'), time_str, item.get('pct'), minutes])
    write_csv_debug(out_dir / f'hourly_focus-{date_str}.csv', hf_rows, ['hour', 'time', 'pct', 'minutes'])
    
    # Top domains CSV
    print("DEBUG: Generating top domains CSV...")
    domains = data.get('browser_highlights', {}).get('top_domains', [])
    print(f"DEBUG: Found {len(domains)} top domains")
    dom_rows = [[d.get('domain'), d.get('visits')] for d in domains]
    write_csv_debug(out_dir / f'top_domains-{date_str}.csv', dom_rows, ['domain', 'visits'])
    
    # Category distribution CSV
    print("DEBUG: Generating category distribution CSV...")
    cats = data.get('by_category', {})
    print(f"DEBUG: Found {len(cats)} categories: {list(cats.keys())}")
    cat_rows = []
    for k, v in cats.items():
        minutes = hhmm_to_minutes(v)
        cat_rows.append([k, v, minutes])
        print(f"DEBUG: Category {k}: {v} ({minutes} minutes)")
    write_csv_debug(out_dir / f'category_distribution-{date_str}.csv', cat_rows, ['category', 'time', 'minutes'])
    
    # Generate charts
    print("DEBUG: Attempting to generate charts...")
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        print("DEBUG: Matplotlib imported successfully")
    except Exception as e:
        print(f'DEBUG: matplotlib required to generate charts: {e}')
        print('DEBUG: CSVs written (charts skipped)')
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
            except ValueError:
                m = min(60, m)
        minutes.append(m)
    
    print(f"DEBUG: Generating hourly focus chart with {len(hours)} data points")
    plt.figure(figsize=(10,4))
    plt.bar(hours, minutes, color='#2563eb')
    plt.xlabel('Hour')
    plt.ylabel('Focused minutes')
    plt.title(f'Hourly Focus — {title_date}')
    plt.xticks(hours)
    plt.tight_layout()
    chart_path = out_dir / f'hourly_focus-{title_date}.svg'
    plt.savefig(chart_path)
    plt.close()
    print(f"DEBUG: Hourly chart saved to {chart_path}")
    
    # Category pie chart
    labels = [r[0] for r in cat_rows]
    sizes = [r[2] for r in cat_rows]
    if any(sizes):
        print(f"DEBUG: Generating category pie chart with {len(labels)} categories")
        plt.figure(figsize=(6,6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title(f'Time by Category — {title_date}')
        plt.tight_layout()
        pie_path = out_dir / f'category_distribution-{title_date}.svg'
        plt.savefig(pie_path)
        plt.close()
        print(f"DEBUG: Category chart saved to {pie_path}")
    else:
        print(f"DEBUG: No category data for {title_date}, skipping pie chart")
    
    print(f'DEBUG: All outputs written to {out_dir}')
    print(f"DEBUG: Report generation complete at {datetime.now()}")

if __name__ == '__main__':
    main()
