#!/usr/bin/env bash
set -euo pipefail

START="${1:-}"
END="${2:-}"
COPY_TODAY_CSVS="${3:-}"

if [[ -z "$START" || -z "$END" ]]; then
  echo "Usage: scripts/backfill_local.sh YYYY-MM-DD YYYY-MM-DD [--copy-today-csvs]"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Activate venv if present
if [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
fi

mkdir -p logs/daily

d="$START"
while [[ "$d" < "$END" || "$d" == "$END" ]]; do
  echo ""
  echo "==== Backfilling $d ===="

  # Screen Time -> merges into ActivityReport-$d.json
  python3 scripts/import_screentime.py --date "$d" --repo "$REPO_ROOT" --update-report

  # Browser history -> merges into ActivityReport-$d.json (if available)
  python3 scripts/import_browser_history.py --date "$d" --repo "$REPO_ROOT" --update-report || true

  # Ensure canonical report JSON exists in reports/$d/
  mkdir -p "reports/$d"
  if [[ -f "ActivityReport-$d.json" ]]; then
    cp -f "ActivityReport-$d.json" "reports/$d/ActivityReport-$d.json"
  fi

  # If a tiny JSONL exists (common culprit), move aside so generator uses the merged JSON
  jsonl="logs/daily/$d.jsonl"
  if [[ -f "$jsonl" ]]; then
    lines="$(wc -l < "$jsonl" | tr -d ' ')"
    if [[ "$lines" -lt 10 ]]; then
      mv -f "$jsonl" "$jsonl.bak"
      echo "Moved tiny $jsonl -> $jsonl.bak"
    fi
  fi

  PYTHONPATH=. python3 tools/generate_reports.py "$d"

  # Next day
  d="$(python3 - <<PY
from datetime import date, timedelta
y,m,dd = map(int, "$d".split("-"))
print((date(y,m,dd) + timedelta(days=1)).isoformat())
PY
)"
done

# Copy END-day CSVs into repo root (for dashboards that read root files)
if [[ "$COPY_TODAY_CSVS" == "--copy-today-csvs" ]]; then
  cp -f "reports/$END/top_domains-$END.csv" "top_domains.csv" 2>/dev/null || true
  cp -f "reports/$END/category_distribution-$END.csv" "category_distribution.csv" 2>/dev/null || true
  cp -f "reports/$END/hourly_focus-$END.csv" "hourly_focus.csv" 2>/dev/null || true
  echo "Copied $END CSVs into repo root."
fi

echo ""
echo "Done."
