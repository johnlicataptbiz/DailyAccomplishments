#!/usr/bin/env python3
"""
Verification script to test Daily Accomplishments Tracker installation.
Run this to verify all components are properly installed.
"""

import sys
from pathlib import Path

def check_file(path, description):
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} missing: {path}")
        return False

def check_directory(path, description):
    """Check if a directory exists."""
    if Path(path).is_dir():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} missing: {path}")
        return False

def check_import(module_name, description):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✓ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {description} failed: {e}")
        return False

def main():
    """Run verification checks."""
    print("Daily Accomplishments Tracker - Installation Verification")
    print("=" * 60)
    
    checks_passed = 0
    total_checks = 0
    
    print("\n1. Checking Core Files...")
    total_checks += 1
    if check_file("config.json", "Configuration file"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("dashboard.html", "Dashboard HTML"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("README.md", "README documentation"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("SETUP.md", "Setup guide"):
        checks_passed += 1
    
    print("\n2. Checking Directories...")
    total_checks += 1
    if check_directory("tools", "Tools directory"):
        checks_passed += 1
    
    total_checks += 1
    if check_directory("tests", "Tests directory"):
        checks_passed += 1
    
    total_checks += 1
    if check_directory("examples", "Examples directory"):
        checks_passed += 1
    
    print("\n3. Checking Python Modules...")
    total_checks += 1
    if check_file("tools/__init__.py", "Tools package"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("tools/daily_logger.py", "Daily logger module"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("tools/analytics.py", "Analytics module"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("tools/auto_report.py", "Auto report module"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("tools/notifications.py", "Notifications module"):
        checks_passed += 1
    
    print("\n4. Checking Python Imports...")
    sys.path.insert(0, str(Path(__file__).parent))
    
    total_checks += 1
    if check_import("tools.daily_logger", "Daily logger import"):
        checks_passed += 1
    
    total_checks += 1
    if check_import("tools.analytics", "Analytics import"):
        checks_passed += 1
    
    print("\n5. Checking Configuration...")
    try:
        from tools.daily_logger import load_config
        config = load_config()
        
        total_checks += 1
        if 'tracking' in config:
            print(f"✓ Config has tracking section")
            checks_passed += 1
        else:
            print(f"✗ Config missing tracking section")
        
        total_checks += 1
        if 'analytics' in config:
            print(f"✓ Config has analytics section")
            checks_passed += 1
        else:
            print(f"✗ Config missing analytics section")
        
        total_checks += 1
        if 'notifications' in config:
            print(f"✓ Config has notifications section")
            checks_passed += 1
        else:
            print(f"✗ Config missing notifications section")
            
    except Exception as e:
        print(f"✗ Config validation failed: {e}")
        total_checks += 3
    
    print("\n6. Checking Example Files...")
    total_checks += 1
    if check_file("examples/sample_events.jsonl", "Sample events"):
        checks_passed += 1
    
    total_checks += 1
    if check_file("examples/integration_example.py", "Integration example"):
        checks_passed += 1
    
    print("\n" + "=" * 60)
    print(f"Verification Results: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("\n✓ Installation verified successfully!")
        print("\nNext steps:")
        print("  1. Review and customize config.json")
        print("  2. Run: python3 examples/integration_example.py")
        print("  3. Generate a report: python3 tools/auto_report.py")
        print("  4. View dashboard: python3 -m http.server 8000")
        return 0
    else:
        print(f"\n✗ Installation incomplete ({total_checks - checks_passed} issues found)")
        print("Please review the errors above and fix any missing components.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
