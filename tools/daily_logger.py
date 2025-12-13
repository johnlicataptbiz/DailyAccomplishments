
import json
import os
import shutil
import fcntl
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Determine repository root path
# If running from tools/ directory, go up one level; otherwise use current directory
repo_root_path = Path(__file__).resolve().parent.parent

# Load configuration
CONFIG_PATH = repo_root_path / 'config.json'
CONFIG_EXAMPLE_PATH = repo_root_path / 'config.json.example'
BASE_DIR = repo_root_path

# Define default log/archive/backup directories relative to BASE_DIR
# These will be overridden by config.json if present
DEFAULT_LOG_DIR = BASE_DIR / 'logs' / 'daily'
DEFAULT_ARCHIVE_DIR = BASE_DIR / 'logs' / 'archive'
DEFAULT_BACKUP_DIR = BASE_DIR / 'logs' / 'backup'

# Initialize these as None; they'll be set after config is loaded
LOG_DIR = None
ARCHIVE_DIR = None
BACKUP_DIR = None

# Event schema for validation
VALID_EVENT_TYPES = {
    'metadata', 'focus_change', 'app_switch', 'window_change',
    'browser_visit', 'meeting_start', 'meeting_end', 'break_start',
    'break_end', 'manual_entry', 'idle_start', 'idle_end'
}

REQUIRED_FIELDS = {
    'focus_change': ['app', 'duration_seconds'],
    'app_switch': ['from_app', 'to_app'],
    'window_change': ['app', 'window_title'],
    'browser_visit': ['domain', 'url'],
    'meeting_start': ['name'],
    'meeting_end': ['name', 'duration_seconds'],
}

# File lock timeout and max retries will now be loaded from config
_LOCK_TIMEOUT = 5.0 # Default value
_MAX_RETRIES = 3 # Default value

_CONFIG_CACHE = None

def load_config() -> Dict[str, Any]:
    """Load configuration with error handling and validation"""
    global _CONFIG_CACHE, LOG_DIR, ARCHIVE_DIR, BACKUP_DIR, _LOCK_TIMEOUT, _MAX_RETRIES

    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config = {}
    try:
        # 1. Try to load from config.json
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from: {CONFIG_PATH}")
        # 2. If config.json doesn't exist, try config.json.example as a template
        elif CONFIG_EXAMPLE_PATH.exists():
            with open(CONFIG_EXAMPLE_PATH, 'r') as f:
                config = json.load(f)
            logger.warning(f"config.json not found. Using config.json.example as template. Please create config.json for custom settings.")
        else:
            raise FileNotFoundError("Neither config.json nor config.json.example found. Please create one.")

        # Validate required config sections (basic check)
        required_sections = ['tracking', 'report', 'retention', 'analytics', 'notifications']
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing recommended config section: {section}. Using defaults where possible.")

        # Override sensitive settings with environment variables
        # Notifications.email
        email_config = config.get('notifications', {}).get('email', {})
        email_config['username'] = os.environ.get('EMAIL_USERNAME', email_config.get('username'))
        email_config['password'] = os.environ.get('EMAIL_PASSWORD', email_config.get('password'))
        if 'from_email' not in email_config and email_config['username']:
            email_config['from_email'] = email_config['username']
        if 'notifications' in config and 'email' not in config['notifications']:
            config['notifications']['email'] = email_config # Ensure the dict is added if not present
        elif 'notifications' not in config:
            config['notifications'] = {'email': email_config}

        # Notifications.slack
        slack_config = config.get('notifications', {}).get('slack', {})
        slack_config['webhook_url'] = os.environ.get('SLACK_WEBHOOK_URL', slack_config.get('webhook_url'))
        if 'notifications' in config and 'slack' not in config['notifications']:
            config['notifications']['slack'] = slack_config # Ensure the dict is added if not present
        elif 'notifications' not in config:
            config['notifications'] = {'slack': slack_config}

        # Update global directory paths based on config or defaults
        LOG_DIR = BASE_DIR / config.get('report', {}).get('log_dir', str(DEFAULT_LOG_DIR.relative_to(BASE_DIR)))
        ARCHIVE_DIR = BASE_DIR / config.get('report', {}).get('archive_dir', str(DEFAULT_ARCHIVE_DIR.relative_to(BASE_DIR)))
        BACKUP_DIR = BASE_DIR / config.get('report', {}).get('backup_dir', str(DEFAULT_BACKUP_DIR.relative_to(BASE_DIR)))

        # Update global lock timeout and max retries
        _LOCK_TIMEOUT = config.get('tracking', {}).get('lock_timeout', _LOCK_TIMEOUT)
        _MAX_RETRIES = config.get('tracking', {}).get('max_retries', _MAX_RETRIES)

        _CONFIG_CACHE = config
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file ({CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE_PATH}): {e}")
        raise ValueError(f"Invalid JSON in configuration file: {e}") from e
    except FileNotFoundError as e:
        logger.critical(f"Configuration file not found: {e}")
        raise RuntimeError("Configuration file is missing.") from e
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise RuntimeError(f"Failed to load configuration: {e}") from e

