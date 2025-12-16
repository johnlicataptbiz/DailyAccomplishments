#!/usr/bin/env python3
import os, re, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

ROOT_REPORT_RE = re.compile(r"^ActivityReport-\d{4}-\d{2}-\d{2}\.json$")
DATED_ASSET_RE = re.compile(r"^reports/\d{4}-\d{2}-\d{2}/.*\.(json|csv|svg|md|txt)$")

def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=REPO, text=True).strip()

def bytes_from_git(ref: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=REPO)

def ensure_parent(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def main():
    os.chdir(REPO)

    refs = run(["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"]).splitlines()
    refs = [r for r in refs if r and r != "origin/HEAD"]

    added = 0
    skipped = 0

    for ref in refs:
        paths = run(["git", "ls-tree", "-r", "--name-only", ref]).splitlines()

        for path in paths:
            if not (DATED_ASSET_RE.match(path) or ROOT_REPORT_RE.match(path)):
                continue

            dest_paths = [path]

            m = re.match(r"^ActivityReport-(\d{4}-\d{2}-\d{2})\.json$", path)
            if m:
                ds = m.group(1)
                dest_paths.append(f"reports/{ds}/{path}")

            for dp in dest_paths:
                out = REPO / dp
                if out.exists():
                    skipped += 1
                    continue

                try:
                    content = bytes_from_git(ref, path)
                except subprocess.CalledProcessError:
                    skipped += 1
                    continue

                ensure_parent(out)
                out.write_bytes(content)
                added += 1

    print(f"Done. added_files={added} skipped_existing_or_unreadable={skipped}")

if __name__ == "__main__":
    main()
