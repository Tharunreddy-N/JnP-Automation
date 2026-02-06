"""
Pytest configuration and fixtures for BenchSale automation tests
"""
import pytest
import time
import logging
import os
import sys
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright.sync_api import Page as PWPage
import re

# GLOBAL PYTEST LOCK - Prevent multiple pytest processes from running
_PYTEST_LOCK_FILE = os.path.join(os.path.dirname(__file__), '.pytest_running.lock')

def _check_pytest_lock():
    """Check if another pytest process is running - FAIL if yes."""
    if os.path.exists(_PYTEST_LOCK_FILE):
        try:
            with open(_PYTEST_LOCK_FILE, 'r') as f:
                lock_pid = int(f.read().strip())
            # Check if process exists
            if sys.platform == 'win32':
                import subprocess
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {lock_pid}'],
                    capture_output=True,
                    text=True
                )
                if str(lock_pid) in result.stdout:
                    error_msg = f"❌ Another pytest process (PID: {lock_pid}) is already running! Only one test can run at a time."
                    print(error_msg)
                    raise RuntimeError(error_msg)
        except (ValueError, FileNotFoundError):
            # Stale lock, remove it
            try:
                os.unlink(_PYTEST_LOCK_FILE)
            except:
                pass
    
    # Create lock file
    try:
        with open(_PYTEST_LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Warning: Could not create pytest lock file: {e}")

def _remove_pytest_lock():
    """Remove pytest lock file."""
    try:
        if os.path.exists(_PYTEST_LOCK_FILE):
            with open(_PYTEST_LOCK_FILE, 'r') as f:
                if f.read().strip() == str(os.getpid()):
                    os.unlink(_PYTEST_LOCK_FILE)
    except Exception:
        pass

# Check lock at module import time - PREVENT MULTIPLE PYTEST PROCESSES
_check_pytest_lock()

# Configure logging
def _detect_run_scope() -> str:
    """
    Detect whether the current pytest invocation is running Admin vs Recruiter file.
    This lets us keep separate log files when you run files one-by-one.
    """
    env_scope = os.getenv("BENCHSALE_LOG_SCOPE", "").strip().lower()
    if env_scope in ("admin", "recruiter"):
        return env_scope
    argv = " ".join(sys.argv or []).lower()
    if "test_benchsale_admin_test_cases.py".lower() in argv:
        return "admin"
    if "test_benchsale_recruiter_test_cases.py".lower() in argv:
        return "recruiter"
    if "test_employer_test_cases.py".lower() in argv:
        return "employer"
    return "all"


def setup_logging():
    """Setup logging configuration similar to Robot Framework"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(os.path.dirname(__file__), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Use per-file log name when a single file is run (admin/recruiter),
    # otherwise fall back to the combined log.
    scope = _detect_run_scope()
    if scope == "admin":
        log_name = "benchsale_admin.log"
    elif scope == "recruiter":
        log_name = "benchsale_recruiter.log"
    elif scope == "employer":
        log_name = "employer.log"
    else:
        log_name = "benchsale_test.log"
    log_file = os.path.join(log_dir, log_name)
    
    # Clean up old timestamped logs (keeps stable per-file logs)
    cleanup_old_logs(log_dir)
    
    # Configure root logger - append to log file to preserve all test results
    # Use Robot Framework-like format
    file_formatter = logging.Formatter(
        '%(message)s',  # Simple format for file - test_logger handles formatting
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)8s] %(filename)s:%(lineno)d - %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()  # Clear existing handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('webdriver_manager').setLevel(logging.WARNING)
    
    return log_file


def cleanup_old_logs(log_dir):
    """
    Automatically clean up old timestamped log files before each test run.
    Keeps only the main benchsale_test.log file (which gets overwritten each run).
    
    Args:
        log_dir: Directory containing log files
    """
    try:
        removed_count = 0
        removed_files = []
        
        if not os.path.exists(log_dir):
            return
        
        # Find and remove old timestamped log files
        for file in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file)
            
            if os.path.isfile(file_path):
                # Remove timestamped log files (but keep benchsale_test.log)
                if file.startswith('benchsale_test_') and file.endswith('.log'):
                    try:
                        os.remove(file_path)
                        removed_files.append(file)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove old log file {file}: {e}")
                
                # Remove corresponding timestamped HTML files
                elif file.startswith('benchsale_test_') and file.endswith('.html'):
                    try:
                        os.remove(file_path)
                        removed_files.append(file)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not remove old HTML file {file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Auto-cleanup: Removed {removed_count} old log file(s)")
            for fname in removed_files:
                logger.debug(f"  - Removed: {fname}")
        
    except Exception as e:
        logger.warning(f"Could not clean up old log files: {e}")


def cleanup_old_log_files():
    """
    Cleanup old dummy log files and failure HTML files.
    Removes old failure HTML files from reports/failures directory that are older than 7 days.
    """
    try:
        from datetime import datetime, timedelta
        import glob
        
        removed_count = 0
        removed_files = []
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # Cleanup old failure HTML files
        failures_dir = os.path.join(os.path.dirname(__file__), 'reports', 'failures')
        if os.path.exists(failures_dir):
            # Get all HTML files in failures directory
            html_files = glob.glob(os.path.join(failures_dir, '*.html'))
            for html_file in html_files:
                try:
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(html_file))
                    if mod_time < cutoff_date:
                        os.remove(html_file)
                        removed_files.append(os.path.basename(html_file))
                        removed_count += 1
                        
                        # Also remove associated PNG and URL files if they exist
                        base_name = os.path.splitext(html_file)[0]
                        for ext in ['.png', '.url.txt']:
                            associated_file = base_name + ext
                            if os.path.exists(associated_file):
                                try:
                                    os.remove(associated_file)
                                    removed_count += 1
                                except Exception:
                                    pass
                except Exception as e:
                    logger.debug(f"Could not remove old failure file {html_file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleanup: Removed {removed_count} old dummy log/failure file(s) (older than 7 days)")
            if len(removed_files) <= 10:  # Only log if not too many
                for fname in removed_files[:10]:
                    logger.debug(f"  - Removed: {fname}")
                if len(removed_files) > 10:
                    logger.debug(f"  ... and {len(removed_files) - 10} more files")
        
    except Exception as e:
        logger.debug(f"Could not cleanup old log files: {e}")

# Setup logging on import
LOG_FILE = setup_logging()
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("BenchSale Automation Test Suite - Logging Initialized")
logger.info(f"Log file: {LOG_FILE}")
logger.info("=" * 80)


# Test Configuration Variables
BROWSER = "chrome"
BASE_URL = "https://jobsnprofiles.com/"
CRM_ADMIN_URL = "https://admin.jobsnprofiles.com/"
BENCHSALE_URL = "https://bs.jobsnprofiles.com/"

# BenchSale Admin credentials
USER_ID = "james@adamitcorp.com"
USER_PASSWORD = "Newpassword@123"
USER_DOMAIN = "@adamitcorp.com"

# BenchSale Recruiter credentials
REC_ID = "test@adamitcorp.com"
REC_PASSWORD = "Welcome@123"
REC_NAME = "Test recruiter"

# Add Recruiter details
RECRUITER_NAME = "Test Recruiter"
RECRUITER_EMAIL = "test@adamitcorp.com"

# Add Candidate
# Use the resume in this repo for upload tests (avoid machine-specific D: paths)
# Try BHAVANA N.pdf first, fallback to Deepika Kashni.pdf if not found
_bhavana_resume = os.path.join(os.path.dirname(__file__), "BHAVANA N.pdf")
_deepika_resume = os.path.join(os.path.dirname(__file__), "Deepika Kashni.pdf")

if os.path.exists(_bhavana_resume):
    ADD_CANDIDATE_PROFILE = _bhavana_resume
    ADD_CANDIDATE_FNAME = "BHAVANA"
    ADD_CANDIDATE_LNAME = "N"
    ADD_CANDIDATE_EMAIL = "bhavanan.upskill@gmail.com"
    ADD_CANDIDATE_ROLE = "Data Engineer"
elif os.path.exists(_deepika_resume):
    # Fallback to Deepika's resume if BHAVANA's resume not found
    ADD_CANDIDATE_PROFILE = _deepika_resume
    ADD_CANDIDATE_FNAME = "Deepika"
    ADD_CANDIDATE_LNAME = "Kashni"
    ADD_CANDIDATE_EMAIL = "deepika.kashni@example.com"  # Update with actual email if needed
    ADD_CANDIDATE_ROLE = "Python Developer"  # Update based on Deepika's resume content
else:
    # If neither exists, use BHAVANA path (will fail with clear error)
    ADD_CANDIDATE_PROFILE = _bhavana_resume
    ADD_CANDIDATE_FNAME = "BHAVANA"
    ADD_CANDIDATE_LNAME = "N"
    ADD_CANDIDATE_EMAIL = "bhavanan.upskill@gmail.com"
    ADD_CANDIDATE_ROLE = "Data Engineer"

# Job Submission Email
OUTLOOK_EMAIL = "dhigvijay.s@jobsnprofiles.com"
OUTLOOK_PASSWORD = "Nitya@123"

# Runtime monitoring
runtime_data = {
    'timings': {},
    'api_calls': [],
    'network_issues': []
}

# -----------------------------
# Fast Mode (Playwright)
# -----------------------------
# Enable with: set FAST_MODE=1   (PowerShell: $env:FAST_MODE="1")
FAST_MODE = os.getenv("FAST_MODE", "0").strip().lower() in ("1", "true", "yes", "on")

# Network check defaults (seconds)
# Can be overridden with environment variables `NET_CHECK_TIMEOUT` and `NET_CHECK_CACHE_TTL`.
NET_CHECK_TIMEOUT = float(os.getenv("NET_CHECK_TIMEOUT", "5"))
# Cache TTL for successful network check results (seconds). Default 5 minutes.
NET_CHECK_CACHE_TTL = float(os.getenv("NET_CHECK_CACHE_TTL", "300"))

# Simple in-memory cache to avoid repeating network checks for every test
_NET_CHECK_CACHE: dict = {"result": None, "timestamp": 0.0}

# -----------------------------
# Browser window behavior (Selenium + Playwright)
# -----------------------------
# When running from Cursor/VS Code, users often want the browser to be "snappable"
# side-by-side with the editor. Starting maximized makes that awkward.
#
# - MAXIMIZE_BROWSER=1 -> start maximized (previous default behavior)
# - MAXIMIZE_BROWSER=0 -> start in a normal window (recommended for side-by-side)
MAXIMIZE_BROWSER = os.getenv("MAXIMIZE_BROWSER", "1").strip().lower() in ("1", "true", "yes", "on")

# Optional explicit window size/position (mainly for Playwright Chromium).
# Example (PowerShell):
#   $env:PW_WINDOW_SIZE="1200,900"; $env:PW_WINDOW_POS="700,0"
PW_WINDOW_SIZE = os.getenv("PW_WINDOW_SIZE", "").strip()
PW_WINDOW_POS = os.getenv("PW_WINDOW_POS", "").strip()

AUTH_DIR = os.path.join(os.path.dirname(__file__), ".auth")
os.makedirs(AUTH_DIR, exist_ok=True)
ADMIN_STATE_PATH = os.path.join(AUTH_DIR, "admin.storage_state.json")
RECRUITER_STATE_PATH = os.path.join(AUTH_DIR, "recruiter.storage_state.json")


@pytest.fixture(scope="function")
def driver():
    """Create and configure Chrome WebDriver"""
    logger.info("Initializing Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-save-password-bubble")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    if MAXIMIZE_BROWSER:
        chrome_options.add_argument("--start-maximized")
    
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver_path = ChromeDriverManager().install()
        driver_dir = os.path.dirname(driver_path)
        driver_file = os.path.basename(driver_path)

        # Ensure we point to the actual chromedriver executable
        candidate_paths = []

        # 1) If the returned path is already an executable, keep it
        if driver_file.lower().startswith("chromedriver") and (driver_file.endswith(".exe") or os.access(driver_path, os.X_OK)):
            candidate_paths.append(driver_path)

        # 2) If a directory was returned, look inside for chromedriver(.exe)
        if os.path.isdir(driver_path):
            candidate_paths.append(os.path.join(driver_path, "chromedriver.exe"))
            candidate_paths.append(os.path.join(driver_path, "chromedriver"))

        # 3) Always try siblings in the same directory (handles THIRD_PARTY_NOTICES.chromedriver issue)
        if driver_dir and os.path.isdir(driver_dir):
            candidate_paths.append(os.path.join(driver_dir, "chromedriver.exe"))
            candidate_paths.append(os.path.join(driver_dir, "chromedriver"))

        # Pick the first existing executable
        resolved_path = None
        for path in candidate_paths:
            if os.path.exists(path):
                resolved_path = path
                break

        if not resolved_path:
            raise FileNotFoundError(f"Could not find chromedriver executable near {driver_path}")

        logger.info(f"Using ChromeDriver at: {resolved_path}")
        service = Service(resolved_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {str(e)}")
        logger.error("Try clearing webdriver-manager cache: Remove C:\\Users\\Nityainc\\.wdm\\drivers\\chromedriver")
        raise
    
    yield driver
    
    logger.info("Closing Chrome WebDriver...")
    driver.quit()
    logger.info("Chrome WebDriver closed")


@pytest.fixture(scope="function")
def wait(driver):
    """Create WebDriverWait instance"""
    return WebDriverWait(driver, 30)


# -----------------------------
# Playwright fixtures - SINGLETON BROWSER PATTERN
# -----------------------------
# Global variables to ensure only one browser instance exists
_global_playwright = None
_global_browser = None
_browser_lock = threading.Lock()  # Lock to prevent concurrent browser creation
_BROWSER_LOCK_FILE = os.path.join(os.path.dirname(__file__), '.browser_lock')

@pytest.fixture(scope="session")
def playwright_instance():
    """Start Playwright - singleton pattern to ensure only one instance"""
    global _global_playwright
    if _global_playwright is None:
        _global_playwright = sync_playwright().start()
    yield _global_playwright
    # Don't stop here - let it persist for browser reuse
    # Only stop when browser is closed


def _acquire_browser_lock(timeout=30):
    """Acquire file-based lock to prevent multiple browsers across processes."""
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if not os.path.exists(_BROWSER_LOCK_FILE):
                # Create lock file with process ID
                with open(_BROWSER_LOCK_FILE, 'w') as f:
                    f.write(str(os.getpid()))
                time.sleep(0.2)  # Small delay to ensure file is written
                # Verify we still own the lock
                if os.path.exists(_BROWSER_LOCK_FILE):
                    with open(_BROWSER_LOCK_FILE, 'r') as f:
                        if f.read().strip() == str(os.getpid()):
                            logger.info(f"Acquired browser lock (PID: {os.getpid()})")
                            return True
            else:
                # Check if lock is stale - if file is old (>60 seconds), consider it stale
                try:
                    file_age = time.time() - os.path.getmtime(_BROWSER_LOCK_FILE)
                    if file_age > 60:
                        # Stale lock, remove it
                        logger.warning(f"Removing stale browser lock (age: {file_age:.1f}s)")
                        os.unlink(_BROWSER_LOCK_FILE)
                        continue
                    else:
                        # Lock is held by another process, wait
                        time.sleep(0.5)
                        continue
                except (ValueError, OSError):
                    # Invalid lock, remove it
                    try:
                        os.unlink(_BROWSER_LOCK_FILE)
                    except:
                        pass
                    continue
        except Exception as e:
            logger.debug(f"Error acquiring lock: {e}")
            time.sleep(0.5)
    logger.warning("Could not acquire browser lock within timeout")
    return False

def _release_browser_lock():
    """Release file-based lock."""
    try:
        if os.path.exists(_BROWSER_LOCK_FILE):
            with open(_BROWSER_LOCK_FILE, 'r') as f:
                lock_pid = f.read().strip()
            if lock_pid == str(os.getpid()):
                os.unlink(_BROWSER_LOCK_FILE)
    except Exception:
        pass

@pytest.fixture(scope="session")
def pw_browser(playwright_instance, request):
    """Launch Chrome browser for Playwright tests - SINGLETON: only one browser instance across ALL processes"""
    global _global_browser, _global_playwright, _browser_lock
    
    # STRICT: Use file-based lock to prevent multiple browsers across processes
    # If we can't acquire lock, FAIL - don't create browser
    if not _acquire_browser_lock(timeout=30):
        error_msg = f"❌ CRITICAL: Could not acquire browser lock! Another browser may be running. PID: {os.getpid()}"
        logger.error(error_msg)
        pytest.fail(error_msg)
    
    # Use thread lock to ensure only one browser is created at a time within this process
    with _browser_lock:
        # Check if browser already exists and is connected
        if _global_browser is not None:
            try:
                # Check if browser is still connected
                if _global_browser.is_connected():
                    logger.info("Reusing existing browser instance")
                    return _global_browser
            except Exception:
                # Browser was closed, reset it
                logger.info("Browser was closed, creating new instance")
                _global_browser = None
        
        # Create new browser only if one doesn't exist
        logger.info("Creating new browser instance (only one will be created across all processes)")
        args = []
        if MAXIMIZE_BROWSER:
            args.append("--start-maximized")
        else:
            # If size/pos are provided, apply them; otherwise keep a normal window
            # so Windows Snap (Win+Left/Right) can dock it beside the editor.
            if PW_WINDOW_SIZE:
                args.append(f"--window-size={PW_WINDOW_SIZE}")
            if PW_WINDOW_POS:
                args.append(f"--window-position={PW_WINDOW_POS}")
        
        # Use Chrome channel instead of Chromium for better compatibility
        # This will use the actual Chrome browser installed on the system
        _global_browser = playwright_instance.chromium.launch(
            channel="chrome",  # Use Chrome instead of Chromium
            headless=False,     # Make browser visible
            args=args
        )
        
        # Register finalizer to close browser at end of session
        def close_browser():
            global _global_browser, _global_playwright
            with _browser_lock:
                if _global_browser is not None:
                    try:
                        logger.info("Closing browser instance")
                        _global_browser.close()
                    except Exception as e:
                        logger.warning(f"Error closing browser: {e}")
                    finally:
                        _global_browser = None
                if _global_playwright is not None:
                    try:
                        _global_playwright.stop()
                    except Exception:
                        pass
                    finally:
                        _global_playwright = None
                _release_browser_lock()
                _remove_pytest_lock()  # Remove pytest lock when browser closes
        
        request.addfinalizer(close_browser)
    
    yield _global_browser


@pytest.fixture(scope="function")
def page(pw_browser):
    """Create a new Playwright page with sensible defaults and stealth options
    
    Each test gets a fresh, isolated context to prevent test interference.
    """
    # Use realistic user agent to avoid detection
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport=None if MAXIMIZE_BROWSER else {"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/New_York",
        permissions=["geolocation"],
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
    )
    # Set default timeout to 30s similar to Selenium waits
    context.set_default_timeout(30000)
    page = context.new_page()
    
    # Add stealth scripts to make browser less detectable
    page.add_init_script("""
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)
    
    yield page
    
    # Proper cleanup: ensure all operations complete before closing
    try:
        # Wait for any pending operations to complete
        page.wait_for_timeout(500)
        # Close all pages in the context first
        for p in context.pages:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Error during page cleanup: {e}")
    finally:
        # Always close the context, ensuring proper isolation
        try:
            context.close()
            # Small wait to ensure context is fully closed before next test
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")


