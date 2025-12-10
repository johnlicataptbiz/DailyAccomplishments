#!/usr/bin/env python3
"""Validate ActivityReport JSON files against the repository schema.

Usage: python3 .github/scripts/validate_report_schema.py <path> [<path>...]
Exits with code 0 when all files validate, non-zero otherwise.
"""
import sys
import json
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except Exception as e:
    print("Missing dependency 'jsonschema'. Install with: pip install jsonschema")
    raise


def load_schema():
    # Resolve repository root reliably: script is at .github/scripts/
    here = Path(__file__).resolve().parents[2]
    schema_path = here / ".github" / "schemas" / "activity_report_schema.json"
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}")
        sys.exit(2)
    return json.loads(schema_path.read_text())


def validate_file(path, validator):
    p = Path(path)
    if not p.exists():
        print(f"MISSING: {p}")
        return False
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        print(f"Invalid JSON in {p}: {e}")
        return False
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print(f"Schema validation failed for {p}:")
        for e in errors[:50]:
            path = ".".join(map(str, e.path)) if e.path else "<root>"
            print(f" - {path}: {e.message}")
        return False
    # Additional stricter checks beyond Draft7 schema to make CI failures clearer
    # Ensure overview contains expected timing fields
    ok = True
    if 'overview' not in data or not isinstance(data['overview'], dict):
        print(f" - overview: missing or not an object in {p}")
        ok = False
    else:
        for key in ('focus_time', 'coverage_window'):
            if key not in data['overview']:
                print(f" - overview.{key}: missing in {p}")
                ok = False
    # Validate deep_work_blocks items if present
    if 'deep_work_blocks' in data:
        if not isinstance(data['deep_work_blocks'], list):
            print(f" - deep_work_blocks: expected array in {p}")
            ok = False
        else:
            for i, item in enumerate(data['deep_work_blocks']):
                if not isinstance(item, dict):
                    print(f" - deep_work_blocks[{i}]: not an object in {p}")
                    ok = False
                    continue
                for rk in ('start', 'end', 'duration', 'seconds'):
                    if rk not in item:
                        print(f" - deep_work_blocks[{i}].{rk}: missing in {p}")
                        ok = False
                if 'seconds' in item and not isinstance(item['seconds'], (int, float)):
                    print(f" - deep_work_blocks[{i}].seconds: must be number in {p}")
                    ok = False
    if not ok:
        return False
    print(f"VALID: {p}")
    return True


def main(argv):
    if len(argv) < 2:
        print("Usage: validate_report_schema.py <path> [path2 ...]")
        return 2
    schema = load_schema()
    validator = Draft7Validator(schema)
    all_ok = True
    for p in argv[1:]:
        ok = validate_file(p, validator)
        all_ok = all_ok and ok
    return 0 if all_ok else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv))