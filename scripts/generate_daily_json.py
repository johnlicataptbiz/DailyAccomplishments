#!/usr/bin/env python3
"""
Generate Daily JSON Report from activity logs.

Implements 'Proposed Redesign' methodology:
- Precise timeline intervals (no hourly buckets)
- Explicit Meeting vs Focus separation
- Active Time = Direct sum of usage
- Coverage = First to Last activity
"""

import json
import os
import re
from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
LOGS_DIR = REPO_ROOT / "logs"

# Domain to category mapping
CATEGORY_MAP = {
    'slack.com': 'Communication',
    'mail.google.com': 'Communication',
    'gmail': 'Communication',
    'messages': 'Communication',
    'hubspot.com': 'Email/CRM',
    'salesforce.com': 'Email/CRM',
    'github.com': 'Coding',
    'stackoverflow.com': 'Coding',
    'vscode': 'Coding',
    'terminal': 'Coding',
    'code': 'Coding',
    'docs.google.com': 'Docs',
    'notion.so': 'Docs',
    'sheets.google.com': 'Docs',
    'calendar.google.com': 'Meetings',
    'zoom.us': 'Meetings',
    'meet.google.com': 'Meetings',
    'teams.microsoft.com': 'Meetings',
    'grok.com': 'Research',
    'chatgpt.com': 'Research',
    'claude.ai': 'Research',
    'google.com': 'Research',
}

# Apps that always count as "Focus" even if occurring during a meeting interval
FOCUS_OVERRIDE_APPS = ['Coding', 'Docs', 'Research']

class Timeline:
    """Manages time intervals to calculate precise duration metrics."""
    def __init__(self):
        # List of (start_dt, end_dt, category, app_name, source_type)
        self.intervals: List[Tuple[datetime, datetime, str, str, str]] = []

    def add(self, start: datetime, duration_seconds: float, category: str, app: str, type: str):
        if duration_seconds <= 0:
            return
        end = start + timedelta(seconds=duration_seconds)
        self.intervals.append((start, end, category, app, type))

    def _merge_intervals(self, interval_list):
        """Merge overlapping intervals in a list."""
        if not interval_list:
            return []
        # Sort by start time
        sorted_intervals = sorted(interval_list, key=lambda x: x[0])
        merged = []
        current_start, current_end = sorted_intervals[0][0], sorted_intervals[0][1]

        for next_start, next_end, *rest in sorted_intervals[1:]:
            if next_start < current_end:  # Overlap
                current_end = max(current_end, next_end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        merged.append((current_start, current_end))
        return merged

    def export_timeline(self) -> List[Dict[str, Any]]:
        """Export timeline intervals for the report."""
        timeline_export = []
        for start, end, category, app, etype in self.intervals:
            duration_seconds = int((end - start).total_seconds())
            timeline_export.append({
                'start': start.strftime('%H:%M'),
                'end': end.strftime('%H:%M'),
                'seconds': duration_seconds,
                'minutes': int(duration_seconds / 60),
                'category': category,
                'app': app
            })
        return timeline_export
    
    def _create_deep_work_block(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Create a deep work block dictionary from start and end times."""
        block_duration_seconds = (end - start).total_seconds()
        duration_minutes = block_duration_seconds / 60
        return {
            'start': start.strftime('%H:%M'),
            'end': end.strftime('%H:%M'),
            'duration': minutes_to_time_str(duration_minutes),
            'seconds': int(block_duration_seconds),
            'minutes': int(duration_minutes)
        }
    
    def detect_deep_work_blocks(self, threshold_minutes: int = 25, gap_tolerance_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Detect deep work blocks (contiguous non-meeting activity >= threshold).
        
        Args:
            threshold_minutes: Minimum duration for a block to be considered deep work (default: 25)
            gap_tolerance_seconds: Maximum gap between intervals to still be considered contiguous (default: 60)
        
        Returns:
            List of blocks with start, end, duration, seconds, minutes.
        """
        deep_blocks = []
        threshold_seconds = threshold_minutes * 60
        
        # Filter non-meeting intervals and sort by start time
        non_meeting = [
            (start, end, cat, app, etype) 
            for start, end, cat, app, etype in self.intervals 
            if cat != 'Meetings' and etype != 'meeting_end'
        ]
        
        if not non_meeting:
            return []
        
        non_meeting.sort(key=lambda x: x[0])
        
        current_block_start = None
        current_block_end = None
        
        for start, end, cat, app, etype in non_meeting:
            if not current_block_start:
                # Start new block
                current_block_start = start
                current_block_end = end
            else:
                # Check if contiguous (gap <= tolerance)
                gap_seconds = (start - current_block_end).total_seconds()
                if gap_seconds <= gap_tolerance_seconds:
                    # Extend current block
                    current_block_end = end
                else:
                    # Finalize current block if it meets threshold
                    block_duration = (current_block_end - current_block_start).total_seconds()
                    if block_duration >= threshold_seconds:
                        deep_blocks.append(self._create_deep_work_block(current_block_start, current_block_end))
                    # Start new block
                    current_block_start = start
                    current_block_end = end
        
        # Finalize last block
        if current_block_start:
            block_duration = (current_block_end - current_block_start).total_seconds()
            if block_duration >= threshold_seconds:
                deep_blocks.append(self._create_deep_work_block(current_block_start, current_block_end))
        
        return deep_blocks

    def calculate_metrics(self) -> Dict[str, float]:
        """
        Calculate Active, Meeting, and Focus time based on redesign logic.
        Returns duration in minutes.
        """
        if not self.intervals:
            return {'active': 0.0, 'meeting': 0.0, 'focus': 0.0}

        # 1. Total Active Time: Union of all window activity
        # Filter for direct user activity (window events) to determine "Active" presence
        active_events = [x for x in self.intervals if x[4] != 'meeting_end'] 
        
        merged_active = self._merge_intervals(active_events)
        total_active_sec = sum((end - start).total_seconds() for start, end in merged_active)

        # 2. Meeting Time: Union of all Meeting category events OR Explicit meeting logs
        meeting_events = [
            x for x in self.intervals 
            if x[2] == 'Meetings' or x[4] == 'meeting_end'
        ]
        merged_meeting = self._merge_intervals(meeting_events)
        total_meeting_sec = sum((end - start).total_seconds() for start, end in merged_meeting)

        # 3. Focus Time: Active Time excluding Meeting Intervals
        # BUT: "If overlap: attribute to foreground app" (if foreground is Focus-y)
        
        # Create a unified timeline of points.
        points = []
        for start, end, cat, app, etype in self.intervals:
            points.append((start, 'start', cat, app, etype))
            points.append((end, 'end', cat, app, etype))
        
        points.sort(key=lambda x: x[0])
        
        focus_seconds = 0.0
        
        if points:
            current_time = points[0][0]
            
            # State trackers
            active_windows = [] # Stack of active window categories
            active_meetings = 0
            
            for i in range(len(points)):
                time, type, cat, app, etype = points[i]
                
                # Calculate duration from prev point
                duration = (time - current_time).total_seconds()
                
                if duration > 0:
                    # Determine state for this segment
                    is_active = len(active_windows) > 0
                    in_meeting = active_meetings > 0
                    
                    if is_active:
                        foreground_cat = active_windows[-1] if active_windows else 'Other'
                        
                        if in_meeting:
                            # Overlap case: Only count if foreground is a focus app
                            if foreground_cat in FOCUS_OVERRIDE_APPS:
                                focus_seconds += duration
                        else:
                            # Normal active case: Count as focus
                            focus_seconds += duration

                # Update state
                if type == 'start':
                    if etype == 'meeting_end': # It's a meeting block
                        active_meetings += 1
                    elif cat == 'Meetings': # Window is a meeting app
                        active_meetings += 1
                        active_windows.append(cat)
                    else:
                        active_windows.append(cat)
                else: # end
                    if etype == 'meeting_end':
                        active_meetings -= 1
                    elif cat == 'Meetings':
                        active_meetings -= 1
                        if cat in active_windows: active_windows.remove(cat) # Simple remove (stack-ish)
                    else:
                        if cat in active_windows: active_windows.remove(cat)
                
                current_time = time

        return {
            'active_minutes': total_active_sec / 60.0,
            'meeting_minutes': total_meeting_sec / 60.0,
            'focus_minutes': focus_seconds / 60.0
        }

def _normalize_event(obj: dict) -> Optional[dict]:
    """Normalize various event schemas to a flat activity dict."""
    
    # Base extraction
    res = {}
    
    # 1. Timestamp
    if "timestamp" in obj:
        res["timestamp"] = obj["timestamp"]
    else:
        return None

    # 2. Type & Duration
    res["type"] = obj.get("type", "window_event")
    
    # Handle nested data
    data = obj.get("data", {}) if isinstance(obj.get("data"), dict) else obj
    
    # Duration
    if "duration_seconds" in data:
        res["duration_seconds"] = float(data["duration_seconds"])
    elif "duration_seconds" in obj:
        res["duration_seconds"] = float(obj["duration_seconds"])
    else:
        # Default fallback for window polls if missing
        res["duration_seconds"] = 5.0

    # 3. App & Window
    res["app"] = (
        data.get("app") or data.get("from_app") or data.get("to_app") or 
        ("Manual Entry" if obj.get("type") == "manual_entry" else "Unknown")
    )
    res["window"] = (
        data.get("window_title") or data.get("window") or data.get("description", "")
    )
    
    return res

def parse_activity_log(date_str):
    """Parse a day's activity log file with fallback to legacy locations."""
    primary = LOGS_DIR / f"activity-{date_str}.jsonl"
    fallback = LOGS_DIR / "daily" / f"{date_str}.jsonl"
    fallback_alt = LOGS_DIR / "daily" / f"activity-{date_str}.jsonl"

    log_file = None
    if primary.exists(): log_file = primary
    elif fallback.exists(): log_file = fallback
    elif fallback_alt.exists(): log_file = fallback_alt

    if not log_file:
        print(f"No log file found for {date_str}")
        return []

    print(f"Reading: {log_file}")
    activities = []
    with open(log_file, 'r') as f:
        for line in f:
            if not line.strip(): continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError: continue
            
            norm = _normalize_event(obj)
            if norm: activities.append(norm)
    return activities

def categorize_activity(app, window):
    """Determine category based on app and window title."""
    app_lower = app.lower()
    window_lower = window.lower()
    
    if 'terminal' in app_lower or 'iterm' in app_lower: return 'Coding'
    if 'code' in app_lower or 'vscode' in app_lower: return 'Coding'
    if 'slack' in app_lower: return 'Communication'
    if 'messages' in app_lower or 'mail' in app_lower: return 'Communication'
    if 'zoom' in app_lower or 'teams' in app_lower: return 'Meetings'
    if 'finder' in app_lower: return 'Other'
    
    if 'chrome' in app_lower or 'safari' in app_lower or 'firefox' in app_lower:
        for domain, category in CATEGORY_MAP.items():
            if domain in window_lower: return category
        return 'Research'
    
    return 'Other'

def extract_domain(window_title):
    """Extract domain from browser window title."""
    for sep in [' - ', ' | ', ' — ']:
        if sep in window_title:
            parts = window_title.rsplit(sep, 1)
            if len(parts) == 2 and '.' in parts[1]:
                return parts[1].strip().lower()
    match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', window_title)
    if match: return match.group(1).lower()
    return None

def minutes_to_time_str(minutes):
    """Convert minutes to HH:MM format."""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"

def generate_report(date_str=None):
    """Generate the daily report JSON using precise timeline logic."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    activities = parse_activity_log(date_str)
    if not activities: return None
    
    # Initialize Aggregators
    timeline = Timeline()
    app_time = defaultdict(float)
    category_time = defaultdict(float)
    domain_visits = defaultdict(int)
    page_visits = defaultdict(int)
    window_time = defaultdict(float)
    hourly_minutes = defaultdict(float)
    
    first_ts = None
    last_ts = None
    
    # Process Activities
    for activity in activities:
        ts = datetime.fromisoformat(activity['timestamp'])
        duration = activity.get('duration_seconds', 0)
        app = activity.get('app', 'Unknown')
        window = activity.get('window', '')
        etype = activity.get('type', 'window_event')
        
        # Coverage
        if first_ts is None or ts < first_ts: first_ts = ts
        if last_ts is None or ts > last_ts: last_ts = ts
        
        category = categorize_activity(app, window)
        
        # Add to Timeline
        timeline.add(ts, duration, category, app, etype)
        
        # Standard Aggregates (Keep for breakdowns)
        dur_min = duration / 60.0
        hour = ts.hour
        
        app_time[app] += dur_min
        category_time[category] += dur_min
        hourly_minutes[hour] += dur_min
        
        window_key = f"{app} — {window[:50]}" if window else app
        window_time[window_key] += dur_min

        # Browser stats
        # NOTE: Do NOT infer domains from window titles here.
        # Real browser stats come from scripts/import_browser_history.py (URLs from history DB).
        pass

    # Calculate Precise Metrics
    metrics = timeline.calculate_metrics()
    
    # Hourly Focus for Chart
    hourly_focus = []
    max_hourly = max(hourly_minutes.values()) if hourly_minutes else 1
    for hour in range(24):
        mins = hourly_minutes.get(hour, 0)
        pct = int((mins / max_hourly) * 100) if max_hourly > 0 else 0
        hourly_focus.append({
            'hour': hour,
            'time': minutes_to_time_str(mins),
            'pct': f"{pct}%"
        })
    
    # Coverage String
    if first_ts and last_ts:
        coverage = f"{first_ts.strftime('%H:%M')}–{last_ts.strftime('%H:%M')} CST"
        coverage_dur = (last_ts - first_ts).total_seconds() / 60
    else:
        coverage = "Unknown"
        coverage_dur = 0

    # Build Report
    report = {
        "source_file": f"ActivityReport-{date_str}.json",
        "date": date_str,
        "title": f"Daily Accomplishments — {date_str}",
        "overview": {
            # UI: Rename "Active" to "Total Active Time" in frontend if needed, 
            # but here we provide the precise data.
            "active_time": minutes_to_time_str(metrics['active_minutes']),
            "focus_time": minutes_to_time_str(metrics['focus_minutes']),
            "meetings_time": minutes_to_time_str(metrics['meeting_minutes']),
            "coverage_time": minutes_to_time_str(coverage_dur),
            "coverage_window": coverage,
            "appointments": 0,
            "projects_count": len(category_time)
        },
        "prepared_for_manager": [
            f"Active Time: {minutes_to_time_str(metrics['active_minutes'])}",
            f"Focus Time: {minutes_to_time_str(metrics['focus_minutes'])}",
            f"Meeting Time: {minutes_to_time_str(metrics['meeting_minutes'])}",
            f"Top Apps: {', '.join(f'{k}' for k, v in sorted(app_time.items(), key=lambda x: -x[1])[:3])}"
        ],
        "executive_summary": [
            f"Active: {minutes_to_time_str(metrics['active_minutes'])} | Focus: {minutes_to_time_str(metrics['focus_minutes'])}",
            f"Coverage: {coverage}",
        ],
        "accomplishments_today": [
            f"Focused on {app} ({minutes_to_time_str(mins)})" 
            for app, mins in sorted(app_time.items(), key=lambda x: -x[1])[:5]
        ],
        "by_category": {
            cat: minutes_to_time_str(mins) 
            for cat, mins in sorted(category_time.items(), key=lambda x: -x[1])
        },
        "browser_highlights": {
            "top_domains": [
                {"domain": d, "visits": v}
                for d, v in sorted(domain_visits.items(), key=lambda x: -x[1])[:10]
            ],
            "top_pages": [
                {"page": p[:80], "visits": v}
                for p, v in sorted(page_visits.items(), key=lambda x: -x[1])[:10]
            ]
        },
        "hourly_focus": hourly_focus,
        "top_apps": {
            app: minutes_to_time_str(mins)
            for app, mins in sorted(app_time.items(), key=lambda x: -x[1])[:8]
        },
        "top_windows_preview": [
            f"{w}: {minutes_to_time_str(t)}"
            for w, t in sorted(window_time.items(), key=lambda x: -x[1])[:10]
        ],
        "timeline": timeline.export_timeline(),
        "deep_work_blocks": timeline.detect_deep_work_blocks(),
        "foot": "Auto-generated (Redesign v1)"
    }
    
    output_file = REPO_ROOT / f"ActivityReport-{date_str}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Generated: {output_file}")
    return report

if __name__ == '__main__':
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_report(date_arg)
