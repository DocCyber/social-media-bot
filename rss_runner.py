"""
RSS Runner

Continuous runner that executes RSS watcher at :15 and :45 past each hour.
Posts one item per run with pubDate tracking to avoid reposting old content.
"""

from __future__ import annotations

import time
import sys
from datetime import datetime
from pathlib import Path

from rss import rss_watcher
from utils.config_manager import ConfigManager

# Lock file to prevent concurrent runs
LOCK_FILE = Path(__file__).parent / "rss" / ".rss_runner.lock"


def wait_until_next_run_time(test_mode_enabled: bool = False, test_interval_minutes: int = 5) -> None:
    """
    Wait until the next scheduled run time.

    In normal mode: waits until :15 or :45 past the hour
    In test mode: waits for the configured interval (default 5 minutes)
    """
    if test_mode_enabled:
        # Test mode: simple interval-based scheduling
        seconds_to_wait = test_interval_minutes * 60
        next_run = datetime.fromtimestamp(time.time() + seconds_to_wait)
        print(f"[TEST MODE] Next run scheduled for {next_run.strftime('%H:%M:%S')} (waiting {test_interval_minutes} minutes)")
        time.sleep(seconds_to_wait)
    else:
        # Normal mode: scheduled at :15 and :45 past each hour
        now = datetime.now()
        current_minute = now.minute
        current_second = now.second

        # Determine next target minute
        if current_minute < 15:
            minutes_to_wait = 15 - current_minute
        elif current_minute < 45:
            minutes_to_wait = 45 - current_minute
        else:
            # After :45, wait until next hour's :15
            minutes_to_wait = (60 - current_minute) + 15

        # Calculate total seconds to wait (to hit exactly :15:00 or :45:00)
        seconds_to_wait = (minutes_to_wait * 60) - current_second

        if seconds_to_wait > 0:
            next_run = datetime.fromtimestamp(time.time() + seconds_to_wait)
            print(f"Next run scheduled for {next_run.strftime('%H:%M:%S')} (waiting {seconds_to_wait} seconds)")
            time.sleep(seconds_to_wait)


def acquire_lock() -> bool:
    """
    Try to acquire lock file. Returns True if acquired, False if another instance is running.
    """
    try:
        if LOCK_FILE.exists():
            # Check if lock is stale (older than 10 minutes)
            lock_age = time.time() - LOCK_FILE.stat().st_mtime
            if lock_age < 600:  # 10 minutes
                return False
            print(f"Removing stale lock file (age: {lock_age:.0f}s)")
            LOCK_FILE.unlink()

        # Create lock file
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(str(datetime.now()))
        return True
    except Exception as e:
        print(f"Lock acquisition error: {e}")
        return False


def release_lock() -> None:
    """Release the lock file."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception as e:
        print(f"Lock release error: {e}")


def main() -> None:
    # Load config to check test mode
    cfg = ConfigManager()
    cfg.load_all_configs()
    rss_cfg = cfg.get_global_config("rss", {}) or {}
    test_mode = rss_cfg.get("test_mode", {})
    test_mode_enabled = test_mode.get("enabled", False)
    test_interval = test_mode.get("poll_interval_minutes", 5)

    if test_mode_enabled:
        print("=" * 60)
        print("WARNING: TEST MODE ENABLED")
        print(f"RSS runner will poll every {test_interval} minutes")
        print("Set 'test_mode.enabled' to false in master_config.json for production")
        print("=" * 60)
    else:
        print("Starting RSS runner (scheduled at :15 and :45 past each hour)...")

    print("Press Ctrl+C to stop")

    # Ensure we clean up lock on exit
    import atexit
    atexit.register(release_lock)

    while True:
        try:
            # Acquire lock before running
            if not acquire_lock():
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another instance is running, skipping this cycle")
                wait_until_next_run_time(test_mode_enabled, test_interval)
                continue

            now = datetime.now()
            mode_label = "[TEST MODE] " if test_mode_enabled else ""
            print(f"\n{mode_label}[{now.strftime('%Y-%m-%d %H:%M:%S')}] RSS poll cycle start")
            rss_watcher.run_once()
            print(f"{mode_label}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RSS poll cycle complete")

            # Release lock after successful run
            release_lock()

        except KeyboardInterrupt:
            print("\nRSS runner stopped by user")
            release_lock()
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] RSS cycle error: {e}")
            release_lock()

        # Wait until next scheduled time
        wait_until_next_run_time(test_mode_enabled, test_interval)


if __name__ == "__main__":
    main()

