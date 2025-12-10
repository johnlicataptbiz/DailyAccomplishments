#!/usr/bin/env python3
"""
Unit tests for analytics module.
"""

import unittest
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.analytics import ProductivityAnalytics


class TestProductivityAnalytics(unittest.TestCase):
    """Test ProductivityAnalytics class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample events for testing
        self.sample_events = [
            {
                'type': 'metadata',
                'version': '1.0',
                'timezone': 'America/Chicago'
            },
            {
                'type': 'focus_change',
                'timestamp': '2025-12-05T09:00:00-06:00',
                'data': {'app': 'VS Code', 'duration_seconds': 1800}
            },
            {
                'type': 'focus_change',
                'timestamp': '2025-12-05T09:30:00-06:00',
                'data': {'app': 'VS Code', 'duration_seconds': 1200}
            },
            {
                'type': 'app_switch',
                'timestamp': '2025-12-05T09:50:00-06:00',
                'data': {'from_app': 'VS Code', 'to_app': 'Chrome'}
            },
            {
                'type': 'focus_change',
                'timestamp': '2025-12-05T10:00:00-06:00',
                'data': {'app': 'Chrome', 'duration_seconds': 600}
            },
            {
                'type': 'meeting_end',
                'timestamp': '2025-12-05T14:00:00-06:00',
                'data': {'duration_seconds': 1800}
            }
        ]
    
    def test_detect_deep_work_sessions(self):
        """Test deep work session detection."""
        # This test would need actual event data
        # For now, verify the method exists and returns a list
        analytics = ProductivityAnalytics('2025-12-05')
        sessions = analytics.detect_deep_work_sessions()
        self.assertIsInstance(sessions, list)
    
    def test_analyze_interruptions(self):
        """Test interruption analysis."""
        analytics = ProductivityAnalytics('2025-12-05')
        interruptions = analytics.analyze_interruptions()
        
        self.assertIn('total_interruptions', interruptions)
        self.assertIn('interruptions_per_hour', interruptions)
        self.assertIsInstance(interruptions['total_interruptions'], int)
    
    def test_calculate_productivity_score(self):
        """Test productivity score calculation."""
        analytics = ProductivityAnalytics('2025-12-05')
        score = analytics.calculate_productivity_score()
        
        self.assertIn('overall_score', score)
        self.assertIn('rating', score)
        self.assertIn('components', score)
        self.assertGreaterEqual(score['overall_score'], 0)
        self.assertLessEqual(score['overall_score'], 100)
    
    def test_categorize_app(self):
        """Test app categorization."""
        analytics = ProductivityAnalytics('2025-12-05')
        
        self.assertEqual(analytics._categorize_app('VS Code'), 'Coding')
        self.assertEqual(analytics._categorize_app('Chrome'), 'Research')
        self.assertEqual(analytics._categorize_app('Zoom'), 'Meetings')
        self.assertEqual(analytics._categorize_app('Slack'), 'Communication')
        self.assertEqual(analytics._categorize_app('Notion'), 'Docs')
    
    def test_meeting_efficiency(self):
        """Test meeting efficiency analysis."""
        analytics = ProductivityAnalytics('2025-12-05')
        efficiency = analytics.analyze_meeting_efficiency()
        
        self.assertIn('total_meeting_minutes', efficiency)
        self.assertIn('meeting_count', efficiency)
        self.assertIn('meeting_credit_minutes', efficiency)
        self.assertIn('effective_productive_minutes', efficiency)
        self.assertIn('recommendation', efficiency)
    
    def test_focus_windows(self):
        """Test focus window suggestions."""
        analytics = ProductivityAnalytics('2025-12-05')
        windows = analytics.suggest_focus_windows()
        
        self.assertIsInstance(windows, list)
        for window in windows:
            self.assertIn('start_time', window)
            self.assertIn('end_time', window)
            self.assertIn('duration_hours', window)
    
    def test_empty_events(self):
        """Test graceful handling of empty events."""
        analytics = ProductivityAnalytics('2025-12-05')
        analytics.events = []
        
        # Should not raise exceptions
        sessions = analytics.detect_deep_work_sessions()
        self.assertEqual(len(sessions), 0)
        
        score = analytics.calculate_productivity_score()
        # With no events, interruption score is 30 (max), so overall is 30
        self.assertEqual(score['overall_score'], 30)
        self.assertEqual(score['components']['deep_work_score'], 0)
        self.assertEqual(score['components']['quality_score'], 0)
    
    def test_generate_report(self):
        """Test that generate_report returns all required keys."""
        analytics = ProductivityAnalytics('2025-12-05')
        report = analytics.generate_report()
        
        # Verify report is a dictionary
        self.assertIsInstance(report, dict)
        
        meeting_efficiency = report['meeting_efficiency']
        self.assertIn('meeting_credit_minutes', meeting_efficiency)
        self.assertIn('effective_productive_minutes', meeting_efficiency)
        
        # Verify all required keys are present
        required_keys = [
            'date',
            'deep_work_sessions',
            'interruption_analysis',
            'productivity_score',
            'category_trends',
            'meeting_efficiency',
            'focus_windows'
        ]
        
        for key in required_keys:
            self.assertIn(key, report, f"Report missing required key: {key}")
        
        # Verify data types
        self.assertIsInstance(report['date'], str)
        self.assertIsInstance(report['deep_work_sessions'], list)
        self.assertIsInstance(report['interruption_analysis'], dict)
        self.assertIsInstance(report['productivity_score'], dict)
        self.assertIsInstance(report['category_trends'], dict)
        self.assertIsInstance(report['meeting_efficiency'], dict)
        self.assertIsInstance(report['focus_windows'], list)


if __name__ == '__main__':
    unittest.main()
