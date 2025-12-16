#!/usr/bin/env python3
"""
Tracker CLI - Command-line interface for DailyAccomplishments

Usage:
    python3 tracker_cli.py report [--date YYYY-MM-DD] [--data-dir DIR]
    python3 tracker_cli.py log-focus --app NAME [--file PATH] --duration-seconds N [--data-dir DIR] [--report]
    python3 tracker_cli.py log-meeting --title TITLE --duration-minutes N [--data-dir DIR] [--report]
    python3 tracker_cli.py reset [--date YYYY-MM-DD] [--data-dir DIR] [--report]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from mac_tracker_adapter import TrackerAdapter


def cmd_report(args):
    """Generate and display report"""
    adapter = TrackerAdapter(base_dir=args.data_dir) if args.data_dir else TrackerAdapter()
    
    if args.date:
        # Check if date has data
        log_file = adapter.logs_dir / f"{args.date}.jsonl"
        if not log_file.exists():
            print(f"No data for {args.date}")
            return 1
        
        # Temporarily set adapter date
        adapter.current_date = args.date
        adapter.log_file = log_file
    
    events = adapter._read_events()
    if not events or len(events) <= 1:  # Only metadata or empty
        print(f"No data for {adapter.current_date}")
        return 0
    
    adapter.generate_report(print_report=True)
    return 0


def cmd_log_focus(args):
    """Log a focus session"""
    adapter = TrackerAdapter(base_dir=args.data_dir) if args.data_dir else TrackerAdapter()
    
    adapter.log_focus_change(
        app=args.app,
        window_title=args.file or "",
        duration_seconds=args.duration_seconds
    )
    
    print(f"✓ Logged {args.duration_seconds}s focus on {args.app}")
    
    if args.report:
        adapter.generate_report(print_report=True)
    
    return 0


def cmd_log_meeting(args):
    """Log a meeting"""
    adapter = TrackerAdapter(base_dir=args.data_dir) if args.data_dir else TrackerAdapter()
    
    adapter.log_meeting(
        name=args.title,
        duration_minutes=args.duration_minutes
    )
    
    print(f"✓ Logged {args.duration_minutes}min meeting: {args.title}")
    
    if args.report:
        adapter.generate_report(print_report=True)
    
    return 0


def cmd_reset(args):
    """Reset a day's log"""
    adapter = TrackerAdapter(base_dir=args.data_dir) if args.data_dir else TrackerAdapter()
    
    target_date = args.date or adapter.current_date
    adapter.reset_day(target_date)
    
    print("Reset complete.")
    
    if args.report:
        # Show empty report
        adapter.current_date = target_date
        adapter.log_file = adapter.logs_dir / f"{target_date}.jsonl"
        events = adapter._read_events()
        if not events:
            print(f"No data for {target_date}")
        else:
            adapter.generate_report(print_report=True)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="DailyAccomplishments Tracker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s report
  %(prog)s report --date 2025-12-01
  %(prog)s log-focus --app "VS Code" --file main.py --duration-seconds 1800
  %(prog)s log-meeting --title "Sales Call" --duration-minutes 60
  %(prog)s reset --date 2025-12-02
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate and display report")
    report_parser.add_argument("--date", help="Date (YYYY-MM-DD), default: today")
    report_parser.add_argument("--data-dir", help="Data directory path")
    
    # Log focus command
    focus_parser = subparsers.add_parser("log-focus", help="Log a focus session")
    focus_parser.add_argument("--app", required=True, help="Application name")
    focus_parser.add_argument("--file", help="File/window title")
    focus_parser.add_argument("--duration-seconds", type=int, required=True, help="Duration in seconds")
    focus_parser.add_argument("--started", help="Start time (ISO format)")
    focus_parser.add_argument("--data-dir", help="Data directory path")
    focus_parser.add_argument("--report", action="store_true", help="Show report after logging")
    
    # Log meeting command
    meeting_parser = subparsers.add_parser("log-meeting", help="Log a meeting")
    meeting_parser.add_argument("--title", required=True, help="Meeting title")
    meeting_parser.add_argument("--duration-minutes", type=int, required=True, help="Duration in minutes")
    meeting_parser.add_argument("--started", help="Start time (ISO format)")
    meeting_parser.add_argument("--data-dir", help="Data directory path")
    meeting_parser.add_argument("--report", action="store_true", help="Show report after logging")
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset/delete a day's log")
    reset_parser.add_argument("--date", help="Date (YYYY-MM-DD), default: today")
    reset_parser.add_argument("--data-dir", help="Data directory path")
    reset_parser.add_argument("--report", action="store_true", help="Show report after reset")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        "report": cmd_report,
        "log-focus": cmd_log_focus,
        "log-meeting": cmd_log_meeting,
        "reset": cmd_reset,
    }
    
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
