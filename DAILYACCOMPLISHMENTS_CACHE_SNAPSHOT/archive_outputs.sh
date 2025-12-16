#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE="${1:-$(date +%F)}"
OUT_DIR="$REPO_ROOT/reports/$DATE"
mkdir -p "$OUT_DIR"
# Copy JSON report
if [ -f "$REPO_ROOT/ActivityReport-$DATE.json" ]; then
  cp -f "$REPO_ROOT/ActivityReport-$DATE.json" "$OUT_DIR/"
fi
# Ensure dated CSVs exist and copy
for f in hourly_focus.csv category_distribution.csv top_domains.csv; do
  base="${f%.*}"; ext="${f##*.}"
  if [ -f "$REPO_ROOT/$f" ]; then
    cp -f "$REPO_ROOT/$f" "$OUT_DIR/${base}-$DATE.$ext"
  fi
  if [ -f "$REPO_ROOT/${base}-$DATE.$ext" ]; then
    cp -f "$REPO_ROOT/${base}-$DATE.$ext" "$OUT_DIR/" 2>/dev/null || true
  fi
done
# Charts
for f in hourly_focus.svg category_distribution.svg; do
  base="${f%.*}"; ext="${f##*.}"
  if [ -f "$REPO_ROOT/$f" ]; then
    cp -f "$REPO_ROOT/$f" "$OUT_DIR/${base}-$DATE.$ext"
  fi
  if [ -f "$REPO_ROOT/${base}-$DATE.$ext" ]; then
    cp -f "$REPO_ROOT/${base}-$DATE.$ext" "$OUT_DIR/" 2>/dev/null || true
  fi
done
# Index file
cat > "$OUT_DIR/README.txt" <<EON
Archived outputs for $DATE
- ActivityReport-$DATE.json
- hourly_focus-$DATE.csv/svg
- category_distribution-$DATE.csv/svg
- top_domains-$DATE.csv
EON
echo "Archived to $OUT_DIR"
