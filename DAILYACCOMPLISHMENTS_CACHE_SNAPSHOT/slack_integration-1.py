#!/usr/bin/env python3
"""
Slack Integration for Daily Accomplishments.

Tracks messaging activity, huddles, and channel engagement.

Setup:
1. Go to api.slack.com/apps
2. Create a new app (or use existing)
3. Add OAuth scopes: channels:history, groups:history, im:history, users:read
4. Install to workspace
5. Copy the Bot User OAuth Token
6. Add to config.json:
   {
     "slack": {
       "bot_token": "xoxb-your-token",
       "user_token": "xoxp-your-token"  # Optional, for more detailed user stats
     }
   }

Usage:
    python3 scripts/slack_integration.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import requests

# Slack API
SLACK_API = "https://slack.com/api"

# Paths
REPO_PATH = Path.home() / "DailyAccomplishments"


class SlackClient:
    def __init__(self, bot_token: str, user_token: Optional[str] = None):
        self.bot_token = bot_token
        self.user_token = user_token or bot_token
        self.user_id = None
    
    def _get(self, endpoint: str, params: Optional[dict] = None, use_user_token: bool = False) -> dict:
        """Make a GET request to Slack API."""
        url = f"{SLACK_API}/{endpoint}"
        token = self.user_token if use_user_token else self.bot_token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("ok"):
            error = data.get("error", "Unknown error")
            if error == "invalid_auth":
                raise Exception("Invalid Slack token. Check your config.json")
            raise Exception(f"Slack API error: {error}")
        
        return data
    
    def get_user_id(self) -> str:
        """Get the authenticated user's ID."""
        if self.user_id:
            return self.user_id
        
        data = self._get("auth.test", use_user_token=True)
        self.user_id = data.get("user_id", "")
        return self.user_id
    
    def get_channels(self) -> list:
        """Get all channels the bot/user has access to."""
        channels = []
        cursor = None
        
        while True:
            params = {"types": "public_channel,private_channel,im,mpim", "limit": 200}
            if cursor:
                params["cursor"] = cursor
            
            data = self._get("conversations.list", params, use_user_token=True)
            channels.extend(data.get("channels", []))
            
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        
        return channels
    
    def get_messages_for_date(self, date: datetime) -> dict:
        """Get message activity for a specific date across all channels."""
        # Calculate timestamp range
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)
        
        oldest = str(start_of_day.timestamp())
        latest = str(end_of_day.timestamp())
        
        user_id = self.get_user_id()
        
        # Track messages
        messages_sent = []
        messages_received = []
        channel_activity: Dict[str, int] = {}
        dm_activity: Dict[str, int] = {}
        
        try:
            channels = self.get_channels()
            
            for channel in channels:
                channel_id = channel.get("id")
                channel_name = channel.get("name") or channel.get("user", "DM")
                is_im = channel.get("is_im", False)
                
                try:
                    # Get messages from this channel
                    data = self._get("conversations.history", {
                        "channel": channel_id,
                        "oldest": oldest,
                        "latest": latest,
                        "limit": 100
                    }, use_user_token=True)
                    
                    channel_messages = data.get("messages", [])
                    
                    for msg in channel_messages:
                        msg_user = msg.get("user", "")
                        msg_text = msg.get("text", "")
                        msg_ts = msg.get("ts", "")
                        
                        # Parse timestamp
                        try:
                            msg_dt = datetime.fromtimestamp(float(msg_ts))
                            time_str = msg_dt.strftime("%H:%M")
                        except:
                            time_str = ""
                        
                        msg_data = {
                            "channel": channel_name,
                            "channel_id": channel_id,
                            "time": time_str,
                            "timestamp": msg_ts,
                            "text": msg_text[:100],
                            "is_dm": is_im
                        }
                        
                        if msg_user == user_id:
                            messages_sent.append(msg_data)
                            if is_im:
                                dm_activity[channel_name] = dm_activity.get(channel_name, 0) + 1
                            else:
                                channel_activity[channel_name] = channel_activity.get(channel_name, 0) + 1
                        else:
                            messages_received.append(msg_data)
                            
                except Exception as e:
                    # Skip channels we can't access
                    continue
                    
        except Exception as e:
            print(f"Error fetching Slack messages: {e}")
        
        return {
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "channel_activity": channel_activity,
            "dm_activity": dm_activity,
            "stats": {
                "total_sent": len(messages_sent),
                "total_received": len(messages_received),
                "channels_active": len(channel_activity),
                "dms_active": len(dm_activity)
            }
        }
    
    def get_huddles_for_date(self, date: datetime) -> list:
        """Get huddles (Slack calls) for a specific date."""
        # Note: Huddle data requires specific API access
        # This is a placeholder - full implementation would need
        # access to the calls API or huddle-specific endpoints
        huddles = []
        
        # Huddle detection could be done by looking for
        # huddle-related system messages in channels
        
        return huddles


