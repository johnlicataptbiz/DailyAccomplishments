#!/usr/bin/env python3
"""
Script to analyze branches and identify which ones are safe to close.
"""

import subprocess
import json
import os
from datetime import datetime
from typing import List, Dict, Tuple

def run_git_command(cmd: List[str], cwd: str = None) -> str:
    """Run a git command and return its output."""
    if cwd is None:
        cwd = os.getcwd()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return ""

def get_all_remote_branches() -> List[str]:
    """Get list of all remote branches."""
    output = run_git_command(['git', 'ls-remote', '--heads', 'origin'])
    branches = []
    for line in output.split('\n'):
        if line:
            parts = line.split()
            if len(parts) >= 2:
                branch_name = parts[1].replace('refs/heads/', '')
                branches.append(branch_name)
    return branches

def get_branch_info(branch: str) -> Dict:
    """Get detailed information about a branch."""
    # Get commit hash
    commit_hash = run_git_command(['git', 'ls-remote', 'origin', f'refs/heads/{branch}'])
    if commit_hash:
        commit_hash = commit_hash.split()[0]
    
    # Check if branch is merged into main
    # Fetch the branch first
    run_git_command(['git', 'fetch', 'origin', f'{branch}:refs/remotes/origin/{branch}'])
    
    # Check if merged
    merged_branches = run_git_command(['git', 'branch', '-r', '--merged', 'origin/main'])
    is_merged = f'origin/{branch}' in merged_branches
    
    # Get last commit date and message in one call
    if commit_hash:
        commit_info = run_git_command(['git', 'log', '-1', '--format=%ci|%s', commit_hash])
        if '|' in commit_info:
            commit_date, commit_msg = commit_info.split('|', 1)
        else:
            commit_date, commit_msg = "", ""
    else:
        commit_date, commit_msg = "", ""
    
    # Check if branch is ahead/behind main
    if commit_hash:
        ahead_behind = run_git_command(['git', 'rev-list', '--left-right', '--count', f'{commit_hash}...origin/main'])
        if ahead_behind:
            parts = ahead_behind.split()
            ahead = int(parts[0]) if len(parts) > 0 else 0
            behind = int(parts[1]) if len(parts) > 1 else 0
        else:
            ahead, behind = 0, 0
    else:
        ahead, behind = 0, 0
    
    return {
        'branch': branch,
        'commit_hash': commit_hash[:8] if commit_hash else 'unknown',
        'is_merged': is_merged,
        'commit_date': commit_date,
        'commit_message': commit_msg,
        'ahead_of_main': ahead,
        'behind_main': behind
    }

def categorize_branches(branches: List[str]) -> Dict[str, List[str]]:
    """Categorize branches by prefix."""
    categories = {
        'codex': [],
        'copilot': [],
        'feature': [],
        'archive': [],
        'codespace': [],
        'integrate': [],
        'rebuild': [],
        'salvage': [],
        'special': [],  # main, gh-pages, etc.
        'other': []
    }
    
    for branch in branches:
        if branch in ['main', 'gh-pages', 'reports-gh-pages']:
            categories['special'].append(branch)
        elif branch.startswith('codex/'):
            categories['codex'].append(branch)
        elif branch.startswith('copilot/'):
            categories['copilot'].append(branch)
        elif branch.startswith('feature/'):
            categories['feature'].append(branch)
        elif branch.startswith('archive/'):
            categories['archive'].append(branch)
        elif branch.startswith('codespace'):
            categories['codespace'].append(branch)
        elif branch.startswith('integrate/'):
            categories['integrate'].append(branch)
        elif branch.startswith('rebuild/'):
            categories['rebuild'].append(branch)
        elif branch.startswith('salvage/'):
            categories['salvage'].append(branch)
        else:
            categories['other'].append(branch)
    
    return categories

