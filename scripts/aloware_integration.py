#!/usr/bin/env python3
"""
Aloware Integration for Daily Accomplishments.

Fetches call logs and SMS activity from Aloware.

Setup:
1. Log into Aloware admin panel
2. Go to Settings → API/Integrations
3. Generate an API key
4. Add to config.json:
   {
     "aloware": {
       "api_key": "your-api-key",
       "company_id": "your-company-id"
     }
   }

Usage:
    python3 scripts/aloware_integration.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests

# Aloware API base URL
ALOWARE_API = "https://app.aloware.com/api/v1"

# Paths
REPO_PATH = Path.home() / "DailyAccomplishments"


class AlowareClient:
    def __init__(self, api_key: str, company_id: str = ""):
        self.api_key = api_key
        self.company_id = company_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to Aloware API."""
        url = f"{ALOWARE_API}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Invalid Aloware API key. Check your config.json")
        elif response.status_code == 403:
            raise Exception("Access denied. Check your API permissions.")
        
        response.raise_for_status()
        return response.json()
    
    def get_calls_for_date(self, date: datetime) -> list:
        """Get all calls for a specific date."""
        calls = []
        
        # Date range
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            # Aloware API call logs endpoint
            data = self._get("/communications", {
                "type": "call",
                "start_date": start_of_day.isoformat(),
                "end_date": end_of_day.isoformat(),
                "per_page": 100
            })
            
            for call in data.get("data", []):
                # Parse call time
                call_time = call.get("created_at", "")
                if call_time:
                    try:
                        call_dt = datetime.fromisoformat(call_time.replace("Z", "+00:00"))
                        time_str = call_dt.strftime("%H:%M")
                    except:
                        time_str = ""
                else:
                    time_str = ""
                
                # Get duration
                duration_seconds = call.get("duration", 0) or call.get("talk_time", 0) or 0
                
                # Get contact info
                contact_name = call.get("contact", {}).get("name", "") or call.get("from_number", "Unknown")
                
                # Determine direction
                direction = call.get("direction", "outbound")
                
                # Determine disposition/outcome
                disposition = call.get("disposition", "") or call.get("status", "")
                
                calls.append({
                    "id": call.get("id"),
                    "time": time_str,
                    "datetime": call_time,
                    "contact": contact_name,
                    "phone": call.get("to_number") or call.get("from_number", ""),
                    "direction": direction,
                    "duration_seconds": duration_seconds,
                    "duration_formatted": f"{duration_seconds // 60}:{duration_seconds % 60:02d}",
                    "disposition": disposition,
                    "recording_url": call.get("recording_url", ""),
                    "notes": call.get("notes", "")[:200] if call.get("notes") else "",
                    "source": "Aloware"
                })
                
        except Exception as e:
            print(f"Error fetching Aloware calls: {e}")
        
        return calls
    
    def get_sms_for_date(self, date: datetime) -> list:
        """Get all SMS messages for a specific date."""
        messages = []
        
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            data = self._get("/communications", {
                "type": "sms",
                "start_date": start_of_day.isoformat(),
                "end_date": end_of_day.isoformat(),
                "per_page": 100
            })
            
            for sms in data.get("data", []):
                sms_time = sms.get("created_at", "")
                if sms_time:
                    try:
                        sms_dt = datetime.fromisoformat(sms_time.replace("Z", "+00:00"))
                        time_str = sms_dt.strftime("%H:%M")
                    except:
                        time_str = ""
                else:
                    time_str = ""
                
                messages.append({
                    "id": sms.get("id"),
                    "time": time_str,
                    "datetime": sms_time,
                    "contact": sms.get("contact", {}).get("name", "Unknown"),
                    "phone": sms.get("to_number") or sms.get("from_number", ""),
                    "direction": sms.get("direction", "outbound"),
                    "body": (sms.get("body", "") or "")[:100],
                    "source": "Aloware"
                })
                
        except Exception as e:
            print(f"Error fetching Aloware SMS: {e}")
        
        return messages
    
    def get_activity_summary(self, date: datetime) -> dict:
        """Get activity summary for the date."""
        calls = self.get_calls_for_date(date)
        sms = self.get_sms_for_date(date)
        
        # Calculate stats
        outbound_calls = [c for c in calls if c["direction"] == "outbound"]
        inbound_calls = [c for c in calls if c["direction"] == "inbound"]
        
        total_talk_time = sum(c["duration_seconds"] for c in calls)
        
        # Connected calls (duration > 0)
        connected_calls = [c for c in calls if c["duration_seconds"] > 0]
        
        return {
            "calls": calls,
            "sms": sms,
            "stats": {
                "total_calls": len(calls),
                "outbound_calls": len(outbound_calls),
                "inbound_calls": len(inbound_calls),
                "connected_calls": len(connected_calls),
                "total_talk_time_seconds": total_talk_time,
                "total_talk_time_formatted": f"{total_talk_time // 3600}:{(total_talk_time % 3600) // 60:02d}:{total_talk_time % 60:02d}",
                "avg_call_duration": total_talk_time // len(calls) if calls else 0,
                "total_sms": len(sms),
                "outbound_sms": len([s for s in sms if s["direction"] == "outbound"]),
                "inbound_sms": len([s for s in sms if s["direction"] == "inbound"])
            }
        }


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


