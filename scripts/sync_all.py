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
    python3 scripts/sync_all.py --no-push        # Run integrations but do not git push (cron publisher will)

Add to crontab for auto-sync:
    crontab -e
    # Add: 0 * * * * cd ~/DailyAccomplishments && python3 scripts/sync_all.py
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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


def run_integration(name: str, script: str, date_str: str, extra_args: list | None = None) -> bool:
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
            lines = result.stdout.strip().split("\n")
            summary_lines = [l for l in lines if "===" in l or "Found" in l or "Updated" in l]
            if summary_lines:
                print(f"  ✅ {name}: {summary_lines[-1].strip()}")
            else:
                print(f"  ✅ {name}: Success")
            return True

        if "No" in result.stdout and "found" in result.stdout.lower():
            print(f"  ℹ️  {name}: No data for this date")
        elif "Error:" in result.stdout or "Error:" in result.stderr:
            error_line = [l for l in (result.stdout + result.stderr).split("\n") if "Error" in l]
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
        subprocess.run(["git", "add", "ActivityReport-*.json", "logs/"], check=False)

        result = subprocess.run(
            ["git", "commit", "-m", f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            capture_output=True,
            text=True
        )

        if "nothing to commit" in result.stdout:
            print("  ℹ️  No changes to commit")
            return True

        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Pushed to GitHub")
            return True

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

After setup, run:
    python3 scripts/sync_all.py

Dashboard: https://johnlicataptbiz.github.io/DailyAccomplishments/dashboard.html
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("date", nargs="?", help="YYYY-MM-DD (defaults to today)")
    parser.add_argument("--setup", action="store_true", help="Show setup instructions")
    parser.add_argument("--no-push", action="store_true", help="Do not git commit/push (cron publisher handles publishing)")
    args = parser.parse_args()

    if args.setup:
        show_setup()
        return

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║         Daily Accomplishments - Sync All ({date_str})          ║
╚══════════════════════════════════════════════════════════════════╝
""")

    config = load_config()

    print("🔄 Running integrations...\n")
    results = sync_integrations(date_str, config)

    successful = sum(1 for v in results.values() if v)
    total = len([k for k, v in results.items() if v is not False or k == "activity_tracker"])

    print(f"\n📊 Integrations: {successful}/{total} successful")

    if args.no_push:
        print("\n📤 Skipping git push (handled by cron publisher)")
    else:
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
