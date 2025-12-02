#!/bin/bash
# Cron Report and Push - Run every 15 minutes by LaunchAgent
# Generates daily JSON report and optionally pushes to GitHub

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

echo "[$(date)] Starting report generation..."

# Generate the daily JSON report
python3 "$SCRIPT_DIR/generate_daily_json.py"

# Generate charts if matplotlib is available
if python3 -c "import matplotlib" 2>/dev/null; then
    python3 tools/generate_reports.py 2>/dev/null || true
fi

# Check if there are changes to commit
if git diff --quiet && git diff --cached --quiet; then
    echo "[$(date)] No changes to commit"
    exit 0
fi

# Commit locally (always works)
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

git add -A
git commit -m "Auto-update: $DATE $TIME" || true

echo "[$(date)] Changes committed locally"

# Try to push - but don't fail if auth isn't set up
# This allows the LaunchAgent to keep running even without push access
if git push origin main 2>/dev/null; then
    echo "[$(date)] Pushed to main"
else
    echo "[$(date)] Push skipped (no credentials or offline). Run 'git push' manually when ready."
fi

echo "[$(date)] Report generation complete"
