#!/usr/bin/env bash
set -euo pipefail
# Install the ActivityTracker launchd plist for the current user
# Usage: bash scripts/install_launchd.sh [<path-to-repo>]

REPO_ROOT=${1:-$(cd "$(dirname "$0")/.." && pwd)}
TEMPLATE="$REPO_ROOT/scripts/com.activitytracker.daemon.plist.template"
TARGET_PLIST="$HOME/Library/LaunchAgents/com.activitytracker.daemon.plist"

if [ ! -f "$TEMPLATE" ]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

echo "Installing ActivityTracker launchd plist"
echo "Repository: $REPO_ROOT"
echo "Target: $TARGET_PLIST"

mkdir -p "$HOME/Library/LaunchAgents"

# Render template (replace placeholders)
sed \
  -e "s|__REPO_DIR__|$REPO_ROOT|g" \
  -e "s|__HOME__|$HOME|g" \
  "$TEMPLATE" > "$TARGET_PLIST.tmp"

# Validate the generated plist roughly
if ! xmllint --noout "$TARGET_PLIST.tmp" >/dev/null 2>&1; then
  echo "Generated plist is not valid XML. Please inspect $TARGET_PLIST.tmp" >&2
  mv "$TARGET_PLIST.tmp" "$TARGET_PLIST.invalid"
  exit 1
fi

mv "$TARGET_PLIST.tmp" "$TARGET_PLIST"
chmod 644 "$TARGET_PLIST"

echo "Unloading existing job (if any)"
if command -v launchctl >/dev/null 2>&1; then
  launchctl unload "$TARGET_PLIST" 2>/dev/null || true
fi

echo "Loading launchd job"
launchctl load -w "$TARGET_PLIST"

echo "Status:"
launchctl list | grep com.activitytracker.daemon || true

echo "Tailing logs (last 40 lines). Use Ctrl-C to stop"
tail -n 40 "$HOME/Library/Logs/ActivityTracker.out.log" || true

echo "Install complete. Verify logs are being written to: $HOME/Library/Application Support/ActivityTracker/logs"
echo "Run scripts/collector_diagnostics.sh or check: ls -la \"$HOME/Library/Application Support/ActivityTracker/logs\""
