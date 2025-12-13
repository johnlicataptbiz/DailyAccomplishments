# Pull Request Workflow Testing Guide

This document describes the pull request workflows and how to test them with debugging enabled.

## Overview

The repository has two main pull request workflows that automatically run when PRs are created:

1. **Timeline Smoke Test** - Validates report structure and timeline/deep_work_blocks fields
2. **Performance Test** - Ensures report generation performance meets requirements

## Workflows

### 1. Timeline Smoke Test (`timeline-smoke.yml`)

**Trigger Conditions:**
- Pull requests that modify:
  - `reports/**` (any report files)
  - `tools/**` (report generation tools)
  - `dashboard.html` (dashboard file)
  - `.github/scripts/smoke_timeline.py` (the smoke test script itself)

**What it does:**
1. Sets up Python 3.11 environment
2. Installs dependencies (jsonschema, pytest)
3. Cleans Python cache files
4. Validates all reports against JSON schema
5. Runs timeline smoke test on a sample report

**Debugging Features:**
- GitHub Actions groups for organized output
- File discovery with counts
- Detailed validation output
- Success/warning/error notices
- File size reporting

### 2. Performance Test (`performance-test.yml`)

**Trigger Conditions:**
- Pull requests that modify:
  - `tools/generate_reports.py` (report generation logic)
  - `tests/perf_test.py` (the performance test itself)

**What it does:**
1. Sets up Python 3.11 environment
2. Installs pytest
3. Verifies test file exists
4. Runs performance test with verbose output

**Debugging Features:**
- GitHub Actions groups
- File existence verification with size
- Verbose pytest output (`-v --tb=short`)
- Success notices

## Local Testing

### Testing Timeline Smoke Test

#### Basic Usage
```bash
# Test a single report
python3 .github/scripts/smoke_timeline.py reports/2025-12-08/ActivityReport-2025-12-08.json

# Expected output:
# SMOKE OK
```

#### Debug Mode
```bash
# Test with debug output
python3 .github/scripts/smoke_timeline.py reports/2025-12-08/ActivityReport-2025-12-08.json --debug

# Expected output includes:
# [DEBUG] Checking report file: ...
# [DEBUG] Reading JSON from ...
# [DEBUG] JSON parsed successfully, top-level keys: [...]
# [DEBUG] timeline is present and array with N items
# [DEBUG] deep_work_blocks is present and array with N items
# SMOKE OK
# [DEBUG] All checks passed
```

#### Testing Multiple Reports
```bash
# Test all reports in the reports directory
for report in reports/*/ActivityReport-*.json; do
    echo "Testing: $report"
    python3 .github/scripts/smoke_timeline.py "$report" --debug
    echo "---"
done
```

### Testing Schema Validation

#### Basic Usage
```bash
# Validate a single report
python3 .github/scripts/validate_report_schema.py reports/2025-12-08/ActivityReport-2025-12-08.json

# Expected output:
# VALID: reports/2025-12-08/ActivityReport-2025-12-08.json
```

#### Debug Mode
```bash
# Validate with debug output
python3 .github/scripts/validate_report_schema.py reports/2025-12-08/ActivityReport-2025-12-08.json --debug

# Expected output includes:
# [DEBUG] Debug mode enabled
# [DEBUG] Validating 1 file(s)
# [DEBUG] Schema loaded successfully
# [DEBUG] === Validating file 1/1 ===
# [DEBUG] Validating: ...
# [DEBUG] File size: ... bytes
# [DEBUG] JSON parsed successfully
# [DEBUG] Top-level keys: [...]
# [DEBUG] Schema validation passed
# [DEBUG] Overview keys: [...]
# [DEBUG] deep_work_blocks: N items
# VALID: ...
```

#### Testing Multiple Reports
```bash
# Validate all reports
python3 .github/scripts/validate_report_schema.py reports/*/ActivityReport-*.json --debug
```

### Testing Performance

#### Basic Usage
```bash
# Install dependencies
pip install pytest

# Run performance test
pytest tests/perf_test.py

# Expected output:
# tests/perf_test.py::test_perf_1k PASSED [100%]
```

