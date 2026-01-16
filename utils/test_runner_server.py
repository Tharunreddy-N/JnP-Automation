"""
Test Runner Server - Runs pytest tests from dashboard via HTTP or file queue.
This server supports both HTTP requests and file-based queue system.

Usage:
    python utils/test_runner_server.py

The server will:
1. Accept HTTP POST requests to /run-test
2. Watch for test requests in .test_queue.json file
3. Run tests automatically when requested

Then open the dashboard HTML file in a browser and click "Run Test" buttons.
"""

import json
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import threading
import os
import time
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
    except IOError:
        pass


def add_to_queue(test_name):
    """Add test to queue file."""
    queue = read_queue()
    if test_name not in queue:
        queue.append(test_name)
        write_queue(queue)


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


def run_test_command(test_name):
    """Run a pytest test command."""
    try:
        os.chdir(PROJECT_ROOT)
        cmd = [
            sys.executable,
            '-m', 'pytest',
            '-k', test_name,
            '-s', '-vv'
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


class TestRunnerHandler(BaseHTTPRequestHandler):
    """HTTP handler for running tests."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to run tests."""
        if self.path == '/run-test':
            try:
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body.decode('utf-8'))
                test_name = data.get('testName', '')
                
                if not test_name:
                    self.send_error_response(400, 'Test name is required')
                    return
                
                # Add to queue and run in background thread
                add_to_queue(test_name)
                
                def run_test():
                    run_test_command(test_name)
                
                # Start test in background thread
                thread = threading.Thread(target=run_test, daemon=True)
                thread.start()
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = json.dumps({
                    'success': True,
                    'message': f'Test "{test_name}" is running in the background'
                })
                self.wfile.write(response.encode('utf-8'))
                
            except Exception as e:
                self.send_error_response(500, f'Error: {str(e)}')
        else:
            self.send_error_response(404, 'Not found')
    
    def do_GET(self):
        """Handle GET requests - serve dashboard files if needed."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Test Runner Server</h1><p>Server is running. Open your dashboard HTML file.</p>')
        elif self.path.endswith('.html'):
            # Try to serve HTML files from reports directory
            try:
                html_path = PROJECT_ROOT / 'reports' / self.path.lstrip('/')
                if html_path.exists() and html_path.is_file():
                    with open(html_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_error_response(404, 'File not found')
            except Exception as e:
                self.send_error_response(500, f'Error serving file: {str(e)}')
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
        print(f"[{self.address_string()}] {format % args}")


def watch_queue_loop():
    """Background thread to watch file queue."""
    while True:
        try:
            process_queue()
            time.sleep(0.5)  # Check queue every 0.5 seconds
        except Exception as e:
            print(f"Error in queue watcher: {e}", file=sys.stderr)
            time.sleep(1)


def run_server(port=8765):
    """Run the test runner server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, TestRunnerHandler)
    
    # Start file queue watcher in background thread
    queue_watcher = threading.Thread(target=watch_queue_loop, daemon=True)
    queue_watcher.start()
    
    print(f"""
{'='*60}
Test Runner Server
{'='*60}
Server running on http://localhost:{port}
File queue watcher: Active
Queue file: {QUEUE_FILE}

Open your dashboard HTML file in a browser.
Click "Run Test" buttons to execute tests.

The server supports both:
- HTTP requests (via dashboard)
- File queue (via .test_queue.json)

Press Ctrl+C to stop the server.
{'='*60}
""")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()
        remove_lock()
        print("Server stopped.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run test runner HTTP server')
    parser.add_argument('--port', type=int, default=8765, help='Port to run server on (default: 8765)')
    args = parser.parse_args()
    
    run_server(args.port)
