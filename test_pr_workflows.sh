#!/bin/bash
# Simulate PR workflow locally
# This script runs the same checks that GitHub Actions runs on pull requests

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Starting PR Workflow Simulation ==="
echo ""

# Track overall success
OVERALL_SUCCESS=true

# 1. Timeline Smoke Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timeline Smoke Test Workflow"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Step 1: Clean Python cache"
rm -rf imports || true
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
echo -e "${GREEN}✓${NC} Cache cleaned"
echo ""

echo "→ Step 2: Validate report schemas"
shopt -s nullglob
files=(reports/*/ActivityReport-*.json)
if [ ${#files[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC} No reports to validate"
else
    echo "Found ${#files[@]} report files:"
    for f in "${files[@]}"; do
        echo "  - $f"
    done
    echo ""
    
    if python3 .github/scripts/validate_report_schema.py "${files[@]}" --debug; then
        echo -e "${GREEN}✓${NC} All reports validated successfully"
    else
        echo -e "${RED}✗${NC} Schema validation failed"
        OVERALL_SUCCESS=false
    fi
fi
echo ""

echo "→ Step 3: Run timeline smoke test"
if [ ${#files[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC} No sample report found"
else
    REPORT="${files[0]}"
    echo "Testing: $REPORT"
    echo ""
    
    if python3 .github/scripts/smoke_timeline.py "$REPORT" --debug; then
        echo -e "${GREEN}✓${NC} Timeline smoke test passed"
    else
        echo -e "${RED}✗${NC} Timeline smoke test failed"
        OVERALL_SUCCESS=false
    fi
fi
echo ""

# 2. Performance Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Performance Test Workflow"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Step 1: Check test file exists"
if [ -f tests/perf_test.py ]; then
    FILE_SIZE=$(stat -c%s tests/perf_test.py 2>/dev/null || stat -f%z tests/perf_test.py 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} tests/perf_test.py exists (${FILE_SIZE} bytes)"
else
    echo -e "${RED}✗${NC} tests/perf_test.py not found"
    OVERALL_SUCCESS=false
    exit 1
fi
echo ""

echo "→ Step 2: Run performance test"
if pytest tests/perf_test.py -v --tb=short; then
    echo -e "${GREEN}✓${NC} Performance test passed"
else
    echo -e "${RED}✗${NC} Performance test failed"
    OVERALL_SUCCESS=false
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ All PR workflow checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some PR workflow checks failed${NC}"
    exit 1
fi
