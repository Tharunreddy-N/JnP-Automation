"""
Auto-start Server Helper - Starts the always-on server automatically.
This can be called from the dashboard or run as a background service.
"""

import subprocess
import sys
import os
import time
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SERVER_SCRIPT = PROJECT_ROOT / 'utils' / 'always_on_server.py'


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True


def start_server():
    """Start the always-on server in background."""
    try:
        # Check if server is already running
        if is_port_in_use(8766):
            print("Server is already running on port 8766")
            return True
        
        # Change to project root
        os.chdir(PROJECT_ROOT)
        
        # Start server in background (Windows)
        if sys.platform == 'win32':
            # Use DETACHED_PROCESS to run in background
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            
            subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                cwd=PROJECT_ROOT,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Unix-like systems
            subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Verify it started
        if is_port_in_use(8766):
            print("✅ Server started successfully!")
            return True
        else:
            print("❌ Server failed to start")
            return False
            
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if start_server():
        sys.exit(0)
    else:
        sys.exit(1)
