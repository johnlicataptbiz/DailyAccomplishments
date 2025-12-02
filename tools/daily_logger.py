#!/usr/bin/env python3
"""
Daily Activity Logger and Reset Manager

This script handles:
- 6am daily start tracking
- Midnight reset and log rotation
- Running log of daily activities
- Automatic report generation
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / 'config.json'
BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / 'logs' / 'daily'
ARCHIVE_DIR = BASE_DIR / 'logs' / 'archive'

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def ensure_directories():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

def get_current_date(tz_name='America/Chicago'):
    tz = ZoneInfo(tz_name)
    return datetime.now(tz)

def get_log_path(date):
    """Get path to today's activity log"""
    return LOG_DIR / f"{date.strftime('%Y-%m-%d')}.jsonl"

def initialize_daily_log(date, config):
    """Create a new daily log file with metadata"""
    log_path = get_log_path(date)
    
    if not log_path.exists():
        start_hour = config['tracking']['daily_start_hour']
        start_min = config['tracking']['daily_start_minute']
        tz = ZoneInfo(config['tracking']['timezone'])
        
        # Create start timestamp for today at 6am
        start_time = date.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
        
        metadata = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.isoformat(),
            'timezone': config['tracking']['timezone'],
            'coverage_start': config['report']['coverage_start'],
            'coverage_end': config['report']['coverage_end'],
            'initialized_at': datetime.now(tz).isoformat()
        }
        
        with open(log_path, 'w') as f:
            f.write(json.dumps({'type': 'metadata', 'data': metadata}) + '\n')
        
        print(f"Initialized daily log: {log_path}")
        return metadata
    
    return None

def log_activity(event_type, data):
    """Append an activity event to today's log"""
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    now = datetime.now(tz)
    log_path = get_log_path(now)
    
    event = {
        'type': event_type,
        'timestamp': now.isoformat(),
        'data': data
    }
    
    with open(log_path, 'a') as f:
        f.write(json.dumps(event) + '\n')

def midnight_reset():
    """Archive yesterday's log and prepare for new day"""
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    now = datetime.now(tz)
    yesterday = now - timedelta(days=1)
    
    # Archive yesterday's log
    yesterday_log = get_log_path(yesterday)
    if yesterday_log.exists():
        archive_path = ARCHIVE_DIR / f"{yesterday.strftime('%Y-%m-%d')}.jsonl"
        shutil.copy2(yesterday_log, archive_path)
        print(f"Archived: {yesterday_log} -> {archive_path}")
    
    # Initialize today's log
    initialize_daily_log(now, config)
    
    # Clean up old logs based on retention policy
    cleanup_old_logs(config)

def cleanup_old_logs(config):
    """Remove logs older than retention period"""
    retention_days = config['retention']['keep_daily_logs_days']
    tz = ZoneInfo(config['tracking']['timezone'])
    cutoff_date = datetime.now(tz) - timedelta(days=retention_days)
    
    for log_file in LOG_DIR.glob('*.jsonl'):
        try:
            file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
            if file_date.replace(tzinfo=tz) < cutoff_date:
                log_file.unlink()
                print(f"Removed old log: {log_file}")
        except ValueError:
            pass  # Skip files that don't match date pattern

def read_daily_log(date):
    """Read and parse a daily activity log"""
    log_path = get_log_path(date)
    
    if not log_path.exists():
        return []
    
    events = []
    with open(log_path, 'r') as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    
    return events

def generate_summary(date):
    """Generate a summary from the daily log"""
    events = read_daily_log(date)
    
    if not events:
        return None
    
    metadata = None
    activities = []
    
    for event in events:
        if event.get('type') == 'metadata':
            metadata = event.get('data', {})
        else:
            activities.append(event)
    
    return {
        'metadata': metadata,
        'total_events': len(activities),
        'activities': activities
    }

def main():
    """Main entry point"""
    ensure_directories()
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    now = datetime.now(tz)
    
    # Check if we need to initialize today's log
    initialize_daily_log(now, config)
    
    # Log example activity (this would be called by the actual tracker)
    log_activity('focus_change', {
        'app': 'Example App',
        'window_title': 'Example Window',
        'duration_seconds': 60
    })
    
    print(f"Daily log system ready. Current log: {get_log_path(now)}")
    print(f"Tracking starts at {config['tracking']['daily_start_hour']:02d}:{config['tracking']['daily_start_minute']:02d}")
    print(f"Reset occurs at {config['tracking']['reset_hour']:02d}:{config['tracking']['reset_minute']:02d}")

if __name__ == '__main__':
    main()
