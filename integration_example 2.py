#!/usr/bin/env python3
"""
Example: Integrating ActivityTrackerBridge with your existing activity tracker

This file demonstrates how to integrate the new robust tracking system
with your existing activity_tracker.py (3600 lines).

Key integration points:
1. Application switch detection
2. URL tracking (browser activity)
3. Meeting/calendar integration
4. Idle detection
5. Focus session tracking

Author: Daily Accomplishments System
Date: December 2025
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from tracker_bridge import ActivityTrackerBridge  # type: ignore
from idle_detection import IdleDetector  # type: ignore


class IntegratedActivityTracker:
    """
    Example activity tracker with DailyAccomplishments integration.
    
    This class shows how to:
    - Initialize the bridge
    - Log different event types
    - Handle deduplication
    - Track idle time
    - Recommend breaks
    """
    
    def __init__(self):
        """Initialize tracker with bridge and idle detector."""
        # Initialize the bridge (handles logging to JSONL)
        self.bridge = ActivityTrackerBridge()
        
        # Initialize idle detector (5-minute threshold)
        self.idle_detector = IdleDetector(idle_threshold_seconds=300)
        
        # Track current state to prevent duplicate logs
        self.current_app = None
        self.current_url = None
        self.last_idle_log = 0
        
        print("✓ Activity tracker initialized")
        print("✓ Bridge connected to DailyAccomplishments system")
        print("✓ Idle detector ready (5-minute threshold)")
        print()
    
    def track_application_switch(self, app_name: str, window_title: str, duration: int = 60):
        """
        Track when user switches applications.
        
        The bridge automatically handles:
        - Deduplication (won't log if same app within 2 seconds)
        - Timestamp validation
        - JSONL formatting
        
        Args:
            app_name: Name of the application (e.g., "VS Code", "Safari")
            window_title: Current window title or document name
            duration: Duration in seconds spent in this app
        """
        # Only log if app actually changed
        if app_name != self.current_app:
            # Log app switch
            if self.current_app:
                self.bridge.on_app_switch(self.current_app, app_name)
            
            # Log focus change with duration
            self.bridge.on_focus_change(app_name, window_title, duration)
            
            self.current_app = app_name
            print(f"📱 App: {app_name} — {window_title}")
    
    def track_url_visit(self, url: str, title: str):
        """
        Track browser URL visits.
        
        Automatically extracts domain and logs visit.
        Deduplication prevents logging same URL repeatedly.
        
        Args:
            url: Full URL (e.g., "https://github.com/user/repo")
            title: Page title
        """
        from urllib.parse import urlparse
        
        # Only log if URL changed
        if url != self.current_url:
            domain = urlparse(url).netloc
            
            self.bridge.on_browser_visit(
                domain=domain,
                url=url,
                page_title=title
            )
            self.current_url = url
            print(f"🌐 URL: {domain} — {title}")
    
    def track_meeting(self, title: str, duration: int, platform: str = "Unknown"):
        """
        Track meetings from calendar or video conferencing apps.
        
        Args:
            title: Meeting title
            duration: Duration in seconds
            platform: Platform name (Zoom, Teams, Google Meet, etc.)
        """
        # Log meeting start
        self.bridge.on_meeting_start(title, scheduled_duration=duration)
        
        # For completed meetings, also log end
        # (In real usage, you'd call this when the meeting actually ends)
        # self.bridge.on_meeting_end(title, duration)
        
        print(f"📅 Meeting: {title} ({duration//60}min on {platform})")
    
    def check_idle_status(self):
        """
        Check for idle time and recommend breaks.
        
        Logs idle periods and suggests breaks based on:
        - Total time since last break
        - Current idle time
        """
        idle_seconds = self.idle_detector.get_idle_seconds()
        
        # Skip if we can't detect idle time
        if idle_seconds is None:
            return
        
        # Log if idle for more than 5 minutes (and hasn't been logged recently)
        if idle_seconds >= 300 and idle_seconds - self.last_idle_log > 300:
            self.bridge.on_idle_end(idle_duration_seconds=idle_seconds)
            self.last_idle_log = idle_seconds
            print(f"😴 Idle: {idle_seconds//60} minutes")
        
        # Check if break is recommended
        if self.idle_detector.is_break_recommended():
            print("🎯 Break recommended! You've been focused for a while.")
    
    def log_focus_session(self, duration_minutes: int, category: str, interruptions: int = 0):
        """
        Log a completed focus/deep work session.
        
        Args:
            duration_minutes: How long the session lasted
            category: Type of work (Development, Writing, Research, etc.)
            interruptions: Number of interruptions during session
        """
        # Use manual entry to log completed focus sessions
        self.bridge.on_manual_entry(
            description=f"{category} - Focus Session",
            duration_seconds=duration_minutes * 60,
            category=category
        )
        print(f"🎯 Focus session completed: {duration_minutes}min of {category}")
        if interruptions > 0:
            print(f"   ⚠️  {interruptions} interruptions detected")


def example_full_integration():
    """
    Complete example showing a typical day's tracking.
    
    This simulates what your existing activity_tracker.py would do,
    but now integrated with the DailyAccomplishments system.
    """
    tracker = IntegratedActivityTracker()
    
    print("=" * 60)
    print("EXAMPLE: Full Day Tracking Integration")
    print("=" * 60)
    print()
    
    # Morning: Start work in IDE
    print("[09:00] Starting work...")
    tracker.track_application_switch("VS Code", "main.py — DailyAccomplishments")
    time.sleep(1)
    
    # Work on code for a bit, then switch to browser for research
    print("\n[09:15] Researching documentation...")
    tracker.track_application_switch("Safari", "Python Documentation")
    tracker.track_url_visit(
        "https://docs.python.org/3/library/datetime.html",
        "datetime — Basic date and time types"
    )
    time.sleep(1)
    
    # Back to coding
    print("\n[09:30] Back to coding...")
    tracker.track_application_switch("VS Code", "tracker_bridge.py")
    time.sleep(1)
    
    # Check Slack (interruption)
    print("\n[10:15] Quick Slack check...")
    tracker.track_application_switch("Slack", "#engineering")
    time.sleep(1)
    
    # Return to focus work
    print("\n[10:20] Deep work session...")
    tracker.track_application_switch("VS Code", "analytics.py")
    
    # Simulate 2-hour deep work session
    print("   [Working for 2 hours...]")
    
    # Log the completed focus session
    print("\n[12:20] Completing focus session...")
    tracker.log_focus_session(
        duration_minutes=120,
        category="Development",
        interruptions=1  # That Slack check
    )
    time.sleep(1)
    
    # Lunch break (idle detection would catch this)
    print("\n[12:30] Lunch break (idle)...")
    tracker.check_idle_status()
    time.sleep(1)
    
    # Afternoon meeting
    print("\n[14:00] Team standup...")
    tracker.track_meeting(
        title="Daily Standup",
        duration=900,  # 15 minutes
        platform="Zoom"
    )
    time.sleep(1)
    
    # More work
    print("\n[14:20] Writing documentation...")
    tracker.track_application_switch("VS Code", "README.md")
    time.sleep(1)
    
    # End of day summary
    print("\n" + "=" * 60)
    print("End of day! All events logged to:")
    print(f"  logs/daily/{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    print()
    print("Next steps:")
    print("  1. Generate report: python3 tools/auto_report.py")
    print("  2. View dashboard: open dashboard.html")
    print("  3. Send notifications: python3 tools/notifications.py")
    print("=" * 60)


def example_simple_integration():
    """
    Minimal example for quick integration.
    
    Shows the absolute minimum code needed to start logging events.
    """
    print("=" * 60)
    print("EXAMPLE: Minimal Integration (3 lines of code)")
    print("=" * 60)
    print()
    
    # Step 1: Create bridge
    bridge = ActivityTrackerBridge()
    
    # Step 2: Log events using the correct API
    bridge.on_focus_change("Terminal", "~/code", 120)  # 2 minutes in Terminal
    bridge.on_browser_visit("github.com", "https://github.com", "GitHub")
    
    # Step 3: Done! Events are in the log
    print("✓ Events logged successfully!")
    print(f"  Location: logs/daily/{datetime.now().strftime('%Y-%m-%d')}.jsonl")


if __name__ == '__main__':
    """
    Run examples based on command line argument.
    
    Usage:
        python3 integration_example.py              # Run full example
        python3 integration_example.py simple       # Run minimal example
        python3 integration_example.py --help       # Show this help
    """
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'simple':
            example_simple_integration()
        elif sys.argv[1] in ['--help', '-h']:
            print(__doc__)
            print("\nUsage:")
            print("  python3 integration_example.py         # Full example")
            print("  python3 integration_example.py simple  # Minimal example")
            print("  python3 integration_example.py --help  # This help")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        example_full_integration()