@pytest.fixture(scope="function")
def start_runtime_measurement():
    """Start runtime measurement for a test"""
    def _start(test_name: str):
        runtime_data['current_test'] = test_name
        runtime_data['start_time'] = time.time()
        logger.info("=" * 80)
        logger.info(f"Started runtime measurement for: {test_name}")
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        print(f"Started runtime measurement for: {test_name}")
    return _start


@pytest.fixture(scope="function")
def end_runtime_measurement():
    """End runtime measurement and return elapsed time"""
    def _end(operation_name: str = None):
        if 'start_time' not in runtime_data:
            logger.warning("No start time recorded. Call start_runtime_measurement first.")
            print("No start time recorded. Call start_runtime_measurement first.")
            return 0.0
        
        elapsed = time.time() - runtime_data['start_time']
        test_name = runtime_data.get('current_test', operation_name or "Unknown")
        
        if test_name not in runtime_data['timings']:
            runtime_data['timings'][test_name] = []
        
        timing_entry = {
            'operation': operation_name or 'total',
            'elapsed_seconds': elapsed,
            'timestamp': datetime.now().isoformat()
        }
        runtime_data['timings'][test_name].append(timing_entry)
        
        logger.info("=" * 80)
        logger.info(f"Runtime for '{test_name}': {elapsed:.2f} seconds")
        logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        print(f"Runtime for '{test_name}': {elapsed:.2f} seconds")
        runtime_data.pop('start_time', None)
        return elapsed
    return _end


