# PR Cleanup Guide - Quick Start

## TL;DR - Immediate Actions

You have **59 unmerged branches** (excluding main, gh-pages, reports-gh-pages). Here's how to clean them up:

### Option 1: Automated Cleanup (Recommended)

```bash
# See what would be deleted (safe to run)
./delete_old_branches.sh --dry-run

# Actually delete the 26 safe-to-delete branches
./delete_old_branches.sh
```

This will delete 26 branches that are clearly obsolete (merge conflict fixes, old setup branches, etc.)

### Option 2: Manual Cleanup

See `pr_closure_recommendations.md` for the detailed list and reasoning.

---

## What This PR Provides

This PR gives you tools to clean up your repository's 62 branches:

### 📊 Analysis Tools

1. **`analyze_branches.py`** - Scans all branches and checks their merge status
2. **`branch_analysis_report.json`** - Machine-readable analysis results
3. **`pr_closure_recommendations.md`** - Human-readable detailed recommendations
4. **`delete_old_branches.sh`** - Automated deletion script with dry-run mode
5. **`PR_CLEANUP_GUIDE.md`** (this file) - Quick start guide

---

## Branch Categories

### ✅ Safe to Delete Now (26 branches)

These branches can be deleted immediately without risk:

**Merge Conflict Fixes (4)** - These were temporary fix branches:
- `codex/fix-codex-review-issues-in-pull-request-#12`
- `codex/fix-codex-review-issues-in-pull-request-#12-zb1pn2`
- `copilot/fix-merge-conflict-in-validate-report-schema`
- `copilot/fix-merge-conflicts-in-reports`

**Setup/Documentation (4)** - One-time setup tasks:
- `copilot/set-up-copilot-instructions`
- `copilot/set-up-copilot-instructions-again`
- `copilot/copy-repo-to-dailyaccomplishments`
- `codex/document-manual-merge-via-command-line`

**Completed Bug Fixes (6)** - Small fixes that are likely already in main:
- `codex/fix-.gitattributes-trailing-whitespace-rule`
- `copilot/fix-trailing-whitespace-errors`
- `copilot/fix-launch-json-errors`
- `copilot/fix-invalid-image-name`
- `codex/add-workflow-badge-for-deployment`
- `codex/add-workflow-badge-for-deployment-pdcnqh`

**CI/Workflow Fixes (3)** - Verify your CI works, then delete:
- `copilot/ci-fix-and-gh-actions`
- `copilot/fix-codeql-workflow-dockerfile`
- `copilot/fix-codeql-language-matrix`

**Old Implementation (5)** - Superseded development work:
- `copilot/continue-implementation`
- `copilot/execute-notebook`
- `copilot/create-task-list-from-notebook`
- `copilot/continue-task-list-work`
- `copilot/update-instruction-files`

**Codespace Cleanup (4)** - Old codespace snapshots:
- `codespace-consolidation`
- `codespace-consolidation-backup-20251211T012527Z`
- `codespace-consolidation-local-20251210`
- `codespace-consolidation-reconciled`

### ⚠️ Need Review (18 branches)

These branches were created very recently (2025-12-13) and might contain work you want to preserve:

**Recent Fixes** - Check if these issues are resolved in main:
- `copilot/fix-timeline-json-errors`
- `copilot/fix-repo-link-errors`
- `copilot/fix-workflow-failure-rates`
- `copilot/fix-gh-pages-checkout-error`
- `copilot/fix-missing-report-fields`
- `copilot/fix-meeting-overlay-fallback-logic`
- `copilot/fix-timeline-smoke-selection`
- `copilot/fix-timeline-smoke-test-selection`
- `copilot/fix-check-reports-failure`
- `copilot/test-pull-request-flows`
- `copilot/remove-broken-code-instances`

**Dependency Updates** - Verify if dependencies are up to date:
- `copilot/add-fpdf2-version-requirement`
- `copilot/add-jsonschema-to-requirements`

**Codex Fixes** - Recent automated fixes:
- `codex/fix-import-errors-in-test-jobs`
- `codex/fix-meeting-overlay-minutes-bug`
- `codex/run-schema-validation-for-last-3-days`
- `codex/stop-auto-updates-for-dashboard-issues`
- `codex/recover-daily-accomplishments-dashboard`

