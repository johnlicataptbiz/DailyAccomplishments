#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREE_DIR="${ROOT_DIR}/.worktrees/main"
MAIN_BRANCH="${MAIN_BRANCH:-main}"

mkdir -p "${ROOT_DIR}/logs"

ts="$(date +"%Y%m%d-%H%M%S")"
RUN_LOG="${ROOT_DIR}/logs/publisher.run.${ts}.log"

exec > >(tee -a "${RUN_LOG}") 2>&1

echo "PUBLISHER: start $(date -Is)"
echo "PUBLISHER: root=${ROOT_DIR}"
echo "PUBLISHER: worktree=${WORKTREE_DIR}"
echo "PUBLISHER: branch=${MAIN_BRANCH}"

cd "${ROOT_DIR}"

# Ensure worktree exists and is clean
if [[ ! -d "${WORKTREE_DIR}/.git" && ! -f "${WORKTREE_DIR}/.git" ]]; then
  echo "PUBLISHER: creating worktree at ${WORKTREE_DIR}"
  mkdir -p "${ROOT_DIR}/.worktrees"
  git fetch origin "${MAIN_BRANCH}" || true
  git worktree add -f "${WORKTREE_DIR}" "${MAIN_BRANCH}" || git worktree add -f "${WORKTREE_DIR}" "origin/${MAIN_BRANCH}"
fi

echo "PUBLISHER: reset worktree to a clean state"
cd "${WORKTREE_DIR}"
git fetch origin "${MAIN_BRANCH}" || true
git checkout -f "${MAIN_BRANCH}" || true
git reset --hard "origin/${MAIN_BRANCH}" 2>/dev/null || git reset --hard "${MAIN_BRANCH}"
git clean -fd

# Run the real cron script inside the worktree with bash -x tracing
CRON="${WORKTREE_DIR}/scripts/cron_report_and_push.sh"
if [[ ! -x "${CRON}" ]]; then
  echo "PUBLISHER: ERROR missing or not executable: ${CRON}"
  exit 1
fi

echo "PUBLISHER: running ${CRON}"
set +e
bash -x "${CRON}"
rc=$?
set -e

echo "PUBLISHER: cron exit rc=${rc}"
exit "${rc}"
