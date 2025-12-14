#!/usr/bin/env python3
import json
import sys

def main(path):
    try:
        with open(path, 'r') as f:
            j = json.load(f)
    except Exception as e:
        print('INVALID JSON:', e)
        return 2
    # overview.focus_time must exist
    if not isinstance(j.get('overview'), dict) or 'focus_time' not in j.get('overview', {}):
        print('INVALID STRUCTURE: overview.focus_time missing in', path)
        return 3
    # hourly_focus should be a list of 24 entries
    hf = j.get('hourly_focus', [])
    if not isinstance(hf, list) or len(hf) != 24:
        print('INVALID STRUCTURE: hourly_focus must be a list of 24 items in', path)
        return 4
    # top_domains should be list (may be empty)
    td = j.get('browser_highlights', {}).get('top_domains', [])
    if not isinstance(td, list):
        print('INVALID STRUCTURE: browser_highlights.top_domains must be a list in', path)
        return 5
    print('STRUCTURE OK:', path)
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_report.py <path>')
        sys.exit(1)
    sys.exit(main(sys.argv[1]))

