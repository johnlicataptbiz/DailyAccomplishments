
#!/usr/bin/env python3
"""
Bridge module between activity_tracker.py and daily_logger.py

This module provides integration hooks for the main activity tracker
to log events to the daily logging system.
"""

import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime
# Import from daily_logger in the same tools directory
from .daily_logger import (
    log_activity,
    initialize_daily_log,
    midnight_reset,
    load_config,
    get_current_date,
)

logger = logging.getLogger(__name__)


class ActivityTrackerBridge:
    """Bridge between activity tracker and daily logger"""

    def __init__(
        self,
        cache_window_seconds: Optional[int] = None,
        now_fn: Optional[Callable[[], datetime]] = None,
    ):
        """Initialize the bridge"""
        self.config = load_config()
        self.last_app = None
        self.last_window = None
        self.last_event_time = None
        self.event_cache = []  # Deduplication cache
        # Load cache_window_seconds from config, with a default of 2 seconds
        default_window = self.config.get('tracking', {}).get('cache_window_seconds', 2)
        self.cache_window_seconds = cache_window_seconds or default_window
        # Allow dependency injection for timekeeping to make cache tests deterministic
        self._now: Callable[[], datetime] = now_fn or datetime.now

    def _is_duplicate(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Check if this is a duplicate event"""
        now = self._now()

        # Clean old entries from cache
        self.event_cache = [
            (t, et, d) for t, et, d in self.event_cache
            if (now - t).total_seconds() < self.cache_window_seconds
        ]

        # Check for duplicates
        for cached_time, cached_type, cached_data in self.event_cache:
            if cached_type == event_type and cached_data == data:
                return True

        # Add to cache
        self.event_cache.append((now, event_type, data))
        return False

    def on_focus_change(self, app: str, window_title: str, duration_seconds: int) -> bool:
        """Called when application focus changes"""
        try:
            # Don't log if duration is 0 or negative
            if duration_seconds <= 0:
                logger.debug(f"Skipping focus change with duration {duration_seconds}")
                return False

            data = {
                'app': app,
                'window_title': window_title,
                'duration_seconds': duration_seconds
            }

            # Check for duplicates
            if self._is_duplicate('focus_change', data):
                logger.debug("Skipping duplicate focus_change event")
                return False

            return log_activity('focus_change', data)
        except Exception as e:
            logger.error(f"Error logging focus change: {e}")
            return False

    def on_app_switch(self, from_app: str, to_app: str) -> bool:
        """Called when user switches between applications"""
        try:
            # Prevent logging same-app switches
            if from_app == to_app:
                return False

            data = {
                'from_app': from_app,
                'to_app': to_app
            }

            if self._is_duplicate('app_switch', data):
                logger.debug("Skipping duplicate app_switch event")
                return False

            self.last_app = to_app
            return log_activity('app_switch', data)
        except Exception as e:
            logger.error(f"Error logging app switch: {e}")
            return False

    def on_window_change(self, app: str, window_title: str) -> bool:
        """Called when window title changes within an app"""
        try:
            data = {
                'app': app,
                'window_title': window_title
            }

            # Prevent duplicate window events
            if window_title == self.last_window:
                return False

            if self._is_duplicate('window_change', data):
                logger.debug("Skipping duplicate window_change event")
                return False

            self.last_window = window_title
            return log_activity('window_change', data)
        except Exception as e:
            logger.error(f"Error logging window change: {e}")
            return False

    def on_browser_visit(self, domain: str, url: str, page_title: Optional[str] = None) -> bool:
        """Called when browser visits a page"""
        try:
            data = {
                'domain': domain,
                'url': url
            }

            if page_title:
                data['page_title'] = page_title

            if self._is_duplicate('browser_visit', data):
                logger.debug("Skipping duplicate browser_visit event")
                return False

            return log_activity('browser_visit', data)
        except Exception as e:
            logger.error(f"Error logging browser visit: {e}")
            return False

    def on_meeting_start(self, name: str, scheduled_duration: Optional[int] = None) -> bool:
        """Called when a meeting starts"""
        try:
            data: Dict[str, Any] = {'name': name}
            if scheduled_duration:
                data['scheduled_duration_seconds'] = scheduled_duration

            return log_activity('meeting_start', data)
        except Exception as e:
            logger.error(f"Error logging meeting start: {e}")
            return False

    def on_meeting_end(self, name: str, duration_seconds: int) -> bool:
        """Called when a meeting ends"""
        try:
            data = {
                'name': name,
                'duration_seconds': duration_seconds
            }

            return log_activity('meeting_end', data)
        except Exception as e:
            logger.error(f"Error logging meeting end: {e}")
            return False

    def on_idle_start(self) -> bool:
        """Called when user becomes idle"""
        try:
            return log_activity('idle_start', {})
        except Exception as e:
            logger.error(f"Error logging idle start: {e}")
            return False

    def on_idle_end(self, idle_duration_seconds: int) -> bool:
        """Called when user returns from idle"""
        try:
            data = {'idle_duration_seconds': idle_duration_seconds}
            return log_activity('idle_end', data)
        except Exception as e:
            logger.error(f"Error logging idle end: {e}")
            return False

    def on_manual_entry(self, description: str, duration_seconds: int, category: Optional[str] = None) -> bool:
        """Log a manual time entry"""
        try:
            data = {
                'description': description,
                'duration_seconds': duration_seconds
            }
            if category:
                data['category'] = category

            return log_activity('manual_entry', data)
        except Exception as e:
            logger.error(f"Error logging manual entry: {e}")
            return False

    def perform_midnight_reset(self) -> bool:
        """Perform the midnight reset"""
        try:
            return midnight_reset()
        except Exception as e:
            logger.error(f"Error during midnight reset: {e}")
            return False

    def initialize_today(self) -> bool:
        """Initialize today's log"""
        try:
            config = load_config()
            now = get_current_date(config.get('tracking', {}).get('timezone', 'America/Chicago'))
            result = initialize_daily_log(now, config)
            return result is not None or True  # Already initialized is also success
        except Exception as e:
            logger.error(f"Error initializing today: {e}")
            return False


# Singleton instance for easy import
tracker_bridge = ActivityTrackerBridge()

# Convenience functions
def track_focus_change(app: str, window_title: str, duration_seconds: int) -> bool:
    """Convenience function for focus tracking"""
    return tracker_bridge.on_focus_change(app, window_title, duration_seconds)

def track_app_switch(from_app: str, to_app: str) -> bool:
    """Convenience function for app switches"""
    return tracker_bridge.on_app_switch(from_app, to_app)

def track_browser_visit(domain: str, url: str, page_title: Optional[str] = None) -> bool:
    """Convenience function for browser visits"""
    return tracker_bridge.on_browser_visit(domain, url, page_title)

def track_meeting_start(name: str, scheduled_duration: Optional[int] = None) -> bool:
    """Convenience function for meeting starts"""
    return tracker_bridge.on_meeting_start(name, scheduled_duration)

def track_meeting_end(name: str, duration_seconds: int) -> bool:
    """Convenience function for meeting ends"""
    return tracker_bridge.on_meeting_end(name, duration_seconds)


if __name__ == '__main__':
    # Test the bridge
    print("Testing ActivityTrackerBridge...")

    # Test focus changes
    success = tracker_bridge.on_focus_change("VS Code", "daily_logger.py", 120)
    print(f"Focus change logged: {success}")

    # Test duplicate detection
    success = tracker_bridge.on_focus_change("VS Code", "daily_logger.py", 120)
    print(f"Duplicate focus change (should be False): {success}")

    # Test app switch
    success = tracker_bridge.on_app_switch("VS Code", "Google Chrome")
    print(f"App switch logged: {success}")

    # Test browser visit
    success = tracker_bridge.on_browser_visit("github.com", "https://github.com/johnlicataptbiz", "GitHub Profile")
    print(f"Browser visit logged: {success}")

    print("\nBridge test complete!")
