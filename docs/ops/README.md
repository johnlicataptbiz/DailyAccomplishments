# Operations Guides

Operational documentation for maintaining the DailyAccomplishments repository.

---

## 📚 Guide Index

### Git Operations & History Management

#### 🔧 [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md) ⭐ **ESSENTIAL**
**Purpose:** Safely extract code from large historical commits without merge conflicts.

**Use when:**
- Cherry-picking causes conflicts on generated artifacts
- Need to bring code changes without reports/logs/charts
- Working with git worktrees

**Quick start:**
```bash
cd .worktrees/main
git restore --source 53d18c6 -- dashboard.html tools/generate_reports.py [...]
git commit -m "Implement features (code only)"
```

**Contains:**
- Step-by-step extraction workflow
- Worktree-specific instructions
- Verification with repo-specific tools
- Two merge strategies (PR + direct)
- Safety checklists & rollback procedures
- Troubleshooting for 5+ common issues

---

#### 💬 [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md) 
**Purpose:** Ready-to-paste prompts for VS Code Copilot Chat.

**Use when:**
- Need to instruct Copilot to extract historical code
- Want structured, safe extraction guidance
- Collaborating with AI on complex git operations

**Quick start:**
Copy any of 5 prompt templates → Paste into Copilot Chat → Follow guidance.

**Contains:**
- Full prompt (detailed context)
- Short prompt (quick instructions)
- Interactive prompt (Q&A with Copilot)
- Troubleshooting prompt (fix issues)
- Verification prompt (post-merge checks)
- Good vs bad prompt examples
- Quick command cheat sheet

---

#### 🚫 [GITIGNORE_GENERATED_ARTIFACTS.md](./GITIGNORE_GENERATED_ARTIFACTS.md)
**Purpose:** Prevent merge conflicts by excluding generated reports from Git.

**Use when:**
- CSV/SVG/PNG artifacts causing merge conflicts
- Want cleaner diffs (code only)
- Need to clean up tracked artifacts

**Quick start:**
```bash
# Update .gitignore to exclude *.csv, *.svg
git rm --cached *.csv *.svg
git commit -m "Stop tracking generated artifacts"
```

**Contains:**
- Current state analysis (50+ artifacts tracked)
- 3 .gitignore strategies (aggressive/conservative/minimal)
- Step-by-step implementation
- Testing checklist & rollback
- CI/CD best practices
- Impact analysis (before/after)

---

### Branch & PR Management

#### 🌿 [BRANCH_CLEANUP_CHECKLIST.md](./BRANCH_CLEANUP_CHECKLIST.md)
**Purpose:** Interactive checklist for cleaning up 59 unmerged branches.

**Quick start:**
```bash
./delete_old_branches.sh --dry-run
./delete_old_branches.sh
```

---

#### 🗂️ [PR_CLEANUP_GUIDE.md](./PR_CLEANUP_GUIDE.md)
**Purpose:** Guide for closing stale pull requests.

**Contains:**
- PR categorization
- Closure strategies
- GitHub CLI commands

---

### Configuration & Troubleshooting

#### ⚙️ [GIT_CONFIG_FIX.md](./GIT_CONFIG_FIX.md)
**Purpose:** Fix git configuration issues (user.name, user.email, etc.).

---

#### 🛑 [STOP_AUTO_UPDATES_CHECKLIST.md](./STOP_AUTO_UPDATES_CHECKLIST.md)
**Purpose:** Disable auto-update GitHub Actions when needed.

---

#### 🔄 [HANDOFF.md](./HANDOFF.md)
**Purpose:** Repository handoff documentation for team transitions.

---

## 🚀 Quick Navigation by Task

