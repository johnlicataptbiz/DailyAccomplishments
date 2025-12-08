#!/usr/bin/env python3
"""
Daily event logger for tracking productivity events.
Handles reading/writing JSONL event logs with file locking.
"""

import json
import fcntl
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, 'r') as f:
        return json.load(f)


def read_daily_log(date):
    """
    Read events from a daily log file.
    
    Args:
        date: datetime.date or string in YYYY-MM-DD format
        
    Returns:
        List of event dictionaries
    """
    config = load_config()
    log_dir = Path(config['tracking']['log_directory'])
    
    if isinstance(date, str):
        date_str = date
    else:
        date_str = date.strftime('%Y-%m-%d')
    
    log_file = log_dir / f"{date_str}.jsonl"
    
    if not log_file.exists():
        return []
    
    events = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    
    return events


def write_event(event_dict):
    """
    Write an event to the current day's log file.
    Uses file locking to prevent corruption from concurrent writes.
    
    Args:
        event_dict: Dictionary containing event data
    """
    config = load_config()
    log_dir = Path(config['tracking']['log_directory'])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get current date in configured timezone
    tz = ZoneInfo(config['tracking']['timezone'])
    now = datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d')
    
    log_file = log_dir / f"{date_str}.jsonl"
    
    # Add timestamp if not present
    if 'timestamp' not in event_dict:
        event_dict['timestamp'] = now.isoformat()
    
    # Write with file locking
    with open(log_file, 'a') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(event_dict) + '\n')
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
