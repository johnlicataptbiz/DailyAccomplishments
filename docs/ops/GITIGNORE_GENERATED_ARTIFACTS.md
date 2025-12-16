# .gitignore Strategy for Generated Artifacts

**Purpose:** Prevent merge conflicts and noisy diffs by excluding generated reports, charts, and artifacts from Git tracking.

**Problem:** Currently tracked artifacts include:
- ✅ ActivityReport JSON files (30+ files, ~5KB each) - **KEEP THESE**
- ❌ CSV reports (category_distribution, hourly_focus, top_domains) - **SHOULD IGNORE**
- ❌ SVG charts (matching CSV reports) - **SHOULD IGNORE**
- ⚠️ PNG charts (focus_summary, etc.) - **PARTIALLY IGNORED** (some patterns in .gitignore, but not all)

---

## Current State Analysis

### What's Currently Tracked (Should Be Ignored)

```bash
# Root-level generated artifacts (currently tracked ❌)
category_distribution-2025-11-27.csv
category_distribution-2025-11-27.svg
category_distribution-2025-11-28.csv
category_distribution-2025-11-28.svg
# ... (8 more date variants)
category_distribution.csv
category_distribution.svg
focus_summary.csv
focus_summary.svg
hourly_focus-2025-11-27.csv
hourly_focus-2025-11-27.svg
# ... (8 more date variants)
hourly_focus.csv
hourly_focus.svg
test_hourly.svg
top_domains-2025-11-27.csv
# ... (4 more date variants)
top_domains.csv

# Repo also has: reports/** directory with subdirectories per date
```

### What Should Stay Tracked (✅)

```bash
# ActivityReport JSON files (essential for dashboard)
ActivityReport-2025-11-21.json
ActivityReport-2025-11-22.json
# ... (30+ daily reports)

# Data logs (needed for GitHub Actions)
logs/daily/*.jsonl

# Code and configuration
*.py
*.sh
*.md
config.json
requirements.txt
Dockerfile
# ... etc
```

---

## Recommended .gitignore Updates

### Option 1: Aggressive (Recommended for Clean History)

**Add to `.gitignore`:**

```gitignore
# Generated reports and charts (root level)
/*.csv
/*.svg
category_distribution*.csv
category_distribution*.svg
hourly_focus*.csv
hourly_focus*.svg
top_domains*.csv
focus_summary.csv
focus_summary.svg
test_hourly.svg

# Generated reports in subdirectories
reports/**/*.svg
reports/**/*.csv
reports/**/*.png
reports/**/*.jpg
gh-pages/**/*.svg
gh-pages/**/*.png

# Keep JSON reports (negative patterns must come after ignores)
!reports/**/*.json
!ActivityReport-*.json

# Keep JSONL logs (already in .gitignore with negation)
!logs/daily/*.jsonl
```

**Result:**
- ✅ Keeps all ActivityReport-*.json files (essential for dashboard)
- ✅ Keeps logs/daily/*.jsonl (needed for processing)
- ❌ Ignores ALL CSV/SVG/PNG charts (can be regenerated)
- ❌ Ignores root-level generated artifacts

### Option 2: Conservative (Keep Some CSVs)

If you want to track CSV for historical analysis but not charts:

```gitignore
# Generated charts only (keep CSVs)
/*.svg
/*.png
category_distribution*.svg
hourly_focus*.svg
focus_summary.svg
test_hourly.svg
reports/**/*.svg
reports/**/*.png
gh-pages/**/*.svg
gh-pages/**/*.png

# Keep CSVs for data analysis (comment out if you don't need)
# /*.csv
# category_distribution*.csv
# hourly_focus*.csv
# top_domains*.csv

