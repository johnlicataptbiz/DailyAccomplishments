# Safe Historical Commit Code Extraction Guide

**Purpose:** Extract code-only changes from historical commits without importing generated artifacts (reports, logs, CSV/PNG/SVG files) that cause merge conflicts.

**Use case:** When a large historical commit contains both valuable code changes AND generated artifacts that conflict with current main branch.

---

## Quick Reference

### Target Scenario
- Historical commit: `53d18c6` ("UI: Deep Work overlay + integration highlights; Screen Time top apps; privacy + baselines; roadmap")
- Contains: Code changes (dashboard.html, tools/, scripts/) + generated artifacts
- Current main: Has newer schema, auto-updates → cherry-pick causes conflicts
- Repository uses: git worktrees (main branch checked out in repo root, feature branch checked out in `.worktrees/main` subdirectory)

### Goal
Extract only code/docs from `53d18c6` → avoid conflicts → verify generation → merge safely

---

## Prerequisites

### 1. Verify Git Worktree Setup

```bash
# Check worktree configuration
cd /path/to/repo
git worktree list

# Expected output:
# /path/to/repo                 <SHA>  [main]
# /path/to/repo/.worktrees/main <SHA>  [feature/big-commit]
```

### 2. Confirm Target Commit Exists

```bash
# Verify commit is accessible
git log --oneline --all | grep 53d18c6
# OR
git show 53d18c6 --no-patch

# If commit not found in shallow clone, fetch full history
git fetch --unshallow
```

---

## Step-by-Step Extraction Process

### Step 1: Prepare Clean Worktree

**Location:** Run in feature branch worktree (`.worktrees/main`)

```bash
# Navigate to feature worktree
cd .worktrees/main

# Abort any in-progress operations (safe if none exist)
git cherry-pick --abort 2>/dev/null || true
git merge --abort 2>/dev/null || true
git rebase --abort 2>/dev/null || true

# Check for uncommitted changes
git status --porcelain

# Optional: Clean worktree (⚠️ WARNING: Discards local changes)
# Only run if git status shows unwanted changes:
git reset --hard
git clean -fd
```

**Verification:**
```bash
# Confirm clean state
git status
# Should show: "nothing to commit, working tree clean"

# Confirm correct branch
git branch --show-current
# Should show: "feature/big-commit" (or your feature branch name)
```

---

### Step 2: Extract Code-Only Files

**Allowed files from commit `53d18c6`:**
- `dashboard.html` - UI changes
- `tools/generate_reports.py` - Report generation logic
- `scripts/archive_outputs.sh` - Archive script
- `scripts/cron_report_and_push.sh` - Cron automation
- `scripts/import_browser_history.py` - Browser integration
- `scripts/import_screentime.py` - Screen Time integration
- `FUTURE_UPDATES.md` - Documentation

**Excluded (DO NOT restore):**
- `reports/**` - Generated reports
- `ActivityReport-*.json` - Generated JSON outputs
- `hourly_focus*.csv`, `category_distribution*.csv`, `top_domains*.csv` - Generated CSVs
- `*.svg`, `*.png`, `*.jpg` - Generated charts/images
- `logs/**` - Log files
- `gh-pages/**` - Built static site

**Command (preferred - Git 2.23+):**
```bash
cd .worktrees/main

git restore --source 53d18c6 -- \
  dashboard.html \
  tools/generate_reports.py \
  scripts/archive_outputs.sh \
  scripts/cron_report_and_push.sh \
  scripts/import_browser_history.py \
  scripts/import_screentime.py \
  FUTURE_UPDATES.md
```

**Fallback command (older Git versions):**
```bash
git checkout 53d18c6 -- \
  dashboard.html \
  tools/generate_reports.py \
  scripts/archive_outputs.sh \
  scripts/cron_report_and_push.sh \
  scripts/import_browser_history.py \
  scripts/import_screentime.py \
  FUTURE_UPDATES.md
```

**Verification:**
```bash
# Review what changed
git status

# See detailed diffs
git diff --staged

# Verify only intended files are staged
git diff --name-only --staged

# Expected output (only these 7 files):
# dashboard.html
# tools/generate_reports.py
# scripts/archive_outputs.sh
# scripts/cron_report_and_push.sh
# scripts/import_browser_history.py
# scripts/import_screentime.py
# FUTURE_UPDATES.md
```

---

### Step 3: Commit Code Changes

