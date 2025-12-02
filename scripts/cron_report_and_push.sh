#!/bin/bash
# Cron Report and Push - Run every 15 minutes by LaunchAgent
# Generates daily JSON report and pushes to GitHub

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

# Commit and push
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

git add -A
git commit -m "Auto-update: $DATE $TIME" || true

# Push to both branches
git push origin main 2>/dev/null || echo "Failed to push to main"

# Copy to gh-pages deploy folder and push
if [ -d "/tmp/gh-pages-deploy" ]; then
    cp ActivityReport-*.json /tmp/gh-pages-deploy/ 2>/dev/null || true
    cp *.svg *.csv /tmp/gh-pages-deploy/ 2>/dev/null || true
    cd /tmp/gh-pages-deploy
    git add -A
    git commit -m "Auto-update: $DATE $TIME" 2>/dev/null || true
    git push origin gh-pages 2>/dev/null || echo "Failed to push to gh-pages"
fi

echo "[$(date)] Report generation complete"
