import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure repo root is on PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl, seconds_to_hhmm


def make_events(start, count=5, spacing=60):
    events = []
    t = start
    for i in range(count):
        events.append({'timestamp': t.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t = t + timedelta(seconds=spacing)
    return events


def test_interval_merge(tmp_path):
    start = datetime(2025,12,10,9,0,0)
    events = make_events(start, count=4, spacing=30)
    jl = tmp_path / 'test.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')
    report = load_from_jsonl(jl)
    # active time should be > 0
    assert 'overview' in report
    assert report['overview']['active_time'] != '00:00'


def test_deep_work_threshold(tmp_path):
    # create events spanning 30 minutes
    start = datetime(2025,12,10,10,0,0)
    events = []
    t = start
    for i in range(31):
        events.append({'timestamp': t.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t += timedelta(seconds=60)
    jl = tmp_path / 'dw.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')
    report = load_from_jsonl(jl)
    # deep_work_blocks present
    assert 'deep_work_blocks' in report
    assert isinstance(report['deep_work_blocks'], list)
