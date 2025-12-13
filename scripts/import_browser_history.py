#!/usr/bin/env python3
"""
Import browser history for a given date and update ActivityReport-YYYY-MM-DD.json.

Chrome: reads from the newest available Chrome profile History DB
Safari: reads from Safari History.db (if available)

This script is the ONLY trusted source for browser_highlights.
Do not infer domains from window titles in generate_daily_json.py.
"""

import argparse
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

CHROME_BASE = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
SAFARI_DB = Path.home() / "Library" / "Safari" / "History.db"


def _chrome_history_candidates() -> list[Path]:
    candidates = []
    if not CHROME_BASE.exists():
        return candidates
    for p in CHROME_BASE.iterdir():
        if not p.is_dir():
            continue
        if p.name == "Default" or p.name.startswith("Profile "):
            h = p / "History"
            if h.exists():
                candidates.append(h)
    return candidates


def _pick_newest_chrome_history() -> Path | None:
    candidates = _chrome_history_candidates()
    if not candidates:
        return None
    # pick by mtime (most recently updated)
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def _copy_sqlite(src: Path) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="da-browser-"))
    dst = tmpdir / src.name
    shutil.copy2(src, dst)
    return dst


def _read_chrome_urls_for_date(date_str: str) -> list[str]:
    history = _pick_newest_chrome_history()
    if not history:
        return []

    db_path = _copy_sqlite(history)
    start = datetime.fromisoformat(date_str)
    end = start + timedelta(days=1)

    def to_chrome_time(dt: datetime) -> int:
        # Chrome stores microseconds since 1601-01-01
        epoch = datetime(1601, 1, 1)
        return int((dt - epoch).total_seconds() * 1_000_000)

    start_us = to_chrome_time(start)
    end_us = to_chrome_time(end)

    urls: list[str] = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            """
            SELECT urls.url
            FROM visits
            JOIN urls ON visits.url = urls.id
            WHERE visits.visit_time >= ? AND visits.visit_time < ?
            """,
            (start_us, end_us),
        )
        rows = cur.fetchall()
        urls = [r[0] for r in rows if r and r[0]]
        conn.close()
    except Exception:
        urls = []
    return urls


def _read_safari_urls_for_date(date_str: str) -> list[str]:
    if not SAFARI_DB.exists():
        return []

    db_path = _copy_sqlite(SAFARI_DB)
    start = datetime.fromisoformat(date_str)
    end = start + timedelta(days=1)

    urls: list[str] = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # Safari uses CoreData timestamps; easiest is to filter by visit date strings if present.
        # We'll do a best-effort query that works on common Safari schemas.
        cur.execute(
            """
            SELECT history_items.url
            FROM history_visits
            JOIN history_items ON history_visits.history_item = history_items.id
            WHERE history_visits.visit_time >= ? AND history_visits.visit_time < ?
            """,
            (start.timestamp(), end.timestamp()),
        )
        rows = cur.fetchall()
        urls = [r[0] for r in rows if r and r[0]]
        conn.close()
    except Exception:
        urls = []
    return urls


def _domain(url: str) -> str | None:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


def _load_report(repo: Path, date_str: str) -> tuple[Path, dict]:
    f = repo / f"ActivityReport-{date_str}.json"
    if not f.exists():
        raise SystemExit(f"Missing report: {f}")
    return f, json.loads(f.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--repo", default=str(Path(__file__).parent.parent))
    ap.add_argument("--update-report", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo)
    date_str = args.date

    chrome_urls = _read_chrome_urls_for_date(date_str)
    safari_urls = _read_safari_urls_for_date(date_str)
    urls = chrome_urls + safari_urls

    print(f"Importing browser history for {date_str}...")
    print(f"  Chrome: {len(chrome_urls)} entries")
    print(f"  Safari: {len(safari_urls)} entries")
    print(f"  Total: {len(urls)} entries")

    if not urls:
        print("No browser history found for this date.")
        return

    domains = [d for d in (_domain(u) for u in urls) if d]
    top_domains = Counter(domains).most_common(10)
    top_pages = Counter(urls).most_common(10)

    report_path, report = _load_report(repo, date_str)
    report["browser_highlights"] = {
        "top_domains": [{"domain": d, "visits": n} for d, n in top_domains],
        "top_pages": [{"page": p, "visits": n} for p, n in top_pages],
    }

    if args.update_report:
        report_path.write_text(json.dumps(report, indent=2))
        print(f"Updated {report_path}")


if __name__ == "__main__":
    main()
