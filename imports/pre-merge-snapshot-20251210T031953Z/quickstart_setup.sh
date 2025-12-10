#!/bin/bash
# Quick setup script for Daily Accomplishments Tracker
# Creates required directories and initializes configuration

set -e

echo "=========================================="
echo "Daily Accomplishments Tracker - Quick Setup"
echo "=========================================="
echo ""

# Create required directories
echo "Creating required directories..."
mkdir -p reports
echo "  ✓ Created: reports/"

mkdir -p logs/daily
echo "  ✓ Created: logs/daily/"

mkdir -p logs/archive
echo "  ✓ Created: logs/archive/"

echo ""

# Copy config if it doesn't exist
if [ ! -f config.json ]; then
    echo "Setting up configuration..."
    cp config.json.example config.json
    echo "  ✓ Created: config.json (from config.json.example)"
    echo ""
    echo "⚠️  IMPORTANT: Edit config.json with your settings:"
    echo "     1. Set your timezone (tracking.timezone)"
    echo "     2. Configure email settings (notifications.email) - optional"
    echo "     3. Configure Slack webhook (notifications.slack_webhook) - optional"
    echo ""
else
    echo "Configuration file already exists: config.json"
    echo "  ✓ Skipping config setup"
    echo ""
fi

# Print setup instructions
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Edit your configuration:"
echo "   nano config.json"
echo ""
echo "2. Run the integration example to test:"
echo "   python3 examples/integration_example.py"
echo ""
echo "3. Generate your first report:"
echo "   python3 tools/auto_report.py"
echo ""
echo "4. View the dashboard:"
echo "   python3 -m http.server 8000"
echo "   Then open: http://localhost:8000/dashboard.html"
echo ""
echo "5. Read the setup guide for detailed instructions:"
echo "   cat SETUP_GUIDE.md"
echo ""
echo "=========================================="
echo ""