def ensure_directories():
    """Create necessary directories with error handling"""
    # Ensure load_config has run to set LOG_DIR, ARCHIVE_DIR, BACKUP_DIR
    load_config()

    if not all([LOG_DIR, ARCHIVE_DIR, BACKUP_DIR]):
        logger.error("Log directories are not initialized. Configuration might be missing.")
        raise RuntimeError("Log directories could not be determined from configuration.")

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Directories initialized successfully")
    except PermissionError as e:
        logger.error(f"Permission denied creating directories: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise

def get_current_date(tz_name='America/Chicago') -> datetime:
    """Get current date with timezone handling"""
    try:
        tz = ZoneInfo(tz_name)
        return datetime.now(tz)
    except Exception as e:
        logger.error(f"Timezone error, falling back to UTC: {e}")
        return datetime.now(ZoneInfo('UTC'))

def get_log_path(date) -> Path:
    """Get path to today's activity log"""
    # Ensure LOG_DIR is set
    if LOG_DIR is None:
        load_config()
    return LOG_DIR / f"{date.strftime('%Y-%m-%d')}.jsonl"

def get_lock_path(log_path: Path) -> Path:
    """Get path to lock file for a log"""
    return log_path.with_suffix('.lock')

def acquire_file_lock(lock_path: Path, timeout: float = _LOCK_TIMEOUT) -> Optional[int]:
    """Acquire exclusive lock on log file"""
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logger.debug(f"Lock acquired: {lock_path}")
                return lock_fd
            except BlockingIOError:
                time.sleep(0.1)

        logger.warning(f"Lock timeout after {timeout}s: {lock_path}")
        os.close(lock_fd)
        return None
    except Exception as e:
        logger.error(f"Failed to acquire lock: {e}")
        return None

def release_file_lock(lock_fd: int, lock_path: Path):
    """Release file lock"""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        if lock_path.exists():
            lock_path.unlink()
        logger.debug(f"Lock released: {lock_path}")
    except Exception as e:
        logger.error(f"Failed to release lock: {e}")

def validate_event_data(event_type: str, data: Dict[str, Any]) -> bool:
    """Validate event data against schema"""
    if event_type not in VALID_EVENT_TYPES:
        logger.warning(f"Unknown event type: {event_type}")
        return False

    if event_type in REQUIRED_FIELDS:
        required = REQUIRED_FIELDS[event_type]
        for field in required:
            if field not in data:
                logger.warning(f"Missing required field '{field}' for event type '{event_type}'")
                return False

    return True

def create_backup(file_path: Path) -> Optional[Path]:
    """Create backup of log file before modifications"""
    # Ensure BACKUP_DIR is set
    if BACKUP_DIR is None:
        load_config()

    try:
        if not file_path.exists():
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUP_DIR / f"{file_path.stem}_{timestamp}.jsonl"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

def verify_log_integrity(log_path: Path) -> bool:
    """Verify log file is valid JSONL"""
    if not log_path.exists():
        return True  # Empty/new file is valid

    try:
        with open(log_path, 'r') as f:
            line_num = 0
            for line in f:
                line_num += 1
                if line.strip():  # Skip empty lines
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Corrupt line {line_num} in {log_path}: {e}")
                        return False
        return True
    except Exception as e:
        logger.error(f"Failed to verify log integrity: {e}")
        return False

def repair_log_file(log_path: Path) -> bool:
    """Attempt to repair corrupted log file"""
    try:
        backup_path = create_backup(log_path)
        if not backup_path:
            return False

        valid_lines = []
        with open(backup_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        json.loads(line)
                        valid_lines.append(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping corrupt line {line_num}")

        with open(log_path, 'w') as f:
            f.writelines(valid_lines)

        logger.info(f"Repaired {log_path}: kept {len(valid_lines)} valid lines")
        return True
    except Exception as e:
        logger.error(f"Failed to repair log file: {e}")
        return False

def initialize_daily_log(date, config) -> Optional[Dict[str, Any]]:
    """Create a new daily log file with metadata (with error handling and locking)"""
    log_path = get_log_path(date)
    lock_path = get_lock_path(log_path)

    if log_path.exists():
        # Verify existing log integrity
        if not verify_log_integrity(log_path):
            logger.warning(f"Corrupted log detected: {log_path}")
            if repair_log_file(log_path):
                logger.info("Log file repaired successfully")
            else:
                logger.error("Failed to repair log file")
                return None
        return None

    lock_fd = acquire_file_lock(lock_path)
    if lock_fd is None:
        logger.error(f"Failed to acquire lock for {log_path}")
        return None

    try:
        start_hour = config.get('tracking', {}).get('daily_start_hour', 6)
        start_min = config.get('tracking', {}).get('daily_start_minute', 0)
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))

        # Create start timestamp for today at daily_start_hour
        start_time = date.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

        metadata = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.isoformat(),
            'timezone': config.get('tracking', {}).get('timezone', 'America/Chicago'),
            'coverage_start': config.get('report', {}).get('coverage_start', '05:00'),
            'coverage_end': config.get('report', {}).get('coverage_end', '23:59'),
            'initialized_at': datetime.now(tz).isoformat(),
            'version': '2.0'
        }

        with open(log_path, 'w') as f:
            f.write(json.dumps({'type': 'metadata', 'data': metadata}) + '\n')

        logger.info(f"Initialized daily log: {log_path}")
        return metadata
    except Exception as e:
        logger.error(f"Failed to initialize log: {e}")
        return None
    finally:
        release_file_lock(lock_fd, lock_path)

def log_activity(event_type: str, data: Dict[str, Any], retry_count: int = 0) -> bool:
    """Append an activity event to today's log (with validation, locking, and retries)"""
    if retry_count >= _MAX_RETRIES:
        logger.error(f"Max retries exceeded for event type: {event_type}")
        return False

    try:
        # Validate event data
        if not validate_event_data(event_type, data):
            logger.error(f"Invalid event data for type '{event_type}'")
            return False

        config = load_config()
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))
        now = datetime.now(tz)
        log_path = get_log_path(now)
        lock_path = get_lock_path(log_path)

        # Ensure log file exists
        if not log_path.exists():
            logger.warning(f"Log file doesn't exist, initializing: {log_path}")
            initialize_daily_log(now, config)

        # Acquire lock
        lock_fd = acquire_file_lock(lock_path, timeout=_LOCK_TIMEOUT)
        if lock_fd is None:
            logger.warning(f"Lock acquisition failed, retrying ({retry_count + 1}/{_MAX_RETRIES})")
            time.sleep(0.5)
            return log_activity(event_type, data, retry_count + 1)

        try:
            event = {
                'type': event_type,
                'timestamp': now.isoformat(),
                'data': data
            }

            # Atomic write with error recovery
            with open(log_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
                f.flush()
                os.fsync(f.fileno())  # Ensure write to disk

            logger.debug(f"Logged event: {event_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to write event: {e}")
            # Attempt to verify and repair if needed
            if not verify_log_integrity(log_path):
                repair_log_file(log_path)
            return False
        finally:
            release_file_lock(lock_fd, lock_path)
    except Exception as e:
        logger.error(f"Unexpected error in log_activity: {e}")
        return False

def midnight_reset() -> bool:
    """Archive yesterday's log and prepare for new day (with error handling)"""
    try:
        config = load_config()
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))
        now = datetime.now(tz)
        yesterday = now - timedelta(days=1)

        # Archive yesterday's log with verification
        yesterday_log = get_log_path(yesterday)
        if yesterday_log.exists():
            # Verify integrity before archiving
            if not verify_log_integrity(yesterday_log):
                logger.warning("Yesterday's log is corrupted, attempting repair")
                if not repair_log_file(yesterday_log):
                    logger.error("Failed to repair yesterday's log")
                    # Create backup of corrupted file
                    create_backup(yesterday_log)

            archive_path = ARCHIVE_DIR / f"{yesterday.strftime('%Y-%m-%d')}.jsonl"
            try:
                shutil.copy2(yesterday_log, archive_path)
                logger.info(f"Archived: {yesterday_log} -> {archive_path}")
            except Exception as e:
                logger.error(f"Failed to archive log: {e}")
                return False

        # Initialize today's log
        result = initialize_daily_log(now, config)
        if result is None and not get_log_path(now).exists():
            logger.error("Failed to initialize today's log")
            return False

        # Clean up old logs based on retention policy
        cleanup_old_logs(config)

        logger.info("Midnight reset completed successfully")
        return True
    except Exception as e:
        logger.error(f"Midnight reset failed: {e}")
        return False

