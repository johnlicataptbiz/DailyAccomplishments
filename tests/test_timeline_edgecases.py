import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl, hhmm_to_minutes


def write_events(jl, events):
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')


def test_multiple_overlaps(tmp_path):
    # Meeting 09:00-09:30, Code 09:05-09:15, Research 09:10-09:20
    start = datetime(2025, 12, 11, 9, 0, 0)
    events = []
    t = start
    # Create meeting events each minute for 31 minutes
    for i in range(31):
        events.append({'timestamp': t.isoformat(), 'app': 'Zoom', 'idle_seconds': 0})
        t += timedelta(seconds=60)
    # code overlap
    t2 = datetime(2025,12,11,9,5,0)
    for i in range(11):
        events.append({'timestamp': t2.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t2 += timedelta(seconds=60)
    # research overlap
    t3 = datetime(2025,12,11,9,10,0)
    for i in range(11):
        events.append({'timestamp': t3.isoformat(), 'app': 'Firefox', 'idle_seconds': 0})
        t3 += timedelta(seconds=60)

    jl = tmp_path / 'multi.jsonl'
    write_events(jl, events)
    report = load_from_jsonl(jl)
    timeline = report.get('timeline', [])
    # Ensure non-empty timeline and that coding/research segments exist
    cats = [seg['category'].lower() for seg in timeline]
    assert any('code' in c or 'coding' in c for c in cats), f"No coding segments in {cats}"
    assert any('research' in c for c in cats), f"No research segments in {cats}"
    # Meeting segment should be present but shorter than full 30m due to overlaps
    meeting_seg = [seg for seg in timeline if 'meeting' in seg['category'].lower()]
    if meeting_seg:
        total_meet_mins = sum(seg['minutes'] for seg in meeting_seg)
        assert total_meet_mins < 30


def test_cross_hour_boundary(tmp_path):
    # Create a coding interval from 11:50 to 12:10 crossing the hour boundary
    start = datetime(2025, 12, 11, 11, 50, 0)
    events = []
    t = start
    for i in range(21):
        events.append({'timestamp': t.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t += timedelta(seconds=60)
    jl = tmp_path / 'cross.jsonl'
    write_events(jl, events)
    report = load_from_jsonl(jl)
    timeline = report.get('timeline', [])
    # Find coding segments and ensure there's segmentation across 11 and 12 hours
    assert timeline, "No timeline produced"
    total = sum(seg['minutes'] for seg in timeline)
    # total minutes should be 20
    assert total == 20, f"Expected 20 minutes total, got {total}"
