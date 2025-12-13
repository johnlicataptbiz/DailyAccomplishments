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


def validate_file(path, validator, debug=False):
    """Validate a single report file against the schema.
    
    Args:
        path: Path to the JSON report file
        validator: JSONSchema validator instance
        debug: Enable verbose debug output
        
    Returns:
        bool: True if validation passes, False otherwise
    """
    p = Path(path)
    
    if debug:
        print(f"[DEBUG] Validating: {p}")
        
    if not p.exists():
        print(f"MISSING: {p}")
        return False
    
    if debug:
        file_size = p.stat().st_size
        print(f"[DEBUG] File size: {file_size} bytes")
        
    try:
        data = json.loads(p.read_text())
        if debug:
            print(f"[DEBUG] JSON parsed successfully")
            print(f"[DEBUG] Top-level keys: {list(data.keys())}")
    except Exception as e:
        print(f"Invalid JSON in {p}: {e}")
        return False
    
    # Run schema validation
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        print(f"Schema validation failed for {p}:")
        for e in errors[:50]:
            path_str = ".".join(map(str, e.path)) if e.path else "<root>"
            print(f" - {path_str}: {e.message}")
        if len(errors) > 50:
            print(f" ... and {len(errors) - 50} more errors")
        return False
    
    if debug:
        print(f"[DEBUG] Schema validation passed")
    
    # Additional stricter checks beyond Draft7 schema to make CI failures clearer
    # Ensure overview contains expected timing fields
    ok = True
    if 'overview' not in data or not isinstance(data['overview'], dict):
        print(f" - overview: missing or not an object in {p}")
        ok = False
    else:
        if debug:
            print(f"[DEBUG] Overview keys: {list(data['overview'].keys())}")
        for key in ('focus_time', 'coverage_window'):
            if key not in data['overview']:
                print(f" - overview.{key}: missing in {p}")
                ok = False
            elif debug:
                print(f"[DEBUG] overview.{key} = {data['overview'][key]}")
    
    # Validate deep_work_blocks items if present
    if 'deep_work_blocks' in data:
        if not isinstance(data['deep_work_blocks'], list):
            print(f" - deep_work_blocks: expected array in {p}")
            ok = False
        else:
            if debug:
                print(f"[DEBUG] deep_work_blocks: {len(data['deep_work_blocks'])} items")
            for i, item in enumerate(data['deep_work_blocks']):
                if not isinstance(item, dict):
                    print(f" - deep_work_blocks[{i}]: not an object in {p}")
                    ok = False
                    continue
                for rk in ('start', 'end', 'duration', 'seconds'):
                    if rk not in item:
                        print(f" - deep_work_blocks[{i}].{rk}: missing in {p}")
                        ok = False
                    elif debug and i < 3:  # Only print first 3 for brevity
                        print(f"[DEBUG] deep_work_blocks[{i}].{rk} = {item[rk]}")
                if 'seconds' in item and not isinstance(item['seconds'], (int, float)):
                    print(f" - deep_work_blocks[{i}].seconds: must be number in {p}")
                    ok = False
    
    if not ok:
        return False
    print(f"VALID: {p}")
    return True


def main(argv):
    """Main entry point for the validation script."""
    debug = '--debug' in argv or '-v' in argv
    
    # Filter out debug flags from paths
    paths = [arg for arg in argv[1:] if not arg.startswith('-')]
    
    if len(paths) < 1:
        print("Usage: validate_report_schema.py <path> [path2 ...] [--debug|-v]")
        return 2
    
    if debug:
        print(f"[DEBUG] Debug mode enabled")
        print(f"[DEBUG] Validating {len(paths)} file(s)")
    
    schema = load_schema()
    if debug:
        print(f"[DEBUG] Schema loaded successfully")
        
    validator = Draft7Validator(schema)
    all_ok = True
    
    for i, p in enumerate(paths, 1):
        if debug:
            print(f"\n[DEBUG] === Validating file {i}/{len(paths)} ===")
        ok = validate_file(p, validator, debug=debug)
        all_ok = all_ok and ok
    
    if debug:
        print(f"\n[DEBUG] === Summary ===")
        print(f"[DEBUG] Total files: {len(paths)}")
        print(f"[DEBUG] Result: {'ALL VALID' if all_ok else 'SOME FAILED'}")
    
    return 0 if all_ok else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv))
