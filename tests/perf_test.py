import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure repo root is on PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl


def generate_large_jsonl(path: Path, events=1000):
    start = datetime(2025,12,1,8,0,0)
    t = start
    with open(path, 'w') as f:
        for i in range(events):
            evt = {'timestamp': t.isoformat(), 'app': 'Code' if i%5 else 'Zoom', 'idle_seconds': 0}
            f.write(json.dumps(evt) + '\n')
            t += timedelta(seconds=30)


def test_perf_1k(tmp_path):
    jl = tmp_path / 'big.jsonl'
    generate_large_jsonl(jl, events=1000)
    t0 = time.time()
    report = load_from_jsonl(jl)
    t1 = time.time()
    duration = t1 - t0
    # Ensure generator completes within reasonable time (5s here as a baseline)
    assert duration < 5.0, f"Generator too slow: {duration}s"
    assert report is not None
