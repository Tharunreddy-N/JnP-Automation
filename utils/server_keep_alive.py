"""
Server Keep-Alive - Monitors and automatically restarts the test server if it stops.
This ensures the server runs 24/7.

Usage:
    python utils/server_keep_alive.py
    
Or add to Windows startup for automatic monitoring.
"""

import subprocess
import sys
import os
import time
import socket
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SERVER_SCRIPT = PROJECT_ROOT / 'utils' / 'always_on_server.py'
SERVER_PID_FILE = PROJECT_ROOT / '.always_on_server.pid'
SERVER_PORT = 8766
CHECK_INTERVAL = 30  # Check every 30 seconds
MAX_RESTART_ATTEMPTS = 5  # Max restarts per hour
RESTART_WINDOW = 3600  # 1 hour window

restart_times = []  # Track restart times to prevent infinite restart loops


def log_message(msg):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")
    try:
        log_file = PROJECT_ROOT / 'server_keep_alive.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass


def is_port_in_use(port):
    """Check if server port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception:
        return False


def is_server_running():
    """Check if server is running by checking port and PID file."""
    # Check port first (most reliable)
    if is_port_in_use(SERVER_PORT):
        return True
    
    # Check PID file
    if SERVER_PID_FILE.exists():
        try:
            pid = int(SERVER_PID_FILE.read_text().strip())
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if str(pid) in result.stdout and 'python' in result.stdout.lower():
                    return True
            else:
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    return True
                except OSError:
                    pass
        except Exception:
            pass
    
    return False


def cleanup_stale_pid():
    """Remove stale PID file if process is not running."""
    if SERVER_PID_FILE.exists():
        try:
            pid = int(SERVER_PID_FILE.read_text().strip())
            if sys.platform == 'win32':
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if str(pid) not in result.stdout:
                    log_message(f"Removing stale PID file (process {pid} not running)")
                    SERVER_PID_FILE.unlink()
                    return True
            else:
                try:
                    os.kill(pid, 0)
                except OSError:
                    log_message(f"Removing stale PID file (process {pid} not running)")
                    SERVER_PID_FILE.unlink()
                    return True
        except Exception as e:
            log_message(f"Error checking PID file: {e}")
            try:
                SERVER_PID_FILE.unlink()
                return True
            except:
                pass
    return False


def can_restart():
    """Check if we can restart (prevent infinite restart loops)."""
    global restart_times
    
    # Remove old restart times (outside the window)
    current_time = time.time()
    restart_times = [t for t in restart_times if current_time - t < RESTART_WINDOW]
    
    # Check if we've exceeded max restarts
    if len(restart_times) >= MAX_RESTART_ATTEMPTS:
        log_message(f"WARNING: Too many restarts ({len(restart_times)}) in the last hour. Waiting before next restart attempt.")
        return False
    
    return True


def start_server():
    """Start the server in background."""
    try:
        # Clean up stale PID first
        cleanup_stale_pid()
        
        # Check if already running
        if is_server_running():
            log_message("Server is already running")
            return True
        
        log_message("Starting server...")
        os.chdir(PROJECT_ROOT)
        
        if sys.platform == 'win32':
            # Use pythonw for background execution (no console window)
            # Or use python with CREATE_NO_WINDOW for silent background
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            
            process = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                cwd=PROJECT_ROOT,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Unix-like systems
            process = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Verify it started
        if is_server_running():
            log_message("✅ Server started successfully!")
            restart_times.append(time.time())
            return True
        else:
            log_message("❌ Server failed to start (port not responding)")
            return False
            
    except Exception as e:
        log_message(f"❌ Error starting server: {e}")
        import traceback
        log_message(traceback.format_exc())
        return False


def monitor_loop():
    """Main monitoring loop."""
    log_message("=" * 60)
    log_message("Server Keep-Alive Monitor Started")
    log_message("=" * 60)
    log_message(f"Monitoring server on port {SERVER_PORT}")
    log_message(f"Check interval: {CHECK_INTERVAL} seconds")
    log_message(f"Max restarts per hour: {MAX_RESTART_ATTEMPTS}")
    log_message("=" * 60)
    
    consecutive_failures = 0
    last_status = None
    
    while True:
        try:
            is_running = is_server_running()
            
            if is_running:
                if last_status != 'running':
                    log_message("✅ Server is running")
                    consecutive_failures = 0
                last_status = 'running'
            else:
                consecutive_failures += 1
                if last_status != 'stopped':
                    log_message(f"⚠️ Server is not running (failure count: {consecutive_failures})")
                last_status = 'stopped'
                
                # Wait a bit before restarting (in case it's just starting up)
                if consecutive_failures >= 2:  # Wait 2 checks (60 seconds) before restarting
                    if can_restart():
                        log_message("Attempting to restart server...")
                        if start_server():
                            consecutive_failures = 0
                            last_status = 'running'
                        else:
                            log_message("Restart failed, will retry later")
                    else:
                        log_message("Restart limit reached, waiting before next attempt")
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log_message("Monitor stopped by user")
            break
        except Exception as e:
            log_message(f"Error in monitor loop: {e}")
            import traceback
            log_message(traceback.format_exc())
            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    try:
        # Try to start server if not running
        if not is_server_running():
            log_message("Server not running, starting it now...")
            start_server()
        
        # Start monitoring loop
        monitor_loop()
    except KeyboardInterrupt:
        log_message("Keep-alive monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        log_message(f"Fatal error: {e}")
        import traceback
        log_message(traceback.format_exc())
        sys.exit(1)
