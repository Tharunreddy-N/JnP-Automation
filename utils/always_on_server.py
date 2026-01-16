"""
Always-On Test Server - Runs in background and automatically processes test requests.
This server should be started once and kept running. It watches the queue file and runs tests automatically.

Usage:
    python utils/always_on_server.py
    
Or add to Windows startup:
    pythonw utils/always_on_server.py
"""

import json
import subprocess
import sys
import time
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import signal

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
QUEUE_FILE = PROJECT_ROOT / '.test_queue.json'
LOCK_FILE = PROJECT_ROOT / '.test_queue.lock'
SERVER_PID_FILE = PROJECT_ROOT / '.always_on_server.pid'  # PID file to prevent multiple instances
TEST_EXECUTION_LOCK = PROJECT_ROOT / '.test_execution.lock'  # Lock to prevent multiple tests running simultaneously


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
    except IOError:
        pass


def is_locked():
    """Check if queue is currently being processed."""
    if not LOCK_FILE.exists():
        return False
    try:
        lock_age = time.time() - LOCK_FILE.stat().st_mtime
        if lock_age > 300:  # 5 minutes - stale lock
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


def check_server_running():
    """Check if server is already running by checking PID file and port."""
    # Check port first
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', 8766))
            if result == 0:
                return True  # Port is in use
    except Exception:
        pass
    
    # Check PID file
    if SERVER_PID_FILE.exists():
        try:
            pid = int(SERVER_PID_FILE.read_text().strip())
            # Check if process exists (Windows)
            if sys.platform == 'win32':
                try:
                    import subprocess
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}'],
                        capture_output=True,
                        text=True
                    )
                    if str(pid) in result.stdout:
                        return True  # Process is running
                except Exception:
                    pass
            else:
                # Unix-like: check if process exists
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    return True
                except OSError:
                    pass  # Process doesn't exist
        except (ValueError, OSError):
            pass
    
    return False


def write_pid_file():
    """Write current process ID to PID file."""
    try:
        SERVER_PID_FILE.write_text(str(os.getpid()))
    except Exception as e:
        print(f"Warning: Could not write PID file: {e}", file=sys.stderr)


def remove_pid_file():
    """Remove PID file."""
    try:
        if SERVER_PID_FILE.exists():
            SERVER_PID_FILE.unlink()
    except OSError:
        pass


def acquire_test_lock():
    """Acquire lock to prevent multiple tests running simultaneously - STRICT MODE."""
    import time
    start_time = time.time()
    timeout = 10  # Wait max 10 seconds
    
    while time.time() - start_time < timeout:
        try:
            if not TEST_EXECUTION_LOCK.exists():
                # Create lock file with PID
                TEST_EXECUTION_LOCK.write_text(str(os.getpid()))
                time.sleep(0.2)  # Longer delay to ensure file is written
                # Verify we own the lock
                if TEST_EXECUTION_LOCK.exists():
                    lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                    if lock_pid == str(os.getpid()):
                        print(f"✅ Acquired test execution lock (PID: {os.getpid()})")
                        return True
            else:
                # Check if lock is stale
                try:
                    lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                    file_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
                    
                    # Check if process is still running
                    if sys.platform == 'win32':
                        import subprocess
                        result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {lock_pid}'],
                            capture_output=True,
                            text=True
                        )
                        if str(lock_pid) not in result.stdout:
                            # Process is dead, remove stale lock
                            print(f"⚠️  Removing stale test lock (PID {lock_pid} not running)")
                            TEST_EXECUTION_LOCK.unlink()
                            continue
                        else:
                            # Process is running, wait
                            print(f"⏳ Another test is running (PID: {lock_pid}), waiting...")
                            time.sleep(1)
                            continue
                    else:
                        # Unix: check if process exists
                        try:
                            os.kill(int(lock_pid), 0)
                            # Process exists, wait
                            time.sleep(1)
                            continue
                        except OSError:
                            # Process dead, remove lock
                            TEST_EXECUTION_LOCK.unlink()
                            continue
                    
                    if file_age > 600:  # 10 minutes - definitely stale
                        print(f"⚠️  Removing very old test lock (age: {file_age:.0f}s)")
                        TEST_EXECUTION_LOCK.unlink()
                        continue
                except Exception as e:
                    print(f"⚠️  Error checking lock: {e}")
                    try:
                        TEST_EXECUTION_LOCK.unlink()
                    except:
                        pass
                    continue
        except Exception as e:
            print(f"⚠️  Error acquiring lock: {e}")
            time.sleep(0.5)
    
    print(f"❌ Could not acquire test execution lock within {timeout} seconds!")
    return False