# Keep JSON reports
!reports/**/*.json
!ActivityReport-*.json
```

**Result:**
- ✅ Keeps ActivityReport-*.json
- ✅ Keeps CSV files (can track data changes)
- ❌ Ignores all image artifacts (SVG/PNG)

### Option 3: Minimal (Only Root-Level Artifacts)

If you only want to fix root-level clutter:

```gitignore
# Root-level generated files only
/*.csv
/*.svg
/*.png
category_distribution*.csv
category_distribution*.svg
hourly_focus*.csv
hourly_focus*.svg
top_domains*.csv
focus_summary.*

# Keep everything in reports/ and gh-pages/ tracked (except what's already ignored)
# (No additional rules needed)
```

---

## Implementation Steps

### Step 1: Update .gitignore

**Recommended approach:**

```bash
cd /path/to/DailyAccomplishments-repo

# Backup current .gitignore
cp .gitignore .gitignore.backup

# Open .gitignore in editor
nano .gitignore  # or vim, code, etc.

# Add Option 1 (Aggressive) rules to the end of file
# (See "Option 1" section above)

# Save and exit
```

### Step 2: Remove Already-Tracked Files from Git

**⚠️ IMPORTANT:** This only removes files from Git tracking, NOT from your filesystem.

```bash
# Preview what will be removed
git ls-files | grep -E '\.(csv|svg)$' | grep -E '^(category_|hourly_|top_|focus_)'

# Remove root-level CSV/SVG files from Git index
git rm --cached *.csv *.svg 2>/dev/null || true
git rm --cached category_distribution*.csv 2>/dev/null || true
git rm --cached category_distribution*.svg 2>/dev/null || true
git rm --cached hourly_focus*.csv 2>/dev/null || true
git rm --cached hourly_focus*.svg 2>/dev/null || true
git rm --cached top_domains*.csv 2>/dev/null || true
git rm --cached focus_summary.* 2>/dev/null || true
git rm --cached test_hourly.svg 2>/dev/null || true

# Optional: Remove from reports/ and gh-pages/ subdirectories
find reports/ gh-pages/ -name "*.svg" -o -name "*.png" | xargs git rm --cached 2>/dev/null || true

# Check what will be removed
git status

# Verify files still exist on disk
ls -l *.csv *.svg | head -5
# Should show files still present locally
```

### Step 3: Commit .gitignore Changes

```bash
# Stage .gitignore update
git add .gitignore

# Commit both .gitignore and removed file tracking
git commit -m "Update .gitignore: exclude generated charts and reports

- Ignore root-level CSV/SVG artifacts (category_distribution, hourly_focus, etc.)
- Ignore charts in reports/ and gh-pages/
- Keep ActivityReport-*.json (essential for dashboard)
- Keep logs/daily/*.jsonl (needed for processing)
- Reduces diff noise and prevents merge conflicts
- Files remain on disk, only removed from Git tracking"

# Push changes
git push origin main
```

### Step 4: Verify .gitignore Works

```bash
# Create a test artifact
echo "test" > test_report.csv
echo "test" > test_chart.svg

# Check git status
git status

# Should NOT show test_report.csv or test_chart.svg as untracked
# If they appear, .gitignore pattern is wrong

# Clean up test files
rm test_report.csv test_chart.svg

# Verify existing artifacts are ignored
git status --ignored | grep -E '\.(csv|svg)$'
# Should show ignored files
```

---

## Rollback Procedures

### If .gitignore Breaks Something

```bash
# Restore original .gitignore
cp .gitignore.backup .gitignore
git add .gitignore
git commit -m "Revert .gitignore changes"
git push origin main
```

### If Files Were Accidentally Removed

```bash
# Files still exist on disk, just re-add to Git
git add *.csv *.svg
git commit -m "Restore CSV/SVG tracking (rollback)"
git push origin main
```

### If You Need Specific Files Back

```bash
# Re-add specific files to Git tracking
git add category_distribution.csv
git add hourly_focus.svg
git commit -m "Track specific reports for analysis"
git push origin main

# Update .gitignore to explicitly allow them
echo "!category_distribution.csv" >> .gitignore
echo "!hourly_focus.svg" >> .gitignore
git add .gitignore
git commit -m "Update .gitignore: allow specific reports"
git push origin main
```

---

## Best Practices

### 1. Regenerate Instead of Commit

**Philosophy:** Generated artifacts should be reproducible from code + data.

```bash
# Instead of committing charts, document how to generate them
echo "Run ./generate_reports.sh to create charts" >> README.md
```

### 2. CI/CD Should Generate Artifacts

**Example GitHub Actions workflow:**

```yaml
# .github/workflows/generate-reports.yml
name: Generate Daily Reports
on:
  schedule:
    - cron: "0 6 * * *"  # Daily at 6 AM
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate reports
        run: |
          pip install -r requirements.txt
          python3 tools/auto_report.py
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: daily-reports
          path: |
            reports/
            !reports/**/*.svg
            !reports/**/*.png
```

### 3. Keep .gitignore Organized

**Structure:**

```gitignore
# ============================================================
# GENERATED ARTIFACTS (regenerate with ./generate_reports.sh)
# ============================================================

