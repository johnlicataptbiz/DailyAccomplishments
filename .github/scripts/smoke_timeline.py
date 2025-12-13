#!/usr/bin/env python3
"""Smoke test for timeline fields in ActivityReport JSON files.
Usage: python3 .github/scripts/smoke_timeline.py reports/<date>/ActivityReport-<date>.json
Exits 0 when checks pass, 1 otherwise.
"""
import sys, json
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: smoke_timeline.py <report.json>")
    sys.exit(2)

p = Path(sys.argv[1])
if not p.exists():
    print(f"Report not found: {p}")
    sys.exit(3)

j = json.loads(p.read_text())
errors = []
if 'timeline' not in j or not isinstance(j['timeline'], list):
    errors.append('timeline missing or not array')
if 'deep_work_blocks' not in j or not isinstance(j['deep_work_blocks'], list):
    errors.append('deep_work_blocks missing or not array')
else:
    for i, b in enumerate(j['deep_work_blocks']):
        if 'seconds' not in b:
            errors.append(f'deep_work_blocks[{i}].seconds missing')
        elif not isinstance(b['seconds'], (int, float)):
            errors.append(f'deep_work_blocks[{i}].seconds not numeric')

if errors:
    print('SMOKE FAIL:')
    for e in errors:
        print(' -', e)
    sys.exit(4)
print('SMOKE OK')
sys.exit(0)