def check_network_connectivity(url: str | None = None, timeout: float | None = None) -> bool:
    """
    Check basic network connectivity.

    Important for corporate networks:
    - `https://www.google.com` may be blocked, even when BenchSale is reachable.
    - When connectivity isn't available, we SKIP (default) instead of FAILing the test run.

    Controls:
    - NET_CHECK_URL: override default check target.
    - NET_CHECK_MODE: one of {"skip","fail","warn"} when all checks fail (default: "skip").
    - NET_CHECK_RUN: one of {"once","per_test","skip"} (default: "once").
    """
    import pytest
    from utils.test_logger import get_test_logger

    test_logger = get_test_logger()

    # Determine behavior
    run_mode = (os.getenv("NET_CHECK_RUN") or "once").strip().lower()
    if run_mode not in {"once", "per_test", "skip"}:
        run_mode = "once"

    if run_mode == "skip":
        # Explicitly bypass the check for speed. Tests may still fail later if the app is unreachable.
        logger.info("Network connectivity check skipped (NET_CHECK_RUN=skip).")
        try:
            test_logger.log_keyword_start("Check Network Connectivity", ["SKIPPED"])
            test_logger.log_keyword_end("Check Network Connectivity", "PASS")
        except Exception:
            pass
        return True

    # Cache only successful results (avoid re-checking for every test)
    now = time.time()
    if run_mode == "once":
        cached_ok = _NET_CHECK_CACHE.get("result")
        cached_ts = float(_NET_CHECK_CACHE.get("timestamp") or 0.0)
        if cached_ok is True and (now - cached_ts) <= NET_CHECK_CACHE_TTL:
            logger.info(
                f"Network connectivity check: using cached PASS (age={now - cached_ts:.2f}s, ttl={NET_CHECK_CACHE_TTL:.0f}s)"
            )
            try:
                test_logger.log_keyword_start("Check Network Connectivity", ["CACHED"])
                test_logger.log_keyword_end("Check Network Connectivity", "PASS")
            except Exception:
                pass
            return True

    # Default timeout comes from env-configured value
    timeout = float(timeout if timeout is not None else NET_CHECK_TIMEOUT)

    # Prefer checking the app under test (BENCHSALE_URL) over Google.
    env_url = (os.getenv("NET_CHECK_URL") or "").strip() or None
    primary = url or env_url or globals().get("BENCHSALE_URL") or "https://www.google.com"

    # Try a small set of targets; consider "reachable" even if auth is required (401/403)
    candidates: list[str] = []
    for u in [primary, globals().get("BENCHSALE_URL"), "https://www.google.com"]:
        if u and u not in candidates:
            candidates.append(u)

    test_logger.log_keyword_start("Check Network Connectivity", candidates)
    start_time = time.time()

    logger.info(f"Checking network connectivity (timeout={timeout}s). Targets: {candidates}")
    last_err: str | None = None
    session = requests.Session()
    start_loop = time.time()
    for target in candidates:
        try:
            # Try HEAD first (faster) then fallback to GET if HEAD fails
            try:
                resp = session.head(target, timeout=timeout, allow_redirects=True)
            except Exception:
                resp = session.get(target, timeout=timeout, allow_redirects=True)

            # Treat any non-5xx as "reachable" (200/3xx/401/403 are fine)
            reachable = resp.status_code < 500
            status_msg = "Connected" if reachable else "Failed"
            elapsed = time.time() - start_loop
            logger.info(f"Network connectivity check: {status_msg} (Target: {target}, Status: {resp.status_code})")
            logger.debug(f"Network check elapsed: {elapsed:.3f}s")
            if reachable:
                _NET_CHECK_CACHE["result"] = True
                _NET_CHECK_CACHE["timestamp"] = time.time()
                test_logger.log_keyword_end("Check Network Connectivity", "PASS")
                return True
        except Exception as e:
            last_err = str(e)
            logger.warning(f"Network connectivity check failed for {target}: {last_err}")

    # All attempts failed
    mode = (os.getenv("NET_CHECK_MODE") or "skip").strip().lower()
    msg = f"Network connectivity check failed for all targets {candidates}. Last error: {last_err}"
    logger.error(msg)
    test_logger.log_keyword_end("Check Network Connectivity", "FAIL")

    if mode == "warn":
        # Let the test continue; it may still fail later if app isn't reachable.
        return True
    if mode == "fail":
        return False

    # default: skip
    pytest.skip(msg)


def measure_page_load_time(driver, url: str, operation_name: str = None) -> float:
    """Measure page load time"""
    operation_name = operation_name or f"Page Load: {url}"
    start_time = time.time()
    
    try:
        current_url = driver.current_url
        if url.rstrip('/') not in current_url.rstrip('/'):
            driver.get(url)
        
        # Wait for page to be ready
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(("tag name", "body"))
        )
        
        elapsed = time.time() - start_time
        print(f"Page load time for '{url}': {elapsed:.2f}s")
        
        if elapsed > 10.0:
            print(f"Slow page load: {elapsed:.2f}s for {url}")
        
        return elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error measuring page load: {url} - {str(e)}")
        return elapsed


def handle_job_fair_popup(driver, wait):
    """Handle job fair popup if present"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Job fair pop-up")
    start_time = time.time()
    
    try:
        popup_available = wait.until(
            EC.presence_of_element_located(("css selector", ".css-uhb5lp"))
        )
        if popup_available:
            # Try CSS selector first
            try:
                close_button = wait.until(
                    EC.element_to_be_clickable(("css selector", ".css-11q2htf"))
                )
                close_button.click()
            except TimeoutException:
                # Fallback to xpath
                try:
                    close_button = wait.until(
                        EC.element_to_be_clickable(("xpath", "/html/body/div[2]/div[3]/div/div[2]/button[2]"))
                    )
                    close_button.click()
                except TimeoutException:
                    logger.debug("WARNING: Job fair pop-up close button not found")
        time.sleep(2)
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Job fair pop-up", "PASS")
    except TimeoutException:
        # Popup not present, continue
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Job fair pop-up", "PASS")
        pass


def login_benchsale_admin(driver, wait, user_id=USER_ID, password=USER_PASSWORD):
    """Login to BenchSale Admin"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Login credentials for BenchSale")
    start_time = time.time()
    
    try:
        # Wait for email input field
        email_input = wait.until(
            EC.presence_of_element_located(("id", ":r0:"))
        )
        email_input.clear()
        email_input.send_keys(user_id)
        
        # Wait for password input field
        password_input = wait.until(
            EC.presence_of_element_located(("id", ":r1:"))
        )
        password_input.clear()
        password_input.send_keys(password)
        
        time.sleep(1)
        
        # Click sign in button
        sign_in_button = wait.until(
            EC.element_to_be_clickable(("xpath", "/html/body/div/div[2]/main/div/form/button"))
        )
        sign_in_button.click()
        
        time.sleep(2)
        
        # Handle alert if present
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except:
            pass
        
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale", "PASS")
        logger.info("Logged in to BenchSale Admin successfully")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale", "FAIL")
        logger.error(f"Error during login: {str(e)}")
        raise


def login_benchsale_recruiter(driver, wait, rec_id=REC_ID, rec_password=REC_PASSWORD):
    """Login to BenchSale Recruiter"""
    try:
        email_input = wait.until(
            EC.presence_of_element_located(("id", ":r0:"))
        )
        email_input.clear()
        email_input.send_keys(rec_id)
        
        password_input = wait.until(
            EC.presence_of_element_located(("id", ":r1:"))
        )
        password_input.clear()
        password_input.send_keys(rec_password)
        
        time.sleep(1)
        
        sign_in_button = wait.until(
            EC.element_to_be_clickable(("xpath", "/html/body/div/div[2]/main/div/form/button"))
        )
        sign_in_button.click()
        
        print("Logged in to BenchSale Recruiter successfully")
    except Exception as e:
        print(f"Error during recruiter login: {str(e)}")
        raise