def cleanup_old_logs(config) -> int:
    """Remove logs older than retention period (with error handling)"""
    try:
        retention_days = config.get('retention', {}).get('keep_daily_logs_days', 30)
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))
        cutoff_date = datetime.now(tz) - timedelta(days=retention_days)

        removed_count = 0
        if LOG_DIR is None:
            load_config()
        for log_file in LOG_DIR.glob('*.jsonl'):
            try:
                file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                if file_date.replace(tzinfo=tz) < cutoff_date:
                    # Archive before deletion if not already archived
                    archive_path = ARCHIVE_DIR / log_file.name
                    if not archive_path.exists():
                        try:
                            shutil.copy2(log_file, archive_path)
                            logger.info(f"Archived before cleanup: {log_file}")
                        except Exception as e:
                            logger.warning(f"Failed to archive {log_file}: {e}")

                    log_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old log: {log_file}")
            except ValueError:
                logger.debug(f"Skipping non-date file: {log_file}")
            except Exception as e:
                logger.error(f"Failed to cleanup {log_file}: {e}")

        logger.info(f"Cleanup complete: removed {removed_count} old logs")
        return removed_count
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0

def read_daily_log(date) -> List[Dict[str, Any]]:
    """Read and parse a daily activity log (with error handling)"""
    log_path = get_log_path(date)

    if not log_path.exists():
        logger.debug(f"Log file not found: {log_path}")
        return []

    # Verify integrity before reading
    if not verify_log_integrity(log_path):
        logger.warning(f"Corrupted log detected: {log_path}")
        if repair_log_file(log_path):
            logger.info("Log repaired, proceeding with read")
        else:
            logger.error("Failed to repair log, returning partial data")

    events = []
    corrupted_lines = 0

    try:
        with open(log_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    corrupted_lines += 1
                    logger.warning(f"Skipping corrupt line {line_num}: {e}")

        if corrupted_lines > 0:
            logger.warning(f"Skipped {corrupted_lines} corrupted lines in {log_path}")

        return events
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        return []

def generate_summary(date) -> Optional[Dict[str, Any]]:
    """Generate a summary from the daily log (with error handling)"""
    try:
        events = read_daily_log(date)

        if not events:
            logger.info(f"No events found for {date}")
            return None

        metadata = None
        activities = []
        event_types = {}

        for event in events:
            event_type = event.get('type')
            if event_type == 'metadata':
                metadata = event.get('data', {})
            else:
                activities.append(event)
                event_types[event_type] = event_types.get(event_type, 0) + 1

        return {
            'metadata': metadata,
            'total_events': len(activities),
            'event_types': event_types,
            'activities': activities,
            'date': date.strftime('%Y-%m-%d')
        }
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return None

def health_check() -> Dict[str, Any]:
    """Perform system health check"""
    try:
        config = load_config()
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))
        now = datetime.now(tz)
        log_path = get_log_path(now)

        return {
            'status': 'healthy',
            'config_valid': True,
            'directories_exist': all([
                LOG_DIR and LOG_DIR.exists(),
                ARCHIVE_DIR and ARCHIVE_DIR.exists(),
                BACKUP_DIR and BACKUP_DIR.exists()
            ]),
            'current_log_exists': log_path.exists(),
            'current_log_valid': verify_log_integrity(log_path) if log_path.exists() else None,
            'timezone': config.get('tracking', {}).get('timezone', 'America/Chicago'),
            'current_time': now.isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

def main():
    """Main entry point"""
    try:
        ensure_directories()
        config = load_config()
        tz = ZoneInfo(config.get('tracking', {}).get('timezone', 'America/Chicago'))
        now = datetime.now(tz)

        # Run health check
        health = health_check()
        logger.info(f"Health check: {health['status']}")

        # Check if we need to initialize today's log
        result = initialize_daily_log(now, config)
        if result:
            logger.info("New daily log initialized")

        # Log example activity (this would be called by the actual tracker)
        success = log_activity('focus_change', {
            'app': 'Example App',
            'window_title': 'Example Window',
            'duration_seconds': 60
        })

        if success:
            logger.info("Example event logged successfully")
        else:
            logger.error("Failed to log example event")

        print(f"Daily log system ready. Current log: {get_log_path(now)}")
        print(f"Tracking starts at {config.get('tracking', {}).get('daily_start_hour', 6):02d}:{config.get('tracking', {}).get('daily_start_minute', 0):02d}")
        print(f"System health: {health['status']}")

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise

if __name__ == '__main__':
    main()
