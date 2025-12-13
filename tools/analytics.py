#!/usr/bin/env python3
"""
Productivity Analytics Engine

Analyzes daily logs to provide insights on:
- Deep work sessions
- Interruptions and context switches
- Productivity metrics
- Category trends
- Meeting efficiency
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from zoneinfo import ZoneInfo
from collections import defaultdict

if __package__:
    from .daily_logger import read_daily_log, load_config, get_log_path, LOG_DIR
else:  # pragma: no cover - for direct script execution
    from daily_logger import read_daily_log, load_config, get_log_path, LOG_DIR

logger = logging.getLogger(__name__)


class ProductivityAnalytics:
    """Analyze productivity patterns from daily logs"""
    
    def __init__(self, date: Optional[datetime] = None):
        """Initialize analytics for a specific date"""
        self.config = load_config()
        self.tz = ZoneInfo(self.config['tracking']['timezone'])
        self.date = date or datetime.now(self.tz)
        self.events: List[Dict[str, Any]] = read_daily_log(self.date)
        
        # Thresholds (configurable)
        self.deep_work_threshold_minutes = 25  # Minimum for deep work
        self.interruption_window_seconds = 300  # 5 minutes
        self.context_switch_cost_seconds = 60  # Assumed cost per switch
    
    def detect_deep_work_sessions(self) -> List[Dict[str, Any]]:
        """
        Identify uninterrupted focus sessions >= threshold minutes
        
        Returns list of sessions with:
        - start_time, end_time, duration_minutes
        - app, activity_type
        - interruption_count
        """
        sessions: List[Dict[str, Any]] = []
        current_session: Optional[Dict[str, Any]] = None
        
        for event in self.events:
            if event.get('type') == 'metadata':
                continue
            
            event_type = event.get('type')
            ts_str = event.get('timestamp')
            if not ts_str:
                continue
            timestamp = datetime.fromisoformat(ts_str)
            data = event.get('data', {})
            
            if event_type == 'focus_change':
                duration = data.get('duration_seconds', 0)
                app = data.get('app', '')
                
                # Start new session or extend current
                if current_session is None:
                    current_session = {
                        'start_time': timestamp,
                        'end_time': timestamp + timedelta(seconds=duration),
                        'total_seconds': duration,
                        'app': app,
                        'interruptions': 0,
                        'events': [event]
                    }
                else:
                    # Check if this continues the session (within 5 min)
                    end_time: datetime = current_session['end_time']
                    gap = (timestamp - end_time).total_seconds()
                    
                    if gap <= self.interruption_window_seconds:
                        # Continue session
                        current_session['end_time'] = timestamp + timedelta(seconds=duration)
                        current_session['total_seconds'] += duration
                        events_list: List[Dict[str, Any]] = current_session['events']
                        events_list.append(event)
                    else:
                        # Gap too large, end current session
                        total_secs: int = current_session['total_seconds']
                        if total_secs >= self.deep_work_threshold_minutes * 60:
                            sessions.append(self._finalize_session(current_session))
                        
                        # Start new session
                        current_session = {
                            'start_time': timestamp,
                            'end_time': timestamp + timedelta(seconds=duration),
                            'total_seconds': duration,
                            'app': app,
                            'interruptions': 0,
                            'events': [event]
                        }
            
            elif event_type in ['app_switch', 'window_change']:
                # Count as interruption if in a session
                if current_session:
                    interrupts: int = current_session['interruptions']
                    current_session['interruptions'] = interrupts + 1
        
        # Finalize last session
        if current_session:
            total_secs_final: int = current_session['total_seconds']
            if total_secs_final >= self.deep_work_threshold_minutes * 60:
                sessions.append(self._finalize_session(current_session))
        
        return sessions
    
    def _finalize_session(self, session: Dict) -> Dict[str, Any]:
        """Convert session dict to final format"""
        duration_minutes = session['total_seconds'] / 60
        
        return {
            'start_time': session['start_time'].isoformat(),
            'end_time': session['end_time'].isoformat(),
            'duration_minutes': round(duration_minutes, 1),
            'app': session['app'],
            'interruptions': session['interruptions'],
            'quality_score': self._calculate_quality_score(session)
        }
    
    def _calculate_quality_score(self, session: Dict) -> float:
        """
        Calculate session quality (0-100)
        Based on: duration, interruptions, time of day
        """
        score = 100.0
        
        # Penalty for interruptions (5 points each)
        score -= session['interruptions'] * 5
        
        # Bonus for longer sessions (up to 2 hours)
        duration_minutes = session['total_seconds'] / 60
        if duration_minutes >= 120:
            score += 20
        elif duration_minutes >= 60:
            score += 10
        
        # Time of day bonus (morning = better focus)
        hour = session['start_time'].hour
        if 8 <= hour <= 11:
            score += 10  # Morning bonus
        elif 14 <= hour <= 16:
            score -= 5  # Post-lunch dip
        
        return max(0, min(100, score))
    
    def analyze_interruptions(self) -> Dict[str, Any]:
        """
        Analyze interruption patterns
        
        Returns:
        - interruptions_per_hour: dict of hour -> count
        - most_disruptive_hour: hour with most interruptions
        - total_interruptions: total count
        - context_switch_cost_minutes: estimated time lost
        """
        interruptions_by_hour = defaultdict(int)
        total_interruptions = 0
        
        for event in self.events:
            event_type = event.get('type')
            
            if event_type in ['app_switch', 'window_change']:
                ts_str = event.get('timestamp')
                if not ts_str:
                    continue
                timestamp = datetime.fromisoformat(ts_str)
                hour = timestamp.hour
                interruptions_by_hour[hour] += 1
                total_interruptions += 1
        
        # Find peak hour
        most_disruptive_hour = None
        max_count = 0
        
        for hour, count in interruptions_by_hour.items():
            if count > max_count:
                max_count = count
                most_disruptive_hour = hour
        
        # Estimate context switch cost
        cost_minutes = (total_interruptions * self.context_switch_cost_seconds) / 60
        
        return {
            'interruptions_per_hour': dict(interruptions_by_hour),
            'most_disruptive_hour': most_disruptive_hour,
            'max_interruptions': max_count,
            'total_interruptions': total_interruptions,
            'context_switch_cost_minutes': round(cost_minutes, 1),
            'average_per_hour': round(total_interruptions / 24, 1) if total_interruptions else 0
        }
    
    def calculate_productivity_score(self) -> Dict[str, Any]:
        """
        Calculate overall productivity score (0-100)
        
        Factors:
        - Deep work time percentage
        - Interruption frequency
        - Meeting efficiency
        - Focus consistency
        """
        deep_sessions = self.detect_deep_work_sessions()
        interruption_data = self.analyze_interruptions()
        
        # Calculate components
        total_deep_minutes = sum(s['duration_minutes'] for s in deep_sessions)
        total_work_minutes = self._calculate_total_work_time()
        
        # Deep work percentage (0-40 points)
        deep_work_pct = (total_deep_minutes / total_work_minutes * 100) if total_work_minutes else 0
        deep_work_score = min(40, deep_work_pct * 0.4)
        
        # Low interruption bonus (0-30 points)
        interruption_score = max(0, 30 - interruption_data['total_interruptions'])
        
        # Session quality average (0-30 points)
        quality_scores = [s['quality_score'] for s in deep_sessions]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        quality_score = avg_quality * 0.3
        
        total_score = deep_work_score + interruption_score + quality_score
        
        return {
            'overall_score': round(total_score, 1),
            'components': {
                'deep_work_score': round(deep_work_score, 1),
                'interruption_score': round(interruption_score, 1),
                'quality_score': round(quality_score, 1)
            },
            'metrics': {
                'total_deep_minutes': round(total_deep_minutes, 1),
                'total_work_minutes': round(total_work_minutes, 1),
                'deep_work_percentage': round(deep_work_pct, 1),
                'deep_sessions_count': len(deep_sessions)
            },
            'rating': self._get_rating(total_score)
        }
    
    def _calculate_total_work_time(self) -> float:
        """Calculate total work time in minutes"""
        total_seconds = 0
        
        for event in self.events:
            if event.get('type') == 'focus_change':
                total_seconds += event.get('data', {}).get('duration_seconds', 0)
        
        return total_seconds / 60
    
    def _get_rating(self, score: float) -> str:
        """Convert score to rating"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Improvement"
    
    def analyze_category_trends(self) -> Dict[str, Any]:
        """
        Analyze time distribution across categories
        
        Returns category breakdown with trends
        """
        category_time = defaultdict(int)
        category_events = defaultdict(int)
        
        for event in self.events:
            if event.get('type') == 'focus_change':
                data = event.get('data', {})
                app = data.get('app', '')
                duration = data.get('duration_seconds', 0)
                
                category = self._categorize_app(app)
                category_time[category] += duration
                category_events[category] += 1
        
        # Calculate percentages
        total_time = sum(category_time.values())
        
        categories = []
        for cat, seconds in category_time.items():
            pct = (seconds / total_time * 100) if total_time else 0
            categories.append({
                'category': cat,
                'time_minutes': round(seconds / 60, 1),
                'percentage': round(pct, 1),
                'event_count': category_events[cat],
                'avg_duration_minutes': round(seconds / category_events[cat] / 60, 1)
            })
        
        # Sort by time descending
        categories.sort(key=lambda x: x['time_minutes'], reverse=True)
        
        return {
            'categories': categories,
            'total_time_minutes': round(total_time / 60, 1),
            'top_category': categories[0]['category'] if categories else None,
            'category_count': len(categories)
        }
    
    def _categorize_app(self, app: str) -> str:
        """Categorize app into productivity type"""
        app_lower = app.lower()
        
        if any(word in app_lower for word in ['chrome', 'firefox', 'safari', 'browser']):
            return 'Research'
        elif any(word in app_lower for word in ['code', 'terminal', 'iterm', 'pycharm', 'intellij', 'vim']):
            return 'Coding'
        elif any(word in app_lower for word in ['slack', 'zoom', 'teams', 'meet', 'skype']):
            return 'Meetings'
        elif any(word in app_lower for word in ['mail', 'outlook', 'gmail', 'messages']):
            return 'Communication'
        elif any(word in app_lower for word in ['word', 'excel', 'sheets', 'docs', 'notion', 'obsidian']):
            return 'Docs'
        else:
            return 'Other'
    
    def analyze_meeting_efficiency(self) -> Dict[str, Any]:
        """
        Analyze meeting time and efficiency
        
        Returns:
        - total_meeting_time
        - meeting_count
        - average_duration
        - meeting_vs_focus_ratio
        """
        meeting_times = []
        meeting_names = []
        
        for event in self.events:
            if event.get('type') == 'meeting_end':
                data = event.get('data', {})
                duration = data.get('duration_seconds', 0)
                name = data.get('name', 'Unknown')
                
                meeting_times.append(duration)
                meeting_names.append(name)
        
        total_meeting_seconds = sum(meeting_times)
        meeting_count = len(meeting_times)
        avg_duration = total_meeting_seconds / meeting_count if meeting_count else 0
        
        # Calculate focus time
        total_focus_seconds = sum(
            e.get('data', {}).get('duration_seconds', 0)
            for e in self.events
            if e.get('type') == 'focus_change'
        )
        
        # Meeting vs focus ratio
        ratio = total_meeting_seconds / total_focus_seconds if total_focus_seconds else 0
        
        return {
            'total_meeting_minutes': round(total_meeting_seconds / 60, 1),
            'meeting_count': meeting_count,
            'average_duration_minutes': round(avg_duration / 60, 1),
            'meeting_vs_focus_ratio': round(ratio, 2),
            'meetings': meeting_names,
            'recommendation': self._get_meeting_recommendation(ratio)
        }
    
    def _get_meeting_recommendation(self, ratio: float) -> str:
        """Provide recommendation based on meeting/focus ratio"""
        if ratio > 0.5:
            return "Too many meetings - consider declining or delegating some"
        elif ratio > 0.3:
            return "Meeting load is moderate - ensure quality focus time remains"
        else:
            return "Good balance between meetings and focus work"
    
    def suggest_focus_windows(self) -> List[Dict[str, Any]]:
        """
        Suggest optimal time windows for deep work based on historical data
        
        Returns suggested time blocks with rationale
        """
        interruption_data = self.analyze_interruptions()
        interruptions_by_hour = interruption_data['interruptions_per_hour']
        
        # Find hours with low interruptions
        quiet_hours = []
        
        for hour in range(6, 23):  # 6am to 11pm
            interruptions = interruptions_by_hour.get(hour, 0)
            
            if interruptions <= 2:  # Low interruption threshold
                quiet_hours.append({
                    'hour': hour,
                    'time': f"{hour:02d}:00",
                    'interruptions': interruptions,
                    'quality': 'Excellent' if interruptions == 0 else 'Good'
                })
        
        # Group consecutive hours
        windows = []
        current_window = []
        
        for i, hour_data in enumerate(quiet_hours):
            if not current_window:
                current_window = [hour_data]
            elif hour_data['hour'] == current_window[-1]['hour'] + 1:
                current_window.append(hour_data)
            else:
                if len(current_window) >= 2:  # At least 2 hours
                    windows.append(self._format_window(current_window))
                current_window = [hour_data]
        
        # Add last window
        if len(current_window) >= 2:
            windows.append(self._format_window(current_window))
        
        return windows
    
    def _format_window(self, hours: List[Dict]) -> Dict[str, Any]:
        """Format window data"""
        start_hour = hours[0]['hour']
        end_hour = hours[-1]['hour'] + 1
        total_interruptions = sum(h['interruptions'] for h in hours)
        
        return {
            'start_time': f"{start_hour:02d}:00",
            'end_time': f"{end_hour:02d}:00",
            'duration_hours': len(hours),
            'total_interruptions': total_interruptions,
            'quality': 'Excellent' if total_interruptions == 0 else 'Good',
            'recommendation': f"Schedule deep work during {start_hour:02d}:00-{end_hour:02d}:00"
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'deep_work_sessions': self.detect_deep_work_sessions(),
            'interruption_analysis': self.analyze_interruptions(),
            'productivity_score': self.calculate_productivity_score(),
            'category_trends': self.analyze_category_trends(),
            'meeting_efficiency': self.analyze_meeting_efficiency(),
            'focus_windows': self.suggest_focus_windows()
        }


