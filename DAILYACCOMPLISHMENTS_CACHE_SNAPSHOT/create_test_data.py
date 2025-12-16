#!/usr/bin/env python3
"""
Create realistic test data for testing analytics and dashboard
"""
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from daily_logger import load_config, get_log_path

def create_realistic_day_log(date_str='2025-12-08'):
    """Create a realistic day of activity with deep work sessions"""
    
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=tz)
    
    log_path = get_log_path(date)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    events = []
    
    # Metadata
    metadata = {
        'type': 'metadata',
        'data': {
            'date': date_str,
            'start_time': date.replace(hour=6, minute=0).isoformat(),
            'timezone': 'America/Chicago',
            'coverage_start': '06:00',
            'coverage_end': '23:59',
            'initialized_at': datetime.now(tz).isoformat(),
            'version': '2.0'
        }
    }
    events.append(metadata)
    
    # 9:00 AM - Start work in VS Code (30 min deep work session)
    t = date.replace(hour=9, minute=0)
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'VS Code',
            'window_title': 'analytics.py — DailyAccomplishments',
            'duration_seconds': 1800  # 30 minutes
        }
    })
    
    # 9:30 - Check Slack (interruption)
    t = t + timedelta(minutes=30)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'VS Code', 'to_app': 'Slack'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'Slack',
            'window_title': '#engineering',
            'duration_seconds': 300  # 5 minutes
        }
    })
    
    # 9:35 - Back to VS Code (90 min deep work session)
    t = t + timedelta(minutes=5)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'Slack', 'to_app': 'VS Code'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'VS Code',
            'window_title': 'tracker_bridge.py',
            'duration_seconds': 5400  # 90 minutes
        }
    })
    
    # 11:05 - Browser research (20 min)
    t = t + timedelta(minutes=90)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'VS Code', 'to_app': 'Google Chrome'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'Google Chrome',
            'window_title': 'Python documentation',
            'duration_seconds': 1200  # 20 minutes
        }
    })
    events.append({
        'type': 'browser_visit',
        'timestamp': t.isoformat(),
        'data': {
            'domain': 'docs.python.org',
            'url': 'https://docs.python.org/3/library/datetime.html',
            'page_title': 'datetime — Basic date and time types'
        }
    })
    
    # 11:25 - Back to coding (45 min)
    t = t + timedelta(minutes=20)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'Google Chrome', 'to_app': 'VS Code'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'VS Code',
            'window_title': 'daily_logger.py',
            'duration_seconds': 2700  # 45 minutes
        }
    })
    
    # 12:10 - Lunch break
    t = t + timedelta(minutes=45)
    events.append({
        'type': 'idle_start',
        'timestamp': t.isoformat(),
        'data': {}
    })
    
    # 1:00 PM - Meeting
    t = date.replace(hour=13, minute=0)
    events.append({
        'type': 'idle_end',
        'timestamp': t.isoformat(),
        'data': {}
    })
    events.append({
        'type': 'meeting_start',
        'timestamp': t.isoformat(),
        'data': {
            'title': 'Team Standup',
            'duration_seconds': 900  # 15 minutes
        }
    })
    
    # 1:15 - Continue meeting
    t = t + timedelta(minutes=15)
    events.append({
        'type': 'meeting_end',
        'timestamp': t.isoformat(),
        'data': {
            'title': 'Team Standup'
        }
    })
    
    # 1:20 - Documentation (60 min deep work)
    t = t + timedelta(minutes=5)
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'Notion',
            'window_title': 'Integration Guide',
            'duration_seconds': 3600  # 60 minutes
        }
    })
    
    # 2:20 - Email check (interruption)
    t = t + timedelta(minutes=60)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'Notion', 'to_app': 'Gmail'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'Gmail',
            'window_title': 'Inbox',
            'duration_seconds': 600  # 10 minutes
        }
    })
    
    # 2:30 - Terminal work (120 min deep work session)
    t = t + timedelta(minutes=10)
    events.append({
        'type': 'app_switch',
        'timestamp': t.isoformat(),
        'data': {'from_app': 'Gmail', 'to_app': 'Terminal'}
    })
    events.append({
        'type': 'focus_change',
        'timestamp': t.isoformat(),
        'data': {
            'app': 'Terminal',
            'window_title': '~/code/DailyAccomplishments',
            'duration_seconds': 7200  # 120 minutes
        }
    })
    
    # Write all events
    with open(log_path, 'w') as f:
        for event in events:
            f.write(json.dumps(event) + '\n')
    
    print(f"✓ Created test data: {log_path}")
    print(f"  Events: {len(events)}")
    print(f"  Expected deep work sessions: 4 (30min, 90min, 60min, 120min)")
    return log_path

if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else '2025-12-08'
    create_realistic_day_log(date)
