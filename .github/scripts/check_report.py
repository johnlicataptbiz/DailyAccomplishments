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
    if not isinstance(j.get('overview'), dict) or 'focus_time' not in j.get('overview', {}):
        print('INVALID STRUCTURE: overview.focus_time missing in', path)
        return 3
    print('STRUCTURE OK:', path)
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_report.py <path>')
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
