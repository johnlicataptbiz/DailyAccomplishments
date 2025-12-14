# Branch Cleanup Checklist

Quick reference for cleaning up the 59 unmerged branches in this repository.

## Quick Start

```bash
# See what would be deleted
./delete_old_branches.sh --dry-run

# Delete safe branches
./delete_old_branches.sh
```

---

## Automated Deletion (26 branches) ✅

Run `./delete_old_branches.sh` to delete these automatically:

- [ ] 4 merge conflict fix branches
- [ ] 4 setup/documentation branches  
- [ ] 6 completed bug fix branches
- [ ] 3 CI/workflow fix branches
- [ ] 5 old implementation branches
- [ ] 4 codespace cleanup branches

**Total: 26 branches will be deleted**

---

## Manual Review Required (18 branches) ⚠️

Check each branch and decide to merge or delete:

### Recent Copilot Fixes (2025-12-13)
- [ ] `copilot/fix-timeline-json-errors` - Still needed?
- [ ] `copilot/fix-repo-link-errors` - Still needed?
- [ ] `copilot/fix-workflow-failure-rates` - Still needed?
- [ ] `copilot/fix-gh-pages-checkout-error` - Still needed?
- [ ] `copilot/fix-missing-report-fields` - Still needed?
- [ ] `copilot/fix-meeting-overlay-fallback-logic` - Still needed?
- [ ] `copilot/fix-timeline-smoke-selection` - Still needed?
- [ ] `copilot/fix-timeline-smoke-test-selection` - Still needed?
- [ ] `copilot/fix-check-reports-failure` - Still needed?
- [ ] `copilot/test-pull-request-flows` - Still needed?
- [ ] `copilot/remove-broken-code-instances` - Still needed?

### Dependency Updates
- [ ] `copilot/add-fpdf2-version-requirement` - Check requirements.txt
- [ ] `copilot/add-jsonschema-to-requirements` - Check requirements.txt

### Recent Codex Fixes
- [ ] `codex/fix-import-errors-in-test-jobs` - Verify tests work
- [ ] `codex/fix-meeting-overlay-minutes-bug` - Bug fixed?
- [ ] `codex/run-schema-validation-for-last-3-days` - One-time task?
- [ ] `codex/stop-auto-updates-for-dashboard-issues` - Applied?
- [ ] `codex/recover-daily-accomplishments-dashboard` - Dashboard working?

---

## Keep for Now (8 branches) 💾

Don't delete these:

- [ ] `archive/codespace-snapshots` - Intentional archive
- [ ] `salvage/stash0` - Intentional archive
- [ ] `feature/timeline-pr-20251205` - Feature work
- [ ] `integrate/copilot-pr` - Integration work
- [ ] `rebuild/december-2025` - Recent rebuild
- [ ] `johnlicataptbiz-existing-tracker` - Import/migration
- [ ] `codex/bundle-dashboard.html-and-assets` - Dashboard work

---

## Special Cases (7 branches) 🤔

Manual decision needed:

- [ ] `copilot/close-old-prs` - THIS PR (merge when done)
- [ ] `copilot/enable-secret-scanning` - Want to enable?
- [ ] `codex/merge-pull-request-via-command-line` - Process branch
- [ ] `copilot/rebase-and-merge-branch` - Process branch
- [ ] `copilot/sub-pr-63` - What is this?
- [ ] `copilot/check-smoke-fixes-pr` - Check smoke tests
- [ ] `codex/crawl-daily-accomplishments-page` - Analysis branch?

---

## Progress Tracking

- [ ] **Step 1:** Run automated deletion script
  - **Status:** Not started
  - **Expected result:** 59 → 33 branches

- [ ] **Step 2:** Review 18 medium-priority branches
  - **Status:** Not started
  - **Expected result:** 33 → 15-21 branches

- [ ] **Step 3:** Decide on 7 special case branches
  - **Status:** Not started
  - **Expected result:** Final cleanup

- [ ] **Step 4:** Keep 8 archive/feature branches
  - **Status:** -
  - **Action:** None needed

---

## Final Goal

**Target:** Reduce from **59 branches** to **15-21 branches** (65-75% reduction)

**Branches after cleanup:**
- 8 kept branches (archives + active features)
- 7-13 branches needing ongoing work
- 0-7 special case branches (based on decisions)

---

## Completion

Once cleanup is done:

- [ ] Verify main branch is healthy
- [ ] Enable "Delete branch after merge" in repo settings
- [ ] Document branch naming conventions
- [ ] Set up monthly branch review reminder

**Date completed:** ___________

**Final branch count:** ___________

**Reduction achieved:** ___________%
