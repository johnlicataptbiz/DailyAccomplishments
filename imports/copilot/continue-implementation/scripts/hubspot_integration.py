#!/usr/bin/env python3
"""
HubSpot Integration for Daily Accomplishments.
Fetches appointments, deals, and activities from HubSpot.

Setup:
1. Get your HubSpot Private App Access Token:
   - Go to HubSpot > Settings > Integrations > Private Apps
   - Create a new app with scopes: crm.objects.contacts.read, crm.objects.deals.read, 
     crm.objects.companies.read, sales-email-read, crm.objects.owners.read
   - Copy the access token
2. Add to config.json:
   {
     "hubspot": {
       "access_token": "pat-na1-xxxxxxxx"
     }
   }

Usage:
    python3 scripts/hubspot_integration.py [--date YYYY-MM-DD]
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# HubSpot API base URL
HUBSPOT_API = "https://api.hubapi.com"


class HubSpotClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to HubSpot API."""
        url = f"{HUBSPOT_API}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Invalid HubSpot access token. Check your config.json")
        elif response.status_code == 403:
            raise Exception("Access denied. Make sure your Private App has the required scopes.")
        
        response.raise_for_status()
        return response.json()
    
    def get_owner_id(self) -> Optional[str]:
        """Get the current user's owner ID."""
        try:
            data = self._get("/crm/v3/owners", {"limit": 1})
            if data.get("results"):
                return data["results"][0]["id"]
        except:
            pass
        return None
    
    def get_meetings_for_date(self, date: datetime) -> list:
        """Get meetings/appointments for a specific date."""
        meetings = []
        
        # Date range for the target date
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(end_of_day.timestamp() * 1000)
        
        try:
            # Get meetings from engagements
            data = self._get("/engagements/v1/engagements/paged", {
                "limit": 100
            })
            
            for result in data.get("results", []):
                engagement = result.get("engagement", {})
                metadata = result.get("metadata", {})
                
                if engagement.get("type") == "MEETING":
                    # Check if meeting is on target date
                    meeting_time = engagement.get("timestamp", 0)
                    if start_ms <= meeting_time < end_ms:
                        meeting_dt = datetime.fromtimestamp(meeting_time / 1000)
                        
                        meetings.append({
                            "id": engagement.get("id"),
                            "title": metadata.get("title", "Meeting"),
                            "time": meeting_dt.strftime("%H:%M"),
                            "datetime": meeting_dt.isoformat(),
                            "duration_minutes": metadata.get("durationMilliseconds", 0) // 60000,
                            "outcome": metadata.get("meetingOutcome", ""),
                            "notes": metadata.get("body", "")[:200] if metadata.get("body") else "",
                            "type": "meeting"
                        })
        except Exception as e:
            print(f"Error fetching meetings: {e}")
        
        return meetings
    
    def get_deals_updated_today(self, date: datetime) -> list:
        """Get deals that were updated on a specific date."""
        deals = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            # Search for deals updated today
            data = self._get("/crm/v3/objects/deals", {
                "limit": 100,
                "properties": "dealname,amount,dealstage,closedate,pipeline,hs_lastmodifieddate,createdate"
            })
            
            for deal in data.get("results", []):
                props = deal.get("properties", {})
                
                # Check if updated today
                modified = props.get("hs_lastmodifieddate")
                if modified:
                    modified_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    modified_local = modified_dt.replace(tzinfo=None)
                    
                    if start_of_day <= modified_local < end_of_day:
                        created = props.get("createdate", "")
                        created_today = False
                        if created:
                            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            created_local = created_dt.replace(tzinfo=None)
                            created_today = start_of_day <= created_local < end_of_day
                        
                        deals.append({
                            "id": deal.get("id"),
                            "name": props.get("dealname", "Untitled Deal"),
                            "amount": props.get("amount"),
                            "stage": props.get("dealstage"),
                            "pipeline": props.get("pipeline"),
                            "close_date": props.get("closedate"),
                            "modified": modified,
                            "created_today": created_today,
                            "type": "deal"
                        })
        except Exception as e:
            print(f"Error fetching deals: {e}")
        
        return deals
    
    def get_contacts_created_today(self, date: datetime) -> list:
        """Get contacts created on a specific date."""
        contacts = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            data = self._get("/crm/v3/objects/contacts", {
                "limit": 100,
                "properties": "firstname,lastname,email,company,createdate,hs_lead_status"
            })
            
            for contact in data.get("results", []):
                props = contact.get("properties", {})
                
                created = props.get("createdate")
                if created:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    created_local = created_dt.replace(tzinfo=None)
                    
                    if start_of_day <= created_local < end_of_day:
                        name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                        
                        contacts.append({
                            "id": contact.get("id"),
                            "name": name or "Unknown",
                            "email": props.get("email"),
                            "company": props.get("company"),
                            "lead_status": props.get("hs_lead_status"),
                            "created": created,
                            "type": "contact"
                        })
        except Exception as e:
            print(f"Error fetching contacts: {e}")
        
        return contacts
    
    def get_tasks_for_date(self, date: datetime) -> list:
        """Get tasks due on a specific date."""
        tasks = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(end_of_day.timestamp() * 1000)
        
        try:
            data = self._get("/engagements/v1/engagements/paged", {
                "limit": 100
            })
            
            for result in data.get("results", []):
                engagement = result.get("engagement", {})
                metadata = result.get("metadata", {})
                
                if engagement.get("type") == "TASK":
                    task_due = metadata.get("taskDueDate") or engagement.get("timestamp", 0)
                    
                    if start_ms <= task_due < end_ms:
                        task_dt = datetime.fromtimestamp(task_due / 1000)
                        
                        tasks.append({
                            "id": engagement.get("id"),
                            "subject": metadata.get("subject", "Task"),
                            "due_time": task_dt.strftime("%H:%M"),
                            "due_datetime": task_dt.isoformat(),
                            "status": metadata.get("status", ""),
                            "priority": metadata.get("priority", ""),
                            "notes": metadata.get("body", "")[:200] if metadata.get("body") else "",
                            "type": "task"
                        })
        except Exception as e:
            print(f"Error fetching tasks: {e}")
        
        return tasks
    
    def get_calls_for_date(self, date: datetime) -> list:
        """Get calls made on a specific date."""
        calls = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(end_of_day.timestamp() * 1000)
        
        try:
            data = self._get("/engagements/v1/engagements/paged", {
                "limit": 100
            })
            
            for result in data.get("results", []):
                engagement = result.get("engagement", {})
                metadata = result.get("metadata", {})
                
                if engagement.get("type") == "CALL":
                    call_time = engagement.get("timestamp", 0)
                    
                    if start_ms <= call_time < end_ms:
                        call_dt = datetime.fromtimestamp(call_time / 1000)
                        
                        calls.append({
                            "id": engagement.get("id"),
                            "time": call_dt.strftime("%H:%M"),
                            "datetime": call_dt.isoformat(),
                            "duration_seconds": metadata.get("durationMilliseconds", 0) // 1000,
                            "status": metadata.get("status", ""),
                            "disposition": metadata.get("disposition", ""),
                            "to_number": metadata.get("toNumber", ""),
                            "notes": metadata.get("body", "")[:200] if metadata.get("body") else "",
                            "type": "call"
                        })
        except Exception as e:
            print(f"Error fetching calls: {e}")
        
        return calls
    
    def get_emails_for_date(self, date: datetime) -> list:
        """Get emails sent on a specific date."""
        emails = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(end_of_day.timestamp() * 1000)
        
        try:
            data = self._get("/engagements/v1/engagements/paged", {
                "limit": 100
            })
            
            for result in data.get("results", []):
                engagement = result.get("engagement", {})
                metadata = result.get("metadata", {})
                
                if engagement.get("type") == "EMAIL":
                    email_time = engagement.get("timestamp", 0)
                    
                    if start_ms <= email_time < end_ms:
                        email_dt = datetime.fromtimestamp(email_time / 1000)
                        
                        emails.append({
                            "id": engagement.get("id"),
                            "time": email_dt.strftime("%H:%M"),
                            "datetime": email_dt.isoformat(),
                            "subject": metadata.get("subject", ""),
                            "to": metadata.get("to", [{}])[0].get("email", "") if metadata.get("to") else "",
                            "status": metadata.get("status", ""),
                            "type": "email"
                        })
        except Exception as e:
            print(f"Error fetching emails: {e}")
        
        return emails

    def get_booked_appointments(self, date: datetime) -> list:
        """Detect appointments set from emails containing booking confirmation patterns."""
        appointments = []
        
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(end_of_day.timestamp() * 1000)
        
        # Patterns that indicate an appointment was booked
        import re
        booked_patterns = [
            r"all set",
            r"calendar invite",
            r"zoom link",
            r"call booked",
            r"discovery call",
            r"game\s*plan",
            r"strategy call",
            r"confirmed.*call",
            r"see you (on|at)",
            r"looking forward to.*call",
        ]
        booked_regex = re.compile("|".join(booked_patterns), re.IGNORECASE)
        
        try:
            data = self._get("/engagements/v1/engagements/paged", {
                "limit": 250
            })
            
            for result in data.get("results", []):
                engagement = result.get("engagement", {})
                metadata = result.get("metadata", {})
                associations = result.get("associations", {})
                
                if engagement.get("type") == "EMAIL":
                    email_time = engagement.get("timestamp", 0)
                    
                    if start_ms <= email_time < end_ms:
                        # Check email body for booking patterns
                        body = metadata.get("body", "") or metadata.get("text", "") or ""
                        subject = metadata.get("subject", "") or ""
                        
                        if booked_regex.search(body) or booked_regex.search(subject):
                            email_dt = datetime.fromtimestamp(email_time / 1000)
                            
                            # Try to get contact name
                            contact_name = "Unknown Contact"
                            contact_ids = associations.get("contactIds", [])
                            if contact_ids:
                                try:
                                    contact_data = self._get(f"/crm/v3/objects/contacts/{contact_ids[0]}", {
                                        "properties": "firstname,lastname,email"
                                    })
                                    props = contact_data.get("properties", {})
                                    contact_name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                                    if not contact_name:
                                        contact_name = props.get("email", "Unknown Contact")
                                except:
                                    pass
                            
                            appointments.append({
                                "id": engagement.get("id"),
                                "name": f"{contact_name} - Discovery Call",
                                "time": email_dt.strftime("%H:%M"),
                                "datetime": email_dt.isoformat(),
                                "source": "email_booked",
                                "subject": subject[:50],
                                "type": "appointment"
                            })
        except Exception as e:
            print(f"Error fetching booked appointments: {e}")
        
        return appointments


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


