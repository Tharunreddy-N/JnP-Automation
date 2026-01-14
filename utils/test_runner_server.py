"""
Simple HTTP server to run pytest tests from the dashboard.
Run this server to enable the "Run Test" button functionality in the dashboard.

Usage:
    python utils/test_runner_server.py

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

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


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
                
                # Run the test in a separate thread
                def run_test():
                    try:
                        # Change to project root directory
                        os.chdir(PROJECT_ROOT)
                        
                        # Build pytest command
                        cmd = [
                            sys.executable,
                            '-m', 'pytest',
                            '-k', test_name,
                            '-s', '-vv'
                        ]
                        
                        print(f"\n{'='*60}")
                        print(f"Running test: {test_name}")
                        print(f"Command: {' '.join(cmd)}")
                        print(f"{'='*60}\n")
                        
                        # Run pytest
                        result = subprocess.run(
                            cmd,
                            cwd=PROJECT_ROOT,
                            capture_output=False,  # Show output in real-time
                            text=True
                        )
                        
                        print(f"\n{'='*60}")
                        print(f"Test '{test_name}' completed with exit code: {result.returncode}")
                        print(f"{'='*60}\n")
                        
                    except Exception as e:
                        print(f"Error running test: {e}", file=sys.stderr)
                
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


def run_server(port=8765):
    """Run the test runner server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, TestRunnerHandler)
    
    print(f"""
{'='*60}
Test Runner Server
{'='*60}
Server running on http://localhost:{port}
Open your dashboard HTML file in a browser.
Click "Run Test" buttons to execute tests.

Press Ctrl+C to stop the server.
{'='*60}
""")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        httpd.shutdown()
        print("Server stopped.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run test runner HTTP server')
    parser.add_argument('--port', type=int, default=8765, help='Port to run server on (default: 8765)')
    args = parser.parse_args()
    
    run_server(args.port)