def update_activity_report(date_str: str, aloware_data: dict, repo_path: Path):
    """Update ActivityReport with Aloware data."""
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
    
    # Add Aloware section
    report['aloware'] = aloware_data
    
    # Add call stats to overview
    stats = aloware_data.get('stats', {})
    if 'overview' not in report:
        report['overview'] = {}
    
    report['overview']['calls_made'] = stats.get('outbound_calls', 0)
    report['overview']['calls_received'] = stats.get('inbound_calls', 0)
    report['overview']['talk_time'] = stats.get('total_talk_time_formatted', '0:00:00')
    
    # Add to executive summary
    if 'executive_summary' not in report:
        report['executive_summary'] = []
    
    summary_parts = []
    if stats.get('total_calls'):
        connected = stats.get('connected_calls', 0)
        summary_parts.append(f"{stats['total_calls']} calls ({connected} connected)")
    if stats.get('total_sms'):
        summary_parts.append(f"{stats['total_sms']} SMS")
    
    if summary_parts:
        aloware_summary = f"Aloware: {', '.join(summary_parts)}"
        if aloware_summary not in report['executive_summary']:
            report['executive_summary'].append(aloware_summary)
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Aloware call/SMS data')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--api-key', type=str, help='Aloware API key (or use config.json)')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--repo', type=str, default=str(REPO_PATH), help='Path to repo')
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key
    company_id = ""
    if not api_key:
        config = load_config()
        aloware_config = config.get('aloware', {})
        api_key = aloware_config.get('api_key')
        company_id = aloware_config.get('company_id', '')
    
    if not api_key:
        print("Error: No Aloware API key found.")
        print("\nTo set up Aloware integration:")
        print("1. Log into Aloware admin panel")
        print("2. Go to Settings → API/Integrations")
        print("3. Generate an API key")
        print("4. Add to ~/DailyAccomplishments/config.json:")
        print('   {"aloware": {"api_key": "your-key"}}')
        sys.exit(1)
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Fetching Aloware data for {date_str}...")
    
    # Create client
    client = AlowareClient(api_key, company_id)
    
    # Get activity summary
    data = client.get_activity_summary(target_date)
    
    stats = data['stats']
    print(f"\n=== Aloware Summary for {date_str} ===")
    print(f"Total Calls: {stats['total_calls']}")
    print(f"  Outbound: {stats['outbound_calls']}")
    print(f"  Inbound: {stats['inbound_calls']}")
    print(f"  Connected: {stats['connected_calls']}")
    print(f"Total Talk Time: {stats['total_talk_time_formatted']}")
    print(f"\nSMS: {stats['total_sms']} ({stats['outbound_sms']} sent, {stats['inbound_sms']} received)")
    
    if data['calls']:
        print("\nCalls:")
        for call in data['calls'][:10]:
            direction = "→" if call['direction'] == "outbound" else "←"
            print(f"  {call['time']} {direction} {call['contact']} ({call['duration_formatted']})")
    
    # Update report if requested
    if args.update_report:
        update_activity_report(date_str, data, Path(args.repo))


if __name__ == '__main__':
    main()
