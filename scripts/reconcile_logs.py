#!/usr/bin/env python3
"""Reconcile JSONL daily logs from backups and optional source paths into `logs/daily/`.

Usage:
  python3 scripts/reconcile_logs.py [--source <glob>] [--dest <path>] [--run-reports]

Features:
- Scans `logs.backup-*` and optional source path(s) for `*.jsonl` files.
- Copies missing JSONL files into `logs/daily/` without overwriting existing files.
- Optionally invokes `tools/generate_reports.py <date>` for any newly restored dates.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
import glob
import sys


def find_backup_jsonl(source_glob: str) -> list[Path]:
    paths = []
    for p in glob.glob(source_glob):
        pth = Path(p)
        if pth.is_dir():
            for f in pth.rglob('*.jsonl'):
                paths.append(f)
        elif pth.is_file() and pth.suffix == '.jsonl':
            paths.append(pth)
    return sorted(set(paths))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='logs.backup-*', help='Glob to search for backup folders/files')
    ap.add_argument('--dest', default='logs/daily', help='Destination directory for daily JSONL files')
    ap.add_argument('--run-reports', action='store_true', help='Run tools/generate_reports.py for restored dates')
    args = ap.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    found = find_backup_jsonl(args.source)
    if not found:
        print('No JSONL files found under', args.source)
        return 0

    restored_dates = []
    for src in found:
        dest = dest_dir / src.name
        if dest.exists():
            print('Skipping existing:', dest)
            continue
        try:
            shutil.copy2(src, dest)
            print('Restored:', dest)
            restored_dates.append(dest.stem)
        except Exception as e:
            print('Failed to copy', src, '->', dest, ':', e)

    if args.run_reports and restored_dates:
        for d in sorted(set(restored_dates)):
            print('Generating reports for', d)
            try:
                subprocess.run([sys.executable, 'tools/generate_reports.py', d], check=False)
            except Exception as e:
                print('Report generation failed for', d, e)

    print('Done. Restored dates:', restored_dates)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