```bash
cd .worktrees/main

# Stage the extracted files (if not auto-staged by git restore)
git add \
  dashboard.html \
  tools/generate_reports.py \
  scripts/archive_outputs.sh \
  scripts/cron_report_and_push.sh \
  scripts/import_browser_history.py \
  scripts/import_screentime.py \
  FUTURE_UPDATES.md

# Verify staging
git status --short
# Should show 'M' or 'A' for the 7 files only

# Commit with descriptive message
git commit -m "Implement dashboard UI + Screen Time integration (code only)

- Extract code-only changes from commit 53d18c6
- Includes: dashboard UI, generate_reports, import scripts
- Excludes: generated artifacts (reports, CSV, SVG, logs)
- Safe for merge: no generated file conflicts"
```

**Verification:**
```bash
# Show commit details
git show --name-status HEAD

# Confirm only intended files in commit
git show --name-only HEAD

# Review commit message
git log -1 --format="%B"
```

---

### Step 4: Verify Code Works (Critical!)

**Why:** Ensure extracted code runs before merging to main.

**Test with single-date generation:**

```bash
cd .worktrees/main

# Option A: Use generate_daily_json.py (repo-specific)
# Pick a date you have logs for
python3 scripts/generate_daily_json.py 2025-12-02

# Option B: Use tools/generate_reports.py (if available)
python3 tools/generate_reports.py 2025-12-02

# Option C: Use shell wrapper
./generate_reports.sh 2025-12-02
```

**Schema validation (repo-specific output path):**

```bash
# DailyAccomplishments uses: reports/YYYY-MM-DD/ActivityReport-YYYY-MM-DD.json
# Adjust date to match what you generated

# Method 1: Using jq (if installed)
jq -r '
  "timeline_type: " + (.timeline | type),
  "deep_work_blocks_type: " + (.deep_work_blocks | type),
  "hourly_focus_length: " + (.hourly_focus | length | tostring)
' reports/2025-12-02/ActivityReport-2025-12-02.json

# Expected output:
# timeline_type: array
# deep_work_blocks_type: array
# hourly_focus_length: 24

# Method 2: Using Python (always available)
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("reports/2025-12-02/ActivityReport-2025-12-02.json")
j = json.load(open(p))
print(f"timeline: {isinstance(j.get('timeline'), list)}")
print(f"deep_work_blocks: {isinstance(j.get('deep_work_blocks'), list)}")
print(f"hourly_focus_len: {len(j.get('hourly_focus', []))}")
PY

# Expected output:
# timeline: True
# deep_work_blocks: True
# hourly_focus_len: 24
```

**⚠️ Important:** Do NOT commit the generated test files. They are for verification only.

```bash
# Clean up generated test files
git clean -fd reports/
# OR manually delete:
rm -rf reports/2025-12-02/
```

**Additional verification (optional):**

```bash
# Run existing tests if available
pytest

# Run smoke test
python3 examples/integration_example.py

# Check imports don't break
python3 -c "import tools.generate_reports; print('OK')"
```

---

### Step 5: Merge to Main

You have **two safe options** depending on your workflow:

#### Option A: Pull Request (Recommended) ✅

**Advantages:**
- CI validation before merge
- Code review by team
- Automated checks catch issues
- Merge history preserved

**Steps:**

```bash
# Push feature branch from worktree
cd .worktrees/main
git push origin feature/big-commit

# Create PR using GitHub CLI
gh pr create \
  --base main \
  --head feature/big-commit \
  --title "Implement dashboard UI + Screen Time integration (code only)" \
  --body "## Summary

Code-only extraction from historical commit 53d18c6.

## Changes
- ✅ Dashboard UI improvements (dashboard.html)
- ✅ Report generation enhancements (tools/generate_reports.py)
- ✅ Screen Time import script (scripts/import_screentime.py)
- ✅ Browser history import (scripts/import_browser_history.py)
- ✅ Archive and cron scripts
- ✅ Documentation updates (FUTURE_UPDATES.md)

## What's NOT included
- ❌ Generated reports (reports/*)
- ❌ Generated charts (*.svg, *.png)
- ❌ Historical logs (logs/*)
- ❌ Built artifacts (gh-pages/*)

## Verification
- [x] Single-date generation tested
- [x] Schema validation passed (timeline, deep_work_blocks, hourly_focus)
- [x] No generated artifacts included
- [x] Clean diff with only 7 code files

## Merge strategy
Safe to merge: no conflicts with current main branch artifacts."

# Alternative: Create PR via web UI
# Then merge when CI passes and review approves
```

