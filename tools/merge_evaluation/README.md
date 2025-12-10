Merge evaluation framework

This folder contains scripts to safely evaluate a planned merge from a source directory
(e.g. `DailyAccomplishments-1`) into the destination repository (`DailyAccomplishments`).

Files:
- `evaluate_merge.py` - Python script that inspects file additions, removals, changed files, and generates a JSON report. It can optionally run tests in the destination repository.
- `merge_preview.sh` - Shell wrapper that runs an rsync dry-run to preview file changes and then invokes `evaluate_merge.py` to produce a report.

Recommended workflow (safe):
1. Review the repo backup (there should be a tarball in your home directory from earlier actions).
2. Run `merge_preview.sh` to preview and evaluate the merge:

   ./merge_preview.sh ~/DailyAccomplishments-1 ~/DailyAccomplishments /tmp/merge_report.json

3. Inspect `/tmp/merge_report.json` and the human-readable summary printed by the script. Pay attention to `changed` (files that would be overwritten) and any `large_added_files`.
4. If the report looks good, run the actual rsync and perform the merge commit/push as previously described.

Notes:
- The evaluation script is read-only and will not modify your repositories.
- The `--run-tests` flag attempts to run `pytest` in the destination; ensure your environment has the required dependencies if you want to run tests as part of the evaluation.
