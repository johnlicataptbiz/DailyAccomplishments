# Copilot Prompt: Extract Code from Historical Commit

**Quick-start prompt template for VS Code Copilot Chat**

---

## Full Prompt (Paste into Copilot Chat)

```
You are working in the DailyAccomplishments Git repository that uses worktrees.

CONTEXT:
- Repository root: /path/to/DailyAccomplishments-repo (has main checked out)
- Feature worktree: /path/to/DailyAccomplishments-repo/.worktrees/main (has feature/big-commit checked out)
- Target commit: 53d18c6 ("UI: Deep Work overlay + integration highlights; Screen Time top apps")
- Problem: Commit contains both code changes AND generated artifacts (reports, CSV/PNG/SVG, logs)
- Current main: Has newer schema and auto-updates, so cherry-pick causes conflicts

GOAL:
Extract ONLY code/docs from commit 53d18c6 onto feature/big-commit branch, avoiding all generated artifacts.

ALLOWED FILES TO EXTRACT:
- dashboard.html
- tools/generate_reports.py
- scripts/archive_outputs.sh
- scripts/cron_report_and_push.sh
- scripts/import_browser_history.py
- scripts/import_screentime.py
- FUTURE_UPDATES.md

DO NOT EXTRACT:
- reports/**
- ActivityReport-*.json
- *.csv, *.svg, *.png (charts/images)
- logs/**
- gh-pages/**

TASKS:
1. Navigate to feature worktree: .worktrees/main
2. Abort any in-progress git operations (cherry-pick, merge, rebase)
3. Ensure clean worktree state
4. Use `git restore --source 53d18c6 -- <allowed-files>` to extract code only
5. Stage and commit with message: "Implement dashboard UI + Screen Time integration (code only)"
6. Verify by running: `python3 scripts/generate_daily_json.py 2025-12-02`
7. Validate schema using Python to check ActivityReport JSON has:
   - timeline (array)
   - deep_work_blocks (array)
   - hourly_focus (length 24)
8. DO NOT commit generated test files
9. Push feature branch and create PR (recommended) OR merge directly to main
10. Provide exact commands and outputs for each step

REFERENCE: See full guide at docs/ops/SAFE_HISTORICAL_COMMIT_EXTRACTION.md
```

---

## Shorter "Just Do It" Prompt

```
Extract code-only changes from commit 53d18c6 onto branch feature/big-commit (in worktree .worktrees/main).

Use git restore --source 53d18c6 to get ONLY:
- dashboard.html
- tools/generate_reports.py
- scripts/archive_outputs.sh
- scripts/cron_report_and_push.sh
- scripts/import_browser_history.py
- scripts/import_screentime.py
- FUTURE_UPDATES.md

SKIP: reports/, ActivityReport-*.json, *.csv, *.svg, *.png, logs/, gh-pages/.

Commit, verify generation works (python3 scripts/generate_daily_json.py 2025-12-02), check schema, then create PR.

Provide exact commands for each step.
```

---

## Interactive Prompt (Copilot Asks Questions)

```
I need to safely extract code from a historical commit without bringing in generated artifacts.

Commit: 53d18c6
Branch: feature/big-commit (in .worktrees/main)
Files I want: dashboard.html, tools/generate_reports.py, 5 scripts files, FUTURE_UPDATES.md
Files to skip: All reports, logs, CSV, SVG, PNG, gh-pages

Walk me through the safest approach, asking questions as needed to understand my setup.
```

---

## Prompt for Merge Conflicts

```
I tried cherry-picking commit 53d18c6 but got merge conflicts on generated files (reports/, ActivityReport-*.json, CSV/SVG).

I want to extract ONLY the code changes (dashboard.html, tools/generate_reports.py, scripts/) without the generated artifacts.

Repository uses worktrees:
- Main repo root: /path/to/repo
- Feature branch: /path/to/repo/.worktrees/main

Show me how to:
1. Abort the failed cherry-pick
2. Safely extract just code files using git restore
3. Verify the extraction worked
4. Merge to main via PR

Reference: docs/ops/SAFE_HISTORICAL_COMMIT_EXTRACTION.md
```

---

## Troubleshooting Prompt

```
Problem: [Describe your issue]

Context:
- Working in worktree: .worktrees/main
- Tried to extract from commit: 53d18c6
- Got error: [Paste error message]

Please help me:
1. Diagnose the issue
2. Provide safe recovery steps
3. Continue the extraction process

Reference the procedures in docs/ops/SAFE_HISTORICAL_COMMIT_EXTRACTION.md
```

