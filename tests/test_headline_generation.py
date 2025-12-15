import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl


def test_headlines_are_generated(tmp_path):
    # Create a simple report with some focused time and a meeting
    start = datetime(2025, 12, 14, 9, 0, 0)
    events = []
    t = start
    # 90 minutes of Code activity
    for _ in range(180):
        events.append({'timestamp': t.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t += timedelta(seconds=30)
    # 60 minutes of Zoom
    for _ in range(120):
        events.append({'timestamp': t.isoformat(), 'app': 'Zoom', 'idle_seconds': 0})
        t += timedelta(seconds=30)

    jl = tmp_path / 'headlines.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')

    report = load_from_jsonl(jl)
    assert 'headline_variations' in report and isinstance(report['headline_variations'], list)
    assert len(report['headline_variations']) >= 1
    assert 'headline_batch_id' in report and report['headline_batch_id'] is not None