### 💾 Keep for Now (8 branches)

These contain significant work or are intentional archives:
- `archive/codespace-snapshots`
- `salvage/stash0`
- `feature/timeline-pr-20251205`
- `integrate/copilot-pr`
- `rebuild/december-2025`
- `johnlicataptbiz-existing-tracker`
- `codex/bundle-dashboard.html-and-assets`

### 🤔 Special Cases (7 branches)

These need your decision:
- `copilot/close-old-prs` ← This current PR
- `copilot/enable-secret-scanning`
- `codex/merge-pull-request-via-command-line`
- `copilot/rebase-and-merge-branch`
- `copilot/sub-pr-63`
- `copilot/check-smoke-fixes-pr`
- `codex/crawl-daily-accomplishments-page`

---

## Step-by-Step Cleanup Process

### Step 1: Delete Safe Branches (2 minutes)

```bash
# Run the automated script
cd /path/to/DailyAccomplishments
./delete_old_branches.sh --dry-run  # Preview what will be deleted
./delete_old_branches.sh            # Actually delete them
```

**Result:** Reduces from 59 branches to 33 branches (44% reduction)

### Step 2: Review Medium Priority Branches (15-30 minutes)

For each of the 18 "Need Review" branches:

1. Check if the issue/fix is still relevant
2. If yes, consider merging or cherry-picking
3. If no, delete the branch

**Commands to help:**
```bash
# See what's in a branch
git log main..origin/BRANCH_NAME --oneline

# See the diff
git diff main...origin/BRANCH_NAME

# Delete if not needed
git push origin --delete BRANCH_NAME
```

**Result:** Potentially reduces to 15-21 branches

### Step 3: Establish Branch Hygiene (ongoing)

To prevent this from happening again:

1. **Enable "Delete branch after merge"** in GitHub repo settings
2. **Set up branch protection** on `main`
3. **Weekly cleanup:** Delete branches for closed PRs
4. **Squash merge strategy:** Helps with cleanup
5. **Review automation:** Use GitHub Actions to remind about old branches

---

## Common Questions

### Q: Why are there no merged branches?

**A:** This suggests your workflow either:
- Uses squash merges (commits look different after merge)
- Closes PRs without merging
- Works directly on main

Git's merge detection looks for exact commits, so squash merges appear as "unmerged."

### Q: Is it safe to delete these branches?

**A:** Yes, with caveats:
- **Green category (26 branches):** Definitely safe
- **Yellow category (18 branches):** Probably safe, but check first
- **Other branches:** Keep for now

Remember: Even if you delete a branch, the commits still exist in GitHub for ~90 days and can be restored.

### Q: How do I restore a deleted branch?

**A:** If you accidentally delete a branch:
```bash
# Find the commit hash from the analysis report or GitHub
git push origin COMMIT_HASH:refs/heads/BRANCH_NAME
```

Or use GitHub's UI: Go to the closed PR → "Restore branch" button

### Q: Should I merge or delete?

**A:** Quick decision tree:
- **Merge** if: Code is good, adds value, passes tests
- **Delete** if: Superseded, experimental, or issue no longer relevant
- **Keep** if: Still working on it, might need later

---

## Next Steps After Cleanup

Once you've cleaned up old branches, consider:

1. **Document your workflow** - Add CONTRIBUTING.md with branch conventions
2. **Set up automation** - GitHub Actions to close stale PRs
3. **Regular reviews** - Monthly branch cleanup schedule
4. **Clear naming** - Use prefixes like `feature/`, `fix/`, `chore/`

---

## Files Reference

- **`pr_closure_recommendations.md`** - Detailed analysis and recommendations
- **`branch_analysis_report.json`** - Raw data in JSON format
- **`analyze_branches.py`** - Re-run analysis anytime with `python3 analyze_branches.py`
- **`delete_old_branches.sh`** - Safe deletion script (always test with `--dry-run` first)

---

## Getting Help

If you're unsure about any branch:

1. Check the branch's last commit message
2. Look at the PR description (if it exists)
3. Check if the issue is still open
4. When in doubt, **keep it** - you can always delete later

---

**Ready to clean up?** Start with Step 1 above! 🧹
