#!/bin/bash
# Cron Report and Push
# Single publisher: generates report, runs integrations, enriches, then commits and pushes.

set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "[$(date)] DEBUG: cwd=$(pwd)"
echo "[$(date)] DEBUG: script source=$SCRIPT_SOURCE"
echo "[$(date)] DEBUG: script dir=$SCRIPT_DIR"
echo "[$(date)] DEBUG: git work-tree=$(git rev-parse --is-inside-work-tree 2>/dev/null || echo 'no')"
echo "[$(date)] DEBUG: branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "[$(date)] ERROR: Not inside a git work tree: $(pwd)" >&2
  exit 1
}

# Guard against detached HEAD (LaunchAgent can do this)
git fetch origin >/dev/null 2>&1 || true
CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$CUR" = "HEAD" ] || [ -z "$CUR" ]; then
  echo "[$(date)] WARN: Detached HEAD or unknown branch; recovering main"
  git checkout -B main origin/main >/dev/null 2>&1 || git checkout main >/dev/null 2>&1 || true
fi

CUR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$CUR" = "main" ]; then
  git pull --rebase origin main >/dev/null 2>&1 || true
else
  echo "[$(date)] WARN: Not on main (current: $CUR). Will commit locally but skip push."
fi

DATE_ARG="${1:-}"
TARGET_DATE="${DATE_ARG:-$(date +%F)}"

# If running on a schedule without an explicit date, also refresh yesterday shortly
# after midnight so the prior day's report finalizes cleanly.
EXTRA_DATES=""
if [ -z "$DATE_ARG" ]; then
  HOUR="$(date +%H)"
  if [ "${HOUR#0}" -lt 3 ]; then
    YESTERDAY="$(python3 - <<'PY'
from datetime import date, timedelta
print((date.today() - timedelta(days=1)).isoformat())
PY
)"
    EXTRA_DATES="$YESTERDAY"
  fi
fi

for D in "$TARGET_DATE" $EXTRA_DATES; do
  echo "[$(date)] Generating report for $D"

  # 1) Generate the base daily JSON report from local activity logs
  python3 "$SCRIPT_DIR/generate_daily_json.py" "$D" 2>/dev/null || true

  # 2) Run integrations but DO NOT push. This prevents drift.
  if [ -f "$SCRIPT_DIR/sync_all.py" ]; then
    echo "[$(date)] Syncing integrations (no-push) for $D..."
    python3 "$SCRIPT_DIR/sync_all.py" "$D" --no-push 2>/dev/null || true
  fi

  # 3) Enrichers run AFTER integrations so the committed report includes them
  python3 "$SCRIPT_DIR/import_screentime.py" --date "$D" --update-report --repo "$REPO_ROOT" 2>/dev/null || true

  if [ -f "$REPO_ROOT/credentials/calendar.ics" ]; then
    python3 "$SCRIPT_DIR/import_calendar_ics.py" --date "$D" --ics "$REPO_ROOT/credentials/calendar.ics" --update-report --repo "$REPO_ROOT" 2>/dev/null || true
  fi

  python3 "$SCRIPT_DIR/import_browser_history.py" --date "$D" --update-report --repo "$REPO_ROOT" 2>/dev/null || true

  # 4) Charts and archives
  if python3 -c "import matplotlib" 2>/dev/null; then
    python3 tools/generate_reports.py "$D" 2>/dev/null || true
  fi

  "$SCRIPT_DIR"/archive_outputs.sh "$D" 2>/dev/null || true
done

# 5) Copy files to gh-pages worktree if it exists
GH_PAGES="$REPO_ROOT/gh-pages"
if [ -d "$GH_PAGES" ] && [ -f "$GH_PAGES/.git" ]; then
  echo "[$(date)] Syncing to gh-pages worktree..."
  cp -f "$REPO_ROOT"/ActivityReport-*.json "$GH_PAGES/" 2>/dev/null || true
  cp -f "$REPO_ROOT"/dashboard.html "$GH_PAGES/" 2>/dev/null || true
  cp -f "$REPO_ROOT"/*.csv "$GH_PAGES/" 2>/dev/null || true
  cp -f "$REPO_ROOT"/*.svg "$GH_PAGES/" 2>/dev/null || true
  mkdir -p "$GH_PAGES/reports"
  cp -f "$REPO_ROOT"/reports/*.json "$GH_PAGES/reports/" 2>/dev/null || true
  cp -f "$REPO_ROOT"/reports/*.md "$GH_PAGES/reports/" 2>/dev/null || true
fi

python3 "$SCRIPT_DIR/postprocess_report.py" "$TARGET_DATE" 2>/dev/null || true
# 6) Commit and push main (single publisher)
if git diff --quiet && git diff --cached --quiet; then
  echo "[$(date)] No changes to main"
else
  DATE="$(date +%Y-%m-%d)"
  TIME="$(date +%H:%M)"
  git add ActivityReport-*.json reports/ *.csv *.svg dashboard.html 2>/dev/null || true
  git commit -m "Auto-update: $DATE $TIME" || true
  echo "[$(date)] Changes committed to main"

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

# 7) Push gh-pages if it has changes
if [ -d "$GH_PAGES" ] && [ -f "$GH_PAGES/.git" ]; then
  cd "$GH_PAGES"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    DATE="$(date +%Y-%m-%d)"
    TIME="$(date +%H:%M)"
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