def main():
    print("Analyzing branches for DailyAccomplishments repository...")
    print("=" * 80)
    
    # Get all branches
    all_branches = get_all_remote_branches()
    print(f"\nTotal branches: {len(all_branches)}")
    
    # Categorize branches
    categories = categorize_branches(all_branches)
    
    print("\nBranches by category:")
    for category, branches in categories.items():
        if branches:
            print(f"  {category}: {len(branches)}")
    
    # Analyze each branch
    print("\n" + "=" * 80)
    print("Analyzing branch status (this may take a moment)...")
    print("=" * 80)
    
    merged_branches = []
    unmerged_branches = []
    
    for branch in all_branches:
        if branch in ['main', 'gh-pages', 'reports-gh-pages']:
            continue  # Skip special branches
        
        info = get_branch_info(branch)
        
        if info['is_merged']:
            merged_branches.append(info)
        else:
            unmerged_branches.append(info)
    
    # Report merged branches (safe to delete)
    print(f"\n{'=' * 80}")
    print(f"MERGED BRANCHES (Safe to delete - {len(merged_branches)} total)")
    print(f"{'=' * 80}\n")
    
    for info in sorted(merged_branches, key=lambda x: x['branch']):
        print(f"✓ {info['branch']}")
        print(f"  Commit: {info['commit_hash']} - {info['commit_message'][:60]}")
        print(f"  Date: {info['commit_date']}")
        print()
    
    # Report unmerged branches (need review)
    print(f"\n{'=' * 80}")
    print(f"UNMERGED BRANCHES (Need review - {len(unmerged_branches)} total)")
    print(f"{'=' * 80}\n")
    
    for info in sorted(unmerged_branches, key=lambda x: x['branch']):
        status = ""
        if info['ahead_of_main'] > 0:
            status = f"{info['ahead_of_main']} commits ahead"
        if info['behind_main'] > 0:
            if status:
                status += f", {info['behind_main']} behind"
            else:
                status = f"{info['behind_main']} commits behind"
        
        print(f"⚠ {info['branch']}")
        print(f"  Commit: {info['commit_hash']} - {info['commit_message'][:60]}")
        print(f"  Date: {info['commit_date']}")
        print(f"  Status: {status}")
        print()
    
    # Summary and recommendations
    print(f"\n{'=' * 80}")
    print("SUMMARY & RECOMMENDATIONS")
    print(f"{'=' * 80}\n")
    
    print(f"Total branches analyzed: {len(all_branches) - 3}")  # Excluding main, gh-pages, reports-gh-pages
    print(f"Merged (safe to delete): {len(merged_branches)}")
    print(f"Unmerged (need review): {len(unmerged_branches)}")
    
    print("\nRECOMMENDATIONS:")
    print("\n1. SAFE TO DELETE (merged into main):")
    if merged_branches:
        for info in sorted(merged_branches, key=lambda x: x['branch']):
            print(f"   - {info['branch']}")
    else:
        print("   None found")
    
    print("\n2. ARCHIVE BRANCHES:")
    archive_branches = [b for b in unmerged_branches if b['branch'].startswith('archive/') or b['branch'].startswith('salvage/')]
    if archive_branches:
        print("   These appear to be intentional archives - keep unless confirmed obsolete:")
        for info in archive_branches:
            print(f"   - {info['branch']}")
    
    print("\n3. CODESPACE BRANCHES:")
    codespace_branches = [b for b in unmerged_branches if 'codespace' in b['branch']]
    if codespace_branches:
        print("   These are codespace snapshots - likely safe to delete if codespace is closed:")
        for info in codespace_branches:
            print(f"   - {info['branch']}")
    
    print("\n4. FEATURE/FIX BRANCHES (unmerged):")
    active_branches = [b for b in unmerged_branches 
                      if not b['branch'].startswith('archive/') 
                      and not b['branch'].startswith('salvage/')
                      and 'codespace' not in b['branch']]
    if active_branches:
        print("   These need manual review to determine if work should be completed or abandoned:")
        for info in sorted(active_branches, key=lambda x: x['commit_date'], reverse=True)[:10]:
            print(f"   - {info['branch']} (last update: {info['commit_date'][:10]})")
    
    # Save to file
    report = {
        'generated_at': datetime.now().isoformat(),
        'total_branches': len(all_branches),
        'merged_branches': [b['branch'] for b in merged_branches],
        'unmerged_branches': [b['branch'] for b in unmerged_branches],
        'categories': {k: v for k, v in categories.items() if v}
    }
    
    with open('branch_analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print("Full report saved to: branch_analysis_report.json")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
