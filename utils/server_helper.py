"""
Server Helper - Simple HTTP server that can start the main test server.
This runs on port 8767 and can be called from the dashboard to auto-start the main server.
"""

import subprocess
import sys
import os
import time
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
import threading

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SERVER_SCRIPT = PROJECT_ROOT / 'utils' / 'always_on_server.py'
AUTO_START_SCRIPT = PROJECT_ROOT / 'utils' / 'auto_start_server.py'


def is_port_in_use(port):
    """Check if a port is already in use by trying to connect to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0  # True if connection was successful (port is in use)
        except Exception:
            return False


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass


class HelperHandler(BaseHTTPRequestHandler):
    """HTTP handler for server helper."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - check server status or start server."""
        if self.path.startswith('/status'):
            # Check if main server is running
            is_running = is_port_in_use(8766)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            import json
            response = json.dumps({'running': is_running})
            self.wfile.write(response.encode('utf-8'))
            
        elif self.path == '/start':
            # Start the main server
            def start_in_background():
                try:
                    os.chdir(PROJECT_ROOT)
                    if sys.platform == 'win32':
                        CREATE_NO_WINDOW = 0x08000000
                        subprocess.Popen(
                            [sys.executable, str(AUTO_START_SCRIPT)],
                            cwd=PROJECT_ROOT,
                            creationflags=CREATE_NO_WINDOW,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        subprocess.Popen(
                            [sys.executable, str(AUTO_START_SCRIPT)],
                            cwd=PROJECT_ROOT,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                except Exception as e:
                    print(f"Error starting server: {e}", file=sys.stderr)
            
            thread = threading.Thread(target=start_in_background, daemon=True)
            thread.start()
            
            # Wait a bit and check
            time.sleep(1)
            is_running = is_port_in_use(8766)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            import json
            response = json.dumps({
                'success': is_running,
                'message': 'Server starting...' if not is_running else 'Server is running'
            })
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error_response(404, 'Not found')
    
    def send_error_response(self, code, message):
        """Send an error response."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'success': False, 'error': message}
        self.wfile.write(str(response).replace("'", '"').encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to suppress logging."""
        pass


def run_helper_server(port=8767):
    """Run the helper server."""
    server_address = ('127.0.0.1', port)
    httpd = ThreadingHTTPServer(server_address, HelperHandler)
    
    print(f"Helper server running on http://127.0.0.1:{port}")
    print("This server helps auto-start the main test server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down helper server...")
        httpd.shutdown()


if __name__ == '__main__':
    run_helper_server()
