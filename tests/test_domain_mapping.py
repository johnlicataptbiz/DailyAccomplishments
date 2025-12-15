import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import load_from_jsonl, hhmm_to_minutes


def test_domain_mapping_applies(tmp_path):
    start = datetime(2025, 12, 15, 8, 0, 0)
    events = []
    t = start
    # 40 minutes of Chrome activity on github.com (one event every 30s -> 80 events)
    for _ in range(80):
        events.append({'timestamp': t.isoformat(), 'app': 'Google Chrome', 'idle_seconds': 0, 'data': {'url': 'https://github.com/org/repo'}})
        t += timedelta(seconds=30)

    jl = tmp_path / 'domain.jsonl'
    with open(jl, 'w') as f:
        for e in events:
            f.write(json.dumps(e) + '\n')

    config = {
        'analytics': {
            'domain_mapping': {
                'github.com': 'Coding'
            }
        }
    }

    report = load_from_jsonl(jl, config=config)
    coding_mins = hhmm_to_minutes(report['by_category'].get('Coding'))
    # Expect roughly 40 minutes
    assert coding_mins >= 39 and coding_mins <= 41, f"Expected ~40 minutes Coding, got {coding_mins}"
