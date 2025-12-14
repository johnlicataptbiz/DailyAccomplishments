import json
import sys
from pathlib import Path


# Ensure repo root is on PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools.daily_logger as daily_logger


def test_load_config_merges_example_defaults(tmp_path, monkeypatch):
    base_config = {
        "tracking": {"timezone": "America/New_York"},
        "report": {"log_dir": "logs/daily", "archive_dir": "logs/archive", "backup_dir": "logs/backup"},
        "retention": {},
        "analytics": {},
        "notifications": {},
        "weights": {"meeting_credit": 0.25},
    }
    user_config = {"weights": {"meeting_credit": 0.5}}

    base_path = tmp_path / "config.json.example"
    user_path = tmp_path / "config.json"
    base_path.write_text(json.dumps(base_config))
    user_path.write_text(json.dumps(user_config))

    monkeypatch.setattr(daily_logger, "CONFIG_EXAMPLE_PATH", base_path)
    monkeypatch.setattr(daily_logger, "CONFIG_PATH", user_path)

    # Reset module cache/state so load_config re-reads files.
    monkeypatch.setattr(daily_logger, "_CONFIG_CACHE", None)
    monkeypatch.setattr(daily_logger, "LOG_DIR", None)
    monkeypatch.setattr(daily_logger, "ARCHIVE_DIR", None)
    monkeypatch.setattr(daily_logger, "BACKUP_DIR", None)

    cfg = daily_logger.load_config()
    assert cfg["tracking"]["timezone"] == "America/New_York"
    assert cfg["weights"]["meeting_credit"] == 0.5

