#!/usr/bin/env bash
set -euo pipefail

LABEL="com.dailyaccomplishments.reporter"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1800}"

REPO_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_PATH}/logs"
OUT_LOG="${LOG_DIR}/reporter.out.log"
ERR_LOG="${LOG_DIR}/reporter.err.log"

mkdir -p "${LOG_DIR}"

cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${REPO_PATH}/scripts/cron_report_and_push_publisher.sh</string>
  </array>

  <key>StartInterval</key>
  <integer>${INTERVAL_SECONDS}</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${OUT_LOG}</string>

  <key>StandardErrorPath</key>
  <string>${ERR_LOG}</string>
</dict>
</plist>
PLIST

echo "Wrote ${PLIST_PATH}"

launchctl bootout "gui/$(id -u)" "${PLIST_PATH}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

echo "Installed and kickstarted ${LABEL}"
