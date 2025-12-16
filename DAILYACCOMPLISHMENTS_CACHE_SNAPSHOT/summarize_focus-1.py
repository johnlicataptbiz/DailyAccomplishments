"""
scripts/summarize_focus.py
Regenerates focus_summary.csv, focus_summary.svg, and focus_summary.png
from ActivityReport-YYYY-MM-DD.json files in repo root.

Usage:
    python3 scripts/summarize_focus.py

This script is intentionally simple and uses matplotlib to draw the chart.
"""
import json
import re
import csv
import pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

pattern = re.compile(r'^(\d+):(\d{2})$')

def to_seconds(s):
    if not s:
        return 0
    m = pattern.match(s.strip())
    if not m:
        return 0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60


dates = ['2025-12-01', '2025-12-02', '2025-12-03']
rows = []
for d in dates:
    p = f'ActivityReport-{d}.json'
    if not pathlib.Path(p).exists():
        rows.append({'date': d, 'focus_time': '', 'focus_minutes': '', 'hourly_sum_minutes': '', 'focus_05_23_minutes': '', 'coverage_window': ''})
        continue
    data = json.load(open(p))
    overview = data.get('overview', {})
    ft = overview.get('focus_time')
    ft_secs = to_seconds(ft)
    hourly = data.get('hourly_focus', [])
    hourly_secs = sum(to_seconds(e.get('time')) for e in hourly)
    hourly_5to23_secs = sum(to_seconds(e.get('time')) for e in hourly if isinstance(e.get('hour'), int) and 5 <= e['hour'] <= 23)
    cov = overview.get('coverage_window', '')
    rows.append({'date': d, 'focus_time': ft or '', 'focus_minutes': str(ft_secs // 60), 'hourly_sum_minutes': str(hourly_secs // 60), 'focus_05_23_minutes': str(hourly_5to23_secs // 60), 'coverage_window': cov})

csv_path = 'focus_summary.csv'
with open(csv_path, 'w', newline='', encoding='utf8') as f:
    writer = csv.DictWriter(f, fieldnames=['date', 'focus_time', 'focus_minutes', 'hourly_sum_minutes', 'focus_05_23_minutes', 'coverage_window'])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
print('Wrote', csv_path)

# Chart
labels = [r['date'] for r in rows]
values = [int(r['focus_minutes']) if r['focus_minutes'] else (int(r['hourly_sum_minutes']) if r['hourly_sum_minutes'] else 0) for r in rows]
plt.figure(figsize=(6, 3))
bars = plt.bar(labels, values, color='#4C72B0')
plt.title('Focus time (minutes) per day')
plt.ylabel('Minutes')
for bar, val in zip(bars, values):
    h = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2, h + 1, str(val), ha='center', va='bottom', fontsize=8)
plt.tight_layout()
svg_path = 'focus_summary.svg'
png_path = 'focus_summary.png'
plt.savefig(svg_path, format='svg')
plt.savefig(png_path, dpi=150)
print('Wrote', svg_path, 'and', png_path)
