#!/usr/bin/env bash
# Preview and evaluate a planned merge from source -> dest
set -euo pipefail
SRC=${1:-"$HOME/DailyAccomplishments-1"}
DST=${2:-"$HOME/DailyAccomplishments"}
REPORT=${3:-"$PWD/merge_report.json"}

echo "Dry-run rsync from $SRC -> $DST"
rsync -nav --exclude='.git' "$SRC/" "$DST/"

echo "Running evaluation script to produce $REPORT"
python3 "$(dirname "$0")/evaluate_merge.py" --source "$SRC" --dest "$DST" --report "$REPORT" --sample-diff

echo "Done. Report at: $REPORT"
