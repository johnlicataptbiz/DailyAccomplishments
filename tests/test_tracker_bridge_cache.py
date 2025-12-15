import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure the repository root is importable so tools.* modules resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.tracker_bridge import ActivityTrackerBridge  # noqa: E402


def test_duplicate_filter_respects_cache_window():
    """Events within the cache window are suppressed, later ones are allowed."""

    # Controlled clock values to exercise cache expiry
    base = datetime(2025, 1, 1, 12, 0, 0)
    ticks = [base, base + timedelta(seconds=1), base + timedelta(seconds=6)]

    def _now():
        return ticks.pop(0)

    bridge = ActivityTrackerBridge(cache_window_seconds=5, now_fn=_now)
    payload = {'app': 'Code', 'window_title': 'main.py', 'duration_seconds': 60}

    # First event should populate cache
    assert bridge._is_duplicate('focus_change', payload) is False
    # Second call within 5s window should be flagged as duplicate
    assert bridge._is_duplicate('focus_change', payload) is True
    # After 6s window elapsed, event should no longer be considered duplicate
    assert bridge._is_duplicate('focus_change', payload) is False

