#!/usr/bin/env python3
"""
Activity Collector - Runs continuously to track Mac activity.
Logs active window/app every 5 seconds to a daily JSONL file.
"""

import json
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

# Configuration
POLL_INTERVAL = 5  # seconds
REPO_ROOT = Path(__file__).parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def get_active_window():
    """Get the currently active application and window title using System Events only.

    This avoids sending AppleEvents directly to the frontmost app (which can
    require extra Automation permissions) and instead queries UI elements via
    System Events, improving reliability under launchd.
    """
    try:
        # Use multiple -e segments to avoid quoting issues
        cmd = [
            '/usr/bin/osascript',
            '-e', 'tell application "System Events"',
            '-e', 'set P to (first process whose frontmost is true)',
            '-e', 'set frontApp to name of P',
            '-e', 'set frontAppId to bundle identifier of P',
            '-e', 'if (exists window 1 of P) then',
            '-e', 'set windowTitle to name of window 1 of P',
            '-e', 'else',
            '-e', 'set windowTitle to ""',
            '-e', 'end if',
            '-e', 'return frontApp & "|" & frontAppId & "|" & windowTitle',
            '-e', 'end tell',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            if len(parts) >= 3:
                return {
                    'app': parts[0],
                    'bundle_id': parts[1],
                    'window': parts[2]
                }
    except Exception as e:
        print(f"Error getting active window: {e}")

    return None

def get_idle_time():
    """Get system idle time in seconds."""
    try:
        result = subprocess.run(
            ['/usr/sbin/ioreg', '-c', 'IOHIDSystem'],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'HIDIdleTime' in line:
                # Value is in nanoseconds
                idle_ns = int(line.split('=')[1].strip())
                return idle_ns / 1_000_000_000
    except Exception:
        pass
    return 0

def log_activity(activity_data):
    """Append activity to today's JSONL log file."""
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f"activity-{today}.jsonl"
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(activity_data) + '\n')

def main():
    print(f"Activity Collector started at {datetime.now().isoformat()}")
    print(f"Logging to: {LOGS_DIR}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    
    last_activity = None
    
    while True:
        try:
            now = datetime.now()
            idle_time = get_idle_time()
            
            # Consider idle if no input for 5+ minutes
            is_idle = idle_time > 300
            
            if not is_idle:
                window_info = get_active_window()
                
                if window_info:
                    activity = {
                        'timestamp': now.isoformat(),
                        'app': window_info['app'],
                        'bundle_id': window_info['bundle_id'],
                        'window': window_info['window'],
                        'idle_seconds': round(idle_time, 1)
                    }
                    
                    # Only log if activity changed or every minute
                    activity_key = f"{window_info['app']}|{window_info['window']}"
                    if activity_key != last_activity or now.second < POLL_INTERVAL:
                        log_activity(activity)
                        last_activity = activity_key
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nCollector stopped.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
