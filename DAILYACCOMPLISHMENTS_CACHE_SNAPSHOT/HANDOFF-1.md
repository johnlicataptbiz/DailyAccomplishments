# DailyAccomplishments handoff

Owner: John Licata
Issues: open a GitHub Issue in this repo

Last verified: 2025-12-13 (America/Chicago)

## What this system does
A launchd StartInterval job runs a "publisher" wrapper. The wrapper ensures a clean git worktree at:

  .worktrees/main

Then it executes the main cron script:

  .worktrees/main/scripts/cron_report_and_push.sh

That cron script generates the daily ActivityReport JSON, archives outputs, postprocesses the report, and updates the dashboard assets when applicable.

Dashboard:
  https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html

## Key files and locations

Primary (live) clone:
  ~/DailyAccomplishments

LaunchAgent plist:
  ~/Library/LaunchAgents/com.dailyaccomplishments.reporter.plist

Publisher wrapper (runs under launchd):
  scripts/cron_report_and_push_publisher.sh

Worktree used for publishing:
  .worktrees/main

Main cron script (runs inside the worktree):
  .worktrees/main/scripts/cron_report_and_push.sh

Launchd stdout and stderr:
  logs/reporter.out.log
  logs/reporter.err.log

Per run traced log (publisher creates this and includes bash -x trace):
  logs/publisher.run.YYYYMMDD-HHMMSS.log

Reports:
  ActivityReport-YYYY-MM-DD.json
  reports/YYYY-MM-DD/

## Normal behavior
`launchctl print gui/$(id -u)/com.dailyaccomplishments.reporter` often shows:

  state = not running

This is expected for StartInterval jobs. They start, run, exit, and then wait for the next interval.

A successful run will end with:

  PUBLISHER: cron exit rc=0

and launchctl will show:

  last exit code = 0

Also normal:
If there were no file changes in the repo after generation, the cron script will log:

  No changes to main

## Useful commands

Kickstart now:
  launchctl kickstart -k gui/$(id -u)/com.dailyaccomplishments.reporter

Reboot the agent cleanly:
  launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.dailyaccomplishments.reporter.plist 2>/dev/null || true
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dailyaccomplishments.reporter.plist
  launchctl enable gui/$(id -u)/com.dailyaccomplishments.reporter
  launchctl kickstart -k gui/$(id -u)/com.dailyaccomplishments.reporter

Tail latest publisher run log:
  ls -t logs/publisher.run.*.log | head -n 1
  tail -n 200 "$(ls -t logs/publisher.run.*.log | head -n 1)"

Check exit code quickly:
  launchctl print gui/$(id -u)/com.dailyaccomplishments.reporter | egrep -n "state|pid|last exit|LastExitStatus" | head -n 120

## Gotchas

1) Worktree is disposable
Any direct edits inside `.worktrees/main` will be wiped by the publisher reset. If a change must persist, it must be committed to the real repo branch.

2) zsh globs
zsh will error on unmatched globs. When checking optional logs, use `2>/dev/null`:
  ls -t logs/publisher.run.*.log 2>/dev/null | head -n 3

3) Screen Time permissions
If Screen Time import returns 0 records, grant Full Disk Access to the relevant terminal/shell or agent host process and rerun.
