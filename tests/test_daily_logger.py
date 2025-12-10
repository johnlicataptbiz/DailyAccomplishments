#!/usr/bin/env python3
"""
Unit tests for daily_logger module.
"""

import unittest
import tempfile
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.daily_logger import load_config, read_daily_log, write_event


class TestDailyLogger(unittest.TestCase):
    """Test daily logger functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def test_load_config(self):
        """Test config loading."""
        config = load_config()
        
        self.assertIn('tracking', config)
        self.assertIn('timezone', config['tracking'])
        self.assertIn('log_directory', config['tracking'])
    
    def test_read_daily_log_nonexistent(self):
        """Test reading non-existent log file."""
        # Should return empty list for non-existent file
        events = read_daily_log('2099-12-31')
        self.assertEqual(events, [])
    
    def test_write_and_read_event(self):
        """Test writing and reading events."""
        # This test would need to mock the config
        # For now, verify the functions exist and have correct signatures
        self.assertTrue(callable(write_event))
        self.assertTrue(callable(read_daily_log))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
