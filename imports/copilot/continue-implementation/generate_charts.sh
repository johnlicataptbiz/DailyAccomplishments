#!/bin/bash
START_DATE="2025-11-21"
END_DATE="2025-12-05"
NUM_DAYS=$$ (( ( $$(date -j -f %Y-%m-%d "$END_DATE" +%s) - $(date -j -f %Y-%m-%d "$START_DATE" +%s) ) / 86400 ))
for D in $(seq 0 "$NUM_DAYS"); do
    DATE_TO_RUN=$(date -j -v+"$D"d -f "%Y-%m-%d" "$START_DATE" +%Y-%m-%d)
    echo "Generating charts for $DATE_TO_RUN..."
    python3 tools/generate_reports.py "$DATE_TO_RUN" || echo "Failed for $DATE_TO_RUN"
done
