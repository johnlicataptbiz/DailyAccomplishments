#!/bin/bash
# Uninstall LaunchAgents for DailyAccomplishments

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "Uninstalling DailyAccomplishments LaunchAgents..."

# Unload agents
launchctl unload "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist" 2>/dev/null || true

# Remove plist files
rm -f "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist"

echo "✅ LaunchAgents uninstalled."
echo "   Activity collection has stopped."
echo "   Your log files in logs/ are preserved."
