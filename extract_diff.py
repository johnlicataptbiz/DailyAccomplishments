#!/usr/bin/env python3
"""
Extract and apply changes from a diff file intelligently.
Handles cases where files already exist or don't exist.
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

def parse_diff_file(diff_path):
    """Parse diff file and categorize changes."""
    with open(diff_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split by file changes
    file_changes = re.split(r'^diff --git ', content, flags=re.MULTILINE)[1:]
    
    results = {
        'new_files': [],
        'deleted_files': [],
        'modified_files': [],
        'binary_files': []
    }
    
    for change in file_changes:
        lines = change.split('\n')
        
        # Parse file paths from first line: a/path b/path
        match = re.match(r'a/(.*?) b/(.*?)$', lines[0])
        if not match:
            continue
        
        file_path = match.group(2)
        
        # Check if it's a new file
        if 'new file mode' in change[:500]:
            results['new_files'].append({
                'path': file_path,
                'content': extract_new_file_content(change)
            })
        # Check if it's a deleted file
        elif 'deleted file mode' in change[:500]:
            results['deleted_files'].append(file_path)
        # Check if it's binary
        elif 'Binary files' in change[:500]:
            results['binary_files'].append(file_path)
        # Otherwise it's a modification
        else:
            results['modified_files'].append({
                'path': file_path,
                'diff': change
            })
    
    return results

def extract_new_file_content(diff_chunk):
    """Extract content from a new file in diff format."""
    lines = diff_chunk.split('\n')
    content_lines = []
    in_content = False
    
    for line in lines:
        if line.startswith('@@'):
            in_content = True
            continue
        
        if in_content:
            if line.startswith('+'):
                # Remove the leading '+'
                content_lines.append(line[1:])
            elif line.startswith('\\'):
                # Handle "\ No newline at end of file"
                continue
    
    return '\n'.join(content_lines)

def main(diff_file, output_dir='.', dry_run=True):
    """Main extraction logic."""
    diff_path = Path(diff_file)
    output_path = Path(output_dir)
    
    if not diff_path.exists():
        print(f"Error: Diff file not found: {diff_path}")
        return 1
    
    print(f"Parsing diff file: {diff_path}")
    results = parse_diff_file(diff_path)
    
    print(f"\n{'='*60}")
    print(f"DIFF ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"New files:      {len(results['new_files'])}")
    print(f"Deleted files:  {len(results['deleted_files'])}")
    print(f"Modified files: {len(results['modified_files'])}")
    print(f"Binary files:   {len(results['binary_files'])}")
    print(f"{'='*60}\n")
    
    # Check which new files already exist
    existing_new = []
    missing_new = []
    
    for file_info in results['new_files']:
        target = output_path / file_info['path']
        if target.exists():
            existing_new.append(file_info['path'])
        else:
            missing_new.append(file_info['path'])
    
    if existing_new:
        print(f"\n⚠️  WARNING: {len(existing_new)} 'new' files already exist:")
        for path in existing_new[:10]:
            print(f"  - {path}")
        if len(existing_new) > 10:
            print(f"  ... and {len(existing_new) - 10} more")
    
    if missing_new:
        print(f"\n✅ {len(missing_new)} new files can be created:")
        for path in missing_new[:10]:
            print(f"  - {path}")
        if len(missing_new) > 10:
            print(f"  ... and {len(missing_new) - 10} more")
    
    # Check modified files
    existing_modified = []
    missing_modified = []
    
    for file_info in results['modified_files']:
        target = output_path / file_info['path']
        if target.exists():
            existing_modified.append(file_info['path'])
        else:
            missing_modified.append(file_info['path'])
    
    if missing_modified:
        print(f"\n⚠️  WARNING: {len(missing_modified)} files to modify don't exist:")
        for path in missing_modified[:10]:
            print(f"  - {path}")
        if len(missing_modified) > 10:
            print(f"  ... and {len(missing_modified) - 10} more")
    
    if dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No files were created or modified")
        print("Run with --apply to actually apply changes")
        print(f"{'='*60}")
        return 0
    
    # Apply changes
    print(f"\n{'='*60}")
    print("APPLYING CHANGES")
    print(f"{'='*60}\n")
    
    created = 0
    skipped = 0
    
    for file_info in results['new_files']:
        target = output_path / file_info['path']
        
        if target.exists():
            print(f"SKIP (exists): {file_info['path']}")
            skipped += 1
            continue
        
        # Create parent directories
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        target.write_text(file_info['content'], encoding='utf-8')
        print(f"CREATE: {file_info['path']}")
        created += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: Created {created} files, Skipped {skipped} existing files")
    print(f"{'='*60}")
    
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_diff.py <diff_file> [--apply]")
        print("  --apply: Actually create files (default is dry-run)")
        sys.exit(1)
    
    diff_file = sys.argv[1]
    apply = '--apply' in sys.argv
    
    sys.exit(main(diff_file, dry_run=not apply))
