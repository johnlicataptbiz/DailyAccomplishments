#!/bin/bash
# Script to delete old branches that are safe to remove
# Usage: ./delete_old_branches.sh [--dry-run] [--high-priority-only]

set -euo pipefail

DRY_RUN=false
HIGH_PRIORITY_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --high-priority-only)
      HIGH_PRIORITY_ONLY=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run] [--high-priority-only]"
      exit 1
      ;;
  esac
done

# High priority branches (safe to delete)
HIGH_PRIORITY_BRANCHES=(
  # Merge conflict fixes
  "codex/fix-codex-review-issues-in-pull-request-#12"
  "codex/fix-codex-review-issues-in-pull-request-#12-zb1pn2"
  "copilot/fix-merge-conflict-in-validate-report-schema"
  "copilot/fix-merge-conflicts-in-reports"
  
  # Setup/Documentation
  "copilot/set-up-copilot-instructions"
  "copilot/set-up-copilot-instructions-again"
  "copilot/copy-repo-to-dailyaccomplishments"
  "codex/document-manual-merge-via-command-line"
  
  # Bug fixes
  "codex/fix-.gitattributes-trailing-whitespace-rule"
  "copilot/fix-trailing-whitespace-errors"
  "copilot/fix-launch-json-errors"
  "copilot/fix-invalid-image-name"
  "codex/add-workflow-badge-for-deployment"
  "codex/add-workflow-badge-for-deployment-pdcnqh"
  
  # CI/Workflow fixes
  "copilot/ci-fix-and-gh-actions"
  "copilot/fix-codeql-workflow-dockerfile"
  "copilot/fix-codeql-language-matrix"
  
  # Old implementation
  "copilot/continue-implementation"
  "copilot/execute-notebook"
  "copilot/create-task-list-from-notebook"
  "copilot/continue-task-list-work"
  "copilot/update-instruction-files"
  
  # Codespace cleanup
  "codespace-consolidation"
  "codespace-consolidation-backup-20251211T012527Z"
  "codespace-consolidation-local-20251210"
  "codespace-consolidation-reconciled"
)

echo "=========================================="
echo "Branch Deletion Script"
echo "=========================================="
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "🔍 DRY RUN MODE - No branches will be deleted"
  echo ""
fi

if [ "$HIGH_PRIORITY_ONLY" = true ]; then
  echo "📋 HIGH PRIORITY ONLY - Only deleting safe branches"
  echo ""
fi

echo "Branches to be deleted: ${#HIGH_PRIORITY_BRANCHES[@]}"
echo ""

deleted_count=0
failed_count=0
skipped_count=0

for branch in "${HIGH_PRIORITY_BRANCHES[@]}"; do
  # Check if branch exists using proper exit code check
  if ! git ls-remote --exit-code --heads origin "$branch" > /dev/null 2>&1; then
    echo "⏭️  Skipping: $branch (doesn't exist)"
    skipped_count=$((skipped_count + 1))
    continue
  fi
  
  if [ "$DRY_RUN" = true ]; then
    echo "🔍 Would delete: $branch"
    deleted_count=$((deleted_count + 1))
  else
    echo "🗑️  Deleting: $branch"
    # Properly quote branch name to handle special characters
    if git push origin --delete "$branch"; then
      echo "   ✓ Deleted successfully"
      deleted_count=$((deleted_count + 1))
    else
      echo "   ✗ Failed to delete"
      failed_count=$((failed_count + 1))
    fi
  fi
  echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Total branches processed: ${#HIGH_PRIORITY_BRANCHES[@]}"
if [ "$DRY_RUN" = true ]; then
  echo "Would delete: $deleted_count"
else
  echo "Successfully deleted: $deleted_count"
  echo "Failed to delete: $failed_count"
fi
echo "Skipped (not found): $skipped_count"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "To actually delete these branches, run:"
  echo "  $0"
  echo ""
  echo "Or to use GitHub CLI (if available):"
  echo "  See pr_closure_recommendations.md for branch list"
fi

exit 0