**After PR created:**
```bash
# Monitor CI status
gh pr checks

# View PR
gh pr view

# When ready and approved, merge
gh pr merge --squash  # or --merge or --rebase
```

#### Option B: Direct Merge (Use with caution) ⚠️

**When to use:** Only if your team allows direct merges and you have verified all checks pass.

**Steps:**

```bash
# Switch to repo root (where main is checked out)
cd /path/to/repo  # NOT the worktree

# Ensure main is up-to-date
git fetch origin
git checkout main
git pull --ff-only

# Merge feature branch
git merge --no-ff feature/big-commit -m "Merge: Implement dashboard UI + Screen Time integration (code only)"

# Verify merge
git log --oneline -5
git diff HEAD~1 --name-status

# Push to remote
git push origin main
```

**Verification after merge:**
```bash
# Confirm push succeeded
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
# Both should show same SHA

# Verify merged files
git show --name-only HEAD
```

---

## Post-Merge Verification

### 1. Verify on Main Branch

```bash
cd /path/to/repo  # repo root with main
git pull

# Verify the code changes are present
ls -lh dashboard.html
ls -lh tools/generate_reports.py
ls -lh scripts/import_screentime.py

# Run generation on main
python3 scripts/generate_daily_json.py $(date +%Y-%m-%d)

# Validate schema
python3 - <<'PY'
import json, pathlib, datetime
date = datetime.date.today().strftime("%Y-%m-%d")
p = pathlib.Path(f"reports/{date}/ActivityReport-{date}.json")
if p.exists():
    j = json.load(open(p))
    print(f"✓ timeline: {isinstance(j.get('timeline'), list)}")
    print(f"✓ deep_work_blocks: {isinstance(j.get('deep_work_blocks'), list)}")
    print(f"✓ hourly_focus_len: {len(j.get('hourly_focus', []))}")
else:
    print(f"⚠ No report generated for {date}")
PY
```

### 2. Clean Up Worktree (Optional)

```bash
# List worktrees
git worktree list

# Remove feature worktree if no longer needed
git worktree remove .worktrees/main

# Delete merged branch (if using PR workflow)
git branch -d feature/big-commit
git push origin --delete feature/big-commit
```

---

## Prevent Future Issues: .gitignore Strategy

**Problem:** Generated artifacts (SVG/PNG charts, CSV reports) create noisy diffs and merge conflicts.

**Solution:** Update `.gitignore` to exclude generated images while keeping JSON/CSV if desired.

### Recommended .gitignore Additions

```bash
# Add to repository root .gitignore

# Ignore generated charts and images
reports/**/*.svg
reports/**/*.png
reports/**/*.jpg
reports/**/*.jpeg
gh-pages/**/*.svg
gh-pages/**/*.png
gh-pages/**/*.jpg

# Ignore root-level generated CSVs and charts
/*.csv
/*.svg
/*.png
category_distribution*.csv
category_distribution*.svg
hourly_focus*.csv
hourly_focus*.svg
top_domains*.csv

# Keep JSON reports (negative patterns must come AFTER ignore patterns)
!reports/**/*.json
!ActivityReport-*.json

# Keep CSV if needed for version control (uncomment if desired)
# !reports/**/*.csv
```

### Apply .gitignore Changes

```bash
# Edit .gitignore
nano .gitignore  # or vim, code, etc.

# Test what would be ignored (dry run)
git status --ignored

# Remove already-tracked files from Git (keeps local copies)
git rm --cached reports/**/*.svg
git rm --cached reports/**/*.png
git rm --cached *.svg *.csv

# Commit .gitignore update
git add .gitignore
git commit -m "Update .gitignore: exclude generated charts and CSVs

- Ignore *.svg, *.png in reports/ and gh-pages/
- Ignore root-level CSV/SVG artifacts
- Keep JSON reports for dashboard
- Reduces diff noise and merge conflicts"

git push origin main
```

---

## Troubleshooting

### Issue: "fatal: ambiguous argument '53d18c6': unknown revision"

**Cause:** Commit not in repository history (shallow clone).

**Solution:**
```bash
# Fetch full history
git fetch --unshallow

# Or fetch all branches
git fetch --all

# Try again
git show 53d18c6 --no-patch
```

### Issue: git restore not recognized

**Cause:** Git version < 2.23.

**Solution:** Use `git checkout` instead:
```bash
git checkout 53d18c6 -- dashboard.html tools/generate_reports.py [...]
```

### Issue: "error: pathspec 'tools/generate_reports.py' did not match any file(s)"

