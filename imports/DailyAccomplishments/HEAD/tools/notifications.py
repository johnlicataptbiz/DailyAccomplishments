#!/usr/bin/env python3
"""
Notification system for sending daily reports via email and Slack.
"""

import smtplib
import json
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

from .daily_logger import load_config


def send_email_report(report_date, report_path):
    """
    Send daily report via email.
    
    Args:
        report_date: Date string (YYYY-MM-DD)
        report_path: Path to markdown report file
    """
    config = load_config()
    email_config = config.get('notifications', {}).get('email', {})
    
    if not email_config.get('enabled', False):
        print("Email notifications are disabled in config")
        return
    
    # Read markdown report
    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(
            f"Markdown report not found: {report_path}\n"
            f"Generate the report first with: python3 tools/auto_report.py --date {report_date}"
        )
    
    with open(report_path, 'r') as f:
        markdown_content = f.read()
    
    # Convert markdown to simple HTML
    html_content = markdown_content.replace('\n## ', '\n<h2>').replace('\n### ', '\n<h3>')
    html_content = html_content.replace('## ', '<h2>').replace('### ', '<h3>')
    html_content = html_content.replace('\n# ', '\n<h1>').replace('# ', '<h1>')
    html_content = html_content.replace('\n', '<br>\n')
    html_content = f"<html><body>{html_content}</body></html>"
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Daily Accomplishments Report - {report_date}"
    msg['From'] = email_config.get('from_email', email_config.get('username'))
    msg['To'] = ', '.join(email_config.get('to_emails', []))
    
    # Attach both plain text and HTML
    part1 = MIMEText(markdown_content, 'plain')
    part2 = MIMEText(html_content, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    # Send email
    try:
        smtp_server = email_config.get('smtp_server')
        smtp_port = email_config.get('smtp_port', 587)
        username = email_config.get('username')
        password = email_config.get('password')
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        if email_config.get('use_tls', True):
            server.starttls()
        
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email sent successfully to {msg['To']}")
        
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        raise


def send_slack_notification(report_date, report_data):
    """
    Send daily report summary to Slack.
    
    Args:
        report_date: Date string (YYYY-MM-DD)
        report_data: Report dictionary
    """
    if requests is None:
        print("✗ requests library not installed. Install with: pip install requests")
        return
    
    config = load_config()
    slack_config = config.get('notifications', {}).get('slack_webhook', {})
    
    if not slack_config.get('enabled', False):
        print("Slack notifications are disabled in config")
        return
    
    webhook_url = slack_config.get('webhook_url')
    if not webhook_url:
        print("✗ Slack webhook URL not configured")
        return
    
    # Validate report data has required keys
    required_keys = ['productivity_score', 'interruption_analysis', 'category_trends']
    missing_keys = [key for key in required_keys if key not in report_data]
    if missing_keys:
        raise ValueError(
            f"Report data missing required keys: {', '.join(missing_keys)}\n"
            f"Ensure the report was generated correctly with all analytics data."
        )
    
    # Extract key metrics
    score = report_data['productivity_score']
    deep_work_minutes = score['metrics']['deep_work_minutes']
    interruptions = report_data['interruption_analysis']['total_interruptions']
    top_category = report_data['category_trends']['top_category']
    
    # Build Slack message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Daily Accomplishments - {report_date}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Productivity Score:*\n{score['overall_score']}/100 ({score['rating']})"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Deep Work:*\n{deep_work_minutes} minutes"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Interruptions:*\n{interruptions}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Top Category:*\n{top_category or 'N/A'}"
                }
            ]
        }
    ]
    
    # Add focus windows if available
    if report_data['focus_windows']:
        focus_text = "\n".join([
            f"• {w['start_time']}-{w['end_time']} ({w['quality']})"
            for w in report_data['focus_windows'][:3]
        ])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎯 Suggested Focus Windows:*\n{focus_text}"
            }
        })
    
    # Send to Slack
    payload = {
        "blocks": blocks,
        "username": slack_config.get('username', 'Daily Accomplishments Bot'),
        "channel": slack_config.get('channel', '#general')
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"✓ Slack notification sent successfully")
        
    except Exception as e:
        print(f"✗ Failed to send Slack notification: {e}")
        raise


def main():
    """CLI for testing notifications."""
    parser = argparse.ArgumentParser(
        description='Send productivity report notifications'
    )
    parser.add_argument(
        '--email',
        action='store_true',
        help='Send email notification'
    )
    parser.add_argument(
        '--slack',
        action='store_true',
        help='Send Slack notification'
    )
    parser.add_argument(
        '--date',
        help='Report date (YYYY-MM-DD, default: today)'
    )
    
    args = parser.parse_args()
    
    # Get date
    if args.date:
        date_str = args.date
    else:
        config = load_config()
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(config['tracking']['timezone'])
        date_str = datetime.now(tz).strftime('%Y-%m-%d')
    
    # Find report files
    reports_dir = Path('./reports')
    json_path = reports_dir / f"daily-report-{date_str}.json"
    md_path = reports_dir / f"daily-report-{date_str}.md"
    
    if not json_path.exists():
        print(f"✗ Report not found: {json_path}")
        print("  Generate a report first with: python3 tools/auto_report.py")
        return
    
    # Load report data
    with open(json_path, 'r') as f:
        report_data = json.load(f)
    
    # Send notifications
    if args.email:
        send_email_report(date_str, md_path)
    
    if args.slack:
        send_slack_notification(date_str, report_data)
    
    if not args.email and not args.slack:
        print("No notification method specified. Use --email or --slack")


if __name__ == '__main__':
    main()
