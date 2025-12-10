#!/bin/bash
# Repository Cleanup Script
# This script will clean up your DailyAccomplishments repository
# Each step explains what it's doing and why

set -e  # Exit if any command fails

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  DailyAccomplishments Repository Cleanup Script               ║"
echo "║  This will organize your files and teach you git basics        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to explain and execute
explain_and_run() {
    local description="$1"
    local command="$2"
    local why="$3"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}DOING:${NC} $description"
    echo -e "${YELLOW}WHY:${NC} $why"
    echo -e "${BLUE}COMMAND:${NC} $command"
    echo ""
    
    # Ask for confirmation
    read -p "Press ENTER to run this command (or Ctrl+C to stop): " 
    
    # Run the command
    eval "$command"
    
    echo -e "${GREEN}✓ Done!${NC}"
    echo ""
}

# PHASE 1: Remove Duplicate Files
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1: Removing Duplicate Files"
echo "═══════════════════════════════════════════════════════════════"
echo ""

explain_and_run \
    "Remove duplicate README files" \
    "rm -v 'README 2.md' 'README 3.md' 'README 4.md' 'SETUP 2.md' 2>/dev/null || echo 'Some files already removed'" \
    "These are duplicate copies. We only need one README.md and one SETUP.md"

explain_and_run \
    "Remove duplicate Python files" \
    "rm -v 'integration_example 2.py' 'tracker_bridge 2.py' activity_tracker.py.bak dashboard.html.bak 2>/dev/null || echo 'Some files already removed'" \
    "These are backup copies. We don't need them because git keeps all history"

explain_and_run \
    "Remove the DailyAccomplishments file" \
    "rm -v DailyAccomplishments 2>/dev/null || echo 'File already removed'" \
    "This is a git submodule reference that's not needed"

# PHASE 2: Remove Cache Files
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 2: Removing Cache Files"
echo "═══════════════════════════════════════════════════════════════"
echo ""

explain_and_run \
    "Remove Python cache directory" \
    "rm -rfv __pycache__/ 2>/dev/null || echo 'Already removed'" \
    "Python creates these automatically. They're not needed in git and waste space"

explain_and_run \
    "Remove .pyc files" \
    "find . -name '*.pyc' -not -path './.venv/*' -delete -print 2>/dev/null || echo 'No .pyc files found'" \
    "These are compiled Python files. Python recreates them automatically"

# PHASE 3: Organize Generated Files
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 3: Organizing Generated Files"
echo "═══════════════════════════════════════════════════════════════"
echo ""

explain_and_run \
    "Create reports/charts directory" \
    "mkdir -p reports/charts" \
    "We'll move all generated charts here to keep the repo organized"

explain_and_run \
    "Move category distribution charts" \
    "mv -v category_distribution-*.{csv,png,svg} reports/charts/ 2>/dev/null || echo 'Files already moved or not found'" \
    "These are generated from your data. They belong in reports/charts/"

explain_and_run \
    "Move hourly focus charts" \
    "mv -v hourly_focus-*.{csv,png,svg} reports/charts/ 2>/dev/null || echo 'Files already moved or not found'" \
    "These are generated from your data. They belong in reports/charts/"

explain_and_run \
    "Move top domains charts" \
    "mv -v top_domains-*.csv reports/charts/ 2>/dev/null || echo 'Files already moved or not found'" \
    "These are generated from your data. They belong in reports/charts/"

explain_and_run \
    "Move focus summary charts" \
    "mv -v focus_summary.* reports/charts/ 2>/dev/null || echo 'Files already moved or not found'" \
    "These are generated from your data. They belong in reports/charts/"

# PHASE 4: Update .gitignore
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 4: Updating .gitignore"
echo "═══════════════════════════════════════════════════════════════"
echo ""

cat > .gitignore.new << 'EOF'
# Ignore runtime logs
logs/

# Config with secrets (API tokens)
config.json

# Credentials directory (OAuth tokens, API keys)
credentials/
!credentials/README.md

# Python virtual environment
.venv/
venv/
__pycache__/
*.pyc
*.pyo
*.pyd

# Generated reports and charts (can be regenerated)
reports/charts/*.png
reports/charts/*.svg
reports/charts/*.csv

# Temporary and backup files
*.bak
*.tmp
*.rtf
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/settings.json
*.code-workspace
EOF

explain_and_run \
    "Update .gitignore file" \
    "mv .gitignore.new .gitignore && cat .gitignore" \
    "This tells git to ignore generated files, cache files, and secrets"

# PHASE 5: Check Git Status
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 5: Checking Current Git Status"
echo "═══════════════════════════════════════════════════════════════"
echo ""

explain_and_run \
    "Show what files have changed" \
    "git status --short" \
    "This shows what git sees as changed, new, or deleted"

# PHASE 6: Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  CLEANUP COMPLETE!                                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "What we did:"
echo "  ✓ Removed duplicate files (README 2.md, etc.)"
echo "  ✓ Removed cache files (__pycache__, *.pyc)"
echo "  ✓ Organized generated files into reports/charts/"
echo "  ✓ Updated .gitignore to prevent future clutter"
echo ""
echo "Next steps:"
echo "  1. Review the git status above"
echo "  2. Decide what to do with modified files"
echo "  3. Commit the changes you want to keep"
echo ""
echo "Git commands you'll need:"
echo "  git add <file>          # Add a file to staging"
echo "  git commit -m 'message' # Commit staged files"
echo "  git push origin main    # Push to GitHub"
echo ""
echo "I can help you with the next steps!"
