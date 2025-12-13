#!/bin/bash
set -euo pipefail

export GIT_TERMINAL_PROMPT=0
export SSH_ASKPASS=/usr/bin/false
export GIT_SSH_COMMAND='ssh -o BatchMode=yes'

BASE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLISH_ROOT="$BASE_ROOT/.worktrees/main"
LOG_DIR="$BASE_ROOT/logs"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUNLOG="$LOG_DIR/publisher.run.$STAMP.log"

mkdir -p "$BASE_ROOT/.worktrees" "$LOG_DIR"

exec > >(tee -a "$RUNLOG") 2>&1

echo "[$(date)] PUBLISHER: base=$BASE_ROOT"
echo "[$(date)] PUBLISHER: publish=$PUBLISH_ROOT"
echo "[$(date)] PUBLISHER: whoami=$(whoami) uid=$(id -u) gid=$(id -g)"
echo "[$(date)] PUBLISHER: pwd=$(pwd)"
echo "[$(date)] PUBLISHER: PATH=$PATH"
echo "[$(date)] PUBLISHER: git version: $(git --version || true)"
echo "[$(date)] PUBLISHER: runlog=$RUNLOG"

if [ ! -d "$BASE_ROOT/.git" ]; then
  echo "[$(date)] PUBLISHER ERROR: not a git repo: $BASE_ROOT"
  exit 1
fi

git -C "$BASE_ROOT" fetch origin >/dev/null 2>&1 || true

# If directory exists but is not a valid worktree, remove it
if [ -d "$PUBLISH_ROOT" ] && [ ! -e "$PUBLISH_ROOT/.git" ]; then
  echo "[$(date)] PUBLISHER: removing stale publish dir (no .git file): $PUBLISH_ROOT"
  rm -rf "$PUBLISH_ROOT"
fi

# Ensure worktree exists (in worktrees, .git is a FILE)
if [ ! -e "$PUBLISH_ROOT/.git" ]; then
  echo "[$(date)] PUBLISHER: creating worktree at $PUBLISH_ROOT"
  git -C "$BASE_ROOT" worktree add -B main "$PUBLISH_ROOT" origin/main
fi

echo "[$(date)] PUBLISHER: worktree .git:"
ls -la "$PUBLISH_ROOT/.git" || true

git -C "$PUBLISH_ROOT" fetch origin >/dev/null 2>&1 || true
git -C "$PUBLISH_ROOT" checkout -B main origin/main >/dev/null 2>&1 || true
git -C "$PUBLISH_ROOT" reset --hard origin/main >/dev/null 2>&1 || true

echo "[$(date)] PUBLISHER: starting cron (bash -x)"
cd "$PUBLISH_ROOT"
set +e
/bin/bash -x "$PUBLISH_ROOT/scripts/cron_report_and_push.sh"
rc=$?
set -e
echo "[$(date)] PUBLISHER: cron exit rc=$rc"
exit $rc
