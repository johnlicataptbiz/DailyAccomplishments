**Purpose**:
- This repository holds a static "Daily Accomplishments" report and the data used to render it. The primary source is `ActivityReport-2025-12-01.json`; charts and CSVs are produced by `tools/generate_reports.py`.

**Key files**:
- `ActivityReport-2025-12-01.json`: canonical JSON data for the report.
- `index.html`, `report_view.html`: report HTML (root and `gh-pages/` copy). Assets (SVG/CSV/JSON) are in the repo root and mirrored in `gh-pages/` worktree for deployment.
- `tools/generate_reports.py`: generates `hourly_focus.csv`, `top_domains.csv`, `category_distribution.csv` and charts (SVG/PNG).
- `.github/workflows/publish-gh-pages.yml`: CI workflow that publishes the contents of the `gh-pages/` worktree to the `gh-pages` branch.

**Agent instructions / Do this first**:
- Always work from the `main` branch and update `ActivityReport-2025-12-01.json` in the repo root. After updates, run `python3 tools/generate_reports.py` to regenerate CSVs and charts, then commit those generated files.
- If you need the live site preview locally, run `python3 -m http.server 8000` in the repo root and open `http://localhost:8000/`.
- When publishing to GitHub Pages, update files in the `gh-pages/` directory (it's a git worktree). Commit in the worktree (`git -C gh-pages add . && git -C gh-pages commit -m "..." && git -C gh-pages push origin gh-pages`) or rely on the CI workflow which copies the worktree into the Action workspace and publishes.

**Data format notes**:
- `ActivityReport-*.json` uses these keys agents will edit:
  - `overview`: `focus_time`, `meetings_time`, `appointments`, `coverage_window` (human readable).
  - `executive_summary`, `client_summary`, `prepared_for_manager`: arrays of human-friendly lines.
  - `debug_appointments`: contains `appointments_today` and `meetings_today` lists with `name` and `time` fields. Keep these in sync with `overview` counts.

**Ensure full-day capture (no 4pm/5pm cutoff)**:
- Problem: some reports include `cutoff` wording or truncated `coverage_window` (e.g., "cutoff 4pm CST/CDT"). Agents must not intentionally shorten the coverage window.
- Checklist for agents when fixing or preventing cutoffs:
  1. Search the repo for any code that applies a cutoff or filters timestamps (look for keywords: `cutoff`, `coverage_window`, `end_time`, `truncate`, `limit`). If you find code, update logic to use the full-day range or make the window configurable.
  2. If the data collector is external (browser extension, remote agent, or separate service), request access or instructions from the repository owner. Document where the collector runs and any timezone conversions.
  3. Ensure timestamps are timezone-aware and stored in ISO 8601 where possible. When converting to local display, present the full range and do not trim earlier than the last recorded event.
  4. Update `ActivityReport-YYYY-MM-DD.json` `coverage_window` to reflect the true earliest->latest activity (e.g., `08:00–18:15 CST`) and remove misleading "cutoff" text from the `title` or summaries.
  5. Run `tools/generate_reports.py` and visually check `hourly_focus.svg` and the `coverage_window` shown in the HTML to confirm full coverage.

**Deployment / CI**:
- The workflow in `.github/workflows/publish-gh-pages.yml` expects a `gh-pages/` worktree. The Action copies the worktree contents into the action workspace then uses `peaceiris/actions-gh-pages` to publish.
- Actions need `contents: write` permission to push to the `gh-pages` branch. If you see 403 push errors, check workflow permissions and the runner token.
- To enable Pages (if not already enabled), a repo owner can enable it in Settings > Pages, or use the `gh` CLI: `gh api repos/:owner/:repo/pages -X POST` (requires repo admin access).

**Troubleshooting**:
- If VS Code shows worktree-related git URIs or "No url found for submodule path 'gh-pages'", it's a cosmetic issue from the worktree. You can remove the `gh-pages` folder from the workspace or use the `git worktree` commands to inspect (`git worktree list`).
- If charts fail to generate: install `matplotlib` in the repo Python environment: `pip install matplotlib`.
- If shellcheck messages appear in VS Code logs, install `shellcheck` or disable the specific extension.

**When editing files**:
- Keep changes minimal and update both root and `gh-pages/` copies when appropriate. Prefer updating the root JSON and regenerating artifacts, then copying to `gh-pages/` worktree.
- Run tests or local server to validate before committing.

**Commit and PR guidance**:
- Use clear commit messages describing data fixes, e.g. `report: correct meetings and appointments for 2025-12-01`.
- If creating a PR, include a short summary of data sources and the reason for the change (e.g. user report that a Slack huddle at 08:00 occurred and Banfield moved to Discovery appointment).

If you want, I can:
- Update today's `ActivityReport` entries and push commits (I already made the JSON + SUMMARY updates locally),
- Run `tools/generate_reports.py` to regenerate CSVs and charts and commit them, and
- Attempt to enable Pages via the GitHub API if you grant permission.