def compare_trends(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Compare productivity trends across a date range
    
    Returns aggregated metrics and trends
    """
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    
    daily_scores = []
    daily_deep_minutes = []
    daily_interruptions = []
    
    current = start_date
    while current <= end_date:
        analytics = ProductivityAnalytics(current)
        
        score_data = analytics.calculate_productivity_score()
        interruption_data = analytics.analyze_interruptions()
        
        daily_scores.append(score_data['overall_score'])
        daily_deep_minutes.append(score_data['metrics']['total_deep_minutes'])
        daily_interruptions.append(interruption_data['total_interruptions'])
        
        current += timedelta(days=1)
    
    # Calculate trends
    avg_score = sum(daily_scores) / len(daily_scores) if daily_scores else 0
    avg_deep_minutes = sum(daily_deep_minutes) / len(daily_deep_minutes) if daily_deep_minutes else 0
    avg_interruptions = sum(daily_interruptions) / len(daily_interruptions) if daily_interruptions else 0
    
    # Trend direction
    score_trend = 'improving' if daily_scores[-1] > daily_scores[0] else 'declining'
    
    return {
        'period': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'days': len(daily_scores)
        },
        'averages': {
            'productivity_score': round(avg_score, 1),
            'deep_work_minutes': round(avg_deep_minutes, 1),
            'interruptions': round(avg_interruptions, 1)
        },
        'trends': {
            'score_trend': score_trend,
            'score_change': round(daily_scores[-1] - daily_scores[0], 1) if daily_scores else 0
        },
        'daily_data': {
            'scores': daily_scores,
            'deep_minutes': daily_deep_minutes,
            'interruptions': daily_interruptions
        }
    }


def main():
    """Main entry point for testing"""
    config = load_config()
    tz = ZoneInfo(config['tracking']['timezone'])
    today = datetime.now(tz)
    
    print("Productivity Analytics Report")
    print("=" * 60)
    
    analytics = ProductivityAnalytics(today)
    report = analytics.generate_report()
    
    print(f"\nDate: {report['date']}")
    print(f"\nProductivity Score: {report['productivity_score']['overall_score']}/100 ({report['productivity_score']['rating']})")
    
    print(f"\nDeep Work Sessions: {len(report['deep_work_sessions'])}")
    for i, session in enumerate(report['deep_work_sessions'][:3], 1):
        print(f"  {i}. {session['duration_minutes']}min starting at {session['start_time'][-8:-3]} "
              f"(quality: {session['quality_score']}/100)")
    
    print(f"\nInterruptions: {report['interruption_analysis']['total_interruptions']} total")
    print(f"  Most disruptive hour: {report['interruption_analysis']['most_disruptive_hour']}:00 "
          f"({report['interruption_analysis']['max_interruptions']} interruptions)")
    
    print(f"\nCategory Breakdown:")
    for cat in report['category_trends']['categories'][:5]:
        print(f"  {cat['category']}: {cat['time_minutes']}min ({cat['percentage']}%)")
    
    print(f"\nMeetings: {report['meeting_efficiency']['meeting_count']} "
          f"({report['meeting_efficiency']['total_meeting_minutes']}min total)")
    print(f"  {report['meeting_efficiency']['recommendation']}")
    
    print(f"\nSuggested Focus Windows:")
    for window in report['focus_windows']:
        print(f"  {window['start_time']}-{window['end_time']} ({window['duration_hours']}h, {window['quality']})")


if __name__ == '__main__':
    main()
