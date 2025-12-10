#!/usr/bin/env python3
"""
Monday.com Integration for Daily Accomplishments.

Fetches tasks, updates, and activity from Monday.com boards.

Setup:
1. Go to Monday.com → Your Avatar → Developers
2. Click "Developer" → "My Access Tokens"
3. Create a new token with read access
4. Add to config.json:
   {
     "monday": {
       "api_token": "your-api-token",
       "board_ids": [123456789]  # Optional: specific boards to track
     }
   }

Usage:
    python3 scripts/monday_integration.py [--date YYYY-MM-DD]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import requests

# Monday.com GraphQL API
MONDAY_API = "https://api.monday.com/v2"

# Paths
REPO_PATH = Path.home() / "DailyAccomplishments"


class MondayClient:
    def __init__(self, api_token: str, board_ids: Optional[List[int]] = None):
        self.api_token = api_token
        self.board_ids = board_ids or []
        self.headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }
    
    def _query(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        response = requests.post(
            MONDAY_API,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code == 401:
            raise Exception("Invalid Monday.com API token. Check your config.json")
        
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"Monday.com API error: {data['errors']}")
        
        return data.get("data", {})
    
    def get_boards(self) -> list:
        """Get all boards the user has access to."""
        query = """
        query {
            boards(limit: 50) {
                id
                name
                state
                board_kind
            }
        }
        """
        data = self._query(query)
        return data.get("boards", [])
    
    def get_items_updated_on_date(self, date: datetime) -> list:
        """Get all items updated on a specific date."""
        items = []
        
        # Get boards to search
        if self.board_ids:
            boards_to_check = [{"id": str(bid)} for bid in self.board_ids]
        else:
            boards_to_check = self.get_boards()
        
        date_str = date.strftime("%Y-%m-%d")
        
        for board in boards_to_check:
            board_id = board.get("id")
            if not board_id:
                continue
            
            try:
                # Query items from this board
                query = """
                query ($boardId: ID!) {
                    boards(ids: [$boardId]) {
                        name
                        items_page(limit: 100) {
                            items {
                                id
                                name
                                state
                                created_at
                                updated_at
                                column_values {
                                    id
                                    text
                                    type
                                }
                                updates(limit: 5) {
                                    id
                                    body
                                    created_at
                                    creator {
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
                """
                
                data = self._query(query, {"boardId": board_id})
                
                for board_data in data.get("boards", []):
                    board_name = board_data.get("name", "Unknown Board")
                    items_page = board_data.get("items_page", {})
                    
                    for item in items_page.get("items", []):
                        updated_at = item.get("updated_at", "")
                        
                        # Check if updated on target date
                        if updated_at and updated_at.startswith(date_str):
                            # Get status column
                            status = ""
                            for col in item.get("column_values", []):
                                if col.get("type") == "status":
                                    status = col.get("text", "")
                                    break
                            
                            # Get recent updates
                            updates = []
                            for update in item.get("updates", []):
                                update_date = update.get("created_at", "")
                                if update_date.startswith(date_str):
                                    updates.append({
                                        "body": update.get("body", "")[:200],
                                        "creator": update.get("creator", {}).get("name", "Unknown"),
                                        "created_at": update_date
                                    })
                            
                            items.append({
                                "id": item.get("id"),
                                "name": item.get("name", "Untitled"),
                                "board": board_name,
                                "board_id": board_id,
                                "status": status,
                                "state": item.get("state", ""),
                                "created_at": item.get("created_at", ""),
                                "updated_at": updated_at,
                                "updates_today": updates,
                                "source": "Monday.com"
                            })
                            
            except Exception as e:
                print(f"Error fetching board {board_id}: {e}")
        
        return items
    
    def get_activity_log(self, date: datetime) -> list:
        """Get activity log for the date."""
        activities = []
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Note: Activity log requires admin access in some cases
        # This is a simplified version that gets updates from items
        
        items = self.get_items_updated_on_date(date)
        
        for item in items:
            for update in item.get("updates_today", []):
                activities.append({
                    "type": "update",
                    "item": item.get("name"),
                    "board": item.get("board"),
                    "body": update.get("body"),
                    "creator": update.get("creator"),
                    "created_at": update.get("created_at"),
                    "source": "Monday.com"
                })
        
        return activities


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


def update_activity_report(date_str: str, monday_data: dict, repo_path: Path):
    """Update ActivityReport with Monday.com data."""
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
    
    # Add Monday.com section
    report['monday'] = monday_data
    
    # Add task stats to overview
    if 'overview' not in report:
        report['overview'] = {}
    
    report['overview']['tasks_updated'] = monday_data.get('items_updated', 0)
    report['overview']['updates_made'] = monday_data.get('updates_count', 0)
    
    # Add to executive summary
    if 'executive_summary' not in report:
        report['executive_summary'] = []
    
    summary_parts = []
    if monday_data.get('items_updated'):
        summary_parts.append(f"{monday_data['items_updated']} tasks updated")
    if monday_data.get('updates_count'):
        summary_parts.append(f"{monday_data['updates_count']} updates")
    
    # Count by board
    boards_touched = set(item.get('board') for item in monday_data.get('items', []))
    if boards_touched:
        summary_parts.append(f"across {len(boards_touched)} boards")
    
    if summary_parts:
        monday_summary = f"Monday.com: {', '.join(summary_parts)}"
        if monday_summary not in report['executive_summary']:
            report['executive_summary'].append(monday_summary)
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Monday.com data')
    parser.add_argument('--date', type=str, help='Date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--token', type=str, help='Monday.com API token (or use config.json)')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--list-boards', action='store_true', help='List available boards')
    parser.add_argument('--repo', type=str, default=str(REPO_PATH), help='Path to repo')
    args = parser.parse_args()
    
    # Get API token
    api_token = args.token
    board_ids = []
    if not api_token:
        config = load_config()
        monday_config = config.get('monday', {})
        api_token = monday_config.get('api_token')
        board_ids = monday_config.get('board_ids', [])
    
    if not api_token:
        print("Error: No Monday.com API token found.")
        print("\nTo set up Monday.com integration:")
        print("1. Go to Monday.com → Your Avatar → Developers")
        print("2. Click 'Developer' → 'My Access Tokens'")
        print("3. Create a new token")
        print("4. Add to ~/DailyAccomplishments/config.json:")
        print('   {"monday": {"api_token": "your-token"}}')
        sys.exit(1)
    
    # Create client
    client = MondayClient(api_token, board_ids)
    
    if args.list_boards:
        print("Fetching boards...")
        boards = client.get_boards()
        print("\nAvailable boards:")
        for board in boards:
            print(f"  - {board['name']} (ID: {board['id']}, {board['board_kind']})")
        return
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Fetching Monday.com data for {date_str}...")
    
    # Get items updated today
    items = client.get_items_updated_on_date(target_date)
    
    # Count updates
    total_updates = sum(len(item.get('updates_today', [])) for item in items)
    
    # Compile data
    monday_data = {
        'date': date_str,
        'items': items,
        'items_updated': len(items),
        'updates_count': total_updates,
        'by_board': {}
    }
    
    # Group by board
    for item in items:
        board = item.get('board', 'Unknown')
        if board not in monday_data['by_board']:
            monday_data['by_board'][board] = []
        monday_data['by_board'][board].append(item['name'])
    
    print(f"\n=== Monday.com Summary for {date_str} ===")
    print(f"Items Updated: {len(items)}")
    print(f"Total Updates: {total_updates}")
    
    if items:
        print("\nItems by Board:")
        for board, item_names in monday_data['by_board'].items():
            print(f"\n  {board}:")
            for name in item_names[:5]:
                print(f"    - {name}")
            if len(item_names) > 5:
                print(f"    ... and {len(item_names) - 5} more")
    
    # Update report if requested
    if args.update_report:
        update_activity_report(date_str, monday_data, Path(args.repo))


if __name__ == '__main__':
    main()
