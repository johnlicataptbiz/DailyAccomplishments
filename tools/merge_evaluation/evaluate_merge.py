#!/usr/bin/env python3
"""
Evaluate a planned merge from a source directory into a destination git repository.
Generates a JSON report and a brief human-readable summary of potential conflicts,
new files, changed files, binary files, and optional test run output.

Usage:
  python evaluate_merge.py --source /path/to/DailyAccomplishments-1 --dest /path/to/DailyAccomplishments --report /tmp/merge_report.json [--run-tests]

This script is intentionally conservative and only reads files. It does not modify anything.
"""
import argparse
import os
import hashlib
import json
import filecmp
import difflib
import subprocess
import sys
from pathlib import Path

TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.json', '.yml', '.yaml', '.csv', '.html', '.js', '.css', '.sh', '.ini', '.cfg', '.toml'
}


def is_text_file(path: Path) -> bool:
    # Quick heuristic: extension check then try to read
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return True
    try:
        with open(path, 'rb') as f:
            chunk = f.read(4096)
            if b"\0" in chunk:
                return False
            # decode attempt
            try:
                chunk.decode('utf-8')
                return True
            except Exception:
                return False
    except Exception:
        return False


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def relative_files(root: Path):
    files = []
    for p in root.rglob('*'):
        if p.is_file():
            files.append(p.relative_to(root))
    return set(files)


def sample_text_diff(src_path: Path, dst_path: Path, max_lines=200):
    try:
        src = src_path.read_text(encoding='utf-8', errors='replace').splitlines()
        dst = dst_path.read_text(encoding='utf-8', errors='replace').splitlines()
        diff = list(difflib.unified_diff(dst[:max_lines], src[:max_lines], fromfile=str(dst_path), tofile=str(src_path), lineterm=''))
        return diff[:1000]  # limit large diffs
    except Exception as e:
        return [f"ERROR: Could not create diff: {e}"]


def run_tests(dest_root: Path):
    # Try pytest first, then nose/unittest discover
    out = {'success': None, 'cmd': None, 'stdout': '', 'stderr': ''}
    try:
        # prefer pytest if available
        cmd = ['pytest', '-q']
        out['cmd'] = ' '.join(cmd)
        proc = subprocess.run(cmd, cwd=str(dest_root), capture_output=True, text=True, timeout=300)
        out['stdout'] = proc.stdout
        out['stderr'] = proc.stderr
        out['success'] = (proc.returncode == 0)
        return out
    except FileNotFoundError:
        out['stderr'] = 'pytest not found'
        out['success'] = None
        return out
    except subprocess.TimeoutExpired:
        out['stderr'] = 'pytest timed out'
        out['success'] = False
        return out
    except Exception as e:
        out['stderr'] = str(e)
        out['success'] = False
        return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True, help='Source directory (to be merged from)')
    p.add_argument('--dest', required=True, help='Destination repository directory (to be merged into)')
    p.add_argument('--report', default='merge_report.json', help='Path to write JSON report')
    p.add_argument('--run-tests', action='store_true', help='Attempt to run tests in destination (optional)')
    p.add_argument('--sample-diff', action='store_true', help='Include small sample diffs for changed text files')
    args = p.parse_args()

    src = Path(args.source).expanduser().resolve()
    dst = Path(args.dest).expanduser().resolve()

    if not src.exists() or not src.is_dir():
        print('Source not found or not a directory:', src, file=sys.stderr)
        sys.exit(2)
    if not dst.exists() or not dst.is_dir():
        print('Destination not found or not a directory:', dst, file=sys.stderr)
        sys.exit(2)

    print(f'Inspecting source: {src}\n destination: {dst}')

    src_files = relative_files(src)
    dst_files = relative_files(dst)

    added = sorted([str(f) for f in (src_files - dst_files)])
    common = sorted([f for f in (src_files & dst_files)])
    removed = sorted([str(f) for f in (dst_files - src_files)])

    changed = []
    for f in common:
        s = src.joinpath(f)
        d = dst.joinpath(f)
        try:
            s_sha = sha1_of_file(s)
            d_sha = sha1_of_file(d)
            if s_sha != d_sha:
                entry = {'path': str(f), 'src_sha1': s_sha, 'dst_sha1': d_sha}
                entry['is_text'] = is_text_file(s) and is_text_file(d)
                if args.sample_diff and entry['is_text']:
                    entry['sample_diff'] = sample_text_diff(s, d)
                changed.append(entry)
        except Exception as e:
            changed.append({'path': str(f), 'error': str(e)})

    # Look for large binaries in additions
    large_files = []
    for f in added:
        p = src.joinpath(f)
        try:
            sz = p.stat().st_size
            if sz > 10 * 1024 * 1024:
                large_files.append({'path': f, 'size_bytes': sz})
        except Exception:
            pass

    # Simple sanity checks
    total_src = len(src_files)
    total_dst = len(dst_files)

    report = {
        'source': str(src),
        'destination': str(dst),
        'summary': {
            'src_file_count': total_src,
            'dst_file_count': total_dst,
            'added_files': len(added),
            'removed_files': len(removed),
            'changed_files': len(changed),
        },
        'added': added[:2000],
        'removed': removed[:2000],
        'changed': changed[:2000],
        'large_added_files': large_files,
    }

    if args.run_tests:
        print('Attempting to run tests in destination (may take a while)')
        report['tests'] = run_tests(dst)

    # write report
    rp = Path(args.report).expanduser().resolve()
    rp.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Report written to {rp}')

    # Print a brief human-readable summary
    print('\n==== Merge Evaluation Summary ====')
    print(f"Source files: {total_src}, Destination files: {total_dst}")
    print(f"New files to add: {len(added)}; Files that would be removed from destination: {len(removed)}")
    print(f"Files that differ and would be overwritten: {len(changed)}")
    if large_files:
        print('\nLarge files to be added (>10MB):')
        for lf in large_files:
            print(f" - {lf['path']} ({lf['size_bytes']/1024/1024:.1f} MB)")
    print('\nDetailed report saved as:', rp)


if __name__ == '__main__':
    main()
