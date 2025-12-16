import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.generate_reports import _generate_headlines


def make_report(focus_minutes=0, meeting_minutes=0, deep_blocks=None, by_category=None, coverage='08:00–20:00'):
    d = {
        'overview': {'focus_time': f"{focus_minutes//60:02d}:{focus_minutes%60:02d}", 'meetings_time': f"{meeting_minutes//60:02d}:{meeting_minutes%60:02d}", 'coverage_window': coverage},
        'by_category': by_category or {},
        'deep_work_blocks': deep_blocks or []
    }
    return d


def test_focus_templates():
    r = make_report(focus_minutes=150, deep_blocks=[{'duration':'01:10'}])
    vars, bid = _generate_headlines(r)
    assert isinstance(vars, list) and len(vars) >= 1
    assert any('Focused' in v or 'Deep-focus' in v for v in vars)
    assert bid is not None


def test_meeting_templates():
    r = make_report(focus_minutes=30, meeting_minutes=130)
    vars, bid = _generate_headlines(r)
    assert any('Meetings' in v or 'Meeting-heavy' in v for v in vars)


def test_top_category_and_snapshot():
    r = make_report(focus_minutes=45, meeting_minutes=10, by_category={'Coding':'00:45'})
    vars, bid = _generate_headlines(r)
    assert any('Top category' in v or 'Snapshot' in v for v in vars)