def navigate_to_benchsale(driver, wait):
    """Navigate to BenchSale from homepage"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Go To", [BASE_URL])
    start_time = time.time()
    
    # Navigate to homepage
    driver.get(BASE_URL)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Go To", "PASS")
    
    test_logger.log_keyword_start("Maximize Browser Window")
    start_time = time.time()
    driver.maximize_window()
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Maximize Browser Window", "PASS")
    
    test_logger.log_keyword_start("Sleep", [2])
    start_time = time.time()
    time.sleep(2)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Sleep", "PASS")
    
    # Handle job fair popup
    handle_job_fair_popup(driver, wait)
    
    test_logger.log_keyword_start("Sleep", [3])
    start_time = time.time()
    time.sleep(3)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Sleep", "PASS")
    
    # Click BenchSales button in navigation header
    test_logger.log_keyword_start("Click Element", ["BenchSales button"])
    start_time = time.time()
    benchsale_button = wait.until(
        EC.element_to_be_clickable(("xpath", "/html/body/div/div[2]/header/div/nav/ul/div[3]/button/p"))
    )
    benchsale_button.click()
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Click Element", "PASS")
    
    test_logger.log_keyword_start("Sleep", [3])
    start_time = time.time()
    time.sleep(3)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Sleep", "PASS")
    
    # Click Sign In link in dropdown menu
    test_logger.log_keyword_start("Click Element", ["Sign In link"])
    start_time = time.time()
    sign_in_link = wait.until(
        EC.element_to_be_clickable(("xpath", "/html/body/div[2]/div[3]/ul/a[2]"))
    )
    sign_in_link.click()
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Click Element", "PASS")
    
    test_logger.log_keyword_start("Sleep", [2])
    start_time = time.time()
    time.sleep(2)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Sleep", "PASS")
    
    # Switch to new window
    test_logger.log_keyword_start("Switch Window", ["NEW"])
    start_time = time.time()
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(3)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Switch Window", "PASS")
    
    logger.info("Navigated to BenchSale login page")


# -----------------------------
# Playwright helper functions
# -----------------------------
def measure_page_load_time_pw(page, url, operation_name="Page Load"):
    """
    Measure page load time using Playwright.
    """
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Measure Page Load Time", [url, operation_name])
    start_time = time.time()
    page.goto(url, wait_until="load", timeout=60000)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Measure Page Load Time", "PASS", elapsed=elapsed)
    logger.info(f"Page load time for '{url}': {elapsed:.2f}s")
    return elapsed


def goto_fast(page: PWPage, url: str, timeout: int = 60000):
    """
    Faster navigation: domcontentloaded is usually enough for SPA apps.
    For dashboard/login URLs, use 'load' to ensure redirects complete without waiting for networkidle.
    Has fallback mechanism if 'load' times out.
    
    IMPORTANT: Always use this function instead of page.goto() directly to avoid timeout issues.
    This function has multiple fallback strategies to handle slow page loads.
    
    Example:
        goto_fast(page, "https://jobsnprofiles.com/Login")  # ✅ Good
        page.goto("https://jobsnprofiles.com/Login")  # ❌ Bad - may timeout
    """
    # Use shorter timeout for fallbacks to avoid long waits
    fallback_timeout = min(30000, timeout // 2)  # Use half of original timeout or 30s, whichever is smaller
    commit_timeout = min(15000, timeout // 4)  # Even shorter for commit
    
    # For dashboard/login URLs, use 'load' instead of 'networkidle' to avoid timeout issues
    # 'load' waits for page load event (redirects complete) but doesn't wait for network to be idle
    if "dashboard" in url.lower() or "login" in url.lower() or "EmpLogin" in url or "Empdashboard" in url:
        # Try 'load' first, but fallback to 'domcontentloaded' if it times out
        try:
            page.goto(url, wait_until="load", timeout=timeout)
            # Additional wait for DOM to be ready (with shorter timeout)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                logger.debug(f"goto_fast: domcontentloaded wait skipped for {url}")
        except Exception as e:
            # If 'load' times out, try faster 'domcontentloaded' approach
            logger.warning(f"goto_fast: 'load' timed out for {url}, trying 'domcontentloaded'...")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=fallback_timeout)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    logger.debug(f"goto_fast: domcontentloaded wait skipped for {url}")
            except Exception as e2:
                # Last resort: try with commit (fastest) - don't wait for load_state after commit
                logger.warning(f"goto_fast: 'domcontentloaded' also failed for {url}, trying 'commit'...")
                try:
                    page.goto(url, wait_until="commit", timeout=commit_timeout)
                    # Don't wait for load_state after commit - it's already the fastest option
                except Exception as e3:
                    # Final fallback: just navigate without any wait condition
                    logger.error(f"goto_fast: All navigation attempts failed for {url}, attempting basic navigation...")
                    try:
                        page.goto(url, wait_until="commit", timeout=10000)
                    except Exception as final_e:
                        logger.error(f"goto_fast: Complete navigation failure for {url}: {final_e}")
                        raise
    else:
        # For other pages, use faster domcontentloaded
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except Exception as e:
            # Fallback to commit if domcontentloaded fails
            logger.warning(f"goto_fast: 'domcontentloaded' timed out for {url}, trying 'commit'...")
            try:
                page.goto(url, wait_until="commit", timeout=fallback_timeout)
                # Don't wait for load_state after commit - commit is already fast enough
            except Exception as e2:
                # Final fallback: try with even shorter timeout
                logger.warning(f"goto_fast: 'commit' also failed for {url}, trying with minimal timeout...")
                page.goto(url, wait_until="commit", timeout=10000)


def handle_job_fair_popup_pw(page):
    """Close job fair popup if present (Playwright)"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Job fair pop-up")
    start_time = time.time()
    try:
        popup = page.locator(".css-uhb5lp")
        if popup.is_visible():
            # Try CSS selector first
            close_btn = page.locator(".css-11q2htf")
            if close_btn.is_visible():
                close_btn.click()
            else:
                alt_btn = page.locator("xpath=/html/body/div[2]/div[3]/div/div[2]/button[2]")
                if alt_btn.is_visible():
                    alt_btn.click()
        page.wait_for_timeout(2000)
        test_logger.log_keyword_end("Job fair pop-up", "PASS")
    except PWTimeoutError:
        test_logger.log_keyword_end("Job fair pop-up", "PASS")
    except Exception as e:
        test_logger.log_keyword_end("Job fair pop-up", "FAIL")
        logger.debug(f"Job fair popup handling skipped: {e}")


