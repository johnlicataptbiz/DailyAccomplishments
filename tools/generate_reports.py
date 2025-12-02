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
        minutes = hhmm_to_minutes(item.get('time', '00:00'))
        hf_rows.append([item.get('hour'), item.get('time'), item.get('pct'), minutes])
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
    minutes = [hhmm_to_minutes(x['time']) for x in hf]
    plt.figure(figsize=(10,4))
    plt.bar(hours, minutes, color='#2563eb')
    plt.xlabel('Hour')
    plt.ylabel('Focused minutes')
    plt.title('Hourly Focus — 2025-12-01')
    plt.xticks(hours)
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'hourly_focus.png')
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
        plt.close()

    print('CSVs and charts written to', OUT_DIR)

if __name__ == '__main__':
    main()
