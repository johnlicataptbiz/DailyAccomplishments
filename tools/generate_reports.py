#!/usr/bin/env python3
"""Generate CSV exports and charts from ActivityReport JSON."""
import json
from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / 'ActivityReport-2025-12-01.json'
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

def main():
    data = json.loads(INPUT.read_text())

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
    hours = [int(x['hour']) for x in hf]
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
    plt.title('Hourly Focus — 2025-12-01')
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
        plt.title('Time by Category — 2025-12-01')
        plt.tight_layout()
        plt.savefig(OUT_DIR / 'category_distribution.png')
        plt.savefig(OUT_DIR / 'category_distribution.svg')
        plt.close()

    print('CSVs and charts written to', OUT_DIR)

if __name__ == '__main__':
    main()