**Cause:** File doesn't exist in target commit.

**Solution:**
```bash
# List files in commit
git show 53d18c6 --name-only | grep generate_reports

# Adjust path or exclude missing files
```

### Issue: Merge conflicts after merge

**Cause:** Generated artifacts still present in commit.

**Solution:**
```bash
# Abort merge
git merge --abort

# Return to Step 2: ensure ONLY code files were extracted
git diff --name-only feature/big-commit
# Should show only 7 files, no reports/logs/csvs

# Re-extract if needed
cd .worktrees/main
git reset --hard origin/feature/big-commit
# Start over from Step 2
```

### Issue: Schema validation fails

**Cause:** Code changes incompatible with current data format.

**Solution:**
```bash
# Check error messages
python3 scripts/generate_daily_json.py 2025-12-02 2>&1 | tee generation_errors.log

# Review code changes for schema incompatibilities
git diff HEAD~1 tools/generate_reports.py

# Fix schema issues before merging
# Or rollback commit:
git revert HEAD
git push origin feature/big-commit
```

---

## Safety Checklist

Before merging to main, verify:

- [ ] ✅ Only 7 code files changed (no generated artifacts)
- [ ] ✅ `git diff --name-only --staged` shows expected files only
- [ ] ✅ Single-date generation test passed
- [ ] ✅ Schema validation passed (timeline, deep_work_blocks, hourly_focus)
- [ ] ✅ No generated test files staged (reports/, logs/, *.csv, *.svg)
- [ ] ✅ Commit message clearly states "code only"
- [ ] ✅ Feature branch builds successfully (CI passes)
- [ ] ✅ Tests pass (`pytest` if applicable)
- [ ] ✅ No merge conflicts with main
- [ ] ✅ .gitignore updated to prevent future artifact commits (optional but recommended)

---

## Rollback Procedures

### If Issues Found After Merge to Main

**Option 1: Revert the merge commit**
```bash
git checkout main
git log --oneline -5  # find merge commit SHA
git revert -m 1 <merge-commit-sha>
git push origin main
```

**Option 2: Reset to before merge (⚠️ destructive, coordinate with team)**
```bash
# NOT RECOMMENDED for shared branches
git checkout main
git reset --hard HEAD~1  # or specific SHA before merge
git push --force origin main  # requires force push permissions
```

### If Issues Found Before Merge

```bash
# In worktree
cd .worktrees/main
git log --oneline -5  # find commit SHA to revert
git revert <commit-sha>
git push origin feature/big-commit

# Or reset (if commit not pushed)
git reset --hard HEAD~1
```

---

## Summary: Quick Command Reference

```bash
# 1. Prepare
cd .worktrees/main
git cherry-pick --abort || true
git status

# 2. Extract code only
git restore --source 53d18c6 -- \
  dashboard.html \
  tools/generate_reports.py \
  scripts/archive_outputs.sh \
  scripts/cron_report_and_push.sh \
  scripts/import_browser_history.py \
  scripts/import_screentime.py \
  FUTURE_UPDATES.md

# 3. Commit
git add [files]
git commit -m "Implement dashboard UI + Screen Time integration (code only)"

# 4. Verify
python3 scripts/generate_daily_json.py 2025-12-02
python3 - <<'PY'
import json, pathlib
j = json.load(open("reports/2025-12-02/ActivityReport-2025-12-02.json"))
print("timeline:", isinstance(j.get("timeline"), list))
print("deep_work_blocks:", isinstance(j.get("deep_work_blocks"), list))
print("hourly_focus_len:", len(j.get("hourly_focus", [])))
PY

# 5. Merge via PR (recommended)
git push origin feature/big-commit
gh pr create --base main --head feature/big-commit

# OR direct merge (careful!)
cd /path/to/repo
git checkout main
git pull --ff-only
git merge --no-ff feature/big-commit
git push origin main
```

---

## Related Documentation

- [Branch Cleanup Checklist](./BRANCH_CLEANUP_CHECKLIST.md)
- [PR Cleanup Guide](./PR_CLEANUP_GUIDE.md)
- [Git Config Fix](./GIT_CONFIG_FIX.md)
- [Railway Deploy](../RAILWAY_DEPLOY.md)
- [Recovery Mode](../RECOVERY_MODE.md)

---

## Maintenance

**Last updated:** 2025-12-16

**Maintainer:** Repository operations team

**Review frequency:** Update after major git workflow changes or when extraction patterns change.
