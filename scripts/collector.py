#!/usr/bin/env python3
import json
import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(os.environ.get("DA_LOG_DIR", str(Path.home() / "DailyAccomplishments" / "logs")))
POLL_SECONDS = float(os.environ.get("DA_POLL_SECONDS", "5"))
OSASCRIPT_TIMEOUT = float(os.environ.get("DA_OSASCRIPT_TIMEOUT", "2.0"))
OSASCRIPT_RETRIES = int(os.environ.get("DA_OSASCRIPT_RETRIES", "1"))
FSYNC_EVERY_N = int(os.environ.get("DA_FSYNC_EVERY_N", "25"))

STOP = False

def _handle_stop(_sig, _frame):
    global STOP
    STOP = True

signal.signal(signal.SIGTERM, _handle_stop)
signal.signal(signal.SIGINT, _handle_stop)

def _now_iso():
    return datetime.now().isoformat()

def _ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def _activity_path_for_today():
    d = datetime.now().strftime("%Y-%m-%d")
    return LOG_DIR / f"activity-{d}.jsonl"

def _safe_print(msg: str, stream=None):
    if stream is None:
        stream = sys.stdout
    try:
        stream.write(msg + "\n")
        stream.flush()
    except Exception:
        pass

def get_idle_seconds():
    try:
        res = subprocess.run(
            ["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
            check=False,
        )
        out = res.stdout
        marker = "HIDIdleTime"
        idx = out.find(marker)
        if idx == -1:
            return 0.0
        tail = out[idx:idx+200]
        num = ""
        for ch in tail:
            if ch.isdigit():
                num += ch
            elif num:
                break
        if not num:
            return 0.0
        nanoseconds = float(num)
        return nanoseconds / 1e9
    except Exception:
        return 0.0

def get_active_window():
    script = [
        'tell application "System Events"',
        "set P to (first process whose frontmost is true)",
        "set frontApp to name of P",
        "set frontAppId to bundle identifier of P",
        "if (exists window 1 of P) then",
        "set windowTitle to name of window 1 of P",
        "else",
        'set windowTitle to ""',
        "end if",
        'return frontApp & "|" & frontAppId & "|" & windowTitle',
        "end tell",
    ]

    cmd = ["/usr/bin/osascript"]
    for line in script:
        cmd += ["-e", line]

    last_err = None
    for attempt in range(OSASCRIPT_RETRIES + 1):
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=OSASCRIPT_TIMEOUT,
                check=False,
            )
            if res.returncode == 0:
                s = (res.stdout or "").strip()
                parts = s.split("|", 2)
                app = parts[0] if len(parts) > 0 else ""
                bid = parts[1] if len(parts) > 1 else ""
                title = parts[2] if len(parts) > 2 else ""
                return app, bid, title, None
            last_err = (res.stderr or "").strip() or f"osascript exit {res.returncode}"
        except subprocess.TimeoutExpired:
            last_err = f"osascript timed out after {OSASCRIPT_TIMEOUT}s"
        except Exception as e:
            last_err = str(e)

        if attempt < OSASCRIPT_RETRIES:
            time.sleep(0.15)

    return "Unknown", "", "", last_err

def main():
    _ensure_dirs()

    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    _safe_print(f"Activity Collector started at {_now_iso()}")
    _safe_print(f"Logging to: {LOG_DIR}")
    _safe_print(f"Poll interval: {POLL_SECONDS}s")
    _safe_print(f"osascript timeout: {OSASCRIPT_TIMEOUT}s retries: {OSASCRIPT_RETRIES}")

    activity_path = _activity_path_for_today()
    n_since_fsync = 0

    f = open(activity_path, "a", buffering=1, encoding="utf-8")
    try:
        while not STOP:
            ts = _now_iso()
            idle = get_idle_seconds()

            app, bundle_id, window_title, err = get_active_window()
            if err:
                _safe_print(f"Error getting active window: {err}", stream=sys.stderr)

            event = {
                "timestamp": ts,
                "app": app,
                "bundle_id": bundle_id,
                "window": window_title,
                "idle_seconds": round(float(idle), 1),
            }

            try:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                n_since_fsync += 1
                if n_since_fsync >= FSYNC_EVERY_N:
                    try:
                        f.flush()
                        os.fsync(f.fileno())
                    except Exception:
                        pass
                    n_since_fsync = 0
            except Exception as e:
                _safe_print(f"Error writing activity log: {e}", stream=sys.stderr)

            target = POLL_SECONDS
            slept = 0.0
            while slept < target and not STOP:
                step = min(0.25, target - slept)
                time.sleep(step)
                slept += step

            new_path = _activity_path_for_today()
            if new_path != activity_path:
                try:
                    f.flush()
                    f.close()
                except Exception:
                    pass
                activity_path = new_path
                f = open(activity_path, "a", buffering=1, encoding="utf-8")
                n_since_fsync = 0

    finally:
        try:
            f.flush()
            f.close()
        except Exception:
            pass
        _safe_print(f"Activity Collector exiting at {_now_iso()}")

if __name__ == "__main__":
    main()
