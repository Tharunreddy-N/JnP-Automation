"""
Test Queue Watcher - Watches for test execution requests from dashboard
and runs them automatically without needing an HTTP server.

This script runs in the background and watches a queue file.
When the dashboard writes a test name to the queue, this script runs it.

Usage:
    python utils/test_queue_watcher.py
    
Or run it in the background:
    python utils/test_queue_watcher.py &
    
The script will keep running and watching for test requests.
"""

import json
import subprocess
import sys
import time
import os
from pathlib import Path
from datetime import datetime

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
QUEUE_FILE = PROJECT_ROOT / '.test_queue.json'
LOCK_FILE = PROJECT_ROOT / '.test_queue.lock'


def read_queue():
    """Read test queue from file."""
    if not QUEUE_FILE.exists():
        return []
    
    try:
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('queue', [])
    except (json.JSONDecodeError, IOError):
        return []


def write_queue(queue):
    """Write test queue to file."""
    try:
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'queue': queue, 'last_updated': datetime.now().isoformat()}, f, indent=2)
    except IOError as e:
        print(f"Error writing queue: {e}", file=sys.stderr)


def is_locked():
    """Check if queue is currently being processed."""
    if not LOCK_FILE.exists():
        return False
    
    try:
        # Check if lock file is stale (older than 5 minutes)
        lock_age = time.time() - LOCK_FILE.stat().st_mtime
        if lock_age > 300:  # 5 minutes
            # Remove stale lock
            LOCK_FILE.unlink()
            return False
        return True
    except OSError:
        return False


def set_lock():
    """Set lock file."""
    try:
        LOCK_FILE.touch()
    except OSError:
        pass


def remove_lock():
    """Remove lock file."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass


def run_test(test_name):
    """Run a pytest test."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running test: {test_name}")
    print(f"{'='*60}\n")
    
    try:
        # Change to project root
        os.chdir(PROJECT_ROOT)
        
        # Build pytest command
        cmd = [
            sys.executable,
            '-m', 'pytest',
            '-k', test_name,
            '-s', '-vv'
        ]
        
        # Run pytest
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' completed with exit code: {result.returncode}")
        print(f"{'='*60}\n")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test '{test_name}': {e}", file=sys.stderr)
        return False


def process_queue():
    """Process test queue."""
    if is_locked():
        return
    
    queue = read_queue()
    if not queue:
        return
    
    set_lock()
    
    try:
        # Process all queued tests
        while queue:
            test_name = queue.pop(0)
            if test_name:
                run_test(test_name)
            
            # Update queue file after each test
            write_queue(queue)
            
            # Small delay between tests
            if queue:
                time.sleep(1)
    finally:
        remove_lock()


def main():
    """Main watcher loop."""
    print(f"""
{'='*60}
Test Queue Watcher
{'='*60}
Watching for test execution requests...
Queue file: {QUEUE_FILE}
Project root: {PROJECT_ROOT}

The watcher will automatically run tests when requested from the dashboard.
Press Ctrl+C to stop.
{'='*60}
""")
    
    try:
        while True:
            process_queue()
            time.sleep(0.5)  # Check queue every 0.5 seconds
    except KeyboardInterrupt:
        print("\n\nShutting down watcher...")
        remove_lock()
        print("Watcher stopped.")


if __name__ == '__main__':
    main()
