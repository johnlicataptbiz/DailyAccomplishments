#!/usr/bin/env python3
"""
Master Sync Script - Runs all integrations and syncs to GitHub Pages.

This is the ONE script to run daily. It:
1. Pulls activity data from Mac ActivityTracker
2. Fetches data from all configured integrations (HubSpot, Google Calendar, Aloware, Monday.com, Slack)
3. Merges everything into a unified ActivityReport
4. Pushes to GitHub for dashboard viewing

Usage:
    python3 scripts/sync_all.py                  # Sync today
    python3 scripts/sync_all.py 2025-12-03       # Sync specific date
    python3 scripts/sync_all.py --setup          # Show setup instructions

Add to crontab for auto-sync:
    crontab -e
    # Add: 0 * * * * cd ~/DailyAccomplishments && python3 scripts/sync_all.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Paths
REPO_PATH = Path.home() / "DailyAccomplishments"
SCRIPTS_PATH = REPO_PATH / "scripts"
CONFIG_PATH = REPO_PATH / "config.json"


def load_config() -> dict:
    """Load configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def run_integration(name: str, script: str, date_str: str, extra_args: list = None) -> bool:
    """Run an integration script."""
    script_path = SCRIPTS_PATH / script
    
    if not script_path.exists():
        print(f"  ⚠️  {name}: Script not found")
        return False
    
    cmd = [sys.executable, str(script_path), "--date", date_str, "--update-report"]
    if extra_args:
        cmd.extend(extra_args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            # Extract summary from output
            lines = result.stdout.strip().split('\n')
            summary_lines = [l for l in lines if '===' in l or 'Found' in l or 'Updated' in l]
            if summary_lines:
                print(f"  ✅ {name}: {summary_lines[-1].strip()}")
            else:
                print(f"  ✅ {name}: Success")
            return True
        else:
            # Check for common errors
            if "No" in result.stdout and "found" in result.stdout.lower():
                print(f"  ℹ️  {name}: No data for this date")
            elif "Error:" in result.stdout or "Error:" in result.stderr:
                error_line = [l for l in (result.stdout + result.stderr).split('\n') if 'Error' in l]
                print(f"  ❌ {name}: {error_line[0] if error_line else 'Failed'}")
            else:
                print(f"  ❌ {name}: Failed (exit code {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  {name}: Timeout")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def sync_activity_tracker(date_str: str) -> bool:
    """Sync from Mac ActivityTracker logs."""
    print("  📱 Syncing ActivityTracker data...")
    return run_integration("ActivityTracker", "sync_to_github.py", date_str)


def sync_integrations(date_str: str, config: dict) -> dict:
    """Run all configured integrations."""
    results = {
        "activity_tracker": False,
        "google_calendar": False,
        "hubspot": False,
        "aloware": False,
        "monday": False,
        "slack": False
    }
    
    # 1. Mac ActivityTracker (always try)
    results["activity_tracker"] = sync_activity_tracker(date_str)
    
    # 2. Google Calendar
    if (REPO_PATH / "credentials" / "google_credentials.json").exists():
        results["google_calendar"] = run_integration(
            "Google Calendar",
            "google_calendar_integration.py",
            date_str
        )
    else:
        print("  ⏭️  Google Calendar: Not configured (no credentials file)")
    
    # 3. HubSpot
    if config.get("hubspot", {}).get("access_token"):
        results["hubspot"] = run_integration(
            "HubSpot",
            "hubspot_integration.py",
            date_str
        )
    else:
        print("  ⏭️  HubSpot: Not configured")
    
    # 4. Aloware
    if config.get("aloware", {}).get("api_key"):
        results["aloware"] = run_integration(
            "Aloware",
            "aloware_integration.py",
            date_str
        )
    else:
        print("  ⏭️  Aloware: Not configured")
    
    # 5. Monday.com
    if config.get("monday", {}).get("api_token"):
        results["monday"] = run_integration(
            "Monday.com",
            "monday_integration.py",
            date_str
        )
    else:
        print("  ⏭️  Monday.com: Not configured")
    
    # 6. Slack
    if config.get("slack", {}).get("bot_token"):
        results["slack"] = run_integration(
            "Slack",
            "slack_integration.py",
            date_str
        )
    else:
        print("  ⏭️  Slack: Not configured")
    
    return results


def push_to_github() -> bool:
    """Push changes to GitHub."""
    print("\n📤 Pushing to GitHub...")
    
    os.chdir(REPO_PATH)
    
    try:
        # Add and commit
        subprocess.run(["git", "add", "ActivityReport-*.json", "logs/"], check=False)
        
        result = subprocess.run(
            ["git", "commit", "-m", f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            capture_output=True,
            text=True
        )
        
        if "nothing to commit" in result.stdout:
            print("  ℹ️  No changes to commit")
            return True
        
        # Push
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Pushed to GitHub")
            return True
        else:
            print(f"  ❌ Push failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Git error: {e}")
        return False


def show_setup():
    """Show setup instructions for all integrations."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           Daily Accomplishments - Integration Setup              ║
╚══════════════════════════════════════════════════════════════════╝

Your config.json should look like this:

{
  "hubspot": {
    "access_token": "pat-na1-xxxxxxxx",
    "enabled": true
  },
  "aloware": {
    "api_key": "your-aloware-api-key"
  },
  "monday": {
    "api_token": "your-monday-token",
    "board_ids": []
  },
  "slack": {
    "bot_token": "xoxb-your-bot-token",
    "user_token": "xoxp-your-user-token"
  }
}

═══════════════════════════════════════════════════════════════════

📅 GOOGLE CALENDAR
─────────────────
1. Go to https://console.cloud.google.com/
2. Create a project → Enable "Google Calendar API"
3. Create OAuth 2.0 credentials (Desktop app)
4. Download JSON → Save to:
   ~/DailyAccomplishments/credentials/google_credentials.json
5. First run will open browser for OAuth consent

═══════════════════════════════════════════════════════════════════

🟠 HUBSPOT (Already configured ✓)
─────────────────
1. Go to HubSpot → Settings → Integrations → Private Apps
2. Create app with scopes: crm.objects.*.read, sales-email-read
3. Copy access token → Add to config.json

═══════════════════════════════════════════════════════════════════

📞 ALOWARE
─────────────────
1. Log into Aloware admin panel
2. Go to Settings → API/Integrations
3. Generate API key
4. Add to config.json: {"aloware": {"api_key": "your-key"}}

═══════════════════════════════════════════════════════════════════

📋 MONDAY.COM
─────────────────
1. Go to Monday.com → Avatar → Developers
2. Click "My Access Tokens" → Create token
3. Add to config.json: {"monday": {"api_token": "your-token"}}
4. Optional: Add board_ids to track specific boards

═══════════════════════════════════════════════════════════════════

💬 SLACK
─────────────────
1. Go to api.slack.com/apps → Create New App
2. Add OAuth scopes:
   - channels:history, groups:history, im:history
   - users:read
3. Install to workspace
4. Copy Bot Token → Add to config.json
5. Optional: Also add User Token for full DM access

═══════════════════════════════════════════════════════════════════

After setup, run:
    python3 scripts/sync_all.py

For auto-sync, add to crontab (runs every hour):
    crontab -e
    0 * * * * cd ~/DailyAccomplishments && python3 scripts/sync_all.py

Dashboard: https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html
""")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        show_setup()
        return
    
    # Get date
    if len(sys.argv) > 1 and sys.argv[1] != "--setup":
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║         Daily Accomplishments - Sync All ({date_str})          ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Load config
    config = load_config()
    
    # Run all integrations
    print("🔄 Running integrations...\n")
    results = sync_integrations(date_str, config)
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    total = len([k for k, v in results.items() if v is not False or k == "activity_tracker"])
    
    print(f"\n📊 Integrations: {successful}/{total} successful")
    
    # Push to GitHub
    push_to_github()
    
    print(f"""
═══════════════════════════════════════════════════════════════════

✅ Sync complete!

View your dashboard:
  https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html

Local report:
  {REPO_PATH}/ActivityReport-{date_str}.json
""")


if __name__ == "__main__":
    main()