#### Verbose Mode
```bash
# Run with verbose output
pytest tests/perf_test.py -v

# Run with very verbose output showing test details
pytest tests/perf_test.py -vv --tb=short
```

## Simulating Full PR Workflow Locally

You can simulate the complete PR workflow locally with this script:

```bash
#!/bin/bash
# Simulate PR workflow locally

set -euo pipefail

echo "=== Starting PR Workflow Simulation ==="
echo ""

# 1. Timeline Smoke Test
echo "=== Timeline Smoke Test ==="
echo ""

echo "Step 1: Clean Python cache"
rm -rf imports || true
find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
echo "✓ Cache cleaned"
echo ""

echo "Step 2: Validate report schemas"
files=(reports/*/ActivityReport-*.json)
if [ ${#files[@]} -eq 0 ]; then
    echo "⚠ No reports to validate"
else
    echo "Found ${#files[@]} report files"
    python3 .github/scripts/validate_report_schema.py "${files[@]}" --debug
fi
echo ""

echo "Step 3: Run timeline smoke test"
if [ ${#files[@]} -eq 0 ]; then
    echo "⚠ No sample report found"
else
    REPORT="${files[0]}"
    echo "Testing: $REPORT"
    python3 .github/scripts/smoke_timeline.py "$REPORT" --debug
fi
echo ""

# 2. Performance Test
echo "=== Performance Test ==="
echo ""

if [ -f tests/perf_test.py ]; then
    echo "✓ tests/perf_test.py exists"
    pytest tests/perf_test.py -v --tb=short
else
    echo "✗ tests/perf_test.py not found"
    exit 1
fi

echo ""
echo "=== PR Workflow Simulation Complete ==="
```

Save this as `test_pr_workflows.sh` and run with:
```bash
chmod +x test_pr_workflows.sh
./test_pr_workflows.sh
```

## Debugging Features Summary

### Script-Level Debugging

Both Python scripts now support a `--debug` (or `-v`) flag that enables:

- **smoke_timeline.py:**
  - File path verification
  - JSON parsing confirmation
  - Top-level key listing
  - Timeline array size
  - Deep work blocks validation details
  - Individual field checks with values

- **validate_report_schema.py:**
  - File size reporting
  - Top-level key listing
  - Schema validation progress
  - Overview field details
  - Deep work blocks item counts
  - Summary statistics

### Workflow-Level Debugging

Both GitHub Actions workflows now include:

- **Collapsible groups:** Output is organized into `::group::` sections for better readability
- **Notices:** Success messages appear as green notices in the GitHub UI
- **Warnings:** Non-critical issues appear as yellow warnings
- **File discovery:** Lists all files being processed
- **Progress indicators:** Shows current step and total steps

## Troubleshooting

### Common Issues

1. **Schema validation fails:**
   - Run with `--debug` flag to see which fields are missing or invalid
   - Check the schema at `.github/schemas/activity_report_schema.json`
   - Ensure all required fields are present: `overview.focus_time`, `overview.coverage_window`

2. **Timeline smoke test fails:**
   - Use `--debug` to see which fields are missing
   - Older reports may not have `timeline` or `deep_work_blocks` fields
   - This is expected for reports generated before these features were added

3. **Performance test fails:**
   - Check that `tools/generate_reports.py` and its dependencies are present
   - Ensure the test timeout (5 seconds for 1000 events) is reasonable for your system
   - Run with `-vv` for more detailed output

### Getting Help

If you encounter issues:

1. Run the test locally with `--debug` flag
2. Check the full output in GitHub Actions (click on the failed step)
3. Look for `::error::`, `::warning::`, or `FAIL` messages
4. Review the validation output for specific field issues

## Future Improvements

Potential enhancements to consider:

- [ ] Add more granular performance metrics (memory usage, I/O operations)
- [ ] Create fixtures for testing edge cases
- [ ] Add integration tests for the full report generation pipeline
- [ ] Implement automatic report repair for older reports missing new fields
- [ ] Add visual diff for report changes in PRs
- [ ] Create a pre-commit hook that runs these tests locally
