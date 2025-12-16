#!/usr/bin/env python3
"""
Convert ActivityReport JSON to JSONL format for analytics

This bridges the gap between your existing activity tracker output
and the new analytics system.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def parse_time_range(time_str):
    """Parse time range like '08:00–08:15' to start time and duration"""
    if '–' in time_str or '-' in time_str:
        # Handle en-dash or regular dash
        parts = time_str.replace('–', '-').split('-')
        if len(parts) == 2:
            start_time = parts[0].strip()
            end_time = parts[1].strip()
            
            # Parse hours and minutes
            start_h, start_m = map(int, start_time.split(':'))
            end_h, end_m = map(int, end_time.split(':'))
            
            # Calculate duration in seconds
            duration = (end_h * 3600 + end_m * 60) - (start_h * 3600 + start_m * 60)
            
            return start_time, duration
    return None, None

def convert_activity_report_to_jsonl(activity_report_path: Path, output_jsonl_path: Path):
    """Convert ActivityReport JSON to JSONL format"""
    
    with open(activity_report_path, 'r') as f:
        data = json.load(f)
    
    # Extract date from filename (ActivityReport-2025-12-01.json)
    date_str = activity_report_path.stem.split('-', 1)[1]  # "2025-12-01"
    
    # Create JSONL entries
    jsonl_entries = []
    
    # Add metadata entry
    metadata = {
        "type": "metadata",
        "data": {
            "date": date_str,
            "start_time": f"{date_str}T06:00:00-06:00",
            "timezone": "America/Chicago",
            "coverage_start": "06:00",
            "coverage_end": "23:59",
            "initialized_at": datetime.now(ZoneInfo("America/Chicago")).isoformat()
        }
    }
    jsonl_entries.append(metadata)
    
    # Convert meetings to meeting events (these have actual times)
    if 'debug_appointments' in data and 'meetings_today' in data['debug_appointments']:
        for meeting in data['debug_appointments']['meetings_today']:
            time_str = meeting.get('time', '')
            start_time, duration = parse_time_range(time_str)
            
            if start_time:
                event = {
                    "type": "meeting_start",
                    "timestamp": f"{date_str}T{start_time}:00-06:00",
                    "data": {
                        "name": meeting.get('name', 'Unknown Meeting'),
                        "scheduled_duration_seconds": duration if duration else 1800
                    }
                }
                jsonl_entries.append(event)
    
    # Convert hourly_focus to focus sessions
    # This gives us actual working time by hour
    if 'hourly_focus' in data:
        for hour_data in data['hourly_focus']:
            time_str = hour_data.get('time', '00:00')
            hour = hour_data.get('hour', 0)
            
            if time_str and time_str != "00:00":
                # Parse duration like "00:36" or "01:15" (HH:MM format)
                parts = time_str.split(':')
                if len(parts) == 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    duration_seconds = hours * 3600 + minutes * 60
                    
                    if duration_seconds > 0:
                        # Create a focus session for this hour
                        event = {
                            "type": "focus_change",
                            "timestamp": f"{date_str}T{hour:02d}:00:00-06:00",
                            "data": {
                                "app": "Work Session",
                                "window_title": f"Focus work - {hour_data.get('pct', '0%')} utilization",
                                "duration_seconds": duration_seconds
                            }
                        }
                        jsonl_entries.append(event)
    
    # Write JSONL file
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_jsonl_path, 'w') as f:
        for entry in jsonl_entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✓ Converted {len(jsonl_entries)} entries")
    print(f"  From: {activity_report_path}")
    print(f"  To: {output_jsonl_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 convert_activity_report.py <date>")
        print("Example: python3 convert_activity_report.py 2025-12-01")
        sys.exit(1)
    
    date = sys.argv[1]
    
    # Paths
    repo_root = Path(__file__).parent.parent
    activity_report = repo_root / f"ActivityReport-{date}.json"
    output_jsonl = repo_root / "logs" / "daily" / f"{date}.jsonl"
    
    if not activity_report.exists():
        print(f"✗ ActivityReport not found: {activity_report}")
        sys.exit(1)
    
    convert_activity_report_to_jsonl(activity_report, output_jsonl)
    
    print(f"\nNow run: python3 tools/auto_report.py --date {date}")
