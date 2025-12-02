#!/usr/bin/env python3
"""
Mac Tracker Adapter

Drop-in integration for your existing activity_tracker.py on Mac.
Add this to your tracker to output JSONL events in real-time.

USAGE:
------
1. Copy this file to your Mac alongside activity_tracker.py
2. In your tracker, add:

    from mac_tracker_adapter import TrackerAdapter
    adapter = TrackerAdapter()
    
3. When your tracker detects events, call:

    # When app focus changes
    adapter.log_focus_change("VS Code", "main.py - MyProject", duration_seconds=120)
    
    # When a meeting starts
    adapter.log_meeting("Daily Standup", duration_minutes=30)
    
    # At end of day, generate the report
    adapter.generate_report()

4. The JSONL logs will be in ~/DailyAccomplishments/logs/daily/YYYY-MM-DD.jsonl
   Reports will be in ~/DailyAccomplishments/reports/
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import fcntl

class TrackerAdapter:
    """Adapter to connect your existing tracker to the analytics system"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the adapter.
        
        Args:
            base_dir: Base directory for logs. Defaults to ~/DailyAccomplishments
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / "DailyAccomplishments"
        
        self.logs_dir = self.base_dir / "logs" / "daily"
        self.reports_dir = self.base_dir / "reports"
        
        # Create directories
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Current date for log file
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.logs_dir / f"{self.current_date}.jsonl"
        
        # Initialize log file with metadata if new
        if not self.log_file.exists():
            self._write_metadata()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().astimezone().isoformat()
    
    def _write_event(self, event: dict):
        """Write event to JSONL file with file locking"""
        with open(self.log_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event) + '\n')
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def _write_metadata(self):
        """Write initial metadata entry"""
        metadata = {
            "type": "metadata",
            "data": {
                "date": self.current_date,
                "start_time": self._get_timestamp(),
                "timezone": str(datetime.now().astimezone().tzinfo),
                "coverage_start": "06:00",
                "coverage_end": "23:59",
                "initialized_at": self._get_timestamp()
            }
        }
        self._write_event(metadata)
    
    def log_focus_change(self, app: str, window_title: str = "", duration_seconds: int = 0):
        """
        Log when focus changes to a new application.
        
        Args:
            app: Application name (e.g., "VS Code", "Chrome", "Slack")
            window_title: Window/tab title
            duration_seconds: How long the previous focus lasted
        """
        event = {
            "type": "focus_change",
            "timestamp": self._get_timestamp(),
            "data": {
                "app": app,
                "window_title": window_title,
                "duration_seconds": duration_seconds
            }
        }
        self._write_event(event)
    
    def log_app_switch(self, from_app: str, to_app: str):
        """
        Log application switch (counts as potential interruption).
        
        Args:
            from_app: Previous application
            to_app: New application
        """
        event = {
            "type": "app_switch",
            "timestamp": self._get_timestamp(),
            "data": {
                "from_app": from_app,
                "to_app": to_app
            }
        }
        self._write_event(event)
    
    def log_meeting(self, name: str, duration_minutes: int = 30):
        """
        Log a meeting start.
        
        Args:
            name: Meeting name
            duration_minutes: Scheduled duration
        """
        event = {
            "type": "meeting_start",
            "timestamp": self._get_timestamp(),
            "data": {
                "name": name,
                "scheduled_duration_seconds": duration_minutes * 60
            }
        }
        self._write_event(event)
    
    def log_browser_visit(self, url: str, title: str = "", domain: str = ""):
        """
        Log a browser page visit.
        
        Args:
            url: Full URL
            title: Page title
            domain: Domain name
        """
        if not domain and url:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        
        event = {
            "type": "browser_visit",
            "timestamp": self._get_timestamp(),
            "data": {
                "url": url,
                "title": title,
                "domain": domain
            }
        }
        self._write_event(event)
    
    def log_idle_start(self):
        """Log when user becomes idle"""
        event = {
            "type": "idle_start",
            "timestamp": self._get_timestamp(),
            "data": {}
        }
        self._write_event(event)
    
    def log_idle_end(self, idle_seconds: int):
        """
        Log when user returns from idle.
        
        Args:
            idle_seconds: How long they were idle
        """
        event = {
            "type": "idle_end",
            "timestamp": self._get_timestamp(),
            "data": {
                "idle_duration_seconds": idle_seconds
            }
        }
        self._write_event(event)
    
    def log_manual_entry(self, category: str, description: str, duration_minutes: int):
        """
        Log a manual time entry (for offline work, phone calls, etc.)
        
        Args:
            category: Category (e.g., "Development", "Sales", "Admin")
            description: What was done
            duration_minutes: Duration
        """
        event = {
            "type": "manual_entry",
            "timestamp": self._get_timestamp(),
            "data": {
                "category": category,
                "description": description,
                "duration_seconds": duration_minutes * 60
            }
        }
        self._write_event(event)
    
    def generate_report(self) -> Optional[Path]:
        """
        Generate analytics report from today's log.
        
        Returns:
            Path to the generated report, or None if failed
        """
        try:
            # Import analytics (needs to be in same directory or PYTHONPATH)
            import sys
            sys.path.insert(0, str(self.base_dir / "tools"))
            from analytics import ProductivityAnalytics
            
            analytics = ProductivityAnalytics(str(self.log_file))
            report = analytics.generate_report()
            
            # Save report
            report_path = self.reports_dir / f"daily-report-{self.current_date}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"✓ Report generated: {report_path}")
            print(f"  Score: {report['productivity_score']['overall_score']}/100")
            
            return report_path
            
        except ImportError:
            print("⚠ Analytics module not found. Copy tools/analytics.py to your Mac.")
            return None
        except Exception as e:
            print(f"✗ Report generation failed: {e}")
            return None


# Example usage / self-test
if __name__ == "__main__":
    print("Mac Tracker Adapter - Test Mode")
    print("=" * 40)
    
    adapter = TrackerAdapter()
    print(f"Log file: {adapter.log_file}")
    
    # Simulate some activity
    adapter.log_focus_change("VS Code", "activity_tracker.py", duration_seconds=300)
    adapter.log_focus_change("Chrome", "GitHub - Pull Requests", duration_seconds=60)
    adapter.log_app_switch("Chrome", "Slack")
    adapter.log_focus_change("Slack", "#general", duration_seconds=30)
    adapter.log_meeting("Team Standup", duration_minutes=15)
    
    print(f"\n✓ Logged test events to {adapter.log_file}")
    print("\nTo view: cat " + str(adapter.log_file))
