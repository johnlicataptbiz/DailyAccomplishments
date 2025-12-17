#!/usr/bin/env bash
set -euo pipefail

START="${1:-}"
END="${2:-}"
COPY_ROOT_CSVS="${3:-}"  # pass --copy-end-csvs

if [[ -z "$START" || -z "$END" ]]; then
  echo "Usage: scripts/backfill_local_jsonl.sh YYYY-MM-DD YYYY-MM-DD [--copy-end-csvs]"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
fi

mkdir -p logs/daily

append_screentime_jsonl () {
  local d="$1"
  PYTHONPATH=. python - <<PY
import json
from pathlib import Path
import scripts.import_screentime as st

date_str = "$d"
repo = Path("$REPO_ROOT")
db = Path.home() / "Library/Application Support/Knowledge/knowledgeC.db"
log_path = repo / "logs/daily" / f"{date_str}.jsonl"
log_path.parent.mkdir(parents=True, exist_ok=True)

tmp = st._copy_db_safely(db)
if not tmp:
    raise SystemExit("Could not access knowledgeC.db (need Full Disk Access for your terminal/agent).")

try:
    usages = st.query_app_usage(tmp, date_str)
finally:
    try: tmp.unlink()
    except Exception: pass

added = 0
with log_path.open("a", encoding="utf-8") as f:
    for u in usages:
        secs = int(getattr(u, "seconds", 0))
        if secs <= 0:
            continue
        bundle = getattr(u, "bundle_id", None) or getattr(u, "app", "")
        app = st.friendly_app_name(bundle)
        ev = {
            "type": "focus_change",
            "timestamp": u.start.isoformat(),
            "data": {
                "app": app,
                "duration_seconds": secs,
            },
        }
        f.write(json.dumps(ev) + "\n")
        added += 1

print(f"Appended {added} Screen Time focus_change events to {log_path}")
PY
}

d="$START"
while [[ "$d" < "$END" || "$d" == "$END" ]]; do
  echo ""
  echo "==== Backfilling $d ===="

  # 1) Ensure the JSONL exists and is populated with Screen Time focus_change events
  append_screentime_jsonl "$d"

  # 2) Generate report artifacts from JSONL (this is now the source of truth)
  PYTHONPATH=. python tools/generate_reports.py "$d"

  # 3) Optional: also merge browser history into the root ActivityReport for highlights/inferences
  #    This does not feed top_domains unless your generator uses those fields, but it keeps the insights in the JSON.
  PYTHONPATH=. python scripts/import_browser_history.py --date "$d" --repo "$REPO_ROOT" --update-report || true

  # 4) Keep the canonical reports folder JSON aligned with the enriched root JSON (if it exists)
  mkdir -p "reports/$d"
  if [[ -f "ActivityReport-$d.json" ]]; then
    cp -f "ActivityReport-$d.json" "reports/$d/ActivityReport-$d.json"
  fi

  # Next day
  d="$(python - <<PY
from datetime import date, timedelta
y,m,dd = map(int, "$d".split("-"))
print((date(y,m,dd) + timedelta(days=1)).isoformat())
PY
)"
done

# Copy END day CSVs into repo root for dashboards that read root files
if [[ "$COPY_ROOT_CSVS" == "--copy-end-csvs" ]]; then
  cp -f "reports/$END/hourly_focus-$END.csv" "hourly_focus.csv" 2>/dev/null || true
  cp -f "reports/$END/category_distribution-$END.csv" "category_distribution.csv" 2>/dev/null || true
  cp -f "reports/$END/top_domains-$END.csv" "top_domains.csv" 2>/dev/null || true
  echo "Copied $END CSVs into repo root."
fi

echo ""
echo "Done."
