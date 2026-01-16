"""
Auto-start Test Watcher - Automatically starts the test watcher in the background.
This script can be run at system startup or called from the dashboard.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WATCHER_SCRIPT = PROJECT_ROOT / 'utils' / 'test_queue_watcher.py'


def is_watcher_running():
    """Check if watcher is already running."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('test_queue_watcher.py' in str(arg) for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # If psutil not available, try simple check
        pass
    return False


def start_watcher():
    """Start the test watcher in background."""
    try:
        # Change to project root
        os.chdir(PROJECT_ROOT)
        
        # Start watcher in background (Windows)
        if sys.platform == 'win32':
            # Use START command to run in new window
            subprocess.Popen(
                [sys.executable, str(WATCHER_SCRIPT)],
                cwd=PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
            )
        else:
            # Unix-like systems
            subprocess.Popen(
                [sys.executable, str(WATCHER_SCRIPT)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # Give it a moment to start
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Error starting watcher: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if not is_watcher_running():
        print("Starting test watcher...")
        if start_watcher():
            print("✅ Test watcher started successfully!")
        else:
            print("❌ Failed to start test watcher")
            sys.exit(1)
    else:
        print("Test watcher is already running")
