from mac_tracker_adapter import TrackerAdapter
adapter = TrackerAdapter()

# When app focus changes:
adapter.log_focus_change("VS Code", "main.py", duration_seconds=120)

# When a meeting starts:
adapter.log_meeting("Sales Call", duration_minutes=60)

# At end of day:
adapter.generate_report()