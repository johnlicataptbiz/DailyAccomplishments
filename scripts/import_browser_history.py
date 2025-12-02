#!/usr/bin/env python3
"""
Import browser history from Chrome and Safari for today.
Reads directly from macOS SQLite databases - no API keys needed.

Usage:
    python3 scripts/import_browser_history.py [--date YYYY-MM-DD]
"""

import os
import sys
import json
import sqlite3
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
from typing import Optional

# Chrome stores timestamps as microseconds since 1601-01-01
CHROME_EPOCH = datetime(1601, 1, 1)

# Safari stores timestamps as seconds since 2001-01-01
SAFARI_EPOCH = datetime(2001, 1, 1)


def get_chrome_history_path() -> Path:
    """Get Chrome history database path on macOS."""
    return Path.home() / "Library/Application Support/Google/Chrome/Default/History"


def get_safari_history_path() -> Path:
    """Get Safari history database path on macOS."""
    return Path.home() / "Library/Safari/History.db"


def chrome_time_to_datetime(chrome_timestamp: int) -> datetime:
    """Convert Chrome timestamp to datetime."""
    return CHROME_EPOCH + timedelta(microseconds=chrome_timestamp)


def safari_time_to_datetime(safari_timestamp: float) -> datetime:
    """Convert Safari timestamp to datetime."""
    return SAFARI_EPOCH + timedelta(seconds=safari_timestamp)


def copy_db_safely(db_path: Path) -> Optional[str]:
    """Copy database to temp location (browsers lock their DBs)."""
    if not db_path.exists():
        return None
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_path = temp_file.name
    temp_file.close()
    
    shutil.copy2(db_path, temp_path)
    return temp_path


def get_chrome_history(target_date: datetime) -> list:
    """Get Chrome history for a specific date."""
    history = []
    db_path = get_chrome_history_path()
    
    if not db_path.exists():
        print(f"Chrome history not found at {db_path}")
        return history
    
    temp_db = copy_db_safely(db_path)
    if not temp_db:
        return history
    
    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get start and end of target date in Chrome timestamp format
        start_of_day = datetime(target_date.year, target_date.month, target_date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Convert to Chrome microseconds since 1601
        start_chrome = int((start_of_day - CHROME_EPOCH).total_seconds() * 1_000_000)
        end_chrome = int((end_of_day - CHROME_EPOCH).total_seconds() * 1_000_000)
        
        cursor.execute("""
            SELECT url, title, visit_count, last_visit_time
            FROM urls
            WHERE last_visit_time >= ? AND last_visit_time < ?
            ORDER BY last_visit_time DESC
        """, (start_chrome, end_chrome))
        
        for row in cursor.fetchall():
            url, title, visit_count, last_visit_time = row
            visit_dt = chrome_time_to_datetime(last_visit_time)
            
            history.append({
                'browser': 'Chrome',
                'url': url,
                'title': title or url,
                'visit_count': visit_count,
                'last_visit': visit_dt.isoformat(),
                'hour': visit_dt.hour
            })
        
        conn.close()
    except Exception as e:
        print(f"Error reading Chrome history: {e}")
    finally:
        os.unlink(temp_db)
    
    return history


def get_safari_history(target_date: datetime) -> list:
    """Get Safari history for a specific date."""
    history = []
    db_path = get_safari_history_path()
    
    if not db_path.exists():
        print(f"Safari history not found at {db_path}")
        return history
    
    temp_db = copy_db_safely(db_path)
    if not temp_db:
        return history
    
    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get start and end of target date in Safari timestamp format
        start_of_day = datetime(target_date.year, target_date.month, target_date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Convert to Safari seconds since 2001
        start_safari = (start_of_day - SAFARI_EPOCH).total_seconds()
        end_safari = (end_of_day - SAFARI_EPOCH).total_seconds()
        
        cursor.execute("""
            SELECT 
                history_items.url,
                history_visits.title,
                history_visits.visit_time
            FROM history_visits
            JOIN history_items ON history_visits.history_item = history_items.id
            WHERE history_visits.visit_time >= ? AND history_visits.visit_time < ?
            ORDER BY history_visits.visit_time DESC
        """, (start_safari, end_safari))
        
        for row in cursor.fetchall():
            url, title, visit_time = row
            visit_dt = safari_time_to_datetime(visit_time)
            
            history.append({
                'browser': 'Safari',
                'url': url,
                'title': title or url,
                'visit_count': 1,  # Safari doesn't aggregate like Chrome
                'last_visit': visit_dt.isoformat(),
                'hour': visit_dt.hour
            })
        
        conn.close()
    except Exception as e:
        print(f"Error reading Safari history: {e}")
    finally:
        os.unlink(temp_db)
    
    return history


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return 'unknown'


def categorize_url(url: str, title: str) -> str:
    """Categorize a URL into activity categories."""
    domain = extract_domain(url).lower()
    title_lower = (title or '').lower()
    url_lower = url.lower()
    
    # Communication
    if any(x in domain for x in ['slack.com', 'mail.google.com', 'gmail.com', 'outlook', 
                                   'messages', 'teams.microsoft', 'zoom.us', 'meet.google']):
        return 'Communication'
    
    # Meetings
    if any(x in domain for x in ['zoom.us', 'meet.google.com', 'teams.microsoft.com', 
                                   'calendly.com', 'hubspot.com/meetings']):
        return 'Meetings'
    
    # Coding/Development
    if any(x in domain for x in ['github.com', 'gitlab.com', 'stackoverflow.com', 
                                   'developer.', 'docs.python', 'npmjs.com', 'localhost']):
        return 'Coding'
    
    # Research/Learning
    if any(x in domain for x in ['google.com/search', 'bing.com', 'wikipedia.org', 
                                   'medium.com', 'dev.to', 'youtube.com']):
        return 'Research'
    
    # CRM/Sales
    if any(x in domain for x in ['hubspot.com', 'salesforce.com', 'pipedrive.com']):
        return 'CRM'
    
    # Docs/Productivity
    if any(x in domain for x in ['docs.google.com', 'sheets.google.com', 'notion.so',
                                   'airtable.com', 'asana.com', 'trello.com', 'monday.com']):
        return 'Docs'
    
    # Calendar
    if any(x in domain for x in ['calendar.google.com', 'outlook.office.com/calendar']):
        return 'Calendar'
    
    # Social (potential distraction)
    if any(x in domain for x in ['twitter.com', 'x.com', 'facebook.com', 'instagram.com',
                                   'linkedin.com', 'reddit.com', 'tiktok.com']):
        return 'Social'
    
    return 'Other'


def analyze_history(history: list) -> dict:
    """Analyze browser history and generate stats."""
    if not history:
        return {}
    
    # Domain visits
    domain_visits = defaultdict(int)
    domain_titles = {}
    
    # Hourly distribution
    hourly_visits = defaultdict(int)
    
    # Category breakdown
    category_visits = defaultdict(int)
    category_domains = defaultdict(set)
    
    # Page visits
    page_visits = defaultdict(int)
    page_titles = {}
    
    for item in history:
        domain = extract_domain(item['url'])
        title = item['title']
        hour = item['hour']
        category = categorize_url(item['url'], title)
        
        domain_visits[domain] += item.get('visit_count', 1)
        domain_titles[domain] = title
        
        hourly_visits[hour] += 1
        
        category_visits[category] += 1
        category_domains[category].add(domain)
        
        # Track individual pages (truncate long titles)
        page_key = item['url'][:100]
        page_visits[page_key] += 1
        page_titles[page_key] = (title or item['url'])[:80]
    
    # Sort domains by visits
    top_domains = sorted(domain_visits.items(), key=lambda x: -x[1])[:20]
    
    # Sort pages by visits
    top_pages = sorted(page_visits.items(), key=lambda x: -x[1])[:20]
    
    # Coverage window
    if history:
        times = [datetime.fromisoformat(h['last_visit']) for h in history]
        earliest = min(times)
        latest = max(times)
        coverage = f"{earliest.strftime('%H:%M')}–{latest.strftime('%H:%M')}"
    else:
        coverage = "No data"
    
    return {
        'total_visits': len(history),
        'unique_domains': len(domain_visits),
        'coverage_window': coverage,
        'top_domains': [
            {'domain': d, 'visits': v, 'sample_title': domain_titles.get(d, '')}
            for d, v in top_domains
        ],
        'top_pages': [
            {'page': page_titles.get(url, url), 'url': url, 'visits': v}
            for url, v in top_pages
        ],
        'hourly_distribution': dict(sorted(hourly_visits.items())),
        'by_category': dict(sorted(category_visits.items(), key=lambda x: -x[1])),
        'category_domains': {k: list(v)[:5] for k, v in category_domains.items()}
    }


def update_activity_report(date_str: str, browser_data: dict, repo_path: Path):
    """Update the ActivityReport JSON with browser data."""
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
            "browser_highlights": {},
            "by_category": {},
            "hourly_focus": []
        }
    
    # Update browser highlights
    report['browser_highlights'] = {
        'total_visits': browser_data.get('total_visits', 0),
        'unique_domains': browser_data.get('unique_domains', 0),
        'top_domains': browser_data.get('top_domains', []),
        'top_pages': browser_data.get('top_pages', []),
        'by_category': browser_data.get('by_category', {}),
        'coverage_window': browser_data.get('coverage_window', '')
    }
    
    # Merge category data
    if 'by_category' not in report:
        report['by_category'] = {}
    existing_categories = report['by_category']
    for cat, count in browser_data.get('by_category', {}).items():
        # Convert visit count to rough time estimate (30 sec per visit)
        minutes = count // 2
        time_str = f"{minutes // 60:02d}:{minutes % 60:02d}"
        if cat not in existing_categories:
            existing_categories[cat] = time_str
    
    # Update coverage window to include browser data
    if browser_data.get('coverage_window'):
        if 'overview' not in report:
            report['overview'] = {}
        overview = report['overview']
        existing_coverage = overview.get('coverage_window', '')
        browser_coverage = browser_data['coverage_window']
        if not existing_coverage or existing_coverage == 'In progress...':
            overview['coverage_window'] = f"{browser_coverage} (browser)"
    
    # Add browser stats to executive summary
    if 'executive_summary' not in report:
        report['executive_summary'] = []
    exec_summary = report['executive_summary']
    browser_summary = f"Visited {browser_data.get('unique_domains', 0)} unique domains ({browser_data.get('total_visits', 0)} page views)"
    if browser_summary not in exec_summary:
        exec_summary.append(browser_summary)
    
    # Save
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Updated {report_file}")
    return report_file


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import browser history')
    parser.add_argument('--date', type=str, help='Date to import (YYYY-MM-DD), defaults to today')
    parser.add_argument('--output', type=str, help='Output JSON file')
    parser.add_argument('--update-report', action='store_true', help='Update ActivityReport JSON')
    parser.add_argument('--repo', type=str, default=os.path.expanduser('~/DailyAccomplishments'),
                        help='Path to repo')
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    date_str = target_date.strftime('%Y-%m-%d')
    print(f"Importing browser history for {date_str}...")
    
    # Get history from both browsers
    chrome_history = get_chrome_history(target_date)
    print(f"  Chrome: {len(chrome_history)} entries")
    
    safari_history = get_safari_history(target_date)
    print(f"  Safari: {len(safari_history)} entries")
    
    # Combine and analyze
    all_history = chrome_history + safari_history
    print(f"  Total: {len(all_history)} entries")
    
    if not all_history:
        print("No browser history found for this date.")
        return
    
    # Analyze
    analysis = analyze_history(all_history)
    
    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        repo_path = Path(args.repo)
        repo_path.mkdir(parents=True, exist_ok=True)
        output_path = repo_path / 'logs' / f'browser-history-{date_str}.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'date': date_str,
            'raw_entries': len(all_history),
            'analysis': analysis,
            'entries': all_history[:100]  # Keep first 100 for reference
        }, f, indent=2)
    
    print(f"\nSaved to {output_path}")
    
    # Print summary
    print(f"\n=== Browser History Summary for {date_str} ===")
    print(f"Coverage: {analysis.get('coverage_window', 'N/A')}")
    print(f"Total visits: {analysis.get('total_visits', 0)}")
    print(f"Unique domains: {analysis.get('unique_domains', 0)}")
    
    print("\nTop 10 Domains:")
    for i, d in enumerate(analysis.get('top_domains', [])[:10], 1):
        print(f"  {i}. {d['domain']} ({d['visits']} visits)")
    
    print("\nBy Category:")
    for cat, count in analysis.get('by_category', {}).items():
        print(f"  {cat}: {count} visits")
    
    # Update ActivityReport if requested
    if args.update_report:
        repo_path = Path(args.repo)
        update_activity_report(date_str, analysis, repo_path)


if __name__ == '__main__':
    main()
