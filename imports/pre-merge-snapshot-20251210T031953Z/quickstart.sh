#!/bin/bash
# Quick start script for Daily Accomplishments Tracker

set -e

echo "=========================================="
echo "Daily Accomplishments Tracker - Quick Start"
echo "=========================================="
echo ""

# Check Python version
echo "1. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "   ✓ Python 3 found: $PYTHON_VERSION"
else
    echo "   ✗ Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# Verify installation
echo ""
echo "2. Verifying installation..."
python3 verify_installation.py
if [ $? -ne 0 ]; then
    echo "   ✗ Installation verification failed"
    exit 1
fi

# Create directories
echo ""
echo "3. Creating required directories..."
mkdir -p logs/daily logs/archive reports
echo "   ✓ Directories created"

# Check if config needs setup
echo ""
echo "4. Checking configuration..."
if grep -q "YOUR_APP_PASSWORD" config.json 2>/dev/null || grep -q "your-email@gmail.com" config.json 2>/dev/null; then
    echo "   ⚠ Configuration contains placeholder values"
    echo "   Please edit config.json with your settings:"
    echo "     - Set your timezone (tracking.timezone)"
    echo "     - Configure email settings (notifications.email)"
    echo "     - Configure Slack webhook (notifications.slack_webhook)"
else
    echo "   ✓ Configuration appears customized"
fi

# Offer to run example
echo ""
echo "5. Would you like to run the integration example? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "   Running integration example..."
    python3 examples/integration_example.py
fi

# Offer to start dashboard
echo ""
echo "6. Would you like to start the dashboard? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "   Starting web server on http://localhost:8000"
    echo "   Open http://localhost:8000/dashboard.html in your browser"
    echo "   Press Ctrl+C to stop the server"
    echo ""
    python3 -m http.server 8000
fi

echo ""
echo "=========================================="
echo "Quick start complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  • Generate a report: python3 tools/auto_report.py"
echo "  • View documentation: cat README.md"
echo "  • Setup guide: cat SETUP.md"
echo "  • Run tests: python3 -m pytest tests/"
echo ""
