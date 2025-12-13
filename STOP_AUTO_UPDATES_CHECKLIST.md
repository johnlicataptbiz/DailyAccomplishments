# Stop Auto-Updates + Recovery Mode

This checklist captures the steps needed to halt failing automation and restore the dashboard after the nested reports change.

## 1) Stop the bleeding
- Disable any scheduled GitHub Actions, cron jobs, or scripts that push `Auto-update` commits.
- Make the branch read-only (e.g., using branch protection rules) until the mismatch is resolved.

## 2) Pick a forensic anchor
- Identify the last commit where the dashboard renders correctly (verify by opening the published dashboard for that SHA).
- Use that commit as the gold reference for behavior and data layout.

## 3) Diff forward from the anchor
- Compare the anchor commit to the commit(s) that introduced the breaking change.
- Audit differences in:
  - Report paths and filenames
  - JSON structure or schema
  - Dashboard fetch and render logic

## 4) Decide the target version
- From consolidation/salvage folders, choose the version that best represents the intended future (clear comments, fewer hacks, better separation of concerns).
- Treat that version as authoritative even if it is not currently wired up.

## 5) Repair deliberately
- Align the generator output paths with what the dashboard expects (or vice versa).
- Remove or gate any legacy dashboard logic that conflicts with the nested-report design.
- Surface errors in the UI so fetch/render failures do not leave a perpetual spinner.

## 6) Document the outcome
- Record the canonical paths, authoritative files, and dead code.
- Note which scripts generate which data and how the dashboard consumes it.
- Re-enable automation only after the dashboard renders cleanly end-to-end.
