#!/bin/bash
# Test PR workflows on recent reports only (last 3 days)
# This focuses on reports that should have all the latest fields

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Testing PR Workflows on Recent Reports ==="
echo ""

# Track overall success
OVERALL_SUCCESS=true

# Get recent report files (last 3 sorted by name, which is date-based)
shopt -s nullglob
all_files=(reports/*/ActivityReport-*.json)
if [ ${#all_files[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC} No reports found"
    exit 0
fi

# Sort and get last 3
IFS=$'\n' sorted_files=($(sort <<<"${all_files[*]}"))
unset IFS

# Get last 3 files
start_idx=$((${#sorted_files[@]} - 3))
if [ $start_idx -lt 0 ]; then
    start_idx=0
fi
recent_files=("${sorted_files[@]:$start_idx}")

echo "Testing ${#recent_files[@]} most recent reports:"
for f in "${recent_files[@]}"; do
    echo "  - $f"
done
echo ""

# Timeline Smoke Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timeline Smoke Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "→ Validating schemas"
if python3 .github/scripts/validate_report_schema.py "${recent_files[@]}" --debug; then
    echo -e "${GREEN}✓${NC} Schema validation passed"
else
    echo -e "${RED}✗${NC} Schema validation failed"
    OVERALL_SUCCESS=false
fi
echo ""

echo "→ Running timeline smoke tests"
SMOKE_FAILED=false
for report in "${recent_files[@]}"; do
    echo "Testing: $report"
    if python3 .github/scripts/smoke_timeline.py "$report" --debug; then
        echo -e "${GREEN}✓${NC} Passed"
    else
        echo -e "${RED}✗${NC} Failed"
        SMOKE_FAILED=true
    fi
    echo ""
done

if [ "$SMOKE_FAILED" = true ]; then
    OVERALL_SUCCESS=false
fi

# Performance Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Performance Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -f tests/perf_test.py ]; then
    echo -e "${RED}✗${NC} tests/perf_test.py not found"
    OVERALL_SUCCESS=false
else
    if pytest tests/perf_test.py -v --tb=short; then
        echo -e "${GREEN}✓${NC} Performance test passed"
    else
        echo -e "${RED}✗${NC} Performance test failed"
        OVERALL_SUCCESS=false
    fi
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ All tests passed on recent reports!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Note: Older reports may not have all fields (timeline, deep_work_blocks, coverage_window)."
    echo "This is expected. Run test_pr_workflows.sh to see all reports."
    exit 1
fi
