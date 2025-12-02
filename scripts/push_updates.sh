#!/bin/bash
# Push updates to GitHub
# Used by cron_report_and_push.sh or can be run manually

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Check for changes
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to push"
    exit 0
fi

DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

git add -A
git commit -m "Update: $DATE $TIME"
git push origin main

echo "Pushed to main"
