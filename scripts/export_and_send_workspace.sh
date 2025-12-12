#!/usr/bin/env bash
set -euo pipefail

# export_and_send_workspace.sh
#
# Portable helper to create a snapshot archive of the current workspace
# and optionally upload it to a remote via scp or S3. Designed to be copied
# into any codespace or machine and run with minimal dependencies.
#
# WARNING: This script can capture secrets, credentials, caches, and large
# binary files. Review the exclude patterns and run with --dry-run before
# uploading to remote storage. By default it WILL NOT include the .git
# directory unless you pass --include-git.

usage() {
  cat <<'USAGE'
Usage: export_and_send_workspace.sh [options]

Options:
  -o, --output PATH         Output archive path (default: ./workspace_snapshot-<ts>.tar.gz)
  --include-git             Include .git directory in the archive (warning: includes repo data)
  --include-ignored         Include files ignored by git (.gitignore) - may include build artifacts
  --include-hidden          Include hidden files/dirs (default: yes)
  -e, --exclude FILE        Read newline-separated exclude patterns from FILE
  --exclude-pattern PATTERN Exclude a single pattern (can be repeated)
  --upload-scp USER@HOST:DIR Upload archive using scp to remote
  --upload-s3 S3_URI        Upload archive to S3 (requires aws cli configured)
  --rsync USER@HOST:DIR     Use rsync to copy workspace contents to remote dir (not archive)
  --dry-run                 Show what would be archived (no archive created)
  -h, --help                Show this help and exit

Examples:
  # Create archive locally (default):
  ./export_and_send_workspace.sh

  # Create archive and upload by scp:
  ./export_and_send_workspace.sh --upload-scp me@host:/backups/daily

  # Archive and upload to S3:
  ./export_and_send_workspace.sh --upload-s3 s3://my-bucket/backups/

USAGE
}

TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="workspace_snapshot-$TS.tar.gz"
INCLUDE_GIT=0
INCLUDE_IGNORED=0
DRY_RUN=0
RSYNC_TARGET=""
SCP_TARGET=""
S3_TARGET=""
EXCLUDE_FILE=""
EXCLUDE_PATTERNS=()

if [ "$#" -eq 0 ]; then
  : # continue with defaults
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    -o|--output)
      OUT="$2"; shift 2;;
    --include-git)
      INCLUDE_GIT=1; shift;;
    --include-ignored)
      INCLUDE_IGNORED=1; shift;;
    --include-hidden)
      # default behaviour; kept for compatibility
      shift;;
    -e|--exclude)
      EXCLUDE_FILE="$2"; shift 2;;
    --exclude-pattern)
      EXCLUDE_PATTERNS+=("$2"); shift 2;;
    --upload-scp)
      SCP_TARGET="$2"; shift 2;;
    --upload-s3)
      S3_TARGET="$2"; shift 2;;
    --rsync)
      RSYNC_TARGET="$2"; shift 2;;
    --dry-run)
      DRY_RUN=1; shift;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 2;;
  esac
done

REPO_ROOT="$(pwd)"
TMPDIR=$(mktemp -d)
ARCHIVE_PATH="$REPO_ROOT/$OUT"

echo "Workspace root: $REPO_ROOT"
echo "Archive: $ARCHIVE_PATH"

EXCLUDE_ARGS=()

# Default safe excludes (we exclude sensitive/large patterns by default)
DEFAULT_EXCLUDES=(
  ".git"                  # exclude git by default
  "node_modules"
  "venv"
  ".venv"
  "__pycache__"
  "*.pyc"
  "*.sqlite3"
  "*.log"
  "*.cache"
  "*/.cache/*"
  "*/.npm/*"
  "*/.pnpm-store/*"
  "*/.DS_Store"
  "*.key"
  "*.pem"
  "credentials.json"
  "google_credentials.json"
  "credentials/*"
)

if [ "$INCLUDE_GIT" -eq 1 ]; then
  # Remove .git from default excludes
  DEFAULT_EXCLUDES=("${DEFAULT_EXCLUDES[@]/.git}")
fi