def release_test_lock():
    """Release test execution lock."""
    try:
        if TEST_EXECUTION_LOCK.exists() and TEST_EXECUTION_LOCK.read_text().strip() == str(os.getpid()):
            TEST_EXECUTION_LOCK.unlink()
    except Exception:
        pass


def run_test_command(test_name):
    """Run a pytest test command - only one test at a time."""
    # Acquire lock to prevent multiple tests running
    if not acquire_test_lock():
        print(f"⚠️  Another test is currently running. Skipping '{test_name}'")
        return False
    
    try:
        os.chdir(PROJECT_ROOT)
        # Use -k to match test name - ensure only ONE test runs
        cmd = [
            sys.executable,
            '-m', 'pytest',
            '-k', test_name,
            '-s', '-vv',
            '--maxfail=1',  # Stop after first failure
            '-x',  # Exit on first failure
            '--tb=short',  # Shorter traceback
        ]
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running test: {test_name}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*60}\n")
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=False,
            text=True
        )
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' completed with exit code: {result.returncode}")
        print(f"{'='*60}\n")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test '{test_name}': {e}", file=sys.stderr)
        return False
    finally:
        # Always release lock
        release_test_lock()


def process_queue():
    """Process test queue from file."""
    if is_locked():
        return
    
    queue = read_queue()
    if not queue:
        return
    
    set_lock()
    
    try:
        while queue:
            test_name = queue.pop(0)
            if test_name:
                run_test_command(test_name)
            write_queue(queue)
            if queue:
                time.sleep(1)
    finally:
        remove_lock()


class QueueHandler(BaseHTTPRequestHandler):
    """HTTP handler for adding tests to queue."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to add test to queue."""
        if self.path == '/add-test':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                test_name = data.get('testName', '')
                
                if not test_name:
                    self.send_error_response(400, 'Test name is required')
                    return
                
                # Add to queue
                queue = read_queue()
                if test_name not in queue:
                    queue.append(test_name)
                    write_queue(queue)
                
                # Process queue in background
                def process_in_background():
                    time.sleep(0.5)  # Small delay
                    process_queue()
                
                thread = threading.Thread(target=process_in_background, daemon=True)
                thread.start()
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': True,
                    'message': f'Test "{test_name}" added to queue and will run shortly'
                })
                self.wfile.write(response.encode('utf-8'))
                
            except Exception as e:
                self.send_error_response(500, f'Error: {str(e)}')
        else:
            self.send_error_response(404, 'Not found')
    
    def send_error_response(self, code, message):
        """Send an error response."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = json.dumps({
            'success': False,
            'error': message
        })
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        pass  # Suppress default logging


def watch_queue_loop():
    """Background thread to watch file queue."""
    while True:
        try:
            process_queue()
            time.sleep(0.5)  # Check queue every 0.5 seconds
        except Exception as e:
            print(f"Error in queue watcher: {e}", file=sys.stderr)
            time.sleep(1)


def run_server(port=8766):
    """Run the always-on server."""
    # Check if server is already running
    if check_server_running():
        print(f"❌ Server is already running on port {port}!")
        print(f"   PID file: {SERVER_PID_FILE}")
        print(f"   If you're sure it's not running, delete the PID file and try again.")
        sys.exit(1)
    
    # Write PID file
    write_pid_file()
    
    # Register cleanup handler
    def cleanup_handler(signum=None, frame=None):
        remove_pid_file()
        remove_lock()
        sys.exit(0)
    
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, QueueHandler)
    
    # Start file queue watcher in background thread
    queue_watcher = threading.Thread(target=watch_queue_loop, daemon=True)
    queue_watcher.start()
    
    print(f"""
{'='*60}
Always-On Test Server
{'='*60}
Server running on http://localhost:{port}
Queue file: {QUEUE_FILE}

This server will:
- Accept test requests via HTTP POST to /add-test
- Watch queue file for test requests
- Automatically run tests when requested

Keep this running in the background.
Press Ctrl+C to stop.
{'='*60}
""")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()
        remove_lock()
        remove_pid_file()
        print("Server stopped.")
    except Exception as e:
        remove_pid_file()
        remove_lock()
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run always-on test server')
    parser.add_argument('--port', type=int, default=8766, help='Port to run server on (default: 8766)')
    args = parser.parse_args()
    
    run_server(args.port)
