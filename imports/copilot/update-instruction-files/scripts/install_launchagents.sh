#!/bin/bash
# Install LaunchAgents for DailyAccomplishments
# Usage: bash scripts/install_launchagents.sh [/path/to/repo]

set -e

# Determine repo path
if [ -n "$1" ]; then
    REPO_PATH="$1"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    REPO_PATH="$(dirname "$SCRIPT_DIR")"
fi

# Validate
if [ ! -f "$REPO_PATH/scripts/collector.py" ]; then
    echo "Error: Could not find scripts/collector.py in $REPO_PATH"
    echo "Usage: $0 /path/to/DailyAccomplishments"
    exit 1
fi

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

echo "Installing LaunchAgents for: $REPO_PATH"

# Create collector plist
cat > "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaccomplishments.collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${REPO_PATH}/scripts/collector.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/logs/collector.out.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/logs/collector.err.log</string>
</dict>
</plist>
EOF

echo "Created: $LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist"

# Create reporter plist (runs every 15 minutes)
cat > "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaccomplishments.reporter</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_PATH}/scripts/cron_report_and_push.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${REPO_PATH}/logs/reporter.out.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_PATH}/logs/reporter.err.log</string>
</dict>
</plist>
EOF

echo "Created: $LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist"

# Create logs directory
mkdir -p "$REPO_PATH/logs"

# Make scripts executable
chmod +x "$REPO_PATH/scripts/collector.py"
chmod +x "$REPO_PATH/scripts/generate_daily_json.py"
chmod +x "$REPO_PATH/scripts/cron_report_and_push.sh"

# Unload if already loaded (ignore errors)
launchctl unload "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist" 2>/dev/null || true

# Load the agents
launchctl load "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.collector.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.dailyaccomplishments.reporter.plist"

echo ""
echo "✅ LaunchAgents installed and loaded!"
echo ""
echo "The collector is now tracking your activity."
echo "Reports will be generated and pushed every 15 minutes."
echo ""
echo "⚠️  IMPORTANT: Grant Accessibility permissions!"
echo "   System Settings → Privacy & Security → Accessibility"
echo "   Add: Terminal (or iTerm) and /usr/bin/python3"
echo ""
echo "Check logs:"
echo "   tail -f $REPO_PATH/logs/collector.out.log"
echo "   tail -f $REPO_PATH/logs/reporter.out.log"
echo ""
echo "To uninstall: bash $REPO_PATH/scripts/uninstall_launchagents.sh"
