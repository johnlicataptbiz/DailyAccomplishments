#!/usr/bin/env bash
set -euo pipefail

# Import snapshots of every local branch (except the target branch) into
# subdirectories under imports/<branch-name> on the target branch.
#
# This avoids merge conflicts by copying the working tree of each branch
# into its own folder and committing that snapshot.

TARGET_BRANCH="codespace-consolidation"

echo "Switching to target branch: $TARGET_BRANCH"
git checkout "$TARGET_BRANCH"

mkdir -p imports

branches=$(git for-each-ref refs/heads --format='%(refname:short)')
echo "Found branches:"$'\n'"$branches"

for b in $branches; do
  if [ "$b" = "$TARGET_BRANCH" ]; then
    continue
  fi

  echo "\n--- Processing branch: $b ---"
  tmpdir=$(mktemp -d)
  echo "Creating archive of $b into $tmpdir"
  git archive "$b" | tar -x -C "$tmpdir"

  dest="imports/$b"
  # Remove any previous import for this branch so the snapshot is fresh
  rm -rf "$dest"
  mkdir -p "$dest"

  # Copy files from the archive into the destination
  cp -a "$tmpdir/." "$dest/" || true

  # Add and commit (if there are changes)
  git add "$dest"
  if git diff --cached --quiet; then
    echo "No changes to commit for $b"
  else
    git commit -m "Import snapshot from branch '$b' into '$dest'"
    echo "Committed import for $b"
  fi

  rm -rf "$tmpdir"
done

echo "\nAll branches processed. Review commits on $TARGET_BRANCH and push when ready."