def navigate_to_benchsale_pw(page, goto_home: bool = True):
    """Navigate directly to BenchSale login page using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    # Direct navigation to BenchSale login page
    login_url = f"{BENCHSALE_URL}login"
    test_logger.log_keyword_start("Go To", [login_url])
    start_time = time.time()
    page.goto(login_url, wait_until="load", timeout=60000)
    elapsed = time.time() - start_time
    test_logger.log_keyword_end("Go To", "PASS", elapsed=elapsed)
    
    page.wait_for_timeout(1000)

    # Make sure page is loaded
    try:
        page.wait_for_load_state("load", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(1000)
    logger.info("Navigated directly to BenchSale login page (Playwright)")
    return page


# Global flag to track which type of tests are running
_RUNNING_TEST_TYPE = None
# Track which test files are actually being requested
_REQUESTED_TEST_FILES = set()

def ensure_admin_storage_state(pw_browser) -> str:
    """
    Create/reuse admin storage_state using ADMIN credentials only.
    Optimized to avoid unnecessary browser opens - only creates state if missing or invalid.
    IMPORTANT: Always uses ADMIN credentials (USER_ID, USER_PASSWORD) - never recruiter credentials.
    """
    # Check if storage state exists and is valid
    if os.path.exists(ADMIN_STATE_PATH) and os.path.getsize(ADMIN_STATE_PATH) > 0:
        try:
            import json
            with open(ADMIN_STATE_PATH, 'r') as f:
                data = json.load(f)
                # Check if state has valid cookies AND verify it's for admin (not recruiter)
                if data and 'cookies' in data and len(data.get('cookies', [])) > 0:
                    # Verify cookies are for admin account (check for admin email in cookies)
                    cookies = data.get('cookies', [])
                    is_admin_state = False
                    for cookie in cookies:
                        cookie_value = str(cookie.get('value', '')).lower()
                        cookie_name = str(cookie.get('name', '')).lower()
                        # Check if cookie contains admin email or admin-related identifiers
                        if USER_ID.lower() in cookie_value or 'admin' in cookie_name or USER_ID.lower() in str(cookie):
                            is_admin_state = True
                            break
                    
                    if is_admin_state:
                        logger.debug("Admin storage state exists and is valid (verified admin credentials), reusing it")
                        return ADMIN_STATE_PATH
                    else:
                        logger.warning("Admin storage state file exists but contains non-admin credentials - will recreate")
                        os.remove(ADMIN_STATE_PATH)
        except Exception as e:
            logger.debug(f"Error reading admin storage state: {e}")
        
        # State file exists but is invalid, remove it
        try:
            if os.path.exists(ADMIN_STATE_PATH):
                os.remove(ADMIN_STATE_PATH)
                logger.debug("Removed invalid admin storage state file")
        except Exception:
            pass

    # Storage state doesn't exist or is invalid - create it with ADMIN credentials
    logger.debug(f"Creating new admin storage state with ADMIN credentials: {USER_ID} (browser will open for login)")
    context = pw_browser.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
    context.set_default_timeout(30000)
    page = context.new_page()

    try:
        # Navigate directly to BenchSale login page
        login_url = f"{BENCHSALE_URL}login"
        goto_fast(page, login_url)
        page.wait_for_timeout(1000)

        # CRITICAL: Always use ADMIN credentials, never recruiter
        logger.debug(f"Logging in with ADMIN credentials: {USER_ID}")
        login_benchsale_admin_pw(page, user_id=USER_ID, password=USER_PASSWORD)
        try:
            page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=60000)
        except Exception:
            pass
        context.storage_state(path=ADMIN_STATE_PATH)
        logger.debug(f"Admin storage state created and saved successfully with credentials: {USER_ID}")
    finally:
        try:
            page.close()
            context.close()
            time.sleep(0.3)
        except Exception:
            pass
    
    return ADMIN_STATE_PATH


@pytest.fixture(scope="function")
def admin_page(pw_browser, request):
    """
    Authenticated BenchSale admin page fixture with smart isolation.

    This repo's admin Playwright tests expect the left-nav/dashboard to already be present.
    To make "Run Test" (VS Code/Cursor) work without requiring extra flags/env vars,
    this fixture always ensures a valid authenticated `storage_state` and navigates
    directly to the BenchSale app.
    
    Each test gets a fresh, isolated context to prevent test interference.
    Smart Framework: Automatically prevents this fixture from running in recruiter tests.
    """
    # Smart validation: Verify this is actually an admin test
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    
    # Auto-skip if this is a recruiter test file
    if 'test_benchsale_recruiter' in test_file.lower() and 'test_benchsale_admin' not in test_file.lower():
        pytest.skip(f"🧠 Smart Framework: Admin fixture auto-skipped for recruiter test: {test_name}")
    
    # Smart check: If only recruiter tests were requested, skip
    if 'recruiter' in _REQUESTED_TEST_FILES and 'admin' not in _REQUESTED_TEST_FILES:
        pytest.skip(f"🧠 Smart Framework: Admin fixture skipped - only recruiter tests requested")
    
    logger.debug(f"Creating admin_page fixture for test: {test_name}")
    
    # Only create admin storage state - smart framework prevents recruiter state creation
    state_path = ensure_admin_storage_state(pw_browser)
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1920, "height": 1080},
        storage_state=state_path,
    )
    context.set_default_timeout(15000 if FAST_MODE else 30000)
    page = context.new_page()
    # Close any popup pages immediately to avoid about:blank visibility
    try:
        def _close_popup(popup):
            try:
                popup.close()
            except Exception:
                pass

        page.on("popup", _close_popup)
        # Also close any new pages added to the context
        def _close_new_page(p):
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass

        context.on("page", _close_new_page)
    except Exception:
        pass
    
    # Navigate and verify authentication
    goto_fast(page, BENCHSALE_URL)
    page.wait_for_timeout(2000)
    
    # Check if redirected to login page (storage state might be invalid)
    # Only check if we're actually on login page - avoid unnecessary login
    try:
        current_url = page.url
        # If we're already on the dashboard (not login page), skip login check
        if "login" not in current_url.lower() and "signin" not in current_url.lower():
            # Check if dashboard elements are visible (means we're already logged in)
            dashboard_check = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul")
            if dashboard_check.count() > 0:
                logger.debug("Already authenticated, dashboard visible")
                # Wait for dashboard to fully load
                try:
                    dashboard_check.wait_for(timeout=10000)
                except Exception:
                    pass
            else:
                # Dashboard not visible, might need login
                login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
                if login_indicator.count() > 0 and login_indicator.first.is_visible(timeout=3000):
                    logger.debug("Storage state invalid, re-logging in...")
                    try:
                        tgl = page.locator(".css-1hw9j7s")
                        if tgl.count() and tgl.first.is_visible():
                            tgl.first.click()
                            page.wait_for_timeout(300)
                    except Exception:
                        pass
                    login_benchsale_admin_pw(page, user_id=USER_ID, password=USER_PASSWORD)
                    page.wait_for_timeout(2000)
                    # Save updated storage state
                    context.storage_state(path=ADMIN_STATE_PATH)
        else:
            # We're on login page, need to login
            logger.debug("On login page, logging in...")
            try:
                tgl = page.locator(".css-1hw9j7s")
                if tgl.count() and tgl.first.is_visible():
                    tgl.first.click()
                    page.wait_for_timeout(300)
            except Exception:
                pass
            # CRITICAL: Always use ADMIN credentials, never recruiter
            logger.debug(f"Re-logging in with ADMIN credentials: {USER_ID}")
            login_benchsale_admin_pw(page, user_id=USER_ID, password=USER_PASSWORD)
            page.wait_for_timeout(2000)
            # Save updated storage state
            context.storage_state(path=ADMIN_STATE_PATH)
            logger.debug(f"Admin storage state updated with credentials: {USER_ID}")
    except Exception as e:
        logger.debug(f"Error checking authentication status: {e}")
        # Fallback: try to login if we can't determine status
        try:
            login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
            if login_indicator.count() > 0 and login_indicator.first.is_visible(timeout=3000):
                logger.debug("Fallback: Storage state invalid, re-logging in...")
                try:
                    tgl = page.locator(".css-1hw9j7s")
                    if tgl.count() and tgl.first.is_visible():
                        tgl.first.click()
                        page.wait_for_timeout(300)
                except Exception:
                    pass
                login_benchsale_admin_pw(page, user_id=USER_ID, password=USER_PASSWORD)
                page.wait_for_timeout(2000)
                context.storage_state(path=ADMIN_STATE_PATH)
        except Exception:
            pass
    
    # Wait for dashboard to load
    try:
        page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=60000)
    except Exception:
        pass
    
    yield page
    
    # Proper cleanup: ensure all operations complete before closing
    try:
        # Wait for any pending operations to complete
        page.wait_for_timeout(500)
        # Close all pages in the context first
        for p in context.pages:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
        # Save updated storage state after the test (keeps authentication fresh between runs)
        context.storage_state(path=ADMIN_STATE_PATH)
    except Exception as e:
        logger.debug(f"Error during admin_page cleanup: {e}")
    finally:
        # Always close the context, ensuring proper isolation
        try:
            context.close()
            # Small wait to ensure context is fully closed before next test
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")


def ensure_recruiter_storage_state(pw_browser) -> str:
    """Create/reuse recruiter storage_state using RECRUITER credentials only."""
    if os.path.exists(RECRUITER_STATE_PATH) and os.path.getsize(RECRUITER_STATE_PATH) > 0:
        try:
            import json
            with open(RECRUITER_STATE_PATH, 'r') as f:
                data = json.load(f)
                if data and 'cookies' in data and len(data.get('cookies', [])) > 0:
                    return RECRUITER_STATE_PATH
        except Exception:
            pass
        try:
            os.remove(RECRUITER_STATE_PATH)
        except Exception:
            pass

    context = pw_browser.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
    context.set_default_timeout(30000)
    page = context.new_page()

    try:
        # Navigate directly to BenchSale login page
        login_url = f"{BENCHSALE_URL}login"
        goto_fast(page, login_url)
        page.wait_for_timeout(1000)

        login_benchsale_recruiter_pw(page, user_id=REC_ID, password=REC_PASSWORD)
        try:
            page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=60000)
        except Exception:
            pass
        context.storage_state(path=RECRUITER_STATE_PATH)
    finally:
        try:
            page.close()
            context.close()
            time.sleep(0.3)
        except Exception:
            pass
    
    return RECRUITER_STATE_PATH


@pytest.fixture(scope="function")
def recruiter_page(pw_browser, request):
    """
    Authenticated BenchSale recruiter page fixture with smart isolation.

    BenchSale recruiter Playwright tests expect the left-nav/dashboard to already be present.
    
    Each test gets a fresh, isolated context to prevent test interference.
    Smart Framework: Automatically prevents this fixture from running in admin tests.
    """
    # Smart validation: Verify this is actually a recruiter test
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    
    # Auto-skip if this is an admin test file
    if 'test_benchsale_admin' in test_file.lower() and 'test_benchsale_recruiter' not in test_file.lower():
        pytest.skip(f"🧠 Smart Framework: Recruiter fixture auto-skipped for admin test: {test_name}")
    
    # Smart check: If only admin tests were requested, skip
    if 'admin' in _REQUESTED_TEST_FILES and 'recruiter' not in _REQUESTED_TEST_FILES:
        pytest.skip(f"🧠 Smart Framework: Recruiter fixture skipped - only admin tests requested")
    
    logger.debug(f"Creating recruiter_page fixture for test: {test_name}")
    
    # Only create recruiter storage state - smart framework prevents admin state creation
    state_path = ensure_recruiter_storage_state(pw_browser)
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1920, "height": 1080},
        storage_state=state_path,
    )
    context.set_default_timeout(15000 if FAST_MODE else 30000)
    page = context.new_page()
    # Close any popup pages immediately to avoid about:blank visibility
    try:
        def _close_popup(popup):
            try:
                popup.close()
            except Exception:
                pass

        page.on("popup", _close_popup)
        def _close_new_page(p):
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass

        context.on("page", _close_new_page)
    except Exception:
        pass
    
    # Navigate and verify authentication
    goto_fast(page, BENCHSALE_URL)
    page.wait_for_timeout(2000)
    
    # Validating if we are truly logged in
    # 1. Check if dashboard is already visible
    try:
        page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(state="visible", timeout=5000)
        logger.debug("Dashboard sidebar found, session valid.")
    except Exception:
        # 2. If dashboard not found, we assume we need to login or we are on login page
        logger.debug("Dashboard not visible, checking for login page...")
        
        # Check login page indicators
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        try:
            if login_indicator.count() > 0:
                 login_indicator.first.wait_for(state="visible", timeout=5000)
            else:
                 # Wait a bit just in case
                 page.wait_for_selector("input[name='email'], input[type='email']", timeout=5000, state="visible")
        except Exception:
            # If neither dashboard nor login input is found, something is wrong. 
            # But we will try to login anyway or force reload.
            logger.warning("Neither dashboard nor login input found immediately. Reloading...")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

        # Force Login logic (if not on dashboard)
        logger.debug("Attempting to ensure login...")
        
        # Check if we need to click "Sign in" toggle (sometimes req for admin/recruiter switch)
        try:
            tgl = page.locator(".css-1hw9j7s")
            if tgl.count() and tgl.first.is_visible():
                tgl.first.click()
                page.wait_for_timeout(500)
        except Exception:
            pass
            
        login_benchsale_recruiter_pw(page, user_id=REC_ID, password=REC_PASSWORD)
        
        # Save updated storage state
        context.storage_state(path=RECRUITER_STATE_PATH)

    # Final check: Dashboard MUST be visible now
    page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(state="visible", timeout=30000)
    
    yield page
    
    # Proper cleanup: ensure all operations complete before closing
    try:
        # Wait for any pending operations to complete
        page.wait_for_timeout(500)
        # Close all pages in the context first
        for p in context.pages:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
        # Save updated storage state after the test (keeps authentication fresh between runs)
        context.storage_state(path=RECRUITER_STATE_PATH)
    except Exception as e:
        logger.debug(f"Error during recruiter_page cleanup: {e}")
    finally:
        # Always close the context, ensuring proper isolation
        try:
            context.close()
            # Small wait to ensure context is fully closed before next test
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")


def login_benchsale_admin_pw(page, user_id=USER_ID, password=USER_PASSWORD):
    """Login to BenchSale Admin using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    test_logger.log_keyword_start("Login credentials for BenchSale")
    start_time = time.time()
    try:
        # Be flexible: UI IDs can change; prefer semantic selectors first
        email_selectors = [
            "input[name='email']",
            "input[type='email']",
            "[id=':r0:']",
        ]
        email_input = None
        for sel in email_selectors:
            try:
                email_input = page.wait_for_selector(sel, timeout=5000, state="visible")
                break
            except PWTimeoutError:
                continue
        if not email_input:
            raise PWTimeoutError("Email input not found (tried name/email/type/email/:r0:)")
        email_input.fill(user_id)
        
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "[id=':r1:']",
        ]
        password_input = None
        for sel in password_selectors:
            try:
                password_input = page.wait_for_selector(sel, timeout=5000, state="visible")
                break
            except PWTimeoutError:
                continue
        if not password_input:
            raise PWTimeoutError("Password input not found (tried name/password/type/password/:r1:)")
        password_input.fill(password)
        
        page.wait_for_timeout(1000)
        page.locator("xpath=/html/body/div/div[2]/main/div/form/button").click()
        page.wait_for_timeout(2000)
        
        # Handle alert if any
        try:
            page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass
        
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale", "PASS", elapsed=elapsed)
        logger.info("Logged in to BenchSale Admin successfully (Playwright)")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale", "FAIL", elapsed=elapsed)
        logger.error(f"Error during Playwright login: {e}")
        raise


