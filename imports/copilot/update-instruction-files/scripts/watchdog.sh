#!/bin/bash
# Watchdog for Daily Accomplishments collector
# - Ensures collector is loaded at login
# - Every run: restarts collector if not running or stalled

set -euo pipefail

LABEL="com.dailyaccomplishments.collector"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
REPO="$HOME/DailyAccomplishments"
LOGDIR="$REPO/logs"
TODAY="$(date +%F)"
LOGFILE="$LOGDIR/activity-${TODAY}.jsonl"
UIDSTR="gui/$(id -u)"

mkdir -p "$LOGDIR"

# Ensure LaunchAgent is loaded (starts at login due to RunAtLoad)
if ! launchctl list | grep -q "$LABEL"; then
  if [ -f "$PLIST" ]; then
    launchctl load "$PLIST" || true
  fi
fi

# Determine if collector is stalled (no new log entries for > 6 minutes)
now=$(date +%s)
last=0
if [ -f "$LOGFILE" ]; then
  # macOS stat to get mtime epoch
  last=$(stat -f %m "$LOGFILE" 2>/dev/null || echo 0)
fi
age=$(( now - last ))

# If not listed in launchctl, or log too old, force-restart
if ! launchctl list | grep -q "$LABEL" || [ "$age" -gt 360 ]; then
  # kickstart with -k kills existing before start
  launchctl kickstart -k "$UIDSTR/$LABEL" || {
    # Fallback: unload/load
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST" || true
  }
fi

