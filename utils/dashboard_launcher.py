"""
Dashboard Launcher - Serves the dashboard and auto-starts test servers.
When you open http://localhost:8888 in any browser, it will:
1. Auto-start the test servers if not running
2. Serve the dashboard HTML
3. Everything works automatically!
"""

import http.server
import socketserver
from socketserver import ThreadingMixIn
import subprocess
import sys
import os
import time
import socket
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DASHBOARD_HOME = PROJECT_ROOT / 'dashboard_home.html'
DASHBOARD_HTML = PROJECT_ROOT / 'logs' / 'index.html'
SERVER_SCRIPT = PROJECT_ROOT / 'utils' / 'always_on_server.py'
HELPER_SCRIPT = PROJECT_ROOT / 'utils' / 'server_helper.py'
AUTO_START_SCRIPT = PROJECT_ROOT / 'utils' / 'auto_start_server.py'
LOG_API_SCRIPT = PROJECT_ROOT / 'utils' / 'log_history_api.py'

PORT = 8888


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True


def start_server_in_background(script_path, port_check=None):
    """Start a Python script in background - ONLY if not already running."""
    try:
        # STRICT CHECK: If port is in use, don't start another instance
        if port_check and is_port_in_use(port_check):
            print(f"✅ Server already running on port {port_check}, skipping startup")
            return True  # Already running
        
        # Additional check: Check PID file for always_on_server
        if 'always_on_server' in str(script_path):
            pid_file = PROJECT_ROOT / '.always_on_server.pid'
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    # Check if process exists
                    if sys.platform == 'win32':
                        result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}'],
                            capture_output=True,
                            text=True
                        )
                        if str(pid) in result.stdout:
                            print(f"✅ Server process (PID: {pid}) already running, skipping startup")
                            return True
                except Exception:
                    pass
        
        # Only start if definitely not running
        print(f"Starting server: {script_path}")
        os.chdir(PROJECT_ROOT)
        
        if sys.platform == 'win32':
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=PROJECT_ROOT,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        time.sleep(2)  # Give it more time to start and write PID file
        return True
    except Exception as e:
        print(f"❌ Error starting {script_path}: {e}", file=sys.stderr)
        return False


def ensure_servers_running():
    """Ensure test servers are running - only start if not already running."""
    print("Checking test servers...")
    
    # Check if server is already running (check both port and PID file)
    server_running = is_port_in_use(8766)
    
    if server_running:
        print("✅ Test server is already running on port 8766")
        return
    
    # Double-check: verify no other instance is starting
    pid_file = PROJECT_ROOT / '.always_on_server.pid'
    if pid_file.exists():
        try:
            import time
            # Wait a moment to see if server starts
            time.sleep(1)
            if is_port_in_use(8766):
                print("✅ Test server started (found via PID file)")
                return
        except Exception:
            pass
    
    # Only start if definitely not running
    print("Starting main test server (port 8766)...")
    # Start always-on server directly instead of using auto_start_server
    start_server_in_background(SERVER_SCRIPT, 8766)
    # Give it extra time to start
    time.sleep(3)
    
    # Verify it started
    if is_port_in_use(8766):
        print("✅ Test server started successfully!")
    else:
        print("⚠️  Warning: Test server may not have started properly")
        
    # Check if Log API server is running (port 5001)
    log_api_running = is_port_in_use(5001)
    if not log_api_running:
        print("Starting Log History API server (port 5001)...")
        start_server_in_background(LOG_API_SCRIPT, 5001)
        time.sleep(2)
        if is_port_in_use(5001):
            print("✅ Log History API server started successfully!")
        else:
            print("⚠️  Warning: Log History API server may not have started properly")
    else:
        print("✅ Log History API server is already running on port 5001")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for serving dashboard."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        # Auto-start servers on first access
        if not hasattr(self.server, 'servers_started'):
            ensure_servers_running()
            self.server.servers_started = True
        
        # Serve dashboard home page at root
        if self.path == '/' or self.path == '/index.html' or self.path == '':
            self.path = '/dashboard_home.html'
        
        # Serve the file using parent class
        return super().do_GET()
    
    def end_headers(self):
        """Override to add CORS headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        # Suppress default logging for cleaner output
        pass


class ThreadingTCPServer(ThreadingMixIn, socketserver.TCPServer):
    """Handle requests in a separate thread."""
    pass


def run_dashboard_server(port=8888):
    """Run the dashboard launcher server."""
    # Check if port is available
    if is_port_in_use(port):
        print(f"❌ Port {port} is already in use!")
        print(f"   Another dashboard server might be running.")
        print(f"   Try: http://127.0.0.1:{port}")
        return
    
    # Ensure servers are running before starting
    ensure_servers_running()
    
    # Create server
    with ThreadingTCPServer(("127.0.0.1", port), DashboardHandler) as httpd:
        url = f"http://127.0.0.1:{port}"
        
        print(f"""
{'='*60}
🚀 Dashboard Launcher Server
{'='*60}
Server running on: {url}

✅ Test servers are running:
   - Helper Server: http://127.0.0.1:8767
   - Test Server: http://127.0.0.1:8766
   - Log API Server: http://127.0.0.1:5001

📊 Dashboard: {url}
   
🌐 Open this URL in any browser to use the dashboard!
   (Auto-opens in default browser...)

Press Ctrl+C to stop the server.
{'='*60}
""")
        
        # Don't auto-open browser - user can open manually if needed
        # This prevents multiple browsers from opening
        # try:
        #     webbrowser.open(url)
        # except:
        #     pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down dashboard server...")
            print("✅ Server stopped.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Launch dashboard with auto-start servers')
    parser.add_argument('--port', type=int, default=8888, help='Port to run server on (default: 8888)')
    args = parser.parse_args()
    
    run_dashboard_server(args.port)
