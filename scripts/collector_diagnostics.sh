#!/usr/bin/env bash
# Collector diagnostics helper
# Usage: bash scripts/collector_diagnostics.sh [<path-to-repo>]
set -euo pipefail
REPO_ROOT=${1:-$PWD}
LOGS_DIR="$REPO_ROOT/logs/daily"

echo "Collector diagnostics report — $(date -u)"
echo "Repository root: $REPO_ROOT"

echo "\n1) Logs directory status"
if [ -d "$LOGS_DIR" ]; then
  echo "Logs dir exists: $LOGS_DIR"
  echo "Last 10 files:"; ls -la "$LOGS_DIR" | tail -n 10 || true
  echo "Most recent 5 entries (stat):"; ls -lt "$LOGS_DIR" | head -n 5 || true
else
  echo "Logs dir NOT FOUND: $LOGS_DIR"
fi

echo "\n2) Check for missing date (2025-12-11 as sample)"
if [ -f "$LOGS_DIR/2025-12-11.jsonl" ]; then
  echo "Found 2025-12-11.jsonl"
else
  echo "MISSING: 2025-12-11.jsonl"
fi

echo "\n3) Check collector process (launchd/systemd heuristics)"
if command -v launchctl >/dev/null 2>&1; then
  echo "launchctl list | grep activity"; launchctl list | grep -i activity || true
fi
if command -v systemctl >/dev/null 2>&1; then
  echo "systemctl status activitytracker.service (if exists)"; sudo systemctl status activitytracker || true
fi

echo "\n4) Check system logs for 'activitytracker' process (last 2 days)"
if command -v log >/dev/null 2>&1; then
  log show --predicate 'process == "activitytracker"' --last 2d | tail -n 200 || true
else
  echo "macOS 'log' not available in PATH or not macOS";
fi

echo "\n5) Disk usage"
df -h || true

echo "\n6) Quick generate test (dry run)"
if [ -f "$REPO_ROOT/scripts/generate_daily_json.py" ]; then
  echo "Running generator for 2025-12-11 (will only report if logs exist)"
  python3 "$REPO_ROOT/scripts/generate_daily_json.py" 2025-12-11 || true
else
  echo "No scripts/generate_daily_json.py found at $REPO_ROOT/scripts"
fi

echo "\n7) Search for misplaced log file names"
find "$REPO_ROOT" -type f -iname '*2025-12-11*' -maxdepth 4 -print || true

echo "\nDiagnostics complete. If logs are missing, check the collector service or scheduled task on the host that should write files into $LOGS_DIR." 
