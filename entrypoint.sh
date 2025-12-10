#!/bin/sh
set -e

echo "Starting entrypoint..."
echo "ENV: PORT=${PORT:-<unset>}"
echo "Listing /app contents:"
ls -la /app || true

# If ActivityReport exists, print a quick head to surface in logs
if [ -f "/app/ActivityReport-$(date -u +%Y-%m-%d).json" ]; then
  echo "Today's ActivityReport present:";
  head -n 5 "/app/ActivityReport-$(date -u +%Y-%m-%d).json" || true
fi

exec python3 -m http.server "${PORT:-8000}" --bind 0.0.0.0
