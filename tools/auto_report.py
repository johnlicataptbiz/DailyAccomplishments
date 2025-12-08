#!/usr/bin/env python3
"""
Automated report generation for daily and weekly productivity summaries.
Generates both JSON and Markdown formats.
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .daily_logger import load_config
from .analytics import ProductivityAnalytics, compare_trends


def generate_daily_report(date, output_dir):
    """
    Generate daily productivity report.
    
    Args:
        date: datetime.date object
        output_dir: Path to output directory
        
    Returns:
        Path to generated JSON report
    """
    analytics = ProductivityAnalytics(date)
    report = analytics.generate_report()
    
    # Augment with raw event stats
    report['raw_events'] = {
        'total_events': len(analytics.events),
        'event_types': {}
    }
    
    for event in analytics.events:
        event_type = event.get('type', 'unknown')
        report['raw_events']['event_types'][event_type] = \
            report['raw_events']['event_types'].get(event_type, 0) + 1
    
    # Write JSON report
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = date.isoformat()
    json_path = output_dir / f"daily-report-{date_str}.json"
    
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Write Markdown summary
    md_path = output_dir / f"daily-report-{date_str}.md"
    generate_markdown_summary(report, md_path)
    
    return json_path


def generate_markdown_summary(report, output_path):
    """
    Generate human-readable Markdown summary.
    
    Args:
        report: Report dictionary
        output_path: Path to output file
    """
    lines = []
    
    # Header
    lines.append(f"# Daily Accomplishments Report - {report['date']}")
    lines.append("")
    
    # Overall Score
    score = report['productivity_score']
    lines.append("## Overall Productivity Score")
    lines.append(f"**{score['overall_score']}/100** - {score['rating']}")
    lines.append("")
    
    # Components
    lines.append("### Score Components")
    components = score['components']
    lines.append(f"- Deep Work: {components['deep_work_score']}/40")
    lines.append(f"- Interruptions: {components['interruption_score']}/30")
    lines.append(f"- Quality: {components['quality_score']}/30")
    lines.append("")
    
    # Key Metrics
    lines.append("## Key Metrics")
    metrics = score['metrics']
    lines.append(f"- Total Focus Time: {metrics['total_focus_minutes']} minutes")
    lines.append(f"- Deep Work Time: {metrics['deep_work_minutes']} minutes ({metrics['deep_work_percentage']}%)")
    lines.append(f"- Deep Work Sessions: {len(report['deep_work_sessions'])}")
    
    interruptions = report['interruption_analysis']
    lines.append(f"- Total Interruptions: {interruptions['total_interruptions']}")
    
    meetings = report['meeting_efficiency']
    lines.append(f"- Meetings: {meetings['meeting_count']} ({meetings['total_meeting_minutes']} minutes)")
    lines.append("")
    
    # Deep Work Sessions
    lines.append("## Deep Work Sessions")
    if report['deep_work_sessions']:
        for i, session in enumerate(report['deep_work_sessions'], 1):
            lines.append(f"{i}. **{session['app']}** - {session['duration_minutes']} minutes")
            lines.append(f"   - Started: {session['start_time']}")
            lines.append(f"   - Interruptions: {session['interruptions']}")
            lines.append(f"   - Quality Score: {session.get('quality_score', 'N/A')}/100")
    else:
        lines.append("No deep work sessions detected (sessions must be ≥25 minutes).")
    lines.append("")
    
    # Time by Category
    lines.append("## Time by Category")
    categories = report['category_trends']['categories']
    for cat in categories:
        lines.append(f"- **{cat['category']}**: {cat['time_minutes']} min ({cat['percentage']}%) - {cat['event_count']} events")
    lines.append("")
    
    # Interruption Analysis
    lines.append("## Interruption Analysis")
    lines.append(f"- Total Interruptions: {interruptions['total_interruptions']}")
    if interruptions['most_disruptive_hour'] is not None:
        lines.append(f"- Most Disruptive Hour: {interruptions['most_disruptive_hour']}:00 ({interruptions['max_interruptions']} interruptions)")
    lines.append(f"- Context Switch Cost: {interruptions['context_switch_cost_minutes']} minutes")
    lines.append("")
    
    # Meeting Efficiency
    lines.append("## Meeting Efficiency")
    lines.append(f"- Total Meetings: {meetings['meeting_count']}")
    lines.append(f"- Total Time: {meetings['total_meeting_minutes']} minutes")
    if meetings['meeting_count'] > 0:
        lines.append(f"- Average Duration: {meetings['average_duration_minutes']} minutes")
        lines.append(f"- Meeting/Focus Ratio: {meetings['meeting_vs_focus_ratio']}")
    lines.append(f"- **Recommendation**: {meetings['recommendation']}")
    lines.append("")
    
    # Focus Windows
    lines.append("## Suggested Focus Windows")
    if report['focus_windows']:
        for window in report['focus_windows']:
            lines.append(f"- **{window['start_time']} - {window['end_time']}** ({window['duration_hours']} hours)")
            lines.append(f"  - Quality: {window['quality']}")
            lines.append(f"  - Interruptions: {window['total_interruptions']}")
            lines.append(f"  - {window['recommendation']}")
    else:
        lines.append("No optimal focus windows identified.")
    lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(f"*Report generated at {datetime.now().isoformat()}*")
    
    # Write file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))


def generate_weekly_report(end_date, output_dir):
    """
    Generate weekly productivity report.
    
    Args:
        end_date: datetime.date object (last day of week)
        output_dir: Path to output directory
        
    Returns:
        Path to generated JSON report
    """
    start_date = end_date - timedelta(days=6)
    trends = compare_trends(start_date, end_date)
    
    # Build weekly report
    weekly_report = {
        'type': 'weekly',
        'period': trends['period'],
        'summary': trends['averages'],
        'trends': trends['trends'],
        'daily_breakdown': [
            {
                'date': d['date'],
                'score': d['productivity_score']['overall_score'],
                'deep_work_minutes': d['productivity_score']['metrics']['deep_work_minutes'],
                'interruptions': d['interruption_analysis']['total_interruptions']
            }
            for d in trends['daily_data']
        ]
    }
    
    # Write JSON report
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = end_date.isoformat()
    json_path = output_dir / f"weekly-report-{date_str}.json"
    
    with open(json_path, 'w') as f:
        json.dump(weekly_report, f, indent=2)
    
    # Write Markdown summary
    md_path = output_dir / f"weekly-report-{date_str}.md"
    
    lines = []
    lines.append(f"# Weekly Productivity Report")
    lines.append(f"**Period**: {start_date.isoformat()} to {end_date.isoformat()}")
    lines.append("")
    
    lines.append("## Weekly Averages")
    avg = weekly_report['summary']
    lines.append(f"- Productivity Score: {avg['productivity_score']}/100")
    lines.append(f"- Deep Work: {avg['deep_work_minutes']} minutes/day")
    lines.append(f"- Interruptions: {avg['interruptions']}/day")
    lines.append(f"- Meetings: {avg['meeting_minutes']} minutes/day")
    lines.append("")
    
    lines.append("## Trends")
    lines.append(f"- Best Day: {weekly_report['trends']['best_day']}")
    if weekly_report['trends']['most_productive_category']:
        lines.append(f"- Most Productive Category: {weekly_report['trends']['most_productive_category']}")
    lines.append("")
    
    lines.append("## Daily Breakdown")
    lines.append("| Date | Score | Deep Work (min) | Interruptions |")
    lines.append("|------|-------|-----------------|---------------|")
    for day in weekly_report['daily_breakdown']:
        lines.append(f"| {day['date']} | {day['score']} | {day['deep_work_minutes']} | {day['interruptions']} |")
    lines.append("")
    
    lines.append("---")
    lines.append(f"*Report generated at {datetime.now().isoformat()}*")
    
    with open(md_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return json_path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate daily or weekly productivity reports'
    )
    parser.add_argument(
        '--type',
        choices=['daily', 'weekly'],
        default='daily',
        help='Report type (default: daily)'
    )
    parser.add_argument(
        '--date',
        help='Date in YYYY-MM-DD format (default: today)'
    )
    parser.add_argument(
        '--output',
        default='./reports',
        help='Output directory (default: ./reports)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    
    args = parser.parse_args()
    
    # Load config for timezone
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    
    # Parse date
    if args.date:
        date = datetime.fromisoformat(args.date).date()
    else:
        date = datetime.now(tz).date()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate report
    try:
        if args.type == 'daily':
            report_path = generate_daily_report(date, output_dir)
            print(f"✓ Daily report generated: {report_path}")
            
            # Print summary
            with open(report_path, 'r') as f:
                report = json.load(f)
            score = report['productivity_score']['overall_score']
            rating = report['productivity_score']['rating']
            print(f"  Productivity Score: {score}/100 ({rating})")
            
        else:  # weekly
            report_path = generate_weekly_report(date, output_dir)
            print(f"✓ Weekly report generated: {report_path}")
            
            with open(report_path, 'r') as f:
                report = json.load(f)
            avg_score = report['summary']['productivity_score']
            print(f"  Average Score: {avg_score}/100")
    
    except Exception as e:
        print(f"✗ Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
