#!/usr/bin/env python3
"""
Integration example demonstrating event logging and report generation.

This script shows how to:
1. Log productivity events
2. Generate daily reports
3. Access report data

Usage:
    python3 examples/integration_example.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.daily_logger import write_event, load_config
from tools.auto_report import generate_daily_report


def main():
    """Demonstrate logging and reporting."""
    print("Daily Accomplishments Integration Example")
    print("=" * 50)
    
    # Load config to get timezone
    config = load_config()
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(config['tracking']['timezone'])
    today = datetime.now(tz).date()
    
    print(f"\n1. Logging sample events for {today}...")
    
    # Log a coding session
    write_event({
        'type': 'focus_change',
        'data': {
            'app': 'VS Code',
            'duration_seconds': 1800  # 30 minutes
        }
    })
    print("   ✓ Logged coding session (VS Code, 30 min)")
    
    # Log an interruption
    write_event({
        'type': 'app_switch',
        'data': {
            'from_app': 'VS Code',
            'to_app': 'Slack'
        }
    })
    print("   ✓ Logged app switch (VS Code → Slack)")
    
    # Log a meeting
    write_event({
        'type': 'meeting_end',
        'data': {
            'duration_seconds': 1800  # 30 minutes
        }
    })
    print("   ✓ Logged meeting (30 min)")
    
    print(f"\n2. Generating daily report for {today}...")
    
    try:
        report_path = generate_daily_report(today, './reports')
        print(f"   ✓ Report generated: {report_path}")
        
        # Read and display summary
        import json
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        score = report['productivity_score']
        print(f"\n3. Report Summary:")
        print(f"   Productivity Score: {score['overall_score']}/100 ({score['rating']})")
        print(f"   Deep Work Sessions: {len(report['deep_work_sessions'])}")
        print(f"   Total Interruptions: {report['interruption_analysis']['total_interruptions']}")
        print(f"   Meetings: {report['meeting_efficiency']['meeting_count']}")
        
        print(f"\n✓ Integration example completed successfully!")
        print(f"\nNext steps:")
        print(f"  - View dashboard: python3 -m http.server 8000")
        print(f"  - Send notifications: python3 tools/notifications.py --email")
        print(f"  - Generate weekly report: python3 tools/auto_report.py --type weekly")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