def update_activity_report(date_str: str, hubspot_data: dict, repo_path: Path):
    """Update ActivityReport with HubSpot data."""
    report_file = repo_path / f"ActivityReport-{date_str}.json"
    
    report: dict  # type hint for Pylance
    if report_file.exists():
        with open(report_file) as f:
            report = json.load(f)
    else:
        report = {
            "source_file": f"ActivityReport-{date_str}.json",
            "date": date_str,
            "title": f"Daily Accomplishments — {date_str}",
            "overview": {},
            "debug_appointments": {"meetings_today": [], "appointments_today": []}
        }
    
    # Add HubSpot section
    report['hubspot'] = hubspot_data
    
    # Update meetings
    if 'debug_appointments' not in report:
        report['debug_appointments'] = {'meetings_today': [], 'appointments_today': []}
    debug_appts = report['debug_appointments']
    if 'meetings_today' not in debug_appts:
        debug_appts['meetings_today'] = []
    meetings_list = debug_appts['meetings_today']
    
    for meeting in hubspot_data.get('meetings', []):
        meetings_list.append({
            "name": meeting['title'],
            "time": meeting['time'],
            "source": "HubSpot"
        })
    
    # Update appointments from booked emails
    if 'appointments_today' not in debug_appts:
        debug_appts['appointments_today'] = []
    appointments_list = debug_appts['appointments_today']
    
    for appt in hubspot_data.get('booked_appointments', []):
        # Avoid duplicates
        existing_names = [a.get('name', '').lower() for a in appointments_list]
        if appt['name'].lower() not in existing_names:
            appointments_list.append({
                "name": appt['name'],
                "time": appt['time'],
                "source": "HubSpot Email"
            })
    
    # Update appointment count in overview
    overview = report.get('overview', {})
    overview['appointments'] = len(appointments_list)
    
    # Add HubSpot stats to executive summary
    if 'executive_summary' not in report:
        report['executive_summary'] = []
    exec_summary = report['executive_summary']
    
    stats = []
    if hubspot_data.get('booked_appointments'):
        stats.append(f"{len(hubspot_data['booked_appointments'])} appointments set")
    
    if hubspot_data.get('deals'):
        new_deals = sum(1 for d in hubspot_data['deals'] if d.get('created_today'))
        stats.append(f"{new_deals} new deals" if new_deals else f"{len(hubspot_data['deals'])} deals updated")
    
    if hubspot_data.get('contacts'):
        stats.append(f"{len(hubspot_data['contacts'])} new contacts")
    
    if hubspot_data.get('calls'):
        total_call_time = sum(c.get('duration_seconds', 0) for c in hubspot_data['calls'])
        stats.append(f"{len(hubspot_data['calls'])} calls ({total_call_time // 60}m)")
    
    if hubspot_data.get('emails'):
        stats.append(f"{len(hubspot_data['emails'])} emails")
    
    if stats:
        hubspot_summary = f"HubSpot: {', '.join(stats)}"
        if hubspot_summary not in exec_summary:
            exec_summary.append(hubspot_summary)
    
    report['executive_summary'] = exec_summary
    report['overview'] = overview
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch HubSpot data for daily report')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--token', type=str, help='HubSpot access token (or use config.json)')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--repo', type=str, default=os.path.expanduser('~/DailyAccomplishments'),
                        help='Path to repo')
    args = parser.parse_args()
    
    # Get access token
    access_token = args.token
    if not access_token:
        config = load_config()
        access_token = config.get('hubspot', {}).get('access_token')
    
    if not access_token:
        print("Error: No HubSpot access token found.")
        print("\nTo set up HubSpot integration:")
        print("1. Go to HubSpot > Settings > Integrations > Private Apps")
        print("2. Create a new app with required scopes")
        print("3. Copy the access token")
        print("4. Add to ~/DailyAccomplishments/config.json:")
        print('   {"hubspot": {"access_token": "pat-na1-xxxxxxxx"}}')
        sys.exit(1)
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Fetching HubSpot data for {date_str}...")
    
    # Create client
    client = HubSpotClient(access_token)
    
    # Fetch all data
    print("  Fetching meetings...")
    meetings = client.get_meetings_for_date(target_date)
    print(f"    Found {len(meetings)} meetings")
    
    print("  Fetching deals...")
    deals = client.get_deals_updated_today(target_date)
    print(f"    Found {len(deals)} deals updated")
    
    print("  Fetching contacts...")
    contacts = client.get_contacts_created_today(target_date)
    print(f"    Found {len(contacts)} new contacts")
    
    print("  Fetching calls...")
    calls = client.get_calls_for_date(target_date)
    print(f"    Found {len(calls)} calls")
    
    print("  Fetching tasks...")
    tasks = client.get_tasks_for_date(target_date)
    print(f"    Found {len(tasks)} tasks")
    
    print("  Fetching emails...")
    emails = client.get_emails_for_date(target_date)
    print(f"    Found {len(emails)} emails")
    
    print("  Fetching booked appointments from emails...")
    booked_appointments = client.get_booked_appointments(target_date)
    print(f"    Found {len(booked_appointments)} booked appointments")
    
    # Compile data
    hubspot_data = {
        'date': date_str,
        'meetings': meetings,
        'deals': deals,
        'contacts': contacts,
        'calls': calls,
        'tasks': tasks,
        'booked_appointments': booked_appointments,
        'emails': emails,
        'summary': {
            'meetings_count': len(meetings),
            'deals_updated': len(deals),
            'new_contacts': len(contacts),
            'calls_made': len(calls),
            'tasks_due': len(tasks),
            'emails_sent': len(emails)
        }
    }
    
    # Save to file
    repo_path = Path(args.repo)
    output_file = repo_path / 'logs' / f'hubspot-{date_str}.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(hubspot_data, f, indent=2)
    
    print(f"\nSaved to {output_file}")
    
    # Print summary
    print(f"\n=== HubSpot Summary for {date_str} ===")
    print(f"Meetings: {len(meetings)}")
    for m in meetings:
        print(f"  - {m['time']}: {m['title']}")
    
    print(f"\nDeals Updated: {len(deals)}")
    for d in deals[:5]:
        status = " (NEW)" if d.get('created_today') else ""
        amount = f" ${d['amount']}" if d.get('amount') else ""
        print(f"  - {d['name']}{amount}{status}")
    
    print(f"\nNew Contacts: {len(contacts)}")
    for c in contacts[:5]:
        print(f"  - {c['name']} ({c.get('email', 'no email')})")
    
    print(f"\nCalls: {len(calls)}")
    for c in calls[:5]:
        duration = f" ({c['duration_seconds'] // 60}m)" if c.get('duration_seconds') else ""
        print(f"  - {c['time']}{duration}")
    
    # Update report if requested
    if args.update_report:
        update_activity_report(date_str, hubspot_data, repo_path)


if __name__ == '__main__':
    main()