### "I need to extract code from a historical commit"
1. Read: [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
2. Use prompt: [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md)
3. Update .gitignore: [GITIGNORE_GENERATED_ARTIFACTS.md](./GITIGNORE_GENERATED_ARTIFACTS.md)

### "I want to prevent artifact commit conflicts"
1. Follow: [GITIGNORE_GENERATED_ARTIFACTS.md](./GITIGNORE_GENERATED_ARTIFACTS.md)
2. Test with patterns from [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md#post-merge-verification)

### "I need to clean up old branches"
1. Run: `./delete_old_branches.sh --dry-run`
2. Follow: [BRANCH_CLEANUP_CHECKLIST.md](./BRANCH_CLEANUP_CHECKLIST.md)
3. Review: [PR_CLEANUP_GUIDE.md](./PR_CLEANUP_GUIDE.md)

### "I'm getting git conflicts when merging"
1. Check if it's artifact-related: [GITIGNORE_GENERATED_ARTIFACTS.md](./GITIGNORE_GENERATED_ARTIFACTS.md)
2. Use code-only extraction: [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
3. Ask Copilot with: [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md#prompt-for-merge-conflicts)

### "I'm using git worktrees and having issues"
1. Follow worktree workflow: [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md#prerequisites)
2. See worktree-specific commands in each guide

---

## 🎯 Common Workflows

### Workflow 1: Safe Historical Code Extraction (Full)

**Scenario:** Need code from commit `53d18c6` but it has lots of generated artifacts.

**Steps:**
```bash
# 1. Setup (see SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
cd .worktrees/main
git cherry-pick --abort || true
git status

# 2. Extract code only
git restore --source 53d18c6 -- \
  dashboard.html \
  tools/generate_reports.py \
  scripts/*.sh \
  scripts/import_*.py \
  FUTURE_UPDATES.md

# 3. Commit
git add [files]
git commit -m "Implement features (code only)"

# 4. Verify
python3 scripts/generate_daily_json.py 2025-12-02
python3 - <<'PY'
import json
j = json.load(open("reports/2025-12-02/ActivityReport-2025-12-02.json"))
print(f"timeline: {isinstance(j.get('timeline'), list)}")
print(f"deep_work_blocks: {isinstance(j.get('deep_work_blocks'), list)}")
print(f"hourly_focus_len: {len(j.get('hourly_focus', []))}")
PY

# 5. Merge via PR
git push origin feature/big-commit
gh pr create --base main --head feature/big-commit
```

**Documentation:**
- Full guide: [SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
- Copilot prompts: [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md)

---

### Workflow 2: Prevent Future Artifact Conflicts

**Scenario:** Tired of merge conflicts on CSV/SVG files.

**Steps:**
```bash
# 1. Update .gitignore (see GITIGNORE_GENERATED_ARTIFACTS.md)
nano .gitignore  # Add patterns

# 2. Remove from Git tracking (keeps local files)
git rm --cached *.csv *.svg
git rm --cached category_distribution*.csv
git rm --cached hourly_focus*.svg
# ... (see full list in guide)

# 3. Commit
git add .gitignore
git commit -m "Stop tracking generated artifacts"
git push origin main

# 4. Verify
echo "test" > test.csv
git status  # Should NOT show test.csv
rm test.csv
```

**Documentation:**
- Full guide: [GITIGNORE_GENERATED_ARTIFACTS.md](./GITIGNORE_GENERATED_ARTIFACTS.md)

---

### Workflow 3: Branch Cleanup

**Scenario:** Repository has 59+ unmerged branches.

**Steps:**
```bash
# 1. Preview deletions
./delete_old_branches.sh --dry-run

# 2. Delete safe branches
./delete_old_branches.sh

# 3. Manual review remaining branches
# Follow checklist in BRANCH_CLEANUP_CHECKLIST.md

# 4. Close stale PRs
gh pr list --state open
gh pr close [PR-NUMBER]
# ... (see PR_CLEANUP_GUIDE.md for details)
```

**Documentation:**
- Checklist: [BRANCH_CLEANUP_CHECKLIST.md](./BRANCH_CLEANUP_CHECKLIST.md)
- PR guide: [PR_CLEANUP_GUIDE.md](./PR_CLEANUP_GUIDE.md)

---

## 🔍 Related Documentation

### Repository Root
- [README.md](../../README.md) - Main project documentation
- [ROADMAP.md](../../ROADMAP.md) - Project roadmap
- [INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md) - Integration setup

### Docs Directory
- [docs/RAILWAY_DEPLOY.md](../RAILWAY_DEPLOY.md) - Deployment guide
- [docs/RECOVERY_MODE.md](../RECOVERY_MODE.md) - Recovery procedures
- [docs/REPORTS_HOSTING.md](../REPORTS_HOSTING.md) - Report hosting setup

### GitHub Configuration
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md) - Copilot agent guidance

---

## 📝 Contributing to Ops Guides

### When to Add a New Guide

Add a new ops guide when you:
- Solve a recurring operational issue
- Document a complex workflow
- Create reusable procedures
- Want to prevent future mistakes

### Guide Template

```markdown
# [Guide Title]

**Purpose:** One-sentence description

**Use when:** Bullet list of scenarios

**Quick start:** 3-5 line code example

---

## Prerequisites
[What you need before starting]

## Step-by-Step Instructions
[Detailed walkthrough]

## Verification
[How to confirm success]

## Troubleshooting
[Common issues & solutions]

## Rollback Procedures
[How to undo if something goes wrong]

## Related Documentation
[Links to other guides]
```

### Updating This Index

When adding a new guide:
1. Add entry under appropriate category
2. Include purpose, use cases, quick start
3. Add to "Quick Navigation by Task" if relevant
4. Update workflows if it changes procedures
5. Cross-reference with related guides

---

## 🔗 External Resources

### Git Operations
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Git Restore Command](https://git-scm.com/docs/git-restore)
- [Advanced Git Merge Strategies](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging)

### GitHub
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Best Practices
- [Gitignore Templates](https://github.com/github/gitignore)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📊 Ops Metrics

### Documentation Coverage

| Category | Guides | Status |
|----------|--------|--------|
| Git Operations | 3 | ✅ Complete |
| Branch/PR Management | 2 | ✅ Complete |
| Configuration | 3 | ✅ Complete |
| **Total** | **8** | **✅ Complete** |

### Common Issues Documented

- ✅ Historical commit extraction
- ✅ Merge conflicts on artifacts
- ✅ Git worktree workflows
- ✅ Branch cleanup
- ✅ PR management
- ✅ .gitignore configuration

### Guide Health

| Guide | Last Updated | Review Due |
|-------|--------------|------------|
| SAFE_HISTORICAL_COMMIT_EXTRACTION | 2025-12-16 | 2026-03-16 |
| COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE | 2025-12-16 | 2026-03-16 |
| GITIGNORE_GENERATED_ARTIFACTS | 2025-12-16 | 2026-03-16 |
| BRANCH_CLEANUP_CHECKLIST | [Check file] | [3 months] |
| PR_CLEANUP_GUIDE | [Check file] | [3 months] |

---

## 🆘 Getting Help

### If You Can't Find What You Need

1. **Search this directory:** `grep -r "your issue" docs/ops/`
2. **Check main README:** [../../README.md](../../README.md)
3. **Review Copilot instructions:** [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
4. **Ask Copilot:** Use prompts from [COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md](./COPILOT_PROMPT_EXTRACT_HISTORICAL_CODE.md)

### If You Find an Issue

- ✅ Documentation outdated? Update the guide & this index
- ✅ Procedure doesn't work? Test & document fix
- ✅ New scenario needed? Create guide using template above
- ✅ Broken link? Fix immediately

---

**Last updated:** 2025-12-16  
**Maintainer:** Repository operations team  
**Review frequency:** Quarterly or after major workflow changes
