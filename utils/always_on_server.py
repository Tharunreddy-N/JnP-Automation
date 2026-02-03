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
from socketserver import ThreadingMixIn
import threading
import signal

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
QUEUE_FILE = PROJECT_ROOT / '.test_queue.json'
LOCK_FILE = PROJECT_ROOT / '.test_queue.lock'
SERVER_PID_FILE = PROJECT_ROOT / '.always_on_server.pid'  # PID file to prevent multiple instances
TEST_EXECUTION_LOCK = PROJECT_ROOT / '.test_execution.lock'  # Lock to prevent multiple tests running simultaneously

# Create a thread lock for queue processing to prevent race conditions within the same process
_QUEUE_PROCESSING_LOCK = threading.Lock()

def log_debug(msg):
    """Log debug message to file."""
    try:
        log_file = PROJECT_ROOT / 'server_debug.log'
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass

def print_and_log(msg):
    print(msg)
    log_debug(msg)



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
        if lock_age > 60:  # 1 minute - stale lock (reduced for faster recovery)
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking if server is already running...")
    
    # Check port first
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', 8766))
            if result == 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Port 8766 is in use - server may already be running")
                return True  # Port is in use
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Port 8766 is available")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking port: {e}")
    
    # Check PID file
    if SERVER_PID_FILE.exists():
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PID file exists: {SERVER_PID_FILE}")
        try:
            pid = int(SERVER_PID_FILE.read_text().strip())
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking if process {pid} is running...")
            # Check if process exists (Windows)
            if sys.platform == 'win32':
                try:
                    import subprocess
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if str(pid) in result.stdout and 'python' in result.stdout.lower():
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process {pid} is running")
                        return True  # Process is running
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process {pid} not found - PID file is stale")
                        # Remove stale PID file
                        try:
                            SERVER_PID_FILE.unlink()
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removed stale PID file")
                        except:
                            pass
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking process: {e}")
            else:
                # Unix-like: check if process exists
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process {pid} is running")
                    return True
                except OSError:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Process {pid} not found - PID file is stale")
                    # Remove stale PID file
                    try:
                        SERVER_PID_FILE.unlink()
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removed stale PID file")
                    except:
                        pass
        except (ValueError, OSError) as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error reading PID file: {e}")
            # Remove invalid PID file
            try:
                SERVER_PID_FILE.unlink()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removed invalid PID file")
            except:
                pass
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No PID file found - server not running")
    
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
    server_pid = os.getpid()  # Server's own PID - don't treat server as test execution
    
    while time.time() - start_time < timeout:
        try:
            if not TEST_EXECUTION_LOCK.exists():
                # SERVER NOW CREATES LOCK: To prevent race conditions between server starting 
                # a test and pytest creating its own lock, the server itself will 
                # now create the lock file with its own PID first.
                try:
                    TEST_EXECUTION_LOCK.write_text(str(server_pid))
                    print(f"OK: Server acquired test execution lock (PID: {server_pid})")
                    return True
                except Exception as e:
                    print(f"ERROR: Server could not write lock file: {e}")
                    return False
            else:
                # Check if lock is stale
                try:
                    lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                    file_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
                    
                    # IMPORTANT: If lock PID is the server's own PID, it's a stale lock from server startup
                    # The server should never hold a test execution lock - only pytest processes should
                    if lock_pid == str(server_pid):
                        print(f"WARNING: Removing stale test lock (lock PID {lock_pid} is server PID - this is invalid)")
                        TEST_EXECUTION_LOCK.unlink()
                        continue
                    
                    # Check if process is still running
                    if sys.platform == 'win32':
                        import subprocess
                        result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {lock_pid}'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if str(lock_pid) not in result.stdout:
                            # Process is dead, remove stale lock
                            print(f"WARNING: Removing stale test lock (PID {lock_pid} not running)")
                            TEST_EXECUTION_LOCK.unlink()
                            continue
                        else:
                            # Check if it's a pytest process (not just any Python process)
                            # If it's not pytest, it might be stale
                            cmdline_result = subprocess.run(
                                ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            # Check if lock PID is the server's own PID (invalid - server shouldn't hold test lock)
                            if lock_pid == str(server_pid):
                                print(f"WARNING: Removing invalid test lock (lock PID {lock_pid} is server PID - server should not hold test lock)")
                                TEST_EXECUTION_LOCK.unlink()
                                continue
                            
                            if 'pytest' not in cmdline_result.stdout.lower():
                                # Not a pytest process, might be stale
                                if file_age > 300:  # Older than 5 minutes
                                    print(f"WARNING: Removing stale test lock (PID {lock_pid} is not pytest, age: {file_age:.0f}s)")
                                    TEST_EXECUTION_LOCK.unlink()
                                    continue
                            
                            # Process is running and might be pytest, wait
                            print(f"WAITING: Another test is running (PID: {lock_pid}), waiting...")
                            time.sleep(1)
                            continue
                    else:
                        # Unix: check if process exists
                        try:
                            # Don't treat server PID as test execution
                            if lock_pid == str(server_pid):
                                print(f"WARNING: Removing invalid test lock (lock PID {lock_pid} is server PID)")
                                TEST_EXECUTION_LOCK.unlink()
                                continue
                            os.kill(int(lock_pid), 0)
                            # Process exists, wait
                            time.sleep(1)
                            continue
                        except OSError:
                            # Process dead, remove lock
                            TEST_EXECUTION_LOCK.unlink()
                            continue
                    
                    if file_age > 600:  # 10 minutes - definitely stale
                        print(f"WARNING: Removing very old test lock (age: {file_age:.0f}s)")
                        TEST_EXECUTION_LOCK.unlink()
                        continue
                except Exception as e:
                    print(f"WARNING: Error checking lock: {e}")
                    try:
                        TEST_EXECUTION_LOCK.unlink()
                    except:
                        pass
                    continue
        except Exception as e:
            print(f"WARNING: Error acquiring lock: {e}")
            time.sleep(0.5)
    
    print(f"ERROR: Could not acquire test execution lock within {timeout} seconds!")
    return False


def release_test_lock():
    """Release test execution lock."""
    try:
        if TEST_EXECUTION_LOCK.exists():
            lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
            # Only release if we own it (but server should never own it)
            if lock_pid == str(os.getpid()):
                print(f"WARNING: Server process releasing test lock - this should not happen!")
                TEST_EXECUTION_LOCK.unlink()
            # Also check if lock is stale (older than 10 minutes)
            elif (time.time() - TEST_EXECUTION_LOCK.stat().st_mtime) > 600:
                print(f"WARNING: Removing stale test execution lock (age > 10 minutes)")
                TEST_EXECUTION_LOCK.unlink()
    except Exception:
        pass


def run_test_command(test_name):
    """Run a pytest test command - only one test at a time."""
    # CRITICAL: Create test execution lock IMMEDIATELY to prevent queue watcher from starting another test
    # The lock will be updated by pytest subprocess with its own PID once it starts
    
    print_and_log(f"Attempting to run test: {test_name}")
    
    # Create lock immediately with server PID (pytest will update it later)
    server_pid = os.getpid()
    try:
        TEST_EXECUTION_LOCK.write_text(str(server_pid))
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Created test execution lock (server PID: {server_pid}) - prevents duplicate runs")
        time.sleep(0.3)  # Small delay to ensure lock file is written to disk
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Could not create test execution lock: {e}")

    # Check if another test is running (but don't create lock as server)
    if TEST_EXECUTION_LOCK.exists():
        try:
            lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
            server_pid = os.getpid()
            file_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
            
            # If lock is server's PID, it's invalid - remove it
            if lock_pid == str(server_pid):
                print(f"WARNING: Removing invalid test lock (server PID {lock_pid} should not hold test lock)")
                TEST_EXECUTION_LOCK.unlink()
            # If lock is old (>5 min), might be stale
            elif file_age > 300:
                # Check if process exists
                # Check if process exists
                if sys.platform == 'win32':
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {lock_pid}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if str(lock_pid) not in result.stdout:
                        print(f"WARNING: Removing stale test lock (PID {lock_pid} not running, age: {file_age:.0f}s)")
                        TEST_EXECUTION_LOCK.unlink()
                    else:
                        # Check if it's actually pytest
                        cmdline_result = subprocess.run(
                            ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if 'pytest' not in cmdline_result.stdout.lower():
                            print(f"WARNING: Removing stale test lock (PID {lock_pid} is not pytest)")
                            TEST_EXECUTION_LOCK.unlink()
                        else:
                            print(f"WARNING: Another test is running (PID: {lock_pid}). Skipping '{test_name}'")
                            return False
                else:
                    try:
                        os.kill(int(lock_pid), 0)
                        print(f"WARNING: Another test is running (PID: {lock_pid}). Skipping '{test_name}'")
                        return False
                    except OSError:
                        print(f"WARNING: Removing stale test lock (PID {lock_pid} not running)")
                        TEST_EXECUTION_LOCK.unlink()
            else:
                # Lock exists and is fresh - check if it's a real pytest process
                # Lock exists and is fresh - check if it's a real pytest process
                if sys.platform == 'win32':
                    result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {lock_pid}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if str(lock_pid) in result.stdout:
                        # Check if it's pytest
                        cmdline_result = subprocess.run(
                            ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if 'pytest' in cmdline_result.stdout.lower():
                            print(f"WARNING: Another test is currently running (PID: {lock_pid}). Skipping '{test_name}'")
                            return False
                        else:
                            # Not pytest, remove invalid lock
                            print(f"WARNING: Removing invalid test lock (PID {lock_pid} is not pytest)")
                            TEST_EXECUTION_LOCK.unlink()
                    else:
                        # Process not running, remove stale lock
                        print(f"WARNING: Removing stale test lock (PID {lock_pid} not running)")
                        TEST_EXECUTION_LOCK.unlink()
                else:
                    try:
                        os.kill(int(lock_pid), 0)
                        print(f"WARNING: Another test is running (PID: {lock_pid}). Skipping '{test_name}'")
                        return False
                    except OSError:
                        print(f"WARNING: Removing stale test lock (PID {lock_pid} not running)")
                        TEST_EXECUTION_LOCK.unlink()
        except Exception as e:
            print(f"WARNING: Error checking test lock: {e}")
            # If we can't check, try to remove it
            try:
                TEST_EXECUTION_LOCK.unlink()
            except:
                pass
    
    # No valid lock exists - test can proceed
    # The pytest process will create its own lock when it starts
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OK: No test execution lock - proceeding with test '{test_name}'")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test execution will start now...")
    
    # Force clean .pytest_running.lock to prevent "Another pytest process is running" error
    # This lock is created by BenchSale_Conftest.py
    pytest_lock_file = PROJECT_ROOT / '.pytest_running.lock'
    if pytest_lock_file.exists():
        try:
            print_and_log(f"[DEBUG] Removing stale .pytest_running.lock before starting test")
            pytest_lock_file.unlink()
        except Exception as e:
            print_and_log(f"[WARNING] Could not remove .pytest_running.lock: {e}")

    try:
        # Clean up any stale browser lock files before running test
        browser_lock_file = PROJECT_ROOT / '.browser_lock'
        if browser_lock_file.exists():
            try:
                # Check if lock is stale (older than 5 minutes)
                lock_age = time.time() - browser_lock_file.stat().st_mtime
                if lock_age > 300:  # 5 minutes
                    print(f"[DEBUG] Removing stale browser lock (age: {lock_age:.0f}s)")
                    browser_lock_file.unlink()
                else:
                    # Check if process in lock file is still running
                    try:
                        lock_pid = int(browser_lock_file.read_text().strip())
                        if sys.platform == 'win32':
                            result = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                capture_output=True,
                                text=True
                            )
                            if str(lock_pid) not in result.stdout:
                                print(f"[DEBUG] Removing stale browser lock (PID {lock_pid} not running)")
                                browser_lock_file.unlink()
                    except (ValueError, OSError):
                        # Invalid lock file, remove it
                        browser_lock_file.unlink()
            except Exception as e:
                print(f"[DEBUG] Could not check browser lock: {e}")
        
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
        
        # Prepare environment to ensure browser can open
        env = os.environ.copy()
        # Ensure browser is not headless - explicitly set to visible
        env['HEADLESS'] = '0'
        env['PLAYWRIGHT_BROWSERS_PATH'] = ''  # Use system browsers
        # Ensure MAXIMIZE_BROWSER is set if it was in parent environment
        if 'MAXIMIZE_BROWSER' not in env:
            env['MAXIMIZE_BROWSER'] = '1'
        
        # On Windows, ensure subprocess can show GUI windows
        # Use CREATE_NO_WINDOW (0x08000000) to prevent console window, but allow GUI
        # Or use 0 to inherit parent console and allow GUI windows
        if sys.platform == 'win32':
            # IMPORTANT: Use 0 (default) to allow GUI windows to show
            # CREATE_NO_WINDOW would prevent console but might also prevent browser
            # DETACHED_PROCESS would detach but might hide windows
            # Default (0) is best - inherits console and allows GUI
            creation_flags = 0
        else:
            creation_flags = 0
        
        print(f"[DEBUG] Environment: HEADLESS={env.get('HEADLESS')}, MAXIMIZE_BROWSER={env.get('MAXIMIZE_BROWSER')}")
        print(f"[DEBUG] Platform: {sys.platform}")
        print(f"[DEBUG] Starting test execution - browser should open in visible mode...")
        print(f"[DEBUG] Command: {' '.join(cmd)}")
        print(f"[DEBUG] Working directory: {PROJECT_ROOT}")
        
        # CRITICAL: Use shell=False but ensure GUI windows can show
        # On Windows, subprocess.run with shell=False should allow GUI windows
        # Use CREATE_NEW_CONSOLE to spawn a separate visible terminal for the test
        # Subprocess already imported globally
        
        # CRITICAL: Create test execution lock IMMEDIATELY before starting subprocess
        # This prevents queue watcher from starting another test while this one is launching
        server_pid = os.getpid()
        try:
            TEST_EXECUTION_LOCK.write_text(str(server_pid))
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Created test execution lock (server PID: {server_pid})")
            # Small delay to ensure lock file is written to disk
            time.sleep(0.2)
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Could not create test execution lock: {e}")
        
        print_and_log(f"[DEBUG] Launching test '{test_name}' in new console window...")
        
        if sys.platform == 'win32':
             # 0x10 is CREATE_NEW_CONSOLE
             creation_flags = 0x10 
             
             # Start subprocess (pytest will update the lock with its own PID)
             result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=False, # Must be False to show text in the new window
                text=True,
                env=env,
                creationflags=creation_flags,
                shell=False
            )
        else:
            # Fallback for non-Windows (though user is on Windows)
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=False,
                text=True,
                env=env,
                shell=False
            )
        
        try:
            # Just log the exit code since we aren't capturing output anymore (it's in the popped window)
            print_and_log(f"[DEBUG] Test execution completed. Exit code: {result.returncode}")
        except Exception as log_err:
            print(f"[WARNING] Could not log result: {log_err}")
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' completed with exit code: {result.returncode}")
        print(f"{'='*60}\n")
        
        # CRITICAL: Immediately clean up test execution lock after test completes
        # The pytest process should have cleaned it up, but ensure it's gone
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up test execution lock...")
        if TEST_EXECUTION_LOCK.exists():
            try:
                lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                server_pid = os.getpid()
                # If lock PID is server's PID, remove it (invalid)
                if lock_pid == str(server_pid):
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing invalid test lock (server PID)")
                    TEST_EXECUTION_LOCK.unlink()
                else:
                    # Check if process is still running
                    if sys.platform == 'win32':
                        check_result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {lock_pid}'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if str(lock_pid) not in check_result.stdout:
                            # Process is dead, remove stale lock
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale test lock (PID {lock_pid} not running)")
                            TEST_EXECUTION_LOCK.unlink()
                        else:
                            # Process still running, but test subprocess should be done
                            # Wait a bit more and check again
                            time.sleep(2)
                            check_result2 = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if str(lock_pid) not in check_result2.stdout:
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale test lock after wait")
                                TEST_EXECUTION_LOCK.unlink()
                            else:
                                # Still running - might be a different process, remove lock anyway
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Force removing test lock (test subprocess should be done)")
                                TEST_EXECUTION_LOCK.unlink()
                    else:
                        try:
                            os.kill(int(lock_pid), 0)
                            # Process exists, wait a bit
                            time.sleep(2)
                            try:
                                os.kill(int(lock_pid), 0)
                                # Still exists, force remove
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Force removing test lock")
                                TEST_EXECUTION_LOCK.unlink()
                            except OSError:
                                # Process dead now, remove lock
                                TEST_EXECUTION_LOCK.unlink()
                        except (OSError, ValueError):
                            # Process dead, remove lock
                            TEST_EXECUTION_LOCK.unlink()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error cleaning up lock: {e}, force removing")
                try:
                    TEST_EXECUTION_LOCK.unlink()
                except:
                    pass
        
        # CRITICAL: Wait for log files to be fully written before regenerating dashboard
        # This ensures the latest test status (PASS/FAIL) is captured
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Waiting for log files to be fully written...")
        time.sleep(3)  # Reduced to 3 seconds since we already waited for subprocess
        
        # Regenerate dashboard to reflect new results
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Regenerating dashboard with test results...")
        refresh_script = PROJECT_ROOT / 'refresh_dashboard.py'
        try:
            result = subprocess.run(
                [sys.executable, str(refresh_script)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout for dashboard generation
            )
            if result.returncode == 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard updated successfully with test results and screenshots.")
                # Verify dashboard was actually updated
                dashboard_file = PROJECT_ROOT / 'logs' / 'index.html'
                if dashboard_file.exists():
                    file_mtime = dashboard_file.stat().st_mtime
                    current_time = time.time()
                    age_seconds = current_time - file_mtime
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard file age: {age_seconds:.2f} seconds (fresh)")
                # Give a moment for file system to sync
                time.sleep(1)  # Reduced since we're forcing sync in refresh script
            else:
                print(f"[WARNING] Dashboard refresh returned code {result.returncode}: {result.stderr}")
                if result.stdout:
                    print(f"[DEBUG] Dashboard refresh stdout: {result.stdout}")
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Dashboard refresh timed out after 60 seconds")
        except Exception as e:
            print(f"[WARNING] Error refreshing dashboard: {e}")
        
        # Additional wait to ensure dashboard file is fully written to disk
        # This is critical for UI to see updated status and screenshots
        time.sleep(3)  # Increased to 3 seconds to ensure file system sync and latest status is written
        
        # Verify dashboard file exists and was recently updated
        dashboard_file = PROJECT_ROOT / 'logs' / 'index.html'
        if dashboard_file.exists():
            file_mtime = dashboard_file.stat().st_mtime
            current_time = time.time()
            age_seconds = current_time - file_mtime
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dashboard file age: {age_seconds:.2f} seconds (should be < 5 seconds)")
            
            # Force file system sync to ensure latest status is written
            try:
                dashboard_file.touch()  # Update file timestamp to ensure it's fresh
                # Force a write to ensure file is synced
                with open(dashboard_file, 'r+b') as f:
                    f.seek(0, 2)  # Seek to end
                    f.write(b'\n')  # Add newline
                    f.flush()
                    os.fsync(f.fileno())  # Force sync to disk
            except Exception as e:
                print(f"[WARNING] Could not touch dashboard file: {e}")
        
        return result.returncode == 0
    except Exception as e:
        print_and_log(f"ERROR running test '{test_name}': {e}")
        import traceback
        try:
            with open(PROJECT_ROOT / 'server_debug.log', 'a', encoding='utf-8') as f:
                traceback.print_exc(file=f)
        except:
            pass
        return False
    finally:
        # CRITICAL: Force cleanup of test execution lock after test completes
        # This ensures the server status endpoint correctly reports "not busy"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Final cleanup: Ensuring test execution lock is removed...")
        max_cleanup_attempts = 5
        for attempt in range(max_cleanup_attempts):
            try:
                if not TEST_EXECUTION_LOCK.exists():
                    break  # Lock already gone, good
                
                lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                server_pid = os.getpid()
                lock_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
                
                # If lock is server's PID, remove it (invalid)
                if lock_pid == str(server_pid):
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing invalid test lock (server PID)")
                    TEST_EXECUTION_LOCK.unlink()
                    break
                
                # If lock is old (>2 min), definitely remove it
                if lock_age > 120:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale test lock (age: {lock_age:.0f}s)")
                    TEST_EXECUTION_LOCK.unlink()
                    break
                
                # Check if process is still running
                if sys.platform == 'win32':
                    check_result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {lock_pid}'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if str(lock_pid) not in check_result.stdout:
                        # Process dead, remove lock
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing test lock (PID {lock_pid} not running)")
                        TEST_EXECUTION_LOCK.unlink()
                        break
                    else:
                        # Check if it's pytest
                        cmdline_result = subprocess.run(
                            ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if 'pytest' not in cmdline_result.stdout.lower():
                            # Not pytest, remove lock
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing test lock (PID {lock_pid} is not pytest)")
                            TEST_EXECUTION_LOCK.unlink()
                            break
                        # It's pytest and still running - wait a bit
                        if attempt < max_cleanup_attempts - 1:
                            time.sleep(1)
                            continue
                        else:
                            # Last attempt - force remove if test subprocess should be done
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Force removing test lock (test should be done)")
                            TEST_EXECUTION_LOCK.unlink()
                            break
                else:
                    try:
                        os.kill(int(lock_pid), 0)
                        # Process exists, wait a bit
                        if attempt < max_cleanup_attempts - 1:
                            time.sleep(1)
                            continue
                        else:
                            # Last attempt - force remove
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Force removing test lock")
                            TEST_EXECUTION_LOCK.unlink()
                            break
                    except (OSError, ValueError):
                        # Process dead, remove lock
                        TEST_EXECUTION_LOCK.unlink()
                        break
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in cleanup attempt {attempt + 1}: {e}")
                if attempt == max_cleanup_attempts - 1:
                    # Last attempt - force remove
                    try:
                        TEST_EXECUTION_LOCK.unlink()
                    except:
                        pass
                else:
                    time.sleep(0.5)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleanup complete. Test execution lock removed.")


def process_queue():
    """Process test queue from file with thread safety."""
    # 1. First, acquire the thread-level lock for this process
    if not _QUEUE_PROCESSING_LOCK.acquire(blocking=False):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another thread is already processing the queue in this process, skipping")
        return
    
    try:
        # 2. Then check the file-based lock (across processes)
        if is_locked():
            # Check if lock is stale (older than 1 minute)
            try:
                lock_age = time.time() - LOCK_FILE.stat().st_mtime
                if lock_age > 60:  # Older than 1 minute, consider stale
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale queue lock (age: {lock_age:.0f}s)")
                    remove_lock()
                else:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue is locked, skipping processing")
                    return
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking lock age: {e}, removing lock")
                remove_lock()
    
        queue = read_queue()
        if not queue:
            return
        
        print_and_log(f"\nProcessing queue with {len(queue)} test(s): {queue}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
        
        set_lock()
        
        try:
            # Process queue items one at a time
            processed_tests = []
            while queue:
                test_name = queue.pop(0)
                if test_name:
                    # CRITICAL: Check if ANY test is already running before processing (not just this specific test)
                    # This prevents multiple tests from running simultaneously
                    if TEST_EXECUTION_LOCK.exists():
                        try:
                            lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                            server_pid = os.getpid()
                            
                            # If lock is server's PID, test is starting (just created lock)
                            if lock_pid == str(server_pid):
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test execution lock exists (server PID), another test is starting - skipping '{test_name}' from queue")
                                # Put test back at front of queue to retry later
                                queue.insert(0, test_name)
                                write_queue(queue)
                                break  # Exit loop, will retry on next queue check
                            
                            # Check if it's a real pytest process
                            if sys.platform == 'win32':
                                result = subprocess.run(
                                    ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                if str(lock_pid) in result.stdout:
                                    # Check if it's pytest
                                    cmdline_result = subprocess.run(
                                        ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                                        capture_output=True,
                                        text=True,
                                        timeout=2
                                    )
                                    if 'pytest' in cmdline_result.stdout.lower():
                                        # ANY pytest is running - don't start another test
                                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another test is running (PID: {lock_pid}), skipping '{test_name}' from queue")
                                        # Put test back at front of queue to retry later
                                        queue.insert(0, test_name)
                                        write_queue(queue)
                                        break  # Exit loop, will retry on next queue check
                            else:
                                # Non-Windows: check if process exists
                                try:
                                    os.kill(int(lock_pid), 0)
                                    # Process exists, another test is running
                                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another test is running (PID: {lock_pid}), skipping '{test_name}' from queue")
                                    queue.insert(0, test_name)
                                    write_queue(queue)
                                    break
                                except (OSError, ValueError):
                                    # Process doesn't exist, lock is stale - remove it
                                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale lock (PID {lock_pid} not running)")
                                    try:
                                        TEST_EXECUTION_LOCK.unlink()
                                    except:
                                        pass
                        except Exception as e:
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking running test: {e}")
                            # On error, be safe and don't start test
                            queue.insert(0, test_name)
                            write_queue(queue)
                            break
                    
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting test from queue: {test_name}")
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
                    run_test_command(test_name)
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' execution completed")
                    processed_tests.append(test_name)
                    
                    # CRITICAL: Write queue immediately after removing test to prevent re-processing
                    write_queue(queue)
                    
                    # Wait a bit before processing next test (if any)
                    if queue:
                        time.sleep(1)
            
            # Clear queue file if all tests processed
            if not queue:
                write_queue([])  # Ensure queue file is empty
            
            if processed_tests:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue processing completed. Processed: {processed_tests}")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
            else:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue processing completed (no tests to process)")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR processing queue: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    finally:
        remove_lock()
        # 3. Always release the thread lock
        try:
            _QUEUE_PROCESSING_LOCK.release()
        except RuntimeError:
            pass


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass


class QueueHandler(BaseHTTPRequestHandler):
    """HTTP handler for adding tests to queue."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - status check."""
        if self.path.startswith('/status'):
            # Quick status check - don't log every request to avoid spam
            try:
                # Check if busy (queue locked or test execution locked)
                is_busy = is_locked()
                if not is_busy and TEST_EXECUTION_LOCK.exists():
                    # Double check test execution lock
                    try:
                        lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                        server_pid = os.getpid()
                        lock_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
                        
                        # If lock PID is server's PID, it's invalid - remove it and don't treat as busy
                        if lock_pid == str(server_pid):
                            try:
                                TEST_EXECUTION_LOCK.unlink()
                            except:
                                pass
                            is_busy = False
                        # Basic check if file is fresh (less than 2 mins) and not server PID
                        # Reduced from 5 mins to 2 mins for faster detection of completed tests
                        elif lock_age < 120:
                            # Verify it's actually a pytest process
                            if sys.platform == 'win32':
                                import subprocess
                                result = subprocess.run(
                                    ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                if str(lock_pid) in result.stdout:
                                    # Check if it's pytest
                                    cmdline_result = subprocess.run(
                                        ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                                        capture_output=True,
                                        text=True,
                                        timeout=2
                                    )
                                    if 'pytest' in cmdline_result.stdout.lower():
                                        is_busy = True
                                    else:
                                        # Not pytest, invalid lock - remove it
                                        try:
                                            TEST_EXECUTION_LOCK.unlink()
                                        except:
                                            pass
                                        is_busy = False
                                else:
                                    # Process not running, stale lock - remove it
                                    try:
                                        TEST_EXECUTION_LOCK.unlink()
                                    except:
                                        pass
                                    is_busy = False
                            else:
                                # Unix: check if process exists
                                try:
                                    os.kill(int(lock_pid), 0)
                                    is_busy = True
                                except OSError:
                                    # Process dead, stale lock - remove it
                                    try:
                                        TEST_EXECUTION_LOCK.unlink()
                                    except:
                                        pass
                                    is_busy = False
                        else:
                            # Lock is old (>2 mins), stale - remove it
                            try:
                                TEST_EXECUTION_LOCK.unlink()
                            except:
                                pass
                            is_busy = False
                    except:
                        pass
                
                # Get queue status
                queue = read_queue()
                queue_size = len(queue) if queue else 0
                
                # CRITICAL: If queue has items, consider server as "busy" (test is queued/starting)
                # This ensures dashboard knows test is being processed even before it actually starts
                # This fixes the "Test Not Started" error when test is in queue but not yet running
                if queue_size > 0 and not is_busy:
                    # Test is in queue but not yet started - mark as busy to indicate processing
                    is_busy = True
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'busy': is_busy,
                    'queue_size': queue_size,
                    'status': 'running'
                })
                self.wfile.write(response.encode('utf-8'))
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in /status endpoint: {e}", file=sys.stderr)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e), 'status': 'error'})
                self.wfile.write(response.encode('utf-8'))
            
        elif self.path == '/log-timestamps':
            # Return log file modification times for dashboard Last Run timestamps
            try:
                logs_dir = PROJECT_ROOT / 'logs'
                timestamps = {}
                
                admin_log = logs_dir / 'benchsale_admin.log'
                recruiter_log = logs_dir / 'benchsale_recruiter.log'
                employer_log = logs_dir / 'employer.log'
                jobseeker_log = logs_dir / 'jobseeker.log'
                main_log = logs_dir / 'benchsale_test.log'
                
                # Get the most recent timestamp for BenchSale (Admin or Recruiter)
                benchsale_ts = 0
                if admin_log.exists():
                    benchsale_ts = max(benchsale_ts, admin_log.stat().st_mtime)
                if recruiter_log.exists():
                    benchsale_ts = max(benchsale_ts, recruiter_log.stat().st_mtime)
                if benchsale_ts > 0:
                    timestamps['benchsale'] = benchsale_ts
                
                if employer_log.exists():
                    timestamps['employer'] = employer_log.stat().st_mtime
                if jobseeker_log.exists():
                    timestamps['jobseeker'] = jobseeker_log.stat().st_mtime
                if main_log.exists():
                    timestamps['main'] = main_log.stat().st_mtime
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps(timestamps)
                self.wfile.write(response.encode('utf-8'))
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in /log-timestamps endpoint: {e}", file=sys.stderr)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({'error': str(e)})
                self.wfile.write(response.encode('utf-8'))
        
        elif self.path == '/':
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Health check request received")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'Always-On Test Server Running')
        else:
            self.send_error_response(404, 'Not found')
    
    def do_POST(self):
        """Handle POST requests to add test to queue."""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received POST request to: {self.path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Client: {self.client_address}")
        
        if self.path == '/add-test':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Content-Length: {content_length}")
                body = self.rfile.read(content_length)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Request body: {body.decode('utf-8')}")
                data = json.loads(body.decode('utf-8'))
                test_name = data.get('testName', '')
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Extracted test name: '{test_name}'")
                
                if not test_name:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Test name is empty!")
                    self.send_error_response(400, 'Test name is required')
                    return
                
                # CRITICAL: Check if test is already running OR in queue BEFORE adding
                # First check if test is in queue
                queue = read_queue()
                if test_name in queue:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' already in queue, skipping duplicate")
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps({
                        'success': False,
                        'error': f'Test "{test_name}" is already in queue'
                    })
                    self.wfile.write(response.encode('utf-8'))
                    return
                
                # Then check if test is already running (more robust check)
                test_is_running = False
                if TEST_EXECUTION_LOCK.exists():
                    try:
                        lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                        server_pid = os.getpid()
                        
                        # If lock is server's PID, test is starting (just created lock)
                        if lock_pid == str(server_pid):
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test execution lock exists (server PID), test is starting - rejecting new request")
                            test_is_running = True
                        else:
                            # Check if it's a real pytest process
                            if sys.platform == 'win32':
                                result = subprocess.run(
                                    ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                if str(lock_pid) in result.stdout:
                                    # Check if it's pytest
                                    cmdline_result = subprocess.run(
                                        ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                                        capture_output=True,
                                        text=True,
                                        timeout=2
                                    )
                                    cmdline_lower = cmdline_result.stdout.lower()
                                    # Check if pytest is running (even if test name doesn't match exactly, if pytest is running, don't start another)
                                    if 'pytest' in cmdline_lower:
                                        # If test name is in command line, it's the same test
                                        if test_name in cmdline_result.stdout or test_name.replace('_', ' ') in cmdline_result.stdout:
                                            test_is_running = True
                                        else:
                                            # Another test is running - still reject to prevent multiple tests
                                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another test is running (PID: {lock_pid}), rejecting new test request")
                                            test_is_running = True
                            else:
                                # Non-Windows: check if process exists
                                try:
                                    os.kill(int(lock_pid), 0)
                                    # Process exists, assume test is running
                                    test_is_running = True
                                except (OSError, ValueError):
                                    # Process doesn't exist, lock is stale
                                    pass
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking running test: {e}")
                        # On error, be safe and assume test might be running
                        test_is_running = True
                
                if test_is_running:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test '{test_name}' is already running or starting, skipping")
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = json.dumps({
                        'success': False,
                        'error': f'Test "{test_name}" is already running. Please wait for it to complete.'
                    })
                    self.wfile.write(response.encode('utf-8'))
                    return
                
                # Add to queue (we already checked it's not in queue and not running above)
                queue.append(test_name)
                write_queue(queue)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Added test '{test_name}' to queue (queue size: {len(queue)})")
                
                # NOTE: Queue watcher thread (watch_queue_loop) runs every 0.5 seconds and will automatically
                # pick up the new test. No need for a separate background thread - this prevents duplicate processing.
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test added to queue. Queue watcher will process it automatically (checks every 0.5s).")
                
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
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Successfully sent response to client")
                
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR processing POST request: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
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
        # Don't log status checks to keep console clean
        if args and args[0].startswith("GET /status"):
            return
            
        # Log all other HTTP requests for debugging
        message = format % args
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HTTP: {message}")


def watch_queue_loop():
    """Background thread to watch file queue."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue watcher thread started")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
    iteration = 0
    while True:
        try:
            iteration += 1
            # Only process if queue has items and no test is currently running
            queue = read_queue()
            if queue:
                # CRITICAL: Check if test execution lock exists (means test is running or starting)
                if TEST_EXECUTION_LOCK.exists():
                    try:
                        lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
                        server_pid = os.getpid()
                        
                        # If lock is server's PID, test is starting (lock just created)
                        if lock_pid == str(server_pid):
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test execution lock exists (server PID), test is starting - waiting 3 seconds...")
                            time.sleep(3)  # Wait 3 seconds for test to start
                            continue
                        
                        # Check if process in lock file is running
                        if sys.platform == 'win32':
                            result = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {lock_pid}'],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if str(lock_pid) in result.stdout:
                                # Check if it's pytest
                                cmdline_result = subprocess.run(
                                    ['wmic', 'process', 'where', f'ProcessId={lock_pid}', 'get', 'CommandLine'],
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                if 'pytest' in cmdline_result.stdout.lower():
                                    # Test is running, wait longer before checking again
                                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Test is running (PID: {lock_pid}) - waiting 3 seconds...")
                                    time.sleep(3)  # Wait 3 seconds if test is running
                                    continue
                                else:
                                    # Not pytest, remove stale lock
                                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale lock (PID {lock_pid} is not pytest)")
                                    try:
                                        TEST_EXECUTION_LOCK.unlink()
                                    except:
                                        pass
                            else:
                                # Process not running, remove stale lock
                                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale lock (PID {lock_pid} not running)")
                                try:
                                    TEST_EXECUTION_LOCK.unlink()
                                except:
                                    pass
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking test lock: {e}")
                        # If we can't check, wait a bit to be safe
                        time.sleep(2)
                        continue
                
                # No test running, process queue
                process_queue()
            else:
                # No queue items, normal sleep
                time.sleep(0.5)  # Check queue every 0.5 seconds when idle
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR in queue watcher: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            time.sleep(1)


def run_server(port=8766):
    """Run the always-on server."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Always-On Test Server")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ========================================")
    
    # Check if server is already running
    is_running = check_server_running()
    if is_running:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Server appears to be already running!")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]    PID file: {SERVER_PID_FILE}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]    Port: {port}")
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] If you're sure it's not running:")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]    1. Delete the PID file: {SERVER_PID_FILE}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]    2. Check if port {port} is in use")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]    3. Try: netstat -ano | findstr :{port}")
        sys.exit(1)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OK: No existing server found - proceeding with startup")
    
    # Clean up any stale locks at startup
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up stale locks at startup...")
    if LOCK_FILE.exists():
        try:
            lock_age = time.time() - LOCK_FILE.stat().st_mtime
            if lock_age > 60:  # Older than 1 minute, consider stale
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale queue lock (age: {lock_age:.0f}s)")
                LOCK_FILE.unlink()
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking queue lock: {e}")
    
    if TEST_EXECUTION_LOCK.exists():
        try:
            lock_pid = TEST_EXECUTION_LOCK.read_text().strip()
            lock_age = time.time() - TEST_EXECUTION_LOCK.stat().st_mtime
            server_pid = os.getpid()
            
            # If lock PID is server's own PID, it's invalid (server shouldn't hold test lock)
            if lock_pid == str(server_pid):
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing invalid test execution lock (lock PID {lock_pid} is server PID)")
                TEST_EXECUTION_LOCK.unlink()
            elif lock_age > 300:  # Older than 5 minutes, consider stale
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Removing stale test execution lock (age: {lock_age:.0f}s)")
                TEST_EXECUTION_LOCK.unlink()
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error checking test execution lock: {e}")
            # Try to remove it anyway if there's an error reading it
            try:
                TEST_EXECUTION_LOCK.unlink()
            except:
                pass
    
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
    
    server_address = ('127.0.0.1', port)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting HTTP server on {server_address[0]}:{server_address[1]}")
    
    try:
        httpd = ThreadingHTTPServer(server_address, QueueHandler)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HTTP server created successfully")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Server socket: {httpd.socket.getsockname()}")
    except OSError as e:
        if "Address already in use" in str(e) or "address already in use" in str(e).lower():
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Port {port} is already in use!", file=sys.stderr)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Another server might be running on this port.", file=sys.stderr)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Try:", file=sys.stderr)
            print(f"  1. Check if another server instance is running", file=sys.stderr)
            print(f"  2. Delete the PID file: {SERVER_PID_FILE}", file=sys.stderr)
            print(f"  3. Or use a different port with --port option", file=sys.stderr)
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to create HTTP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed to create HTTP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Start file queue watcher in background thread
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting queue watcher thread...")
    queue_watcher = threading.Thread(target=watch_queue_loop, daemon=True)
    queue_watcher.start()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue watcher thread started")
    
    # Verify queue file location
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue file path: {QUEUE_FILE}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Queue file exists: {QUEUE_FILE.exists()}")
    if QUEUE_FILE.exists():
        try:
            queue = read_queue()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Current queue contents: {queue}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error reading queue: {e}")
    
    print(f"""
{'='*60}
Always-On Test Server
{'='*60}
Server running on http://localhost:{port}
Queue file: {QUEUE_FILE}
Queue file exists: {QUEUE_FILE.exists()}

This server will:
- Accept test requests via HTTP POST to /add-test
- Watch queue file for test requests
- Automatically run tests when requested

Keep this running in the background.
Press Ctrl+C to stop.
{'='*60}
""")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Server is now listening and ready to accept requests...")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] You can test the server by visiting: http://127.0.0.1:{port}/")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Status endpoint: http://127.0.0.1:{port}/status")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Add test endpoint: http://127.0.0.1:{port}/add-test")
    print()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OK: SERVER IS RUNNING - Ready to accept test requests!")
    print()
    
    # Verify server is actually listening
    try:
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)
        result = test_socket.connect_ex(('localhost', port))
        test_socket.close()
        if result == 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OK: Server socket verified - port {port} is listening")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Could not verify server socket")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Socket verification failed: {e}")
    
    print()
    print("=" * 60)
    print("SERVER IS READY - Waiting for requests...")
    print("=" * 60)
    print()
    
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
    
    print("=" * 60)
    print("Always-On Test Server - Starting...")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)
    print()
    
    try:
        parser = argparse.ArgumentParser(description='Run always-on test server')
        parser.add_argument('--port', type=int, default=8766, help='Port to run server on (default: 8766)')
        args = parser.parse_args()
        
        print(f"Starting server on port {args.port}...")
        run_server(args.port)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{'='*60}")
        print("FATAL ERROR: Server failed to start!")
        print(f"{'='*60}")
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print(f"{'='*60}")
        sys.exit(1)
