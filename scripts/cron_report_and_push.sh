#!/bin/bash
# Cron Report and Push - Run every 15 minutes by LaunchAgent
# Generates daily JSON report, syncs integrations, and optionally pushes to GitHub

set -e

# Prefer ${BASH_SOURCE[0]} so the script resolves correctly when invoked
# from a symlink, sourced context, or via LaunchAgent. Fall back to $0.
SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "[$(date)] Starting report generation..."
echo "[$(date)] script source: $SCRIPT_SOURCE"
echo "[$(date)] cwd: $(pwd)"
echo "[$(date)] script dir: $SCRIPT_DIR"

# Ensure repo is on `main` (LaunchAgent can run from a detached HEAD)
if git rev-parse --git-dir >/dev/null 2>&1; then
    git fetch origin >/dev/null 2>&1 || true
    CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
    echo "[$(date)] current branch before guard: $CUR"

    if [ "$CUR" = "HEAD" ] || [ -z "$CUR" ]; then
        # detached or unknown: recover by checking out main from origin if possible
        git checkout -B main origin/main >/dev/null 2>&1 || git checkout main >/dev/null 2>&1 || true
        CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
        echo "[$(date)] branch after recovery: $CUR"
    fi

    if [ "$CUR" = "main" ]; then
        git pull --rebase origin main >/dev/null 2>&1 || true
    fi
fi

# Generate the daily JSON report from local activity logs
python3 "$SCRIPT_DIR/generate_daily_json.py" 2>/dev/null || true

# Enrich report with Screen Time (KnowledgeC) data if accessible
TODAY=$(date +%F)
python3 "$SCRIPT_DIR/import_screentime.py" --date "$TODAY" --update-report --repo "$REPO_ROOT" 2>/dev/null || true

# Enrich report with Browser History for today (Chrome/Safari)
python3 "$SCRIPT_DIR/import_browser_history.py" --date "$TODAY" --update-report --repo "$REPO_ROOT" 2>/dev/null || true

# Sync all integrations (HubSpot, Monday, Slack, Google Calendar, Aloware)
if [ -f "$SCRIPT_DIR/sync_all.py" ]; then
    echo "[$(date)] Syncing integrations..."
    python3 "$SCRIPT_DIR/sync_all.py" 2>/dev/null || true
fi

# Generate charts if matplotlib is available
if python3 -c "import matplotlib" 2>/dev/null; then
    python3 tools/generate_reports.py 2>/dev/null || true
fi

# Archive today
"$SCRIPT_DIR"/archive_outputs.sh "$TODAY" 2>/dev/null || true

# Copy files to gh-pages worktree if it exists
GH_PAGES="$REPO_ROOT/gh-pages"
if [ -d "$GH_PAGES" ] && [ -f "$GH_PAGES/.git" ]; then
    echo "[$(date)] Syncing to gh-pages..."
    cp -f "$REPO_ROOT"/ActivityReport-*.json "$GH_PAGES/" 2>/dev/null || true
    cp -f "$REPO_ROOT"/dashboard.html "$GH_PAGES/" 2>/dev/null || true
    cp -f "$REPO_ROOT"/*.csv "$GH_PAGES/" 2>/dev/null || true
    cp -f "$REPO_ROOT"/*.svg "$GH_PAGES/" 2>/dev/null || true
    mkdir -p "$GH_PAGES/reports"
    cp -f "$REPO_ROOT"/reports/*.json "$GH_PAGES/reports/" 2>/dev/null || true
    cp -f "$REPO_ROOT"/reports/*.md "$GH_PAGES/reports/" 2>/dev/null || true
fi

# Check if there are changes to commit (main branch)
if git diff --quiet && git diff --cached --quiet; then
    echo "[$(date)] No changes to main"
else
    DATE=$(date +%Y-%m-%d)
    TIME=$(date +%H:%M)
    git add ActivityReport-*.json reports/ *.csv *.svg dashboard.html
    git commit -m "Auto-update: $DATE $TIME" || true
    echo "[$(date)] Changes committed to main"

    # Try to push main, but only if we're actually on main
    CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
    if [ "$CUR" != "main" ]; then
        echo "[$(date)] Not on main (current: $CUR); skipping push"
    else
        if git push origin main 2>/dev/null; then
            echo "[$(date)] Pushed to main"
        else
            echo "[$(date)] Main push skipped (no credentials or offline)"
        fi
    fi
fi

# Push gh-pages if it has changes
if [ -d "$GH_PAGES" ] && [ -f "$GH_PAGES/.git" ]; then
    cd "$GH_PAGES"
    if ! git diff --quiet || ! git diff --cached --quiet; then
        DATE=$(date +%Y-%m-%d)
        TIME=$(date +%H:%M)
        git add .
        git commit -m "Dashboard update: $DATE $TIME" || true
        if git push origin gh-pages 2>/dev/null; then
            echo "[$(date)] Pushed to gh-pages"
        else
            echo "[$(date)] gh-pages push skipped"
        fi
    fi
    cd "$REPO_ROOT"
fi

echo "[$(date)] Report generation complete"
