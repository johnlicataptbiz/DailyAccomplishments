import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl, hhmm_to_minutes


def test_meeting_attribution_overlap(tmp_path):
    # Create a meeting interval (Zoom) from 10:00 to 10:30 and a Code interval overlapping 10:10-10:20
    start = datetime(2025, 12, 10, 10, 0, 0)
    events = []
    t = start
    # Meeting events every minute for 31 minutes
    for i in range(31):
        events.append({'timestamp': t.isoformat(), 'app': 'Zoom', 'idle_seconds': 0})
        t += timedelta(seconds=60)
    # Insert code events overlapping between 10:10 and 10:20
    t2 = datetime(2025,12,10,10,10,0)
    for i in range(11):
        events.append({'timestamp': t2.isoformat(), 'app': 'Code', 'idle_seconds': 0})
        t2 += timedelta(seconds=60)

    # Write shuffled events so sorter is exercised
    jl = tmp_path / 'meet.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')

    report = load_from_jsonl(jl)
    # meeting time should be less than full 30 minutes due to overlap attribution
    meetings = report['overview'].get('meetings_time')
    meeting_mins = hhmm_to_minutes(meetings)
    assert meeting_mins < 30, f"Meeting minutes not reduced: {meeting_mins}"


def test_config_mapping_applied(tmp_path):
    start = datetime(2025, 12, 10, 12, 0, 0)
    events = []
    t = start
    for _ in range(11):
        events.append({'timestamp': t.isoformat(), 'app': 'Figma', 'idle_seconds': 0})
        t += timedelta(seconds=60)

    jl = tmp_path / 'design.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')

    config = {
        'analytics': {
            'category_priority': ['Design', 'Other'],
            'category_mapping': {
                'Design': ['Figma']
            }
        }
    }
    report = load_from_jsonl(jl, config=config)
    design_time = hhmm_to_minutes(report['by_category'].get('Design'))
    assert design_time == 10, f"Expected 10 minutes in Design category, got {design_time}"