def login_benchsale_recruiter_pw(page, user_id=REC_ID, password=REC_PASSWORD):
    """Login to BenchSale Recruiter using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()

    test_logger.log_keyword_start("Login credentials for BenchSale-Recruiter")
    start_time = time.time()
    try:
        email_selectors = [
            "input[name='email']",
            "input[type='email']",
            "[id=':r0:']",
        ]
        email_input = None
        for sel in email_selectors:
            try:
                email_input = page.wait_for_selector(sel, timeout=5000, state="visible")
                break
            except PWTimeoutError:
                continue
        if not email_input:
            raise PWTimeoutError("Email input not found (tried name/email/type/email/:r0:)")
        email_input.fill(user_id)

        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "[id=':r1:']",
        ]
        password_input = None
        for sel in password_selectors:
            try:
                password_input = page.wait_for_selector(sel, timeout=5000, state="visible")
                break
            except PWTimeoutError:
                continue
        if not password_input:
            raise PWTimeoutError("Password input not found (tried name/password/type/password/:r1:)")
        password_input.fill(password)

        page.wait_for_timeout(300 if FAST_MODE else 1000)
        page.locator("xpath=/html/body/div/div[2]/main/div/form/button").click()
        page.wait_for_timeout(300 if FAST_MODE else 2000)

        # Handle alert if any
        try:
            page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass

        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale-Recruiter", "PASS", elapsed=elapsed)
        logger.info("Logged in to BenchSale Recruiter successfully (Playwright)")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for BenchSale-Recruiter", "FAIL", elapsed=elapsed)
        logger.error(f"Error during Playwright recruiter login: {e}")
        raise


def close_any_dialogs(driver):
    """Close any open MUI dialogs"""
    logger.debug("Attempting to close any open dialogs...")
    for _ in range(3):
        try:
            dialog = driver.find_element("css selector", ".MuiDialog-container")
            # Try to click backdrop or close button
            driver.execute_script("""
                var d = document.querySelector('.MuiDialog-container');
                if(d) {
                    var b = d.querySelector('.MuiBackdrop-root');
                    if(b) b.click();
                    else {
                        var c = d.querySelector('button[aria-label*="Close"],button[aria-label*="close"]');
                        if(c) c.click();
                        else document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape'}));
                    }
                }
            """)
            time.sleep(0.5)
            # Check if dialog still exists
            try:
                driver.find_element("css selector", ".MuiDialog-container")
            except NoSuchElementException:
                logger.debug("Dialog closed successfully")
                break
        except NoSuchElementException:
            logger.debug("No dialogs found to close")
            break


# Pytest hooks for logging
def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name or "test")


def _extract_locator_hint(error_text: str) -> str:
    """
    Try to extract the most useful locator/xpath from a Playwright error string.
    """
    if not error_text:
        return ""

    # Common Playwright formats:
    # - locator("xpath=...")
    # - waiting for locator("css=...")
    # - Locator.wait_for: ... locator("...")
    m = re.search(r'locator\("([^"]+)"\)', error_text)
    if m:
        return m.group(1).strip()

    # Fallback: try to find an xpath=... snippet
    m = re.search(r"(xpath=[^\s]+)", error_text)
    if m:
        return m.group(1).strip()

    return ""


def _capture_playwright_artifacts(page: PWPage, test_name: str):
    """
    Save screenshot + HTML + URL for easier debugging on failures.
    MANDATORY: Screenshots MUST be captured on test failures - will retry with different strategies.
    """
    base_dir = os.path.dirname(__file__)
    reports_dir = os.path.join(base_dir, "reports", "failures")
    os.makedirs(reports_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = _safe_filename(test_name)

    screenshot_path = os.path.join(reports_dir, f"{safe_name}_{ts}.png")
    html_path = os.path.join(reports_dir, f"{safe_name}_{ts}.html")
    url_path = os.path.join(reports_dir, f"{safe_name}_{ts}.url.txt")

    current_url = ""
    try:
        current_url = page.url
    except Exception:
        pass    

    # MANDATORY SCREENSHOT CAPTURE - Multiple strategies with retries
    screenshot_captured = False
    screenshot_error = None
    
    # Save original timeout settings to restore later
    original_default_timeout = None
    try:
        original_default_timeout = page.context.timeout if hasattr(page.context, 'timeout') else None
    except Exception:
        pass
    
    # Strategy 1: Try full page screenshot with timeout (prevents font loading wait)
    for attempt in range(3):
        try:
            # Temporarily set a shorter default timeout to ensure our timeout parameter is respected
            try:
                if hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(10000)  # Set to 10s to ensure our 8s timeout works
            except Exception:
                pass
            
            # Use shorter timeout to prevent hanging on font loading
            # Playwright will try to capture even if fonts aren't fully loaded
            page.screenshot(
                path=screenshot_path, 
                full_page=True,
                timeout=8000  # 8 second timeout - prevents waiting for fonts indefinitely
            )
            screenshot_captured = True
            logger.info(f"Screenshot captured successfully (attempt {attempt + 1})")
            break
        except Exception as e:
            screenshot_error = e
            logger.warning(f"Screenshot attempt {attempt + 1} failed: {e}")
            if attempt < 2:  # Don't sleep on last attempt
                time.sleep(0.5)
        finally:
            # Restore original timeout if we changed it
            try:
                if original_default_timeout is not None and hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(original_default_timeout)
            except Exception:
                pass
    
    # Strategy 2: If full_page fails, try viewport-only screenshot (faster, no scrolling)
    if not screenshot_captured:
        try:
            logger.warning("Full page screenshot failed, trying viewport-only screenshot...")
            # Set even shorter timeout for viewport
            try:
                if hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(6000)
            except Exception:
                pass
            
            page.screenshot(
                path=screenshot_path,
                full_page=False,  # Viewport only - much faster
                timeout=5000  # Shorter timeout for viewport
            )
            screenshot_captured = True
            logger.info("Viewport-only screenshot captured successfully")
        except Exception as e:
            screenshot_error = e
            logger.warning(f"Viewport-only screenshot also failed: {e}")
        finally:
            # Restore original timeout
            try:
                if original_default_timeout is not None and hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(original_default_timeout)
            except Exception:
                pass
    
    # Strategy 3: Try with even shorter timeout (emergency fallback)
    if not screenshot_captured:
        try:
            logger.warning("Trying emergency screenshot with minimal timeout...")
            # Set very short timeout
            try:
                if hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(4000)
            except Exception:
                pass
            
            # Use the most basic screenshot options with very short timeout
            page.screenshot(path=screenshot_path, timeout=3000, full_page=False)
            screenshot_captured = True
            logger.info("Emergency screenshot captured successfully")
        except Exception as e:
            screenshot_error = e
            logger.warning(f"Emergency screenshot also failed: {e}")
        finally:
            # Restore original timeout
            try:
                if original_default_timeout is not None and hasattr(page.context, 'set_default_timeout'):
                    page.context.set_default_timeout(original_default_timeout)
            except Exception:
                pass
    
    # Strategy 4: Last resort - try to capture body element screenshot
    if not screenshot_captured:
        try:
            logger.warning("Trying body element screenshot as last resort...")
            body = page.locator('body')
            body.screenshot(path=screenshot_path, timeout=3000)
            screenshot_captured = True
            logger.info("Body element screenshot captured successfully")
        except Exception as e:
            screenshot_error = e
            logger.warning(f"Body element screenshot also failed: {e}")
    
    # Strategy 5: Ultra-fast screenshot - try with absolute minimum timeout (1 second)
    if not screenshot_captured:
        try:
            logger.warning("Trying ultra-fast screenshot with 1 second timeout...")
            # Set page timeout to 1 second temporarily
            original_timeout = page.context.timeout if hasattr(page.context, 'timeout') else None
            try:
                page.screenshot(path=screenshot_path, timeout=1000, full_page=False)
                screenshot_captured = True
                logger.info("Ultra-fast screenshot captured successfully")
            finally:
                # Restore original timeout if we changed it
                pass
        except Exception as e:
            screenshot_error = e
            logger.warning(f"Ultra-fast screenshot also failed: {e}")
    
    # Strategy 6: JavaScript-based screenshot capture (last resort)
    if not screenshot_captured:
        try:
            logger.warning("Attempting JavaScript-based screenshot capture...")
            # Try to use JavaScript to get page dimensions and capture
            screenshot_data = page.evaluate("""
                () => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = window.innerWidth;
                        canvas.height = window.innerHeight;
                        const ctx = canvas.getContext('2d');
                        // This won't work for security reasons, but we can try to get page info
                        return {
                            width: window.innerWidth,
                            height: window.innerHeight,
                            url: window.location.href,
                            title: document.title
                        };
                    } catch(e) {
                        return {error: e.message};
                    }
                }
            """)
            # If JS worked, at least try one more time with the page dimensions
            if screenshot_data and 'error' not in screenshot_data:
                page.screenshot(path=screenshot_path, timeout=2000, full_page=False)
                screenshot_captured = True
                logger.info("JavaScript-assisted screenshot captured successfully")
        except Exception as e:
            screenshot_error = e
            logger.warning(f"JavaScript-based screenshot also failed: {e}")
    
    # If screenshot still failed, create a placeholder file with error message
    if not screenshot_captured:
        try:
            error_msg = f"Screenshot capture failed after all retry strategies.\nError: {screenshot_error}\nTest: {test_name}\nURL: {current_url}\nTimestamp: {ts}"
            with open(screenshot_path.replace('.png', '_ERROR.txt'), "w", encoding="utf-8") as f:
                f.write(error_msg)
            logger.error(f"⚠️ CRITICAL: Screenshot capture failed for {test_name}. Error details saved to {screenshot_path.replace('.png', '_ERROR.txt')}")
        except Exception as final_e:
            logger.error(f"Could not even save screenshot error file: {final_e}")
    
    # HTML capture (non-critical, but try to save it)
    try:
        html = page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html or "")
    except Exception as e:
        logger.debug(f"Could not save HTML: {e}")

    # URL capture (always try to save)
    try:
        with open(url_path, "w", encoding="utf-8") as f:
            f.write(current_url or "")
    except Exception:
        pass

    return screenshot_path, html_path, url_path, current_url


def _refresh_dashboard_after_test(test_name: str, outcome: str):
    """Refresh dashboard after each test completes to show latest status.
    This runs after EVERY test (passed/failed/skipped) regardless of how the test was run.
    Optimized for speed - minimal delays.
    """
    try:
        # Import here to avoid circular imports
        import subprocess
        import sys
        import time
        from pathlib import Path
        
        # Skip dashboard refresh after each test - only refresh at session end for speed
        # Dashboard will be refreshed once at the end of all tests
        # This saves significant time (30+ seconds per test)
        return
        
        # OLD CODE - Disabled for speed optimization
        # Minimal delay - just enough for log flush
        # time.sleep(0.1)  # Reduced to minimal
    except Exception as e:
        # Always log the error but don't fail the test
        logger.warning(f"Could not refresh dashboard after test {test_name}: {e}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Generate detailed test reports"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    outcome = yield
    rep = outcome.get_result()
    
    test_name = item.name
    test_file = str(item.fspath) if hasattr(item, 'fspath') else None
    
    # Handle setup errors - log them as FAIL so they appear in history
    if rep.when == "setup" and rep.outcome == "failed":
        error_msg = str(rep.longrepr) if rep.longrepr else "Test setup failed"
        locator_hint = _extract_locator_hint(error_msg)
        if locator_hint:
            error_msg = f"{error_msg}\n\nLocator/XPath hint: {locator_hint}"
        elapsed = rep.duration if hasattr(rep, 'duration') else None
        test_logger.log_test_end(test_name, "FAIL", message=error_msg, elapsed=elapsed)
        # Force flush to ensure log is written immediately
        import logging
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        if rep.longrepr:
            logger.error(f"Setup error details:\n{rep.longrepr}")
    
    if rep.when == "call":
        if rep.outcome == "passed":
            elapsed = rep.duration if hasattr(rep, 'duration') else None
            test_logger.log_test_end(test_name, "PASS", elapsed=elapsed)
            # Force flush to ensure log is written immediately
            import logging
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Dashboard refresh disabled for speed - only refresh at session end
            # _refresh_dashboard_after_test(test_name, rep.outcome)
        elif rep.outcome == "failed":
            error_msg = str(rep.longrepr) if rep.longrepr else "Test failed"
            locator_hint = _extract_locator_hint(error_msg)
            if locator_hint:
                error_msg = f"{error_msg}\n\nLocator/XPath hint: {locator_hint}"
            elapsed = rep.duration if hasattr(rep, 'duration') else None
            test_logger.log_test_end(test_name, "FAIL", message=error_msg, elapsed=elapsed)
            # Force flush to ensure log is written immediately
            import logging
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            # If we have a Playwright page fixture, capture artifacts for debugging
            try:
                pw_page = None
                for key in ("admin_page", "recruiter_page", "employer1_page", "employer2_page", "page"):
                    if hasattr(item, "funcargs") and key in item.funcargs:
                        pw_page = item.funcargs.get(key)
                        break
                # JobSeeker tests create the page inside the test; allow them to attach it to the node.
                if pw_page is None:
                    pw_page = getattr(item, "_pw_page", None) or getattr(item, "pw_page", None) or getattr(item, "page", None)
                if pw_page is not None:
                    screenshot_path, html_path, url_path, current_url = _capture_playwright_artifacts(pw_page, test_name)
                    test_logger.log_info(f"Failure artifacts saved:")
                    test_logger.log_info(f"  URL: {current_url}")
                    test_logger.log_info(f"  Screenshot: {screenshot_path}")
                    test_logger.log_info(f"  HTML: {html_path}")
                    test_logger.log_info(f"  URL file: {url_path}")
            except Exception as e:
                logger.debug(f"Could not capture Playwright failure artifacts: {e}")

            if rep.longrepr:
                logger.error(f"Error details:\n{rep.longrepr}")
            
            # Refresh dashboard after test completes (FAIL)
            _refresh_dashboard_after_test(test_name, rep.outcome)
        elif rep.outcome == "skipped":
            skip_reason = str(rep.longrepr) if rep.longrepr else "Test skipped"
            elapsed = rep.duration if hasattr(rep, 'duration') else None
            test_logger.log_test_end(test_name, "SKIP", message=skip_reason, elapsed=elapsed)
            # Force flush to ensure log is written immediately
            import logging
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Dashboard refresh disabled for speed - only refresh at session end
            # _refresh_dashboard_after_test(test_name, rep.outcome)


@pytest.fixture(autouse=True)
def log_test_start_end(request):
    """Automatically log test start and end and ensure test isolation"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    # Log test start
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else None
    test_logger.log_test_start(test_name, test_file)
    
    # Log which type of test is running (admin vs recruiter) for debugging
    if 'admin_page' in request.fixturenames:
        logger.debug(f"Running ADMIN test: {test_name}")
    elif 'recruiter_page' in request.fixturenames:
        logger.debug(f"Running RECRUITER test: {test_name}")
    
    # Small delay before test starts to ensure previous test cleanup is complete
    time.sleep(0.1)
    
    yield
    
    # Small delay after test completes to ensure cleanup operations finish
    time.sleep(0.2)
    
    # Test end will be logged by pytest_runtest_makereport hook