if [ "$INCLUDE_IGNORED" -eq 1 ]; then
  # If including ignored, also remove node_modules and similar from default excludes
  DEFAULT_EXCLUDES=("")
fi

for p in "${DEFAULT_EXCLUDES[@]}"; do
  [ -z "$p" ] && continue
  EXCLUDE_ARGS+=("--exclude=$p")
done

if [ -n "$EXCLUDE_FILE" ]; then
  if [ -f "$EXCLUDE_FILE" ]; then
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      EXCLUDE_ARGS+=("--exclude=$line")
    done < "$EXCLUDE_FILE"
  else
    echo "Exclude file not found: $EXCLUDE_FILE" >&2
    exit 2
  fi
fi

for p in "${EXCLUDE_PATTERNS[@]}"; do
  EXCLUDE_ARGS+=("--exclude=$p")
done

# Build tar command; use --transform to place files under a top-level folder for clarity
TOPDIR="workspace_snapshot_$TS"
TAR_ARGS=(--create --gzip --file "$ARCHIVE_PATH")

# Add exclude args for tar
for ex in "${EXCLUDE_ARGS[@]}"; do
  TAR_ARGS+=(--exclude="${ex#--exclude=}")
done

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN - files that would be included (first 500 lines):"
  # Use tar --exclude to simulate; use -c to list
  tar --create --file - "${TAR_ARGS[@]}" --show-transformed-names --wildcards --no-recursion . 2>/dev/null || true
  echo "(dry run complete)"
  exit 0
fi

echo "Creating archive..."

# Create a temporary directory and copy workspace contents according to rules
rsync_cmd=(rsync -aH --delete)
for ex in "${EXCLUDE_ARGS[@]}"; do
  rsync_cmd+=(--exclude "${ex#--exclude=}")
done

# If including git, just archive directly; otherwise use rsync to a temp dir then tar
if [ "$INCLUDE_GIT" -eq 1 ] && [ ${#EXCLUDE_ARGS[@]} -eq 0 ]; then
  # Direct tar of repository (including .git)
  tar --transform "s,^,${TOPDIR}/," -czf "$ARCHIVE_PATH" .
else
  # Copy files to tmpdir, then tar
  rsync_cmd+=(./ "$TMPDIR/" )
  echo "Running: ${rsync_cmd[*]}"
  "${rsync_cmd[@]}"

  pushd "$TMPDIR" >/dev/null
  tar --transform "s,^,${TOPDIR}/," -czf "$ARCHIVE_PATH" .
  popd >/dev/null
fi

echo "Archive created: $ARCHIVE_PATH  ($(du -h "$ARCHIVE_PATH" | cut -f1))"

# Upload via scp
if [ -n "$SCP_TARGET" ]; then
  if ! command -v scp >/dev/null 2>&1; then
    echo "scp is not available; cannot upload" >&2; exit 3
  fi
  echo "Uploading via scp to $SCP_TARGET"
  scp "$ARCHIVE_PATH" "$SCP_TARGET"
  echo "scp upload complete"
fi

# Upload via aws s3
if [ -n "$S3_TARGET" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws CLI is not available; cannot upload to S3" >&2; exit 3
  fi
  echo "Uploading to S3: $S3_TARGET"
  aws s3 cp "$ARCHIVE_PATH" "$S3_TARGET"
  echo "S3 upload complete"
fi

# Rsync full workspace to remote dir (alternative to archive)
if [ -n "$RSYNC_TARGET" ]; then
  if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is not available; cannot rsync" >&2; exit 3
  fi
  echo "Rsync to $RSYNC_TARGET"
  # Reuse rsync_cmd to copy current directory to remote
  rsync_remote_cmd=(rsync -aH --compress)
  for ex in "${EXCLUDE_ARGS[@]}"; do
    rsync_remote_cmd+=(--exclude "${ex#--exclude=}")
  done
  rsync_remote_cmd+=(./ "$RSYNC_TARGET")
  echo "Running: ${rsync_remote_cmd[*]}"
  "${rsync_remote_cmd[@]}"
  echo "rsync complete"
fi

echo "Done."
