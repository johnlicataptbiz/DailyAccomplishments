#!/usr/bin/env python3
"""
Example usage of TrackerAdapter

Run: python3 example_usage.py
"""

from mac_tracker_adapter import TrackerAdapter

# Initialize adapter (logs to ~/DailyAccomplishments by default)
adapter = TrackerAdapter()

# Log some activity
adapter.log_focus_change("VS Code", "main.py", duration_seconds=1800)  # 30 min
adapter.log_focus_change("Chrome", "GitHub - Pull Requests", duration_seconds=600)  # 10 min
adapter.log_app_switch("Chrome", "Slack")
adapter.log_focus_change("Slack", "#general", duration_seconds=300)  # 5 min
adapter.log_meeting("Sales Call", duration_minutes=60)

# Generate report with console output
adapter.generate_report(print_report=True)

print("\nDone! Check the reports directory for JSON and Markdown reports.")