def pytest_configure(config):
    """
    Ensure suite start is recorded even when this module is loaded late (via pytest_plugins).
    Also detect which test files are being requested for smart isolation.
    """
    global _REQUESTED_TEST_FILES
    
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    stats = test_logger.get_statistics()
    if not stats.get("start_time"):
        suite_name = "JnP benchSale"
        source = str(getattr(config, "rootpath", "")) or None

        def _detect_suite_name() -> str:
            # Prefer requested test files/args to choose suite name
            candidates = []
            if hasattr(config, 'option') and hasattr(config.option, 'file_or_dir') and config.option.file_or_dir:
                candidates.extend([str(p).lower() for p in config.option.file_or_dir])
            if hasattr(config, 'option') and hasattr(config.option, 'args'):
                candidates.extend([str(a).lower() for a in config.option.args])

            for path_str in candidates:
                if "test_employer" in path_str:
                    return "JnP employer"
                if "test_jobseeker" in path_str:
                    return "JnP jobseeker"
                if "test_benchsale_admin" in path_str:
                    return "JnP benchSale Admin"
                if "test_benchsale_recruiter" in path_str:
                    return "JnP benchSale Recruiter"
            return suite_name

        suite_name = _detect_suite_name()
        try:
            test_logger.log_suite_start(suite_name, source)
        except Exception:
            # Never break test run due to logging
            pass
    
    # Smart detection: Identify which test files are being requested
    if hasattr(config, 'option') and hasattr(config.option, 'file_or_dir') and config.option.file_or_dir:
        for path in config.option.file_or_dir:
            path_str = str(path).lower()
            if 'test_benchsale_admin' in path_str:
                _REQUESTED_TEST_FILES.add('admin')
                logger.info(f"🧠 Smart Framework: Admin test file detected: {path}")
            elif 'test_benchsale_recruiter' in path_str:
                _REQUESTED_TEST_FILES.add('recruiter')
                logger.info(f"🧠 Smart Framework: Recruiter test file detected: {path}")
    
    # Also check command line arguments
    if hasattr(config, 'option') and hasattr(config.option, 'args'):
        for arg in config.option.args:
            arg_str = str(arg).lower()
            if 'test_benchsale_admin' in arg_str:
                _REQUESTED_TEST_FILES.add('admin')
            elif 'test_benchsale_recruiter' in arg_str:
                _REQUESTED_TEST_FILES.add('recruiter')
    
    if _REQUESTED_TEST_FILES:
        logger.info(f"🧠 Smart Framework: Test isolation enabled for: {', '.join(_REQUESTED_TEST_FILES)}")


def pytest_collect_file(file_path, parent):
    """
    Smart file collection: Prevent collecting test files that weren't explicitly requested.
    This ensures complete isolation - if you run admin tests, recruiter test files won't even be collected.
    """
    global _REQUESTED_TEST_FILES
    
    file_str = str(file_path).lower()
    file_name = os.path.basename(file_str)
    
    # Smart detection: If a specific test file type was requested, skip the other type
    is_admin_file = 'test_benchsale_admin' in file_name or 'test_benchsale_admin' in file_str
    is_recruiter_file = 'test_benchsale_recruiter' in file_name or 'test_benchsale_recruiter' in file_str
    
    if is_admin_file:
        if 'recruiter' in _REQUESTED_TEST_FILES and 'admin' not in _REQUESTED_TEST_FILES:
            logger.info(f"🧠 Smart Framework: Skipping admin test file - only recruiter tests requested: {file_name}")
            return None  # Don't collect this file
    elif is_recruiter_file:
        if 'admin' in _REQUESTED_TEST_FILES and 'recruiter' not in _REQUESTED_TEST_FILES:
            logger.info(f"🧠 Smart Framework: Skipping recruiter test file - only admin tests requested: {file_name}")
            return None  # Don't collect this file
    
    # Let pytest handle normal collection for other files
    return None


def pytest_collection_modifyitems(config, items):
    """
    Smart test isolation: Automatically filter tests to prevent cross-file interference.
    This intelligent hook detects which test files are actually requested and filters out
    tests from other files to ensure complete isolation.
    """
    global _RUNNING_TEST_TYPE, _REQUESTED_TEST_FILES
    
    # Detect which test files are actually being requested from command line
    if hasattr(config.option, 'file_or_dir') and config.option.file_or_dir:
        for path in config.option.file_or_dir:
            path_str = str(path).lower()
            if 'test_benchsale_admin' in path_str:
                _REQUESTED_TEST_FILES.add('admin')
            elif 'test_benchsale_recruiter' in path_str:
                _REQUESTED_TEST_FILES.add('recruiter')
    
    # Smart detection: Analyze collected items to determine which file type they belong to
    admin_file_items = []
    recruiter_file_items = []
    
    for item in items:
        test_file = str(item.fspath) if hasattr(item, 'fspath') else ""
        test_file_lower = test_file.lower()
        
        if 'test_benchsale_admin' in test_file_lower and 'test_benchsale_recruiter' not in test_file_lower:
            admin_file_items.append(item)
            if not _REQUESTED_TEST_FILES:
                _REQUESTED_TEST_FILES.add('admin')
        elif 'test_benchsale_recruiter' in test_file_lower:
            recruiter_file_items.append(item)
            if not _REQUESTED_TEST_FILES:
                _REQUESTED_TEST_FILES.add('recruiter')
    
    # Categorize collected tests by file AND fixture
    admin_tests = [item for item in items if 'admin_page' in item.fixturenames]
    recruiter_tests = [item for item in items if 'recruiter_page' in item.fixturenames]
    
    # Smart filtering: Use file-based detection for more accurate filtering
    items_to_remove = []
    
    # Determine which type to keep based on file detection (more reliable than fixtures)
    if admin_file_items and not recruiter_file_items:
        # Only admin file items collected - filter out any recruiter tests
        _RUNNING_TEST_TYPE = "admin"
        for item in recruiter_file_items if recruiter_file_items else recruiter_tests:
            if item not in admin_file_items:  # Don't remove if it's in admin file
                items_to_remove.append(item)
                item.add_marker(pytest.mark.skip(reason="🧠 Smart Framework: Auto-filtered - only admin tests requested"))
        logger.info("=" * 80)
        logger.info("🧠 SMART FRAMEWORK: Admin test file detected - auto-filtering recruiter tests")
        logger.info(f"   ✓ Admin tests: {len(admin_file_items)}, ✗ Recruiter tests filtered: {len(recruiter_file_items)}")
        logger.info("=" * 80)
        
    elif recruiter_file_items and not admin_file_items:
        # Only recruiter file items collected - filter out any admin tests
        _RUNNING_TEST_TYPE = "recruiter"
        for item in admin_file_items if admin_file_items else admin_tests:
            if item not in recruiter_file_items:  # Don't remove if it's in recruiter file
                items_to_remove.append(item)
                item.add_marker(pytest.mark.skip(reason="🧠 Smart Framework: Auto-filtered - only recruiter tests requested"))
        logger.info("=" * 80)
        logger.info("🧠 SMART FRAMEWORK: Recruiter test file detected - auto-filtering admin tests")
        logger.info(f"   ✓ Recruiter tests: {len(recruiter_file_items)}, ✗ Admin tests filtered: {len(admin_file_items)}")
        logger.info("=" * 80)
        
    elif 'admin' in _REQUESTED_TEST_FILES and 'recruiter' not in _REQUESTED_TEST_FILES:
        # Explicitly requested admin only
        _RUNNING_TEST_TYPE = "admin"
        for item in recruiter_file_items if recruiter_file_items else recruiter_tests:
            items_to_remove.append(item)
            item.add_marker(pytest.mark.skip(reason="🧠 Smart Framework: Only admin tests requested"))
        logger.info("=" * 80)
        logger.info("🧠 SMART FRAMEWORK: Admin tests explicitly requested - filtering recruiter tests")
        logger.info(f"   Admin tests: {len(admin_file_items)}, Recruiter tests filtered: {len(recruiter_file_items)}")
        logger.info("=" * 80)
        
    elif 'recruiter' in _REQUESTED_TEST_FILES and 'admin' not in _REQUESTED_TEST_FILES:
        # Explicitly requested recruiter only
        _RUNNING_TEST_TYPE = "recruiter"
        for item in admin_file_items if admin_file_items else admin_tests:
            items_to_remove.append(item)
            item.add_marker(pytest.mark.skip(reason="🧠 Smart Framework: Only recruiter tests requested"))
        logger.info("=" * 80)
        logger.info("🧠 SMART FRAMEWORK: Recruiter tests explicitly requested - filtering admin tests")
        logger.info(f"   Recruiter tests: {len(recruiter_file_items)}, Admin tests filtered: {len(admin_file_items)}")
        logger.info("=" * 80)
        
    elif admin_file_items and recruiter_file_items:
        # Both file types collected - warn user
        logger.warning("=" * 80)
        logger.warning(f"⚠️  WARNING: Both admin ({len(admin_file_items)}) and recruiter ({len(recruiter_file_items)}) test files collected!")
        logger.warning("   This may cause test interference.")
        logger.warning("   💡 TIP: Run tests from one file at a time for best isolation")
        logger.warning("=" * 80)
    
    # Remove filtered items
    for item in items_to_remove:
        if item in items:
            items.remove(item)
    
    # Final summary
    if items:
        final_admin = len([i for i in items if i in admin_file_items or 'admin_page' in i.fixturenames])
        final_recruiter = len([i for i in items if i in recruiter_file_items or 'recruiter_page' in i.fixturenames])
        logger.info(f"✓ Final test execution: {len(items)} tests (Admin: {final_admin}, Recruiter: {final_recruiter})")


def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    from utils.test_logger import get_test_logger
    
    # Automatically clean up old timestamped log files before starting tests
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    cleanup_old_logs(log_dir)
    
    test_logger = get_test_logger()
    
    suite_name = "JnP benchSale"
    source = str(session.fspath) if hasattr(session, 'fspath') else None
    test_logger.log_suite_start(suite_name, source)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SESSION STARTED")
    logger.info(f"Session start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    logger.info("")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()
    
    # Get total tests count
    total_tests = len(session.items) if hasattr(session, 'items') else 0
    
    # Get statistics from test logger
    stats = test_logger.get_statistics()
    
    # If test logger has no stats but tests were collected, try to get from pytest's terminal reporter
    # This handles cases where tests were run but not properly logged
    if stats['total'] == 0 and total_tests > 0:
        # Try to get stats from pytest's terminal reporter if available
        try:
            terminal_reporter = getattr(session.config, '_terminalreporter', None)
            if terminal_reporter and hasattr(terminal_reporter, 'stats'):
                stats_summary = terminal_reporter.stats
                if stats_summary:
                    passed = len(stats_summary.get('passed', []))
                    failed = len(stats_summary.get('failed', []))
                    skipped = len(stats_summary.get('skipped', []))
                    test_logger.test_stats['total'] = total_tests
                    test_logger.test_stats['passed'] = passed
                    test_logger.test_stats['failed'] = failed
                    test_logger.test_stats['skipped'] = skipped
                else:
                    # If stats dict exists but is empty, just set total
                    test_logger.test_stats['total'] = total_tests
            else:
                # If terminal reporter not available, just set total
                test_logger.test_stats['total'] = total_tests
        except Exception as e:
            # If we can't get stats from terminal reporter, just set total
            logger.debug(f"Could not get stats from terminal reporter: {e}")
            test_logger.test_stats['total'] = total_tests
    
    suite_name = "JnP benchSale"
    # Defensive: make sure suite start exists even if pytest_sessionstart didn't run for this plugin.
    if not test_logger.get_statistics().get("start_time"):
        try:
            test_logger.log_suite_start(suite_name, str(getattr(session, "fspath", "")) or None)
        except Exception:
            pass
    test_logger.log_suite_end(suite_name)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SESSION FINISHED")
    logger.info(f"Session end time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Exit status: {exitstatus}")
    
    if total_tests > 0:
        logger.info(f"Total tests executed: {total_tests}")
    
    # Log runtime summary
    if runtime_data.get('timings'):
        logger.info("")
        logger.info("RUNTIME SUMMARY:")
        logger.info("-" * 80)
        for test_name, timings in runtime_data['timings'].items():
            if timings:
                total_time = sum(t['elapsed_seconds'] for t in timings)
                logger.info(f"  {test_name}: {total_time:.2f} seconds")
        logger.info("-" * 80)
    
    logger.info("=" * 80)
    logger.info("")
    
    # Write summary to file (overwrite existing)
    summary_file = os.path.join(os.path.dirname(__file__), 'reports', 'test_summary.txt')
    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
    
    # Get statistics from test logger
    stats = test_logger.get_statistics()
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BENCHSALE TEST EXECUTION SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Session end: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Exit status: {exitstatus}\n")
        f.write(f"\nTest Statistics:\n")
        f.write(f"  Total: {stats['total']}\n")
        f.write(f"  Passed: {stats['passed']}\n")
        f.write(f"  Failed: {stats['failed']}\n")
        f.write(f"  Skipped: {stats['skipped']}\n")
        if runtime_data.get('timings'):
            f.write("\nRuntime Summary:\n")
            f.write("-" * 80 + "\n")
            for test_name, timings in runtime_data['timings'].items():
                if timings:
                    total_time = sum(t['elapsed_seconds'] for t in timings)
                    f.write(f"  {test_name}: {total_time:.2f} seconds\n")
        f.write("=" * 80 + "\n")
    logger.info(f"Test summary written to: {summary_file}")
    
    # Cleanup old dummy log files before generating new ones
    try:
        cleanup_old_log_files()
    except Exception as cleanup_err:
        logger.debug(f"Could not cleanup old log files: {cleanup_err}")
    
    # Generate HTML log viewers for all log files (Admin, Recruiter, Main)
    try:
        from utils.log_viewer import generate_html_log_viewer
        from utils.unified_log_viewer import generate_unified_dashboard
        
        log_dir = os.path.dirname(LOG_FILE)
        html_files = []
        
        # Generate HTML for current log file
        if os.path.exists(LOG_FILE):
            html_file = generate_html_log_viewer(LOG_FILE)
            html_files.append(html_file)
            logger.info(f"HTML log viewer generated: {html_file}")
        
        # Generate HTML for admin log if it exists
        admin_log = os.path.join(log_dir, 'benchsale_admin.log')
        if os.path.exists(admin_log):
            admin_html = generate_html_log_viewer(admin_log)
            html_files.append(admin_html)
            logger.info(f"Admin HTML log viewer generated: {admin_html}")
        
        # Generate HTML for recruiter log if it exists
        recruiter_log = os.path.join(log_dir, 'benchsale_recruiter.log')
        if os.path.exists(recruiter_log):
            recruiter_html = generate_html_log_viewer(recruiter_log)
            html_files.append(recruiter_html)
            logger.info(f"Recruiter HTML log viewer generated: {recruiter_html}")
        
        # Generate unified dashboard - ALWAYS run this at session end to ensure dashboard is updated
        # This ensures dashboard updates regardless of how tests were run (UI, command line, etc.)
        try:
            logger.info("Generating unified dashboard at session end...")
            # Minimal wait - just for log flush
            time.sleep(0.1)  # Reduced from 1 second
            dashboard_path = generate_unified_dashboard()
            logger.info(f"✓ Unified dashboard generated successfully: {dashboard_path}")
            html_files.append(dashboard_path)
            
            # Minimal wait - just for file write
            time.sleep(0.1)  # Reduced from 0.5 seconds
            logger.info("Dashboard update complete. UI will show latest status on next refresh.")
        except Exception as dashboard_err:
            logger.error(f"ERROR: Could not generate unified dashboard: {dashboard_err}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Try one more time with refresh script
            try:
                import subprocess
                from pathlib import Path
                project_root = Path(__file__).parent
                refresh_script = project_root / 'refresh_dashboard.py'
                if refresh_script.exists():
                    logger.info("Attempting dashboard refresh via script...")
                    result = subprocess.run(
                        [sys.executable, str(refresh_script)],
                        cwd=project_root,
                        timeout=60,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        logger.info("✓ Dashboard refreshed via script successfully")
                    else:
                        logger.warning(f"Dashboard refresh script returned code {result.returncode}")
            except Exception as script_err:
                logger.error(f"Dashboard refresh script also failed: {script_err}")
        
        # Automatically open unified dashboard in browser
        try:
            import webbrowser
            import threading
            
            # Open the unified dashboard (index.html) automatically after tests
            dashboard_file = os.path.join(log_dir, 'index.html')
            if os.path.exists(dashboard_file):
                dashboard_path = os.path.abspath(dashboard_file)
                # Windows file:// URL format: file:///C:/path/to/file.html
                file_url = f"file:///{dashboard_path.replace(os.sep, '/').replace(' ', '%20')}"
            else:
                # Fallback to first HTML file (admin or recruiter log)
                if html_files:
                    file_path = os.path.abspath(html_files[0])
                    file_url = f"file:///{file_path.replace(os.sep, '/').replace(' ', '%20')}"
                else:
                    logger.warning("No HTML log files found to open")
                    return
            
            # def open_browser():
            #     time.sleep(3)  # Delay to ensure all files are written and dashboard is ready
            #     try:
            #         webbrowser.open(file_url)
            #         logger.info(f"Opened unified dashboard in browser: {file_url}")
            #     except Exception as e:
            #         logger.warning(f"Could not open browser: {e}")
            #         logger.info(f"Please manually open: {file_url}")
            # 
            # # Open in background thread to not block test completion
            # # threading.Thread(target=open_browser, daemon=True).start()
            # # logger.info(f"Dashboard will open automatically in browser: {file_url}")
        except Exception as browser_err:
            logger.debug(f"Could not open browser automatically: {browser_err}")
    except Exception as e:
        logger.warning(f"Could not generate HTML log viewers: {e}")
