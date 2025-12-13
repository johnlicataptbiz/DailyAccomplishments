#!/usr/bin/env python3
"""
Validate ActivityReport JSON files against the repository schema.

Usage:
  python3 .github/scripts/validate_report_schema.py <path> [<path>...]
  python3 .github/scripts/validate_report_schema.py --changed

Exit codes:
  0: All selected files validate (or no changed report files when using --changed)
  2: Usage error, schema missing, missing file, or git diff failure
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
    return Path(__file__).resolve().parents[2]


def load_schema() -> dict:
    root = repo_root()
    schema_path = root / ".github" / "schemas" / "activity_report_schema.json"
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}")
        sys.exit(2)
    return json.loads(schema_path.read_text(encoding="utf-8"))


def git_changed_reports() -> list[str] | None:
    """
    Return list of changed ActivityReport json paths in this checkout.

    Returns None on git diff failure (treat as exit 2).
    """
    root = repo_root()
    base_ref = os.environ.get("GITHUB_BASE_REF", "").strip()
    github_sha = os.environ.get("GITHUB_SHA", "").strip()

    if base_ref:
        base = f"origin/{base_ref}"
        diff_range = f"{base}...HEAD"
        cmd = ["git", "diff", "--name-only", diff_range]
    elif github_sha:
        cmd = ["git", "diff", "--name-only", "HEAD^...HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "HEAD^...HEAD"]

    try:
        out = subprocess.check_output(
            cmd, cwd=str(root), text=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print("Failed to compute changed files via git diff.")
        print(e.output)
        return None

    paths = [line.strip() for line in out.splitlines() if line.strip()]
    report_paths = [p for p in paths if REPORT_RE.match(p)]
    report_paths.sort()
    return report_paths


def validate_file(path: str, validator: Draft7Validator) -> tuple[bool, bool]:
    """
    Returns (ok, usage_or_setup_error).
      - usage_or_setup_error=True for things like missing files or unreadable JSON.
      - ok=False, usage_or_setup_error=False means "validation failed" (exit code 3 category).
    """
    p = Path(path)
    if not p.is_absolute():
        p = repo_root() / p

    if not p.exists():
        print(f"MISSING: {p}")
        return (False, True)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Invalid JSON in {p}: {e}")
        return (False, True)

    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        print(f"Schema validation failed for {p}:")
        for e in errors[:50]:
            path_str = ".".join(map(str, e.path)) if e.path else "<root>"
            print(f" - {path_str}: {e.message}")
        return (False, False)

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
        return (False, False)

    print(f"VALID: {p}")
    return (True, False)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: validate_report_schema.py <path> [path2 ...] OR --changed")
        return 2

    schema = load_schema()
    validator = Draft7Validator(schema)

    args = argv[1:]
    if args == ["--changed"]:
        files = git_changed_reports()
        if files is None:
            return 2
        if not files:
            print("No changed ActivityReport JSON files to validate.")
            return 0
        print("Validating changed reports:")
        for f in files:
            print(f" - {f}")
    else:
        files = args

    any_usage_or_setup_error = False
    all_ok = True

    for f in files:
        ok, usage_or_setup_error = validate_file(f, validator)
        if usage_or_setup_error:
            any_usage_or_setup_error = True
        all_ok = all_ok and ok

    if any_usage_or_setup_error:
        return 2
    return 0 if all_ok else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
