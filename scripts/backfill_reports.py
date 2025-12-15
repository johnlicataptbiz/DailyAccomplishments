#!/usr/bin/env python3
"""
Backfill ActivityReport JSONs over a date range using real local logs (no placeholders).

This tool:
- Scans one or more log roots for JSONL activity logs for each date
- Generates ActivityReport-YYYY-MM-DD.json via scripts/generate_daily_json.py
- Optionally runs scripts/archive_outputs.sh to ensure reports/<date>/... exists

It will NOT generate output for days without a matching log file.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "scripts" / "generate_daily_json.py"
ARCHIVER = REPO_ROOT / "scripts" / "archive_outputs.sh"


def parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date: {s} (expected YYYY-MM-DD)") from e


def date_range(start: date, end: date) -> Iterable[date]:
    if end < start:
        return []
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


@dataclass(frozen=True)
class LogMatch:
    logs_root: Path
    log_file: Path


def find_log_for_date(logs_root: Path, date_str: str) -> Optional[LogMatch]:
    candidates = [
        # logs_root may itself be a daily/ folder
        logs_root / f"{date_str}.jsonl",
        logs_root / f"activity-{date_str}.jsonl",
        logs_root / "daily" / f"{date_str}.jsonl",
        logs_root / "daily" / f"activity-{date_str}.jsonl",
        # recovered/legacy layouts
        logs_root / "activity" / f"activity-{date_str}.jsonl",
        logs_root / "activity" / f"{date_str}.jsonl",
    ]
    for p in candidates:
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return LogMatch(logs_root=logs_root, log_file=p)
    return None


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return int(proc.returncode)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Backfill ActivityReport JSONs using local logs (no placeholders).")
    parser.add_argument("--start", required=True, type=parse_date, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, type=parse_date, help="End date (YYYY-MM-DD).")
    parser.add_argument(
        "--logs-root",
        action="append",
        default=[],
        help="Logs root directory to scan (repeatable). Defaults: ./logs and any ./logs.backup-*/ directories.",
    )
    parser.add_argument(
        "--include-backups",
        action="store_true",
        help="Also scan ./logs.backup-*/ as additional log roots.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if reports/<date>/ActivityReport-<date>.json already exists.",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Run scripts/archive_outputs.sh for each generated date (recommended).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing files.",
    )
    args = parser.parse_args(argv)

    if not GENERATOR.exists():
        print(f"ERROR: missing generator: {GENERATOR}", file=sys.stderr)
        return 2

    logs_roots: list[Path] = []
    if args.logs_root:
        logs_roots.extend([Path(p).expanduser().resolve() for p in args.logs_root])
    else:
        logs_roots.append((REPO_ROOT / "logs").resolve())
        if args.include_backups:
            logs_roots.extend(sorted(REPO_ROOT.glob("logs.backup-*")))

    generated: list[str] = []
    missing: list[str] = []

    for d in date_range(args.start, args.end):
        ds = d.isoformat()
        out = REPO_ROOT / "reports" / ds / f"ActivityReport-{ds}.json"
        if out.exists() and not args.force:
            continue

        match = None
        for root in logs_roots:
            match = find_log_for_date(root, ds)
            if match:
                break

        if not match:
            missing.append(ds)
            continue

        print(f"[backfill] {ds} logs={match.log_file}")
        if args.dry_run:
            generated.append(ds)
            continue

        rc = run([sys.executable, str(GENERATOR), ds, "--logs-dir", str(match.logs_root)])
        if rc != 0:
            print(f"[backfill] ERROR generating {ds} (rc={rc})", file=sys.stderr)
            return rc

        if args.archive and ARCHIVER.exists():
            run(["/bin/bash", str(ARCHIVER), ds])

        generated.append(ds)

    print("")
    print(f"[backfill] generated={len(generated)} missing_logs={len(missing)}")
    if missing:
        print("[backfill] missing log dates:")
        for ds in missing:
            print(f"  - {ds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
