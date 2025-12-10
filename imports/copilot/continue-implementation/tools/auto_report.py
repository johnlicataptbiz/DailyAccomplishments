#!/usr/bin/env python3
"""
Automated Report Generator

Generates daily, weekly, and monthly reports with analytics.
Can be run manually or scheduled via cron/launchd.
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

# Handle both relative and absolute imports for compatibility
try:
    from .daily_logger import load_config, read_daily_log, get_log_path
    from .analytics import ProductivityAnalytics, compare_trends
except ImportError:
    from daily_logger import load_config, read_daily_log, get_log_path
    from analytics import ProductivityAnalytics, compare_trends


def generate_daily_report(date: Optional[datetime] = None, output_dir: Optional[Path] = None) -> Path:
    """
    Generate daily report with analytics
    
    Args:
        date: Date to generate report for (default: today)
        output_dir: Where to save report (default: reports/)
    
    Returns:
        Path to generated report
    """
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    date = date or datetime.now(tz)
    
    output_dir = output_dir or Path(__file__).parent.parent / 'reports'
    output_dir.mkdir(exist_ok=True)
    
    # Generate analytics
    analytics = ProductivityAnalytics(date)
    report_data = analytics.generate_report()
    
    # Add raw events summary
    events = read_daily_log(date)
    report_data['raw_events'] = {
        'total_events': len(events),
        'event_types': {}
    }
    
    for event in events:
        et = event.get('type', 'unknown')
        event_types = report_data['raw_events']['event_types']  # type: ignore[index]
        event_types[et] = event_types.get(et, 0) + 1  # type: ignore[union-attr]
    
    # Save JSON report
    report_path = output_dir / f"daily-report-{date.strftime('%Y-%m-%d')}.json"
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"Daily report generated: {report_path}")
    
    # Generate markdown summary
    md_path = output_dir / f"daily-report-{date.strftime('%Y-%m-%d')}.md"
    generate_markdown_summary(report_data, md_path)
    print(f"Markdown summary: {md_path}")
    
    return report_path


def generate_markdown_summary(report_data: dict, output_path: Path):
    """Generate human-readable markdown summary"""
    
    lines = [
        f"# Daily Productivity Report — {report_data['date']}",
        "",
        "## Overall Score",
        "",
        f"**{report_data['productivity_score']['overall_score']}/100** "
        f"({report_data['productivity_score']['rating']})",
        "",
        "### Components",
        f"- Deep Work: {report_data['productivity_score']['components']['deep_work_score']:.1f}/40",
        f"- Interruptions: {report_data['productivity_score']['components']['interruption_score']:.1f}/30",
        f"- Quality: {report_data['productivity_score']['components']['quality_score']:.1f}/30",
        "",
        "## Key Metrics",
        "",
        f"- Total Focus Time: {report_data['productivity_score']['metrics']['total_work_minutes']:.0f} minutes",
        f"- Deep Work Time: {report_data['productivity_score']['metrics']['total_deep_minutes']:.0f} minutes "
        f"({report_data['productivity_score']['metrics']['deep_work_percentage']:.1f}%)",
        f"- Deep Work Sessions: {report_data['productivity_score']['metrics']['deep_sessions_count']}",
        f"- Total Interruptions: {report_data['interruption_analysis']['total_interruptions']}",
        f"- Meeting Time: {report_data['meeting_efficiency']['total_meeting_minutes']:.0f} minutes",
        "",
        "## Deep Work Sessions",
        ""
    ]
    
    if report_data['deep_work_sessions']:
        for i, session in enumerate(report_data['deep_work_sessions'], 1):
            start_time = session['start_time'].split('T')[1][:5]
            lines.append(
                f"{i}. **{session['duration_minutes']:.0f}min** starting at {start_time} "
                f"({session['app']}) — Quality: {session['quality_score']:.0f}/100"
            )
    else:
        lines.append("_No deep work sessions detected (minimum 25 minutes)_")
    
    lines.extend([
        "",
        "## Time by Category",
        ""
    ])
    
    for cat in report_data['category_trends']['categories']:
        lines.append(f"- **{cat['category']}**: {cat['time_minutes']:.0f}min ({cat['percentage']:.1f}%)")
    
    lines.extend([
        "",
        "## Interruption Analysis",
        "",
        f"- Total: {report_data['interruption_analysis']['total_interruptions']} interruptions",
        f"- Average per hour: {report_data['interruption_analysis']['average_per_hour']:.1f}",
        f"- Most disruptive hour: {report_data['interruption_analysis']['most_disruptive_hour']}:00 "
        f"({report_data['interruption_analysis']['max_interruptions']} interruptions)",
        f"- Estimated time lost: {report_data['interruption_analysis']['context_switch_cost_minutes']:.0f} minutes",
        "",
        "## Meeting Efficiency",
        "",
        f"- Meetings: {report_data['meeting_efficiency']['meeting_count']}",
        f"- Total time: {report_data['meeting_efficiency']['total_meeting_minutes']:.0f} minutes",
        f"- Average duration: {report_data['meeting_efficiency']['average_duration_minutes']:.0f} minutes",
        f"- Meeting/Focus ratio: {report_data['meeting_efficiency']['meeting_vs_focus_ratio']:.2f}",
        f"- **Recommendation**: {report_data['meeting_efficiency']['recommendation']}",
        "",
        "## Suggested Focus Windows",
        ""
    ])
    
    if report_data['focus_windows']:
        for window in report_data['focus_windows']:
            lines.append(
                f"- **{window['start_time']}–{window['end_time']}** ({window['duration_hours']}h) — "
                f"{window['quality']} ({window['total_interruptions']} interruptions)"
            )
    else:
        lines.append("_No quiet windows identified_")
    
    lines.extend([
        "",
        "---",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))


def generate_weekly_report(end_date: Optional[datetime] = None, output_dir: Optional[Path] = None) -> Path:
    """Generate weekly summary report"""
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    end_date = end_date or datetime.now(tz)
    start_date = end_date - timedelta(days=6)
    
    output_dir = output_dir or Path(__file__).parent.parent / 'reports'
    output_dir.mkdir(exist_ok=True)
    
    # Get trend data
    trends = compare_trends(start_date, end_date)
    
    report_data = {
        'type': 'weekly',
        'period': trends['period'],
        'summary': trends['averages'],
        'trends': trends['trends'],
        'daily_breakdown': trends['daily_data']
    }
    
    # Save JSON
    report_path = output_dir / f"weekly-report-{end_date.strftime('%Y-%m-%d')}.json"
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"Weekly report generated: {report_path}")
    
    # Generate markdown
    md_path = output_dir / f"weekly-report-{end_date.strftime('%Y-%m-%d')}.md"
    
    lines = [
        f"# Weekly Productivity Report",
        "",
        f"**Period**: {trends['period']['start']} to {trends['period']['end']} ({trends['period']['days']} days)",
        "",
        "## Averages",
        "",
        f"- Productivity Score: {trends['averages']['productivity_score']:.1f}/100",
        f"- Deep Work Time: {trends['averages']['deep_work_minutes']:.0f} minutes/day",
        f"- Interruptions: {trends['averages']['interruptions']:.0f}/day",
        "",
        "## Trends",
        "",
        f"- Score trend: **{trends['trends']['score_trend']}**",
        f"- Change: {trends['trends']['score_change']:+.1f} points",
        "",
        "## Daily Breakdown",
        "",
        "| Day | Score | Deep Work (min) | Interruptions |",
        "|-----|-------|-----------------|---------------|"
    ]
    
    for i, score in enumerate(trends['daily_data']['scores']):
        day_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        deep_min = trends['daily_data']['deep_minutes'][i]
        interruptions = trends['daily_data']['interruptions'][i]
        lines.append(f"| {day_date} | {score:.0f} | {deep_min:.0f} | {interruptions} |")
    
    lines.extend([
        "",
        "---",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])
    
    with open(md_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Markdown summary: {md_path}")
    
    return report_path


def main():
    """Main entry point with CLI"""
    parser = argparse.ArgumentParser(description='Generate productivity reports')
    parser.add_argument('--type', choices=['daily', 'weekly'], default='daily',
                        help='Report type (default: daily)')
    parser.add_argument('--date', type=str,
                        help='Date for report (YYYY-MM-DD, default: today)')
    parser.add_argument('--output', type=str,
                        help='Output directory (default: reports/)')
    parser.add_argument('--format', choices=['json', 'markdown', 'both'], default='both',
                        help='Output format (default: both)')
    
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        config = load_config()
        tz = ZoneInfo(config['tracking']['timezone'])
        date = date.replace(tzinfo=tz)
    else:
        date = None
    
    # Parse output dir
    output_dir = Path(args.output) if args.output else None
    
    # Generate report
    if args.type == 'daily':
        report_path = generate_daily_report(date, output_dir)
    else:
        report_path = generate_weekly_report(date, output_dir)
    
    print(f"\n✓ Report generated successfully!")
    print(f"  Location: {report_path.parent}")
    
    # Show quick summary
    if args.type == 'daily':
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        print(f"\n📊 Quick Summary:")
        print(f"  Score: {data['productivity_score']['overall_score']:.0f}/100 ({data['productivity_score']['rating']})")
        print(f"  Deep Work: {data['productivity_score']['metrics']['total_deep_minutes']:.0f}min")
        print(f"  Interruptions: {data['interruption_analysis']['total_interruptions']}")


if __name__ == '__main__':
    main()
