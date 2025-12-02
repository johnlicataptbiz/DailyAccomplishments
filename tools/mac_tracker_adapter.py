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
from collections import defaultdict

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows compatibility

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
            if fcntl:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event) + '\n')
            finally:
                if fcntl:
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
    
    def generate_report(self, print_report: bool = False) -> Optional[Path]:
        """
        Generate analytics report from today's log.
        
        Args:
            print_report: If True, print summary to console
        
        Returns:
            Path to the generated report, or None if failed
        """
        try:
            # Read and analyze the log file
            events = self._read_events()
            report = self._analyze_events(events)
            
            # Save JSON report
            report_path = self.reports_dir / f"daily-report-{self.current_date}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Generate Markdown report
            md_path = self.generate_markdown_report(report)
            
            if print_report:
                self._print_summary(report)
            
            print(f"✓ Report generated: {report_path}")
            print(f"✓ Markdown report: {md_path}")
            print(f"  Score: {report['productivity_score']}/100")
            
            return report_path
            
        except Exception as e:
            print(f"✗ Report generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _read_events(self) -> list:
        """Read all events from today's log"""
        events = []
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return events
    
    def _analyze_events(self, events: list) -> dict:
        """Analyze events and generate report data"""
        from collections import defaultdict
        
        # Initialize counters
        hourly_focus: dict = defaultdict(int)  # hour -> seconds
        app_time: dict = defaultdict(int)  # app -> seconds
        meetings: list = []
        total_focus_seconds = 0
        total_meeting_seconds = 0
        interruptions = 0
        
        for event in events:
            event_type = event.get('type')
            data = event.get('data', {})
            timestamp_str = event.get('timestamp', '')
            
            if event_type == 'focus_change':
                duration = data.get('duration_seconds', 0)
                app = data.get('app', 'Unknown')
                
                total_focus_seconds += duration
                app_time[app] += duration
                
                # Add to hourly breakdown
                if timestamp_str:
                    try:
                        ts = datetime.fromisoformat(timestamp_str)
                        hourly_focus[ts.hour] += duration
                    except ValueError:
                        pass
            
            elif event_type == 'meeting_start':
                meeting_duration = data.get('scheduled_duration_seconds', 1800)
                total_meeting_seconds += meeting_duration
                meetings.append({
                    'name': data.get('name', 'Unknown'),
                    'duration_minutes': meeting_duration // 60,
                    'time': timestamp_str
                })
            
            elif event_type == 'app_switch':
                interruptions += 1
        
        # Calculate deep work (sessions >= 25 min without interruption)
        deep_work_minutes = sum(
            secs // 60 for secs in hourly_focus.values() if secs >= 25 * 60
        )
        
        # Calculate productivity score
        focus_hours = total_focus_seconds / 3600
        meeting_hours = total_meeting_seconds / 3600
        
        # Score formula: base on focus time, penalize interruptions
        base_score = min(100, (focus_hours / 8) * 100)  # 8 hours = 100%
        interruption_penalty = min(30, interruptions * 2)  # Max 30 point penalty
        score = max(0, min(100, base_score - interruption_penalty))
        
        # Build hourly breakdown
        hourly_breakdown = []
        for hour in range(24):
            mins = hourly_focus.get(hour, 0) // 60
            if mins > 0:
                hourly_breakdown.append({
                    'hour': hour,
                    'time_label': f"{hour:02d}:00",
                    'focus_minutes': mins,
                    'percentage': min(100, round((mins / 60) * 100))
                })
        
        # Top apps
        top_apps = sorted(
            [{'app': app, 'minutes': secs // 60} for app, secs in app_time.items()],
            key=lambda x: x['minutes'],
            reverse=True
        )[:10]
        
        return {
            'date': self.current_date,
            'productivity_score': round(score),
            'summary': {
                'total_focus_hours': round(focus_hours, 2),
                'total_meeting_hours': round(meeting_hours, 2),
                'deep_work_minutes': deep_work_minutes,
                'interruptions': interruptions,
                'meetings_count': len(meetings)
            },
            'hourly_breakdown': hourly_breakdown,
            'top_apps': top_apps,
            'meetings': meetings
        }
    
    def generate_markdown_report(self, report: dict) -> Path:
        """
        Generate a Markdown report from the analysis.
        
        Args:
            report: Report dict from _analyze_events
        
        Returns:
            Path to the generated Markdown file
        """
        summary = report.get('summary', {})
        hourly = report.get('hourly_breakdown', [])
        top_apps = report.get('top_apps', [])
        meetings = report.get('meetings', [])
        
        lines = [
            f"# Daily Productivity Report - {report['date']}",
            "",
            f"## 📊 Score: {report['productivity_score']}/100",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Focus Time | {summary.get('total_focus_hours', 0):.1f} hours |",
            f"| Meeting Time | {summary.get('total_meeting_hours', 0):.1f} hours |",
            f"| Deep Work | {summary.get('deep_work_minutes', 0)} minutes |",
            f"| Interruptions | {summary.get('interruptions', 0)} |",
            f"| Meetings | {summary.get('meetings_count', 0)} |",
            "",
        ]
        
        # Hourly breakdown
        if hourly:
            lines.extend([
                "## ⏰ Hourly Breakdown",
                "",
                "| Hour | Focus (min) | Utilization |",
                "|------|-------------|-------------|",
            ])
            for h in hourly:
                bar = "█" * (h['percentage'] // 10) + "░" * (10 - h['percentage'] // 10)
                lines.append(f"| {h['time_label']} | {h['focus_minutes']} | {bar} {h['percentage']}% |")
            lines.append("")
        
        # Top apps
        if top_apps:
            lines.extend([
                "## 💻 Top Applications",
                "",
                "| App | Time (min) |",
                "|-----|------------|",
            ])
            for app in top_apps[:5]:
                lines.append(f"| {app['app']} | {app['minutes']} |")
            lines.append("")
        
        # Meetings
        if meetings:
            lines.extend([
                "## 📅 Meetings",
                "",
                "| Meeting | Duration |",
                "|---------|----------|",
            ])
            for m in meetings:
                lines.append(f"| {m['name']} | {m['duration_minutes']} min |")
            lines.append("")
        
        # Footer
        lines.extend([
            "---",
            f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        md_content = "\n".join(lines)
        md_path = self.reports_dir / f"daily-report-{self.current_date}.md"
        
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        return md_path
    
    def _print_summary(self, report: dict):
        """Print a quick summary to console"""
        summary = report.get('summary', {})
        print("\n" + "=" * 50)
        print(f"📊 DAILY REPORT - {report['date']}")
        print("=" * 50)
        print(f"Score:         {report['productivity_score']}/100")
        print(f"Focus Time:    {summary.get('total_focus_hours', 0):.1f} hours")
        print(f"Meeting Time:  {summary.get('total_meeting_hours', 0):.1f} hours")
        print(f"Deep Work:     {summary.get('deep_work_minutes', 0)} minutes")
        print(f"Interruptions: {summary.get('interruptions', 0)}")
        print("=" * 50)
        
        # Mini hourly chart
        hourly = report.get('hourly_breakdown', [])
        if hourly:
            print("\nHourly Focus:")
            for h in hourly:
                bar = "█" * (h['focus_minutes'] // 6)  # Each block = 6 min
                print(f"  {h['time_label']} {bar} {h['focus_minutes']}min")
        print()


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
