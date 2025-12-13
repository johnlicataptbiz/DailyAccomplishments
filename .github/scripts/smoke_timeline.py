#!/usr/bin/env python3
"""Smoke test for timeline fields in ActivityReport JSON files.
Usage: python3 .github/scripts/smoke_timeline.py reports/<date>/ActivityReport-<date>.json
Exits 0 when checks pass, 1 otherwise.
"""
import sys, json
from pathlib import Path

DEBUG = '--debug' in sys.argv or '-v' in sys.argv

def debug_print(msg):
    """Print debug messages when debug mode is enabled."""
    if DEBUG:
        print(f"[DEBUG] {msg}")

if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
    print("Usage: smoke_timeline.py <report.json> [--debug|-v]")
    sys.exit(2)

# Get the report path (skip debug flags)
non_flag_args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
report_path = non_flag_args[0] if non_flag_args else None

if not report_path:
    print("Usage: smoke_timeline.py <report.json> [--debug|-v]")
    sys.exit(2)

p = Path(report_path)
debug_print(f"Checking report file: {p}")

if not p.exists():
    print(f"Report not found: {p}")
    sys.exit(3)

debug_print(f"Reading JSON from {p}")
try:
    j = json.loads(p.read_text())
    debug_print(f"JSON parsed successfully, top-level keys: {list(j.keys())}")
except json.JSONDecodeError as e:
    print(f"JSON decode error in {p}: {e}")
    sys.exit(5)

errors = []

# Check timeline field
if 'timeline' not in j:
    errors.append('timeline missing')
    debug_print("timeline field is missing")
elif not isinstance(j['timeline'], list):
    errors.append('timeline not array')
    debug_print(f"timeline is not an array, type: {type(j['timeline'])}")
else:
    debug_print(f"timeline is present and array with {len(j['timeline'])} items")

# Check deep_work_blocks field
if 'deep_work_blocks' not in j:
    errors.append('deep_work_blocks missing')
    debug_print("deep_work_blocks field is missing")
elif not isinstance(j['deep_work_blocks'], list):
    errors.append('deep_work_blocks not array')
    debug_print(f"deep_work_blocks is not an array, type: {type(j['deep_work_blocks'])}")
else:
    debug_print(f"deep_work_blocks is present and array with {len(j['deep_work_blocks'])} items")
    for i, b in enumerate(j['deep_work_blocks']):
        if not isinstance(b, dict):
            errors.append(f'deep_work_blocks[{i}] not an object')
            debug_print(f"deep_work_blocks[{i}] is not a dict, type: {type(b)}")
            continue
        if 'seconds' not in b:
            errors.append(f'deep_work_blocks[{i}].seconds missing')
            debug_print(f"deep_work_blocks[{i}].seconds is missing, keys: {list(b.keys())}")
        elif not isinstance(b['seconds'], (int, float)):
            errors.append(f'deep_work_blocks[{i}].seconds not numeric')
            debug_print(f"deep_work_blocks[{i}].seconds is not numeric, type: {type(b['seconds'])}, value: {b['seconds']}")
        else:
            debug_print(f"deep_work_blocks[{i}].seconds = {b['seconds']} (valid)")

if errors:
    print('SMOKE FAIL:')
    for e in errors:
        print(' -', e)
    sys.exit(4)

print('SMOKE OK')
debug_print("All checks passed")
sys.exit(0)
