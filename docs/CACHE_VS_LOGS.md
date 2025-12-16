# Cache vs Logs

## Source of truth input
The generator expects raw event logs at:
- ~/Library/Application Support/ActivityTracker/logs/YYYY-MM-DD.jsonl

These are line-delimited JSON events written by the daemon.

## Cache folder
~/dailyaccomplishmentscache contains already-generated ActivityReport JSON artifacts, often created by older flows or manual runs:
- ActivityReport-YYYY-MM-DD.json
- ActivityReport-YYYY-MM-DD-1.json, etc

These are outputs, not inputs.

## Repo outputs
The published artifacts live in:
- ActivityReport-YYYY-MM-DD.json
- gh-pages/ActivityReport-YYYY-MM-DD.json

## Backfill rule
If raw logs are missing but cache ActivityReport files exist, backfill by copying cache artifacts into repo outputs.
