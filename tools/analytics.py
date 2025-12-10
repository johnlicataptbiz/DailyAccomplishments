#!/usr/bin/env python3
"""
Productivity analytics engine for analyzing daily accomplishments.
Detects deep work sessions, analyzes interruptions, and generates insights.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .daily_logger import load_config, read_daily_log


class ProductivityAnalytics:
    """Analyze productivity metrics from daily event logs."""
    
    def __init__(self, date=None):
        """
        Initialize analytics for a specific date.
        
        Args:
            date: datetime.date or string in YYYY-MM-DD format (default: today)
        """
        self.config = load_config()
        self.tz = ZoneInfo(self.config['tracking']['timezone'])
        
        if date is None:
            self.date = datetime.now(self.tz).date()
        elif isinstance(date, str):
            self.date = datetime.fromisoformat(date).date()
        else:
            self.date = date
        
        self.events = read_daily_log(self.date)
        
        # Load thresholds from config
        analytics_config = self.config.get('analytics', {})
        self.deep_work_threshold = analytics_config.get('deep_work_threshold', 25)
        self.idle_threshold_seconds = analytics_config.get('idle_threshold_seconds', 300)
        self.context_switch_cost = analytics_config.get('context_switch_cost', 60)
    
    def detect_deep_work_sessions(self):
        """
        Detect deep work sessions from focus_change events.
        
        Returns:
            List of session dictionaries with start_time, end_time, duration_minutes,
            app, interruptions, and quality_score
        """
        sessions = []
        current_session = None
        
        for event in self.events:
            if event.get('type') != 'focus_change':
                continue
            
            timestamp = datetime.fromisoformat(event['timestamp'])
            app = event.get('data', {}).get('app', 'Unknown')
            duration_seconds = event.get('data', {}).get('duration_seconds', 0)
            
            # Start new session or continue current
            if current_session is None:
                current_session = {
                    'start_time': timestamp,
                    'last_time': timestamp,
                    'app': app,
                    'total_duration': duration_seconds,
                    'interruptions': 0
                }
            else:
                # Check if gap is too large (>5 minutes)
                gap = (timestamp - current_session['last_time']).total_seconds()
                if gap > 300:  # 5 minutes
                    # Finalize current session
                    sessions.append(self._finalize_session(current_session))
                    # Start new session
                    current_session = {
                        'start_time': timestamp,
                        'last_time': timestamp,
                        'app': app,
                        'total_duration': duration_seconds,
                        'interruptions': 0
                    }
                else:
                    # Continue session
                    current_session['last_time'] = timestamp
                    current_session['total_duration'] += duration_seconds
                    if app != current_session['app']:
                        current_session['interruptions'] += 1
        
        # Finalize last session
        if current_session is not None:
            sessions.append(self._finalize_session(current_session))
        
        # Filter for deep work (>= threshold minutes)
        deep_work_sessions = []
        for session in sessions:
            if session['duration_minutes'] >= self.deep_work_threshold:
                session['quality_score'] = self._calculate_quality_score(session)
                deep_work_sessions.append(session)
        
        return deep_work_sessions
    
    def _finalize_session(self, session):
        """Convert session tracking dict to output format."""
        duration_minutes = session['total_duration'] / 60
        return {
            'start_time': session['start_time'].isoformat(),
            'end_time': session['last_time'].isoformat(),
            'duration_minutes': round(duration_minutes, 1),
            'app': session['app'],
            'interruptions': session['interruptions']
        }
    
    def _calculate_quality_score(self, session):
        """
        Calculate quality score for a session (0-100).
        
        Factors:
        - Interruptions: -5 per interrupt
        - Duration: +10 for >=60min, +20 for >=120min
        - Time of day: +10 for 8-11am, -5 for 2-4pm
        """
        score = 70  # Base score
        
        # Interruption penalty
        score -= session['interruptions'] * 5
        
        # Duration bonus
        if session['duration_minutes'] >= 120:
            score += 20
        elif session['duration_minutes'] >= 60:
            score += 10
        
        # Time of day adjustment
        start_time = datetime.fromisoformat(session['start_time'])
        hour = start_time.hour
        if 8 <= hour < 11:
            score += 10  # Morning bonus
        elif 14 <= hour < 16:
            score -= 5  # Post-lunch dip
        
        return max(0, min(100, score))
    
    def analyze_interruptions(self):
        """
        Analyze interruption patterns throughout the day.
        
        Returns:
            Dictionary with interruption metrics
        """
        interruptions_by_hour = {}
        total_interruptions = 0
        
        for event in self.events:
            if event.get('type') in ['app_switch', 'window_change']:
                timestamp = datetime.fromisoformat(event['timestamp'])
                hour = timestamp.hour
                interruptions_by_hour[hour] = interruptions_by_hour.get(hour, 0) + 1
                total_interruptions += 1
        
        if not interruptions_by_hour:
            return {
                'interruptions_per_hour': {},
                'most_disruptive_hour': None,
                'total_interruptions': 0,
                'max_interruptions': 0,
                'context_switch_cost_minutes': 0,
                'average_per_hour': 0
            }
        
        most_disruptive_hour = max(interruptions_by_hour.items(), key=lambda x: x[1])
        context_switch_cost_minutes = (total_interruptions * self.context_switch_cost) / 60
        
        return {
            'interruptions_per_hour': interruptions_by_hour,
            'most_disruptive_hour': most_disruptive_hour[0],
            'total_interruptions': total_interruptions,
            'max_interruptions': most_disruptive_hour[1],
            'context_switch_cost_minutes': round(context_switch_cost_minutes, 1),
            'average_per_hour': round(total_interruptions / len(interruptions_by_hour), 1)
        }
    
    def calculate_productivity_score(self):
        """
        Calculate overall productivity score (0-100).
        
        Components:
        - Deep work score (max 40): Based on deep work percentage
        - Interruption score (max 30): Penalty for interruptions
        - Quality score (max 30): Average session quality
        
        Returns:
            Dictionary with overall score, components, and rating
        """
        total_focus_time = self._calculate_total_focus_time()
        deep_work_sessions = self.detect_deep_work_sessions()
        interruption_analysis = self.analyze_interruptions()
        
        # Deep work score (max 40)
        deep_work_time = sum(s['duration_minutes'] for s in deep_work_sessions)
        if total_focus_time > 0:
            deep_work_percentage = (deep_work_time / total_focus_time) * 100
            deep_work_score = min(40, (deep_work_percentage / 100) * 40)
        else:
            deep_work_percentage = 0
            deep_work_score = 0
        
        # Interruption score (max 30)
        interruption_penalty = min(30, interruption_analysis['total_interruptions'])
        interruption_score = max(0, 30 - interruption_penalty)
        
        # Quality score (max 30)
        if deep_work_sessions:
            avg_quality = sum(s.get('quality_score', 0) for s in deep_work_sessions) / len(deep_work_sessions)
            quality_score = (avg_quality / 100) * 30
        else:
            quality_score = 0
        
        overall_score = round(deep_work_score + interruption_score + quality_score)
        
        return {
            'overall_score': overall_score,
            'rating': self._get_rating(overall_score),
            'components': {
                'deep_work_score': round(deep_work_score, 1),
                'interruption_score': round(interruption_score, 1),
                'quality_score': round(quality_score, 1)
            },
            'metrics': {
                'total_focus_minutes': round(total_focus_time, 1),
                'deep_work_minutes': round(deep_work_time, 1),
                'deep_work_percentage': round(deep_work_percentage, 1)
            }
        }
    
    def _calculate_total_focus_time(self):
        """Calculate total focus time in minutes from focus_change events."""
        total_seconds = 0
        for event in self.events:
            if event.get('type') == 'focus_change':
                duration = event.get('data', {}).get('duration_seconds', 0)
                total_seconds += duration
        return total_seconds / 60
    
    def _get_rating(self, score):
        """Convert numeric score to text rating."""
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Fair'
        else:
            return 'Needs Improvement'
    
    def analyze_category_trends(self):
        """
        Categorize time spent by activity type.
        
        Returns:
            Dictionary with categories list and summary
        """
        category_time = {}
        category_events = {}
        
        for event in self.events:
            if event.get('type') == 'focus_change':
                app = event.get('data', {}).get('app', 'Unknown')
                duration_seconds = event.get('data', {}).get('duration_seconds', 0)
                category = self._categorize_app(app)
                
                category_time[category] = category_time.get(category, 0) + duration_seconds
                category_events[category] = category_events.get(category, 0) + 1
        
        total_time_seconds = sum(category_time.values())
        
        categories = []
        for category, time_seconds in sorted(category_time.items(), key=lambda x: x[1], reverse=True):
            time_minutes = time_seconds / 60
            percentage = (time_seconds / total_time_seconds * 100) if total_time_seconds > 0 else 0
            avg_duration = time_minutes / category_events[category] if category_events[category] > 0 else 0
            
            categories.append({
                'category': category,
                'time_minutes': round(time_minutes, 1),
                'percentage': round(percentage, 1),
                'event_count': category_events[category],
                'avg_duration_minutes': round(avg_duration, 1)
            })
        
        return {
            'categories': categories,
            'total_time_minutes': round(total_time_seconds / 60, 1),
            'top_category': categories[0]['category'] if categories else None,
            'category_count': len(categories)
        }
    
    def _categorize_app(self, app_name):
        """Categorize app by name using keyword matching."""
        app_lower = app_name.lower()
        
        if any(keyword in app_lower for keyword in ['chrome', 'firefox', 'safari', 'browser', 'web']):
            if any(keyword in app_lower for keyword in ['docs', 'sheets', 'notion', 'confluence']):
                return 'Docs'
            return 'Research'
        elif any(keyword in app_lower for keyword in ['vscode', 'pycharm', 'intellij', 'sublime', 'vim', 'code', 'terminal']):
            return 'Coding'
        elif any(keyword in app_lower for keyword in ['zoom', 'meet', 'teams', 'slack call', 'webex']):
            return 'Meetings'
        elif any(keyword in app_lower for keyword in ['slack', 'discord', 'telegram', 'mail', 'outlook', 'gmail']):
            return 'Communication'
        elif any(keyword in app_lower for keyword in ['word', 'docs', 'notion', 'obsidian', 'evernote', 'notes']):
            return 'Docs'
        else:
            return 'Other'
    
    def analyze_meeting_efficiency(self):
        """
        Analyze meeting time and efficiency.
        
        Returns:
            Dictionary with meeting metrics and recommendations
        """
        meeting_events = [e for e in self.events if e.get('type') == 'meeting_end']
        
        if not meeting_events:
            return {
                'total_meeting_minutes': 0,
                'meeting_count': 0,
                'average_duration_minutes': 0,
                'meeting_vs_focus_ratio': 0,
                'recommendation': 'No meetings detected'
            }
        
        total_meeting_seconds = sum(
            e.get('data', {}).get('duration_seconds', 0) 
            for e in meeting_events
        )
        total_meeting_minutes = total_meeting_seconds / 60
        meeting_count = len(meeting_events)
        avg_duration = total_meeting_minutes / meeting_count
        
        total_focus_time = self._calculate_total_focus_time()
        ratio = total_meeting_minutes / total_focus_time if total_focus_time > 0 else 0
        
        return {
            'total_meeting_minutes': round(total_meeting_minutes, 1),
            'meeting_count': meeting_count,
            'average_duration_minutes': round(avg_duration, 1),
            'meeting_vs_focus_ratio': round(ratio, 2),
            'recommendation': self._get_meeting_recommendation(ratio)
        }
    
    def _get_meeting_recommendation(self, ratio):
        """Provide recommendation based on meeting/focus ratio."""
        if ratio > 0.5:
            return 'Too many meetings - consider blocking more focus time'
        elif ratio > 0.3:
            return 'Moderate meeting load - monitor for balance'
        else:
            return 'Good balance between meetings and focus work'
    
    def suggest_focus_windows(self):
        """
        Suggest optimal focus windows based on low-interruption periods.
        
        Returns:
            List of suggested time windows
        """
        interruption_analysis = self.analyze_interruptions()
        interruptions_by_hour = interruption_analysis['interruptions_per_hour']
        
        # Find hours with <=2 interruptions
        low_interruption_hours = []
        for hour in range(6, 22):  # 6am to 10pm
            interruptions = interruptions_by_hour.get(hour, 0)
            if interruptions <= 2:
                low_interruption_hours.append(hour)
        
        # Group consecutive hours into windows (>=2 hours)
        windows = []
        current_window = []
        
        for hour in low_interruption_hours:
            if not current_window or hour == current_window[-1] + 1:
                current_window.append(hour)
            else:
                if len(current_window) >= 2:
                    windows.append(current_window)
                current_window = [hour]
        
        if len(current_window) >= 2:
            windows.append(current_window)
        
        # Format windows
        formatted_windows = []
        for window in windows:
            total_interruptions = sum(interruptions_by_hour.get(h, 0) for h in window)
            formatted_windows.append(self._format_window(window, total_interruptions))
        
        return formatted_windows
    
    def _format_window(self, hours, total_interruptions):
        """Format a focus window for output."""
        start_hour = hours[0]
        end_hour = hours[-1] + 1
        duration_hours = len(hours)
        
        quality = 'Excellent' if total_interruptions == 0 else 'Good'
        recommendation = f'Schedule deep work during this {duration_hours}-hour window'
        
        return {
            'start_time': f'{start_hour:02d}:00',
            'end_time': f'{end_hour:02d}:00',
            'duration_hours': duration_hours,
            'total_interruptions': total_interruptions,
            'quality': quality,
            'recommendation': recommendation
        }
    
    def generate_report(self):
        """
        Generate comprehensive analytics report.
        
        Returns:
            Dictionary with all analytics
        """
        return {
            'date': self.date.isoformat(),
            'deep_work_sessions': self.detect_deep_work_sessions(),
            'interruption_analysis': self.analyze_interruptions(),
            'productivity_score': self.calculate_productivity_score(),
            'category_trends': self.analyze_category_trends(),
            'meeting_efficiency': self.analyze_meeting_efficiency(),
            'focus_windows': self.suggest_focus_windows()
        }


def compare_trends(start_date, end_date):
    """
    Aggregate analytics over a date range for weekly reports.
    
    Args:
        start_date: Start date (datetime.date or string)
        end_date: End date (datetime.date or string)
        
    Returns:
        Dictionary with aggregated trends
    """
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date).date()
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date).date()
    
    daily_data = []
    total_days = (end_date - start_date).days + 1
    
    current_date = start_date
    while current_date <= end_date:
        analytics = ProductivityAnalytics(current_date)
        report = analytics.generate_report()
        daily_data.append(report)
        current_date += timedelta(days=1)
    
    # Calculate averages
    avg_score = sum(d['productivity_score']['overall_score'] for d in daily_data) / total_days
    avg_deep_work = sum(d['productivity_score']['metrics']['deep_work_minutes'] for d in daily_data) / total_days
    avg_interruptions = sum(d['interruption_analysis']['total_interruptions'] for d in daily_data) / total_days
    avg_meetings = sum(d['meeting_efficiency']['total_meeting_minutes'] for d in daily_data) / total_days
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': total_days
        },
        'averages': {
            'productivity_score': round(avg_score, 1),
            'deep_work_minutes': round(avg_deep_work, 1),
            'interruptions': round(avg_interruptions, 1),
            'meeting_minutes': round(avg_meetings, 1)
        },
        'trends': {
            'best_day': max(daily_data, key=lambda d: d['productivity_score']['overall_score'])['date'],
            'most_productive_category': max(
                set(d['category_trends']['top_category'] for d in daily_data if d['category_trends']['top_category']),
                key=lambda cat: sum(1 for d in daily_data if d['category_trends']['top_category'] == cat)
            ) if any(d['category_trends']['top_category'] for d in daily_data) else None
        },
        'daily_data': daily_data
    }