---

## After-Merge Verification Prompt

```
I just merged code from historical commit 53d18c6 to main.

Help me verify:
1. The 7 code files are present on main
2. No generated artifacts were merged
3. Generation still works (run for today's date)
4. Schema validation passes
5. Dashboard loads correctly

Provide exact verification commands and expected outputs.
```

---

## Usage Tips

### 1. Customize Paths
Replace placeholder paths with your actual paths:
- `/path/to/DailyAccomplishments-repo` → your repo root path
- `.worktrees/main` → your worktree path (check with `git worktree list`)

### 2. Verify Commit SHA
Before running extraction, verify commit exists:
```bash
git log --oneline --all | grep 53d18c6
git show 53d18c6 --no-patch
```

If not found, you may need:
```bash
git fetch --unshallow  # if shallow clone
git fetch --all        # if missing branches
```

### 3. Adapt File List
If your commit has different files, update the allowed/skip lists in the prompt.

### 4. Test First
Run extraction on a throwaway branch first:
```bash
git checkout -b test-extraction
# ... run extraction ...
# If successful, delete test branch and do real extraction
git checkout feature/big-commit
git branch -D test-extraction
```

---

## Related Documentation

- **Full Guide**: [docs/ops/SAFE_HISTORICAL_COMMIT_EXTRACTION.md](./SAFE_HISTORICAL_COMMIT_EXTRACTION.md)
- **Copilot Instructions**: [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
- **Branch Cleanup**: [docs/ops/BRANCH_CLEANUP_CHECKLIST.md](./BRANCH_CLEANUP_CHECKLIST.md)

---

## Success Criteria

After following prompts, you should have:

✅ Feature branch with only code changes (7 files)
✅ No generated artifacts committed
✅ Generation verified to work
✅ Schema validation passed
✅ PR created OR direct merge to main completed
✅ Main branch verified working

---

## Examples of Good vs Bad Prompts

### ❌ Bad Prompt (Too Vague)
```
"Cherry-pick commit 53d18c6"
```
**Why bad:** Will bring in all generated artifacts, causing conflicts.

### ❌ Bad Prompt (Missing Context)
```
"Get code from that old commit"
```
**Why bad:** Copilot doesn't know which commit, which files, or your workflow.

### ✅ Good Prompt (Specific & Safe)
```
Extract code-only from commit 53d18c6 using git restore --source 53d18c6 -- dashboard.html tools/generate_reports.py [list all files]. Skip reports/, *.csv, *.svg. Working in worktree .worktrees/main on branch feature/big-commit. Show exact commands.
```
**Why good:** Specific commit, specific method, specific files, specific location, asks for verification.

### ✅ Good Prompt (Safety-Focused)
```
I need to safely extract code from 53d18c6 without conflicts. I'm using worktrees. Reference docs/ops/SAFE_HISTORICAL_COMMIT_EXTRACTION.md and show step-by-step commands with verification.
```
**Why good:** Emphasizes safety, mentions worktrees, references documentation, asks for verification.

---

## Quick Command Cheat Sheet

```bash
# Navigate to worktree
cd .worktrees/main

# Clean state
git cherry-pick --abort || true
git status

# Extract code only
git restore --source 53d18c6 -- \
  dashboard.html \
  tools/generate_reports.py \
  scripts/archive_outputs.sh \
  scripts/cron_report_and_push.sh \
  scripts/import_browser_history.py \
  scripts/import_screentime.py \
  FUTURE_UPDATES.md

# Verify & commit
git status
git diff --staged
git commit -m "Implement dashboard UI + Screen Time integration (code only)"

# Test
python3 scripts/generate_daily_json.py 2025-12-02

# Validate
python3 - <<'PY'
import json
j = json.load(open("reports/2025-12-02/ActivityReport-2025-12-02.json"))
print("timeline:", isinstance(j.get("timeline"), list))
print("deep_work_blocks:", isinstance(j.get("deep_work_blocks"), list))
print("hourly_focus_len:", len(j.get("hourly_focus", [])))
PY

# Create PR
git push origin feature/big-commit
gh pr create --base main --head feature/big-commit
```

---

**Last updated:** 2025-12-16  
**Maintainer:** Repository operations team
