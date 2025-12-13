#!/usr/bin/env python3
"""
Validate ActivityReport JSON files against the repository schema.

Usage:
  python3 .github/scripts/validate_report_schema.py <path> [<path>...]
  python3 .github/scripts/validate_report_schema.py --changed

Exit codes:
  0: All selected files validate (or no changed report files when using --changed)
  2: Usage error, schema missing, or unable to compute changed files
  3: One or more selected files failed validation
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except Exception:
    print("Missing dependency 'jsonschema'. Install with: pip install jsonschema")
    raise


REPORT_RE = re.compile(r"^reports/[^/]+/ActivityReport-.*\.json$")


def repo_root() -> Path:
    # Script is at .github/scripts/ -> parents[2] is repo root
    return Path(__file__).resolve().parents[2]


def load_schema() -> dict:
    root = repo_root()
    schema_path = root / ".github" / "schemas" / "activity_report_schema.json"
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}")
        sys.exit(2)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _run_git_diff_name_only(diff_range: str) -> list[str]:
    root = repo_root()
    cmd = ["git", "diff", "--name-only", diff_range]
    out = subprocess.check_output(cmd, cwd=str(root), text=True, stderr=subprocess.STDOUT)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _ensure_commit_present(commit: str) -> None:
    """
    Ensure a commit object exists locally. If not, try to fetch it.
    This helps in shallow checkouts where base commits are missing.
    """
    root = repo_root()

    def has_object() -> bool:
        try:
            subprocess.check_output(
                ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                cwd=str(root),
                text=True,
                stderr=subprocess.STDOUT,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    if has_object():
        return

    # Try to fetch the commit object directly (works in most Actions contexts).
    try:
        subprocess.check_output(
            ["git", "fetch", "--no-tags", "--depth=200", "origin", commit],
            cwd=str(root),
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Could not fetch missing commit {commit}:\n{e.output}") from e

    if not has_object():
        raise RuntimeError(f"Commit {commit} is still missing after fetch.")


def git_changed_reports() -> list[str]:
    """
    Return list of changed ActivityReport json paths in this checkout.

    Robust order of operations:
      1) Prefer GitHub Actions PR SHAs: GITHUB_BASE_SHA...GITHUB_SHA
      2) If base SHA not available, try origin/<GITHUB_BASE_REF>...HEAD
      3) Last resort: HEAD^...HEAD

    If we cannot compute a diff, raise so caller can exit 2.
    """
    base_sha = os.environ.get("GITHUB_BASE_SHA", "").strip()
    head_sha = os.environ.get("GITHUB_SHA", "").strip()
    base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()

    # 1) Best: explicit base and head SHAs (works even in PR merge commits).
    if base_sha and head_sha:
        _ensure_commit_present(base_sha)
        _ensure_commit_present(head_sha)
        diff_range = f"{base_sha}...{head_sha}"
        paths = _run_git_diff_name_only(diff_range)
    # 2) Next: diff against base branch ref if available.
    elif base_ref:
        diff_range = f"origin/{base_ref}...HEAD"
        try:
            paths = _run_git_diff_name_only(diff_range)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"git diff failed for range {diff_range}. "
                f"Consider setting actions/checkout fetch-depth: 0.\n{e.output}"
            ) from e
    # 3) Fallback: just compare last commit.
    else:
        diff_range = "HEAD^...HEAD"
        paths = _run_git_diff_name_only(diff_range)

    report_paths = [p for p in paths if REPORT_RE.match(p)]
    report_paths.sort()
    return report_paths


def validate_file(path: str, validator: Draft7Validator) -> bool:
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p

    if not p.exists():
        print(f"MISSING: {p}")
        return False

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Invalid JSON in {p}: {e}")
        return False

    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        print(f"Schema validation failed for {p}:")
        for e in errors[:50]:
            path_str = ".".join(map(str, e.path)) if e.path else "<root>"
            print(f" - {path_str}: {e.message}")
        return False

    # Additional stricter checks beyond Draft7 schema to make CI failures clearer
    ok = True

    if "overview" not in data or not isinstance(data["overview"], dict):
        print(f" - overview: missing or not an object in {p}")
        ok = False
    else:
        for key in ("focus_time", "coverage_window"):
            if key not in data["overview"]:
                print(f" - overview.{key}: missing in {p}")
                ok = False

    if "deep_work_blocks" in data:
        if not isinstance(data["deep_work_blocks"], list):
            print(f" - deep_work_blocks: expected array in {p}")
            ok = False
        else:
            for i, item in enumerate(data["deep_work_blocks"]):
                if not isinstance(item, dict):
                    print(f" - deep_work_blocks[{i}]: not an object in {p}")
                    ok = False
                    continue
                for rk in ("start", "end", "duration", "seconds"):
                    if rk not in item:
                        print(f" - deep_work_blocks[{i}].{rk}: missing in {p}")
                        ok = False
                if "seconds" in item and not isinstance(item["seconds"], (int, float)):
                    print(f" - deep_work_blocks[{i}].seconds: must be number in {p}")
                    ok = False

    if not ok:
        return False

    print(f"VALID: {p}")
    return True


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: validate_report_schema.py <path> [path2 ...] OR --changed")
        return 2

    schema = load_schema()
    validator = Draft7Validator(schema)

    args = argv[1:]
    if args == ["--changed"]:
        try:
            files = git_changed_reports()
        except Exception as e:
            print("Failed to determine changed report files.")
            print(str(e))
            return 2

        if not files:
            print("No changed ActivityReport JSON files to validate.")
            return 0

        print("Validating changed reports:")
        for f in files:
            print(f" - {f}")
    else:
        files = args

    all_ok = True
    for f in files:
        ok = validate_file(f, validator)
        all_ok = all_ok and ok

    return 0 if all_ok else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))