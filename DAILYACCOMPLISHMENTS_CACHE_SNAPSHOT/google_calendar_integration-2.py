#!/usr/bin/env python3
"""
Google Calendar Integration for Daily Accomplishments.

Fetches calendar events and meetings for a given date.

Setup:
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials JSON file
6. Save as ~/DailyAccomplishments/credentials/google_credentials.json

First run will open a browser for OAuth consent.

Usage:
    python3 scripts/google_calendar_integration.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pickle

# Google API imports - install with: pip install google-auth-oauthlib google-api-python-client
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Google API not installed. Run: pip install google-auth-oauthlib google-api-python-client")

# Scopes for read-only calendar access
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Paths
REPO_PATH = Path.home() / "DailyAccomplishments"
CREDENTIALS_DIR = REPO_PATH / "credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "google_credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "google_token.pickle"


class GoogleCalendarClient:
    def __init__(self):
        self.service = None
        self.creds = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API."""
        if not GOOGLE_API_AVAILABLE:
            print("Error: Google API libraries not installed")
            return False
            
        if not CREDENTIALS_FILE.exists():
            print(f"Error: Credentials file not found at {CREDENTIALS_FILE}")
            print("\nSetup instructions:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create/select a project")
            print("3. Enable 'Google Calendar API'")
            print("4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID")
            print("5. Choose 'Desktop app'")
            print("6. Download JSON and save to:")
            print(f"   {CREDENTIALS_FILE}")
            return False
        
        # Load existing token
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'rb') as token:
                self.creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    self.creds = None
            
            if not self.creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save token for next run
            CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
        
        # Build the service
        self.service = build('calendar', 'v3', credentials=self.creds)
        return True
    
    def get_events_for_date(self, date: datetime) -> list:
        """Get all calendar events for a specific date."""
        if not self.service:
            if not self.authenticate():
                return []
        
        # Set time range for the date (in local timezone)
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Convert to RFC3339 format
        time_min = start_of_day.isoformat() + 'Z'
        time_max = end_of_day.isoformat() + 'Z'
        
        events = []
        
        try:
            # Get events from primary calendar
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            for event in events_result.get('items', []):
                # Parse start time
                start = event.get('start', {})
                start_time = start.get('dateTime') or start.get('date')
                
                # Parse end time
                end = event.get('end', {})
                end_time = end.get('dateTime') or end.get('date')
                
                # Calculate duration
                duration_minutes = 0
                time_str = ""
                if start.get('dateTime') and end.get('dateTime'):
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                    time_str = f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}"
                elif start.get('date'):
                    # All-day event
                    time_str = "All day"
                    duration_minutes = 480  # Assume 8 hours for all-day
                
                # Determine event type
                event_type = "meeting"
                summary = event.get('summary', 'Untitled Event').lower()
                if any(word in summary for word in ['call', 'discovery', 'demo', 'consultation']):
                    event_type = "appointment"
                elif any(word in summary for word in ['standup', 'sync', 'team', '1:1', 'one on one']):
                    event_type = "meeting"
                elif any(word in summary for word in ['focus', 'block', 'work time', 'deep work']):
                    event_type = "focus_block"
                
                # Get attendees
                attendees = []
                for attendee in event.get('attendees', []):
                    email = attendee.get('email', '')
                    name = attendee.get('displayName', email.split('@')[0])
                    if not attendee.get('self'):  # Exclude yourself
                        attendees.append(name)
                
                events.append({
                    'id': event.get('id'),
                    'name': event.get('summary', 'Untitled Event'),
                    'time': time_str,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': duration_minutes,
                    'event_type': event_type,
                    'location': event.get('location', ''),
                    'description': (event.get('description', '') or '')[:200],
                    'attendees': attendees,
                    'status': event.get('status', 'confirmed'),
                    'hangout_link': event.get('hangoutLink', ''),
                    'source': 'Google Calendar'
                })
                
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
        
        return events
    
    def get_all_calendars(self) -> list:
        """List all calendars the user has access to."""
        if not self.service:
            if not self.authenticate():
                return []
        
        calendars = []
        try:
            calendar_list = self.service.calendarList().list().execute()
            for cal in calendar_list.get('items', []):
                calendars.append({
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'primary': cal.get('primary', False)
                })
        except Exception as e:
            print(f"Error fetching calendar list: {e}")
        
        return calendars


def update_activity_report(date_str: str, calendar_data: list, repo_path: Path):
    """Update ActivityReport with Google Calendar data."""
    report_file = repo_path / f"ActivityReport-{date_str}.json"
    
    if report_file.exists():
        with open(report_file) as f:
            report = json.load(f)
    else:
        report = {
            "date": date_str,
            "overview": {"appointments": 0},
            "debug_appointments": {"meetings_today": [], "appointments_today": []}
        }
    
    # Ensure structure exists
    if 'debug_appointments' not in report:
        report['debug_appointments'] = {'meetings_today': [], 'appointments_today': []}
    
    meetings_list = report['debug_appointments'].setdefault('meetings_today', [])
    appointments_list = report['debug_appointments'].setdefault('appointments_today', [])
    
    # Track existing to avoid duplicates
    existing_meetings = {m.get('name', '').lower() for m in meetings_list}
    existing_appts = {a.get('name', '').lower() for a in appointments_list}
    
    total_meeting_seconds = 0
    
    for event in calendar_data:
        name = event['name']
        name_lower = name.lower()
        
        entry = {
            "name": name,
            "time": event['time'],
            "duration_minutes": event['duration_minutes'],
            "attendees": event.get('attendees', []),
            "source": "Google Calendar"
        }
        
        if event['event_type'] == 'appointment':
            if name_lower not in existing_appts:
                appointments_list.append(entry)
                existing_appts.add(name_lower)
        elif event['event_type'] in ('meeting', 'focus_block'):
            if name_lower not in existing_meetings:
                meetings_list.append(entry)
                existing_meetings.add(name_lower)
                total_meeting_seconds += event['duration_minutes'] * 60
    
    # Update overview
    if 'overview' not in report:
        report['overview'] = {}
    report['overview']['appointments'] = len(appointments_list)
    
    # Update meetings time if we added meetings
    if total_meeting_seconds > 0:
        existing_meeting_time = report['overview'].get('meetings_time', '00:00')
        try:
            parts = existing_meeting_time.split(':')
            existing_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60
        except:
            existing_seconds = 0
        
        total_seconds = existing_seconds + total_meeting_seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        report['overview']['meetings_time'] = f"{hours:02d}:{minutes:02d}"
    
    # Add Google Calendar section
    report['google_calendar'] = {
        'events': calendar_data,
        'total_events': len(calendar_data),
        'meetings': len([e for e in calendar_data if e['event_type'] == 'meeting']),
        'appointments': len([e for e in calendar_data if e['event_type'] == 'appointment'])
    }
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Google Calendar events')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--list-calendars', action='store_true', help='List available calendars')
    parser.add_argument('--repo', type=str, default=str(REPO_PATH), help='Path to repo')
    args = parser.parse_args()
    
    client = GoogleCalendarClient()
    
    if args.list_calendars:
        print("Authenticating...")
        if client.authenticate():
            print("\nAvailable calendars:")
            for cal in client.get_all_calendars():
                primary = " (primary)" if cal['primary'] else ""
                print(f"  - {cal['summary']}{primary}")
        return
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Fetching Google Calendar events for {date_str}...")
    
    events = client.get_events_for_date(target_date)
    
    if not events:
        print("No events found for this date.")
        return
    
    print(f"\n=== Calendar Events for {date_str} ===")
    for event in events:
        attendees_str = f" with {', '.join(event['attendees'][:3])}" if event['attendees'] else ""
        print(f"  {event['time']}: {event['name']}{attendees_str}")
    
    # Update report if requested
    if args.update_report:
        update_activity_report(date_str, events, Path(args.repo))


if __name__ == '__main__':
    main()
