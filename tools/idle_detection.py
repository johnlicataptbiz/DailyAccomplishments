#!/usr/bin/env python3
"""
Idle Detection and Break Tracking

Monitors system idle time and tracks breaks.
Works on macOS, Linux, and Windows.
"""

import subprocess
import platform
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

try:
    from .daily_logger import log_activity, load_config
except ImportError:  # pragma: no cover
    from daily_logger import log_activity, load_config

logger = logging.getLogger(__name__)


class IdleDetector:
    """Cross-platform idle time detection"""
    
    def __init__(self, idle_threshold_seconds: int = 300):
        """
        Initialize idle detector
        
        Args:
            idle_threshold_seconds: Seconds of inactivity before considered idle (default 5min)
        """
        self.idle_threshold = idle_threshold_seconds
        self.platform = platform.system()
        self.is_idle = False
        self.idle_start_time = None
        self.last_check_time = None
        
        # Validate platform support
        if self.platform not in ['Darwin', 'Linux', 'Windows']:
            logger.warning(f"Idle detection may not work on {self.platform}")
    
    def get_idle_seconds(self) -> Optional[int]:
        """
        Get current system idle time in seconds
        
        Returns None if unable to determine
        """
        try:
            if self.platform == 'Darwin':  # macOS
                return self._get_idle_macos()
            elif self.platform == 'Linux':
                return self._get_idle_linux()
            elif self.platform == 'Windows':
                return self._get_idle_windows()
            else:
                logger.error(f"Unsupported platform: {self.platform}")
                return None
        except Exception as e:
            logger.error(f"Failed to get idle time: {e}")
            return None
    
    def _get_idle_macos(self) -> Optional[int]:
        """Get idle time on macOS using ioreg"""
        try:
            # Query HID idle time
            result = subprocess.run(
                ['ioreg', '-c', 'IOHIDSystem'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                logger.error(f"ioreg failed: {result.stderr}")
                return None
            
            # Parse output for HIDIdleTime
            for line in result.stdout.split('\n'):
                if 'HIDIdleTime' in line:
                    # Extract value: "HIDIdleTime" = 12345678901
                    parts = line.split('=')
                    if len(parts) == 2:
                        idle_ns = int(parts[1].strip())
                        # Convert nanoseconds to seconds
                        return idle_ns // 1_000_000_000
            
            logger.warning("HIDIdleTime not found in ioreg output")
            return None
        except subprocess.TimeoutExpired:
            logger.error("ioreg command timed out")
            return None
        except Exception as e:
            logger.error(f"macOS idle detection error: {e}")
            return None
    
    def _get_idle_linux(self) -> Optional[int]:
        """Get idle time on Linux using xprintidle"""
        try:
            # Requires xprintidle to be installed
            result = subprocess.run(
                ['xprintidle'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode != 0:
                logger.error("xprintidle not available. Install: sudo apt install xprintidle")
                return None
            
            # xprintidle returns milliseconds
            idle_ms = int(result.stdout.strip())
            return idle_ms // 1000
        except FileNotFoundError:
            logger.error("xprintidle not found. Install: sudo apt install xprintidle")
            return None
        except Exception as e:
            logger.error(f"Linux idle detection error: {e}")
            return None
    
    def _get_idle_windows(self) -> Optional[int]:
        """Get idle time on Windows using ctypes"""
        try:
            import ctypes
            from ctypes import Structure, c_uint, sizeof, byref
            windll = ctypes.windll  # type: ignore[attr-defined]
            
            class LASTINPUTINFO(Structure):
                _fields_ = [
                    ('cbSize', c_uint),
                    ('dwTime', c_uint)
                ]
            
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = sizeof(lastInputInfo)
            
            if windll.user32.GetLastInputInfo(byref(lastInputInfo)):
                millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis // 1000
            else:
                logger.error("GetLastInputInfo failed")
                return None
        except Exception as e:
            logger.error(f"Windows idle detection error: {e}")
            return None
    
    def check_idle_state(self) -> Dict[str, Any]:
        """
        Check if system is currently idle and track state changes
        
        Returns:
            Dict with idle state and any events that occurred
        """
        current_idle_seconds = self.get_idle_seconds()
        
        if current_idle_seconds is None:
            return {
                'success': False,
                'error': 'Unable to determine idle time',
                'is_idle': self.is_idle
            }
        
        events = []
        previous_state = self.is_idle
        
        # Check if we crossed the idle threshold
        if current_idle_seconds >= self.idle_threshold and not self.is_idle:
            # Transition to idle
            self.is_idle = True
            self.idle_start_time = datetime.now()
            
            # Log idle start event
            success = log_activity('idle_start', {})
            if success:
                events.append('idle_start')
                logger.info(f"Idle state started (idle for {current_idle_seconds}s)")
        
        elif current_idle_seconds < self.idle_threshold and self.is_idle:
            # Transition to active
            if self.idle_start_time:
                idle_duration = (datetime.now() - self.idle_start_time).total_seconds()
            else:
                idle_duration = current_idle_seconds
            
            self.is_idle = False
            
            # Log idle end event
            success = log_activity('idle_end', {
                'idle_duration_seconds': int(idle_duration)
            })
            if success:
                events.append('idle_end')
                logger.info(f"Idle state ended (was idle for {idle_duration:.0f}s)")
            
            self.idle_start_time = None
        
        self.last_check_time = datetime.now()
        
        return {
            'success': True,
            'is_idle': self.is_idle,
            'current_idle_seconds': current_idle_seconds,
            'state_changed': previous_state != self.is_idle,
            'events': events
        }


class BreakTracker:
    """Track and manage work breaks"""
    
    def __init__(self):
        """Initialize break tracker"""
        self.current_break = None
        self.break_history = []
        self.config = load_config()
        
        # Pomodoro defaults (25min work, 5min break)
        self.work_duration_minutes = 25
        self.short_break_minutes = 5
        self.long_break_minutes = 15
        self.pomodoros_before_long_break = 4
        
        self.pomodoro_count = 0
    
    def start_break(self, break_type: str = 'short', manual: bool = True) -> bool:
        """
        Start a break
        
        Args:
            break_type: 'short', 'long', or 'custom'
            manual: Whether manually triggered or automatic
        
        Returns:
            Success status
        """
        if self.current_break:
            logger.warning("Break already in progress")
            return False
        
        duration_minutes = {
            'short': self.short_break_minutes,
            'long': self.long_break_minutes,
            'custom': 10  # Default for custom
        }.get(break_type, self.short_break_minutes)
        
        self.current_break = {
            'type': break_type,
            'start_time': datetime.now(),
            'duration_minutes': duration_minutes,
            'manual': manual
        }
        
        # Log break start
        success = log_activity('break_start', {
            'break_type': break_type,
            'duration_minutes': duration_minutes,
            'manual': manual
        })
        
        if success:
            logger.info(f"Started {break_type} break ({duration_minutes}min)")
        
        return success
    
    def end_break(self) -> bool:
        """
        End current break
        
        Returns:
            Success status
        """
        if not self.current_break:
            logger.warning("No break in progress")
            return False
        
        start_time: datetime = self.current_break['start_time']  # type: ignore[assignment]
        actual_duration = (datetime.now() - start_time).total_seconds()
        
        # Log break end
        success = log_activity('break_end', {
            'break_type': self.current_break['type'],
            'planned_duration_minutes': self.current_break['duration_minutes'],
            'actual_duration_seconds': int(actual_duration),
            'manual': self.current_break['manual']
        })
        
        if success:
            logger.info(f"Ended break (actual: {actual_duration / 60:.1f}min)")
            self.break_history.append({
                **self.current_break,
                'end_time': datetime.now(),
                'actual_duration_seconds': int(actual_duration)
            })
        
        self.current_break = None
        return success
    
    def suggest_break(self, work_duration_minutes: float) -> Optional[str]:
        """
        Suggest a break based on work duration
        
        Args:
            work_duration_minutes: How long user has been working
        
        Returns:
            Break suggestion or None
        """
        if work_duration_minutes >= self.work_duration_minutes:
            self.pomodoro_count += 1
            
            if self.pomodoro_count % self.pomodoros_before_long_break == 0:
                return f"Time for a {self.long_break_minutes}-minute long break! (Completed {self.pomodoro_count} pomodoros)"
            else:
                return f"Time for a {self.short_break_minutes}-minute short break! (Pomodoro {self.pomodoro_count})"
        
        return None
    
    def get_break_stats(self) -> Dict[str, Any]:
        """Get break statistics for today"""
        total_break_seconds = sum(
            b.get('actual_duration_seconds', 0)
            for b in self.break_history
        )
        
        break_types = {}
        for b in self.break_history:
            bt = b['type']
            break_types[bt] = break_types.get(bt, 0) + 1
        
        return {
            'total_breaks': len(self.break_history),
            'total_break_minutes': round(total_break_seconds / 60, 1),
            'break_types': break_types,
            'pomodoros_completed': self.pomodoro_count,
            'current_break': self.current_break is not None
        }


def monitor_idle(check_interval_seconds: int = 30, duration_seconds: Optional[int] = None):
    """
    Continuously monitor idle state
    
    Args:
        check_interval_seconds: How often to check (default 30s)
        duration_seconds: How long to monitor (None = forever)
    """
    config = load_config()
    idle_threshold = config.get('tracking', {}).get('idle_threshold_seconds', 300)
    
    detector = IdleDetector(idle_threshold)
    
    print(f"Starting idle monitor (threshold: {idle_threshold}s, interval: {check_interval_seconds}s)")
    
    start_time = time.time()
    
    try:
        while True:
            result = detector.check_idle_state()
            
            if result['success']:
                status = "IDLE" if result['is_idle'] else "ACTIVE"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status} "
                      f"(idle: {result['current_idle_seconds']}s)")
                
                if result['events']:
                    print(f"  Events logged: {', '.join(result['events'])}")
            else:
                print(f"Error: {result['error']}")
            
            # Check if we should stop
            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                print("Monitoring duration complete")
                break
            
            time.sleep(check_interval_seconds)
    
    except KeyboardInterrupt:
        print("\nIdle monitoring stopped")


def main():
    """Main entry point for testing"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'monitor':
        # Run continuous monitoring
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else None
        monitor_idle(duration_seconds=duration)
    else:
        # Single check
        detector = IdleDetector()
        idle_seconds = detector.get_idle_seconds()
        
        if idle_seconds is not None:
            print(f"Current idle time: {idle_seconds} seconds ({idle_seconds / 60:.1f} minutes)")
            
            if idle_seconds >= 300:
                print("System is IDLE (>5 minutes)")
            else:
                print("System is ACTIVE")
        else:
            print("Unable to determine idle time")
        
        # Test break tracker
        print("\nBreak Tracker Test:")
        tracker = BreakTracker()
        
        suggestion = tracker.suggest_break(26)
        if suggestion:
            print(f"Suggestion: {suggestion}")
        
        tracker.start_break('short')
        time.sleep(2)
        tracker.end_break()
        
        stats = tracker.get_break_stats()
        print(f"Break stats: {stats}")


if __name__ == '__main__':
    main()