def load_config() -> dict:
    """Load config from config.json."""
    config_paths = [
        Path.home() / "DailyAccomplishments/config.json",
        Path("config.json"),
        Path(__file__).parent.parent / "config.json"
    ]
    
    for path in config_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    
    return {}


def update_activity_report(date_str: str, slack_data: dict, repo_path: Path):
    """Update ActivityReport with Slack data."""
    report_file = repo_path / f"ActivityReport-{date_str}.json"
    
    if report_file.exists():
        with open(report_file) as f:
            report = json.load(f)
    else:
        report = {
            "date": date_str,
            "overview": {},
            "debug_appointments": {"meetings_today": [], "appointments_today": []}
        }
    
    # Add Slack section (without full message content for privacy)
    report['slack'] = {
        'stats': slack_data['stats'],
        'channel_activity': slack_data['channel_activity'],
        'dm_activity': {k: v for k, v in list(slack_data['dm_activity'].items())[:5]},
        'top_channels': dict(sorted(
            slack_data['channel_activity'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
    }
    
    # Add to overview
    if 'overview' not in report:
        report['overview'] = {}
    
    stats = slack_data['stats']
    report['overview']['slack_messages_sent'] = stats['total_sent']
    report['overview']['slack_channels_active'] = stats['channels_active']
    
    # Add to executive summary
    if 'executive_summary' not in report:
        report['executive_summary'] = []
    
    if stats['total_sent'] > 0:
        slack_summary = f"Slack: {stats['total_sent']} messages sent across {stats['channels_active']} channels"
        if slack_summary not in report['executive_summary']:
            report['executive_summary'].append(slack_summary)
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Slack activity data')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--token', type=str, help='Slack bot token (or use config.json)')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--list-channels', action='store_true', help='List available channels')
    parser.add_argument('--repo', type=str, default=str(REPO_PATH), help='Path to repo')
    args = parser.parse_args()
    
    # Get tokens
    bot_token = args.token
    user_token = None
    if not bot_token:
        config = load_config()
        slack_config = config.get('slack', {})
        bot_token = slack_config.get('bot_token')
        user_token = slack_config.get('user_token')
    
    if not bot_token:
        print("Error: No Slack token found.")
        print("\nTo set up Slack integration:")
        print("1. Go to api.slack.com/apps")
        print("2. Create a new app")
        print("3. Add OAuth scopes: channels:history, groups:history, im:history, users:read")
        print("4. Install to workspace")
        print("5. Copy the Bot User OAuth Token")
        print("6. Add to ~/DailyAccomplishments/config.json:")
        print('   {"slack": {"bot_token": "xoxb-your-token"}}')
        sys.exit(1)
    
    # Create client
    client = SlackClient(bot_token, user_token)
    
    if args.list_channels:
        print("Fetching channels...")
        channels = client.get_channels()
        print(f"\nFound {len(channels)} channels:")
        for ch in channels[:20]:
            name = ch.get('name') or f"DM with {ch.get('user', 'unknown')}"
            ch_type = "DM" if ch.get('is_im') else ("Private" if ch.get('is_private') else "Public")
            print(f"  - {name} ({ch_type})")
        if len(channels) > 20:
            print(f"  ... and {len(channels) - 20} more")
        return
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Fetching Slack data for {date_str}...")
    
    # Get message activity
    data = client.get_messages_for_date(target_date)
    
    stats = data['stats']
    print(f"\n=== Slack Summary for {date_str} ===")
    print(f"Messages Sent: {stats['total_sent']}")
    print(f"Messages Received: {stats['total_received']}")
    print(f"Channels Active: {stats['channels_active']}")
    print(f"DMs Active: {stats['dms_active']}")
    
    if data['channel_activity']:
        print("\nTop Channels:")
        for channel, count in sorted(data['channel_activity'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - #{channel}: {count} messages")
    
    # Update report if requested
    if args.update_report:
        update_activity_report(date_str, data, Path(args.repo))


if __name__ == '__main__':
    main()
