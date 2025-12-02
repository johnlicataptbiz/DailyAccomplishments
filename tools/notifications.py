#!/usr/bin/env python3
"""
Email and Slack Notification System

Sends daily productivity reports via email and Slack webhooks.
Configure credentials in config.json.
"""

import json
import smtplib
import requests  # type: ignore
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
import logging

from daily_logger import load_config
from auto_report import generate_daily_report

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send productivity reports via email"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize email notifier with config"""
        email_config = config.get('notifications', {}).get('email', {})
        
        self.enabled = email_config.get('enabled', False)
        self.smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = email_config.get('smtp_port', 587)
        self.username = email_config.get('username', '')
        self.password = email_config.get('password', '')
        self.from_email = email_config.get('from_email', self.username)
        self.to_emails = email_config.get('to_emails', [])
        
        if self.enabled and not all([self.username, self.password, self.to_emails]):
            logger.warning("Email notifications enabled but missing credentials")
            self.enabled = False
    
    def send_daily_report(self, date: Optional[datetime] = None) -> bool:
        """
        Send daily report via email
        
        Args:
            date: Date to send report for (default: yesterday)
        
        Returns:
            Success status
        """
        if not self.enabled:
            logger.info("Email notifications disabled")
            return False
        
        config = load_config()
        tz = ZoneInfo(config['tracking']['timezone'])
        date = date or (datetime.now(tz) - timedelta(days=1))
        
        # Load report data
        report_path = Path(__file__).parent.parent / 'reports' / f"daily-report-{date.strftime('%Y-%m-%d')}.json"
        
        if not report_path.exists():
            logger.error(f"Report not found: {report_path}")
            return False
        
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        # Create email content
        html_content = self._create_html_email(report_data)
        text_content = self._create_text_email(report_data)
        
        subject = f"📊 Productivity Report — {date.strftime('%Y-%m-%d')}"
        
        return self._send_email(subject, text_content, html_content)
    
    def _create_html_email(self, data: Dict[str, Any]) -> str:
        """Create HTML email body"""
        score = data['productivity_score']
        
        # Score color based on rating
        score_color = {
            'Excellent': '#48bb78',
            'Good': '#38a169',
            'Fair': '#ed8936',
            'Needs Improvement': '#f56565'
        }.get(score['rating'], '#718096')
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; text-align: center; }}
                .score {{ font-size: 48px; font-weight: bold; margin: 20px 0; }}
                .rating {{ font-size: 24px; opacity: 0.9; }}
                .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
                .stat {{ background: #f7fafc; padding: 20px; border-radius: 8px; }}
                .stat-label {{ color: #718096; font-size: 14px; text-transform: uppercase; }}
                .stat-value {{ font-size: 32px; font-weight: bold; color: #2d3748; margin-top: 5px; }}
                .session {{ background: #f7fafc; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; border-radius: 8px; }}
                .footer {{ color: #718096; font-size: 12px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Productivity Report</h1>
                    <div class="score" style="color: {score_color}">{score['overall_score']:.0f}/100</div>
                    <div class="rating">{score['rating']}</div>
                </div>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-label">Deep Work</div>
                        <div class="stat-value">{score['metrics']['total_deep_minutes']:.0f}m</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Total Focus</div>
                        <div class="stat-value">{score['metrics']['total_work_minutes']:.0f}m</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Sessions</div>
                        <div class="stat-value">{score['metrics']['deep_sessions_count']}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Interruptions</div>
                        <div class="stat-value">{data['interruption_analysis']['total_interruptions']}</div>
                    </div>
                </div>
                
                <h2 style="margin-top: 30px;">🎯 Deep Work Sessions</h2>
        """
        
        if data['deep_work_sessions']:
            for session in data['deep_work_sessions'][:5]:
                start_time = session['start_time'].split('T')[1][:5]
                html += f"""
                <div class="session">
                    <strong>{session['duration_minutes']:.0f} minutes</strong> starting at {start_time}<br>
                    <span style="color: #718096;">
                        {session['app']} • Quality: {session['quality_score']:.0f}/100 • {session['interruptions']} interruptions
                    </span>
                </div>
                """
        else:
            html += "<p>No deep work sessions detected (minimum 25 minutes)</p>"
        
        html += f"""
                <h2 style="margin-top: 30px;">📁 Time by Category</h2>
        """
        
        for cat in data['category_trends']['categories'][:5]:
            html += f"""
                <div style="margin: 10px 0;">
                    <strong>{cat['category']}</strong>: {cat['time_minutes']:.0f}min ({cat['percentage']:.1f}%)
                </div>
            """
        
        html += f"""
                <div class="footer">
                    Generated by DailyAccomplishments Tracker • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_email(self, data: Dict[str, Any]) -> str:
        """Create plain text email body"""
        score = data['productivity_score']
        
        text = f"""
Daily Productivity Report — {data['date']}

Overall Score: {score['overall_score']:.0f}/100 ({score['rating']})

Key Metrics:
- Deep Work Time: {score['metrics']['total_deep_minutes']:.0f} minutes
- Total Focus Time: {score['metrics']['total_work_minutes']:.0f} minutes
- Deep Work Sessions: {score['metrics']['deep_sessions_count']}
- Interruptions: {data['interruption_analysis']['total_interruptions']}

Deep Work Sessions:
"""
        
        if data['deep_work_sessions']:
            for i, session in enumerate(data['deep_work_sessions'][:5], 1):
                start_time = session['start_time'].split('T')[1][:5]
                text += f"{i}. {session['duration_minutes']:.0f}min at {start_time} ({session['app']}) - Quality: {session['quality_score']:.0f}/100\n"
        else:
            text += "No deep work sessions detected\n"
        
        text += "\nTime by Category:\n"
        for cat in data['category_trends']['categories'][:5]:
            text += f"- {cat['category']}: {cat['time_minutes']:.0f}min ({cat['percentage']:.1f}%)\n"
        
        return text
    
    def _send_email(self, subject: str, text_content: str, html_content: str) -> bool:
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())
            
            logger.info(f"Email sent successfully to {', '.join(self.to_emails)}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class SlackNotifier:
    """Send productivity reports to Slack"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Slack notifier with config"""
        slack_config = config.get('notifications', {}).get('slack', {})
        
        self.enabled = slack_config.get('enabled', False)
        self.webhook_url = slack_config.get('webhook_url', '')
        self.channel = slack_config.get('channel', '#productivity')
        self.username = slack_config.get('username', 'Productivity Bot')
        
        if self.enabled and not self.webhook_url:
            logger.warning("Slack notifications enabled but missing webhook URL")
            self.enabled = False
    
    def send_daily_report(self, date: Optional[datetime] = None) -> bool:
        """
        Send daily report to Slack
        
        Args:
            date: Date to send report for (default: yesterday)
        
        Returns:
            Success status
        """
        if not self.enabled:
            logger.info("Slack notifications disabled")
            return False
        
        config = load_config()
        tz = ZoneInfo(config['tracking']['timezone'])
        date = date or (datetime.now(tz) - timedelta(days=1))
        
        # Load report data
        report_path = Path(__file__).parent.parent / 'reports' / f"daily-report-{date.strftime('%Y-%m-%d')}.json"
        
        if not report_path.exists():
            logger.error(f"Report not found: {report_path}")
            return False
        
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        # Create Slack message
        message = self._create_slack_message(report_data)
        
        return self._send_to_slack(message)
    
    def _create_slack_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Slack message payload"""
        score = data['productivity_score']
        
        # Score emoji based on rating
        score_emoji = {
            'Excellent': '🌟',
            'Good': '✅',
            'Fair': '⚠️',
            'Needs Improvement': '📉'
        }.get(score['rating'], '📊')
        
        # Score color
        score_color = {
            'Excellent': 'good',
            'Good': 'good',
            'Fair': 'warning',
            'Needs Improvement': 'danger'
        }.get(score['rating'], '#718096')
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Daily Productivity Report — {data['date']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Overall Score*\n{score_emoji} {score['overall_score']:.0f}/100 _{score['rating']}_"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Deep Work*\n{score['metrics']['total_deep_minutes']:.0f} minutes"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sessions*\n{score['metrics']['deep_sessions_count']} deep work sessions"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Interruptions*\n{data['interruption_analysis']['total_interruptions']} total"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        # Add top sessions
        if data['deep_work_sessions']:
            sessions_text = "*🎯 Top Deep Work Sessions*\n"
            for i, session in enumerate(data['deep_work_sessions'][:3], 1):
                start_time = session['start_time'].split('T')[1][:5]
                sessions_text += f"{i}. {session['duration_minutes']:.0f}min at {start_time} — {session['app']} (Quality: {session['quality_score']:.0f}/100)\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": sessions_text
                }
            })
        
        # Add category breakdown
        categories_text = "*📁 Time by Category*\n"
        for cat in data['category_trends']['categories'][:5]:
            categories_text += f"• {cat['category']}: {cat['time_minutes']:.0f}min ({cat['percentage']:.1f}%)\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": categories_text
            }
        })
        
        # Add focus windows if any
        if data['focus_windows']:
            windows_text = "*💡 Suggested Focus Windows*\n"
            for window in data['focus_windows'][:2]:
                windows_text += f"• {window['start_time']}-{window['end_time']} ({window['duration_hours']}h, {window['quality']})\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": windows_text
                }
            })
        
        return {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": ":chart_with_upwards_trend:",
            "blocks": blocks
        }
    
    def _send_to_slack(self, message: Dict[str, Any]) -> bool:
        """Send message to Slack webhook"""
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack message sent successfully")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False


def send_notifications(date: Optional[datetime] = None) -> Dict[str, bool]:
    """
    Send all configured notifications
    
    Args:
        date: Date to send report for (default: yesterday)
    
    Returns:
        Dict with success status for each notification type
    """
    config = load_config()
    
    results = {
        'email': False,
        'slack': False
    }
    
    # Send email
    email_notifier = EmailNotifier(config)
    if email_notifier.enabled:
        results['email'] = email_notifier.send_daily_report(date)
    
    # Send Slack
    slack_notifier = SlackNotifier(config)
    if slack_notifier.enabled:
        results['slack'] = slack_notifier.send_daily_report(date)
    
    return results


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Send productivity notifications')
    parser.add_argument('--date', type=str, help='Date to send report for (YYYY-MM-DD)')
    parser.add_argument('--email-only', action='store_true', help='Send email only')
    parser.add_argument('--slack-only', action='store_true', help='Send Slack only')
    
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        date = datetime.strptime(args.date, '%Y-%m-%d')
        config = load_config()
        tz = ZoneInfo(config['tracking']['timezone'])
        date = date.replace(tzinfo=tz)
    else:
        date = None
    
    # Generate report first if it doesn't exist
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    report_date = date or (datetime.now(tz) - timedelta(days=1))
    
    report_path = Path(__file__).parent.parent / 'reports' / f"daily-report-{report_date.strftime('%Y-%m-%d')}.json"
    if not report_path.exists():
        print(f"Generating report for {report_date.strftime('%Y-%m-%d')}...")
        generate_daily_report(report_date)
    
    # Send notifications
    if args.email_only:
        notifier = EmailNotifier(config)
        success = notifier.send_daily_report(date)
        print(f"Email: {'✓ Sent' if success else '✗ Failed'}")
    elif args.slack_only:
        notifier = SlackNotifier(config)
        success = notifier.send_daily_report(date)
        print(f"Slack: {'✓ Sent' if success else '✗ Failed'}")
    else:
        results = send_notifications(date)
        print(f"Email: {'✓ Sent' if results['email'] else '✗ Not configured or failed'}")
        print(f"Slack: {'✓ Sent' if results['slack'] else '✗ Not configured or failed'}")


if __name__ == '__main__':
    main()
