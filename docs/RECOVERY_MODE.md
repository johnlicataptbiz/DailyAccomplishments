# Dashboard Recovery Plan

These steps stop the noisy auto-updates, establish a verified baseline, and guide the forensic diff to fix the dashboard spinner.

## 1) Stop the bleeding
- Temporarily pause scheduled report generation by **not** setting the `ENABLE_SCHEDULED_REPORTS` repository variable. Scheduled runs now respect this guard and will be skipped unless the variable is set to `true`.
- If you need a one-off run, trigger `Generate Daily Reports` or `Generate and publish reports` via **`workflow_dispatch`**.

## 2) Find the last-known-good dashboard
- Identify the most recent commit where the dashboard rendered successfully (e.g., by loading the GitHub Pages snapshot for older commits).
- Record that commit SHA as the baseline for comparison.

## 3) Diff forward from the baseline
- Compare the baseline to the `dashboard: add nested reports/YYYY...` commit.
- Focus the diff on:
  - Report directory layout (root vs. nested `reports/YYYY/MM/DD/`)
  - JSON schema changes in generated reports
  - Dashboard fetch/render logic tied to the new layout

## 4) Decide the target
- Use the cleaner implementation as the future direction (fewer TODOs and hacks, clearer comments, and better separation of concerns), even if it is currently unwired.
- Treat any salvage or consolidation folders as evidence to understand intent; do not delete them until the target is chosen.

## 5) Document the truth and unblock the spinner
- Produce a short handoff that states:
  - Which files are authoritative vs. deprecated
  - Canonical report paths and JSON shape
  - Which scripts generate which artifacts
  - The fetch paths the dashboard should use
- Implement the fetch/path/schema alignment so the render completes and the spinner clears.