# Root-level reports
/*.csv
/*.svg

# Subdirectory reports
reports/**/*.svg
reports/**/*.png

# KEEP THESE (negative patterns)
!reports/**/*.json
!ActivityReport-*.json
!logs/daily/*.jsonl
```

### 4. Document Generation Commands

**In README.md or QUICKSTART.md:**

```markdown
## Regenerating Reports

To regenerate all reports and charts:

```bash
# Single date
python3 scripts/generate_daily_json.py 2025-12-16

# Date range
python3 scripts/backfill_reports.py --start 2025-12-01 --end 2025-12-16

# All available data
./generate_reports.sh
```

Charts are generated as SVG/CSV and saved to `reports/`.
These are not tracked in Git (see `.gitignore`).
```

---

## Testing .gitignore Changes

### Test Checklist

Before pushing .gitignore changes:

- [ ] ✅ Create test CSV/SVG in root: `echo "test" > test.csv && echo "test" > test.svg`
- [ ] ✅ Verify not tracked: `git status | grep test.csv` (should be ignored)
- [ ] ✅ Verify JSON still tracked: `touch ActivityReport-2025-01-01.json && git status` (should appear)
- [ ] ✅ Verify logs still tracked: `touch logs/daily/2025-01-01.jsonl && git status` (should appear)
- [ ] ✅ Clean up: `rm test.csv test.svg ActivityReport-2025-01-01.json logs/daily/2025-01-01.jsonl`
- [ ] ✅ Commit and push .gitignore
- [ ] ✅ Test on another machine/clone: `git clone ... && cd ... && echo "test" > test.csv && git status`

---

## Impact Analysis

### Before .gitignore Update

**Tracked files:** ~350 files
- 30 ActivityReport JSON (~150KB total) ✅
- 50+ CSV files (~500KB) ❌
- 50+ SVG files (~2MB) ❌
- Code and config files ✅

**Problems:**
- 100+ unnecessary files in Git history
- Large diffs for regenerated charts
- Merge conflicts on artifact updates
- Slow `git status` and `git add`

### After .gitignore Update (Option 1)

**Tracked files:** ~250 files
- 30 ActivityReport JSON (~150KB) ✅
- Code and config files ✅

**Benefits:**
- ✅ 100+ fewer files tracked
- ✅ Clean diffs (code only)
- ✅ No merge conflicts on artifacts
- ✅ Faster Git operations
- ✅ Smaller repository size (after GC)

**Tradeoffs:**
- ❌ Must regenerate charts after clone
- ❌ No historical chart diffs (use JSON for data history)

---

## Related Documentation

- **Historical Extraction Guide**: [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
- **Copilot Prompts**: [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md)
- **Main README**: [../../README.md](../../README.md)

---

## FAQ

### Q: Will this delete my local CSV/SVG files?

**A:** No. `git rm --cached` only removes from Git tracking, not from disk. Files remain locally.

### Q: What if I need to share a specific chart?

**A:** Options:
1. Share via GitHub Actions artifacts (upload-artifact)
2. Host on external service (imgur, GitHub Pages)
3. Explicitly re-add to Git: `git add -f specific-chart.svg`
4. Add exception in .gitignore: `!reports/important-chart.svg`

### Q: How do I regenerate charts after clone?

**A:** Run the generation script:
```bash
git clone https://github.com/user/DailyAccomplishments.git
cd DailyAccomplishments
pip install -r requirements.txt
./generate_reports.sh
```

### Q: Can I track CSVs but not SVGs?

**A:** Yes, use Option 2 (Conservative) - ignore only `*.svg` and `*.png`, leave CSV patterns out.

### Q: What about reports already in main branch history?

**A:** They remain in history (Git is immutable). To clean history:
```bash
# Advanced: Use git filter-repo (backup first!)
git filter-repo --path-glob '*.svg' --invert-paths
git filter-repo --path-glob 'category_distribution*.csv' --invert-paths
# ⚠️ Rewrites history, requires force push, coordinate with team
```

### Q: How do I know if .gitignore is working?

**A:** Test:
```bash
echo "test" > category_distribution-test.svg
git status  # Should NOT appear as untracked
git status --ignored  # Should show as ignored
rm category_distribution-test.svg
```

---

**Last updated:** 2025-12-16  
**Maintainer:** Repository operations team  
**Review frequency:** After major workflow changes
