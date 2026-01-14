"""
Pytest configuration and fixtures for Employer automation tests
Separate conftest for Employer test cases (Employer1 and Employer2)
"""
import pytest
import time
import logging
import os
import sys
import json
from pathlib import Path
from playwright.sync_api import Page as PWPage, TimeoutError as PWTimeoutError

# Import common utilities from main conftest
sys.path.insert(0, str(Path(__file__).parent))
from BenchSale_Conftest import (
    BASE_URL as EMPLOYER_URL,
    FAST_MODE,
    MAXIMIZE_BROWSER,
    check_network_connectivity,
    goto_fast,
    start_runtime_measurement,
    end_runtime_measurement,
    logger,
)

# Configure logging for employer tests
def _detect_employer_scope() -> str:
    """Detect whether running Employer tests."""
    env_scope = os.getenv("EMPLOYER_LOG_SCOPE", "").strip().lower()
    if env_scope in ("employer1", "employer2", "employer"):
        return env_scope
    argv = " ".join(sys.argv or []).lower()
    if "test_employer_test_cases.py".lower() in argv:
        return "employer"
    return "employer"


def setup_employer_logging():
    """Setup logging configuration for employer tests."""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    scope = _detect_employer_scope()
    log_name = "employer.log"
    
    log_file = os.path.join(log_dir, log_name)
    
    file_formatter = logging.Formatter('%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
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
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return log_file


# Employer credentials
EMP1_ID = "automationtest@adamitcorp.com"
EMP1_PASSWORD = "Welcome@123"
EMP1_NAME = "Employer 1"

EMP2_ID = "employer2@adamitcorp.com"  # Update with actual employer2 email
EMP2_PASSWORD = "Welcome@123"  # Update with actual employer2 password
EMP2_NAME = "Employer 2"

# Storage state paths
AUTH_DIR = os.path.join(os.path.dirname(__file__), '.auth')
os.makedirs(AUTH_DIR, exist_ok=True)
EMPLOYER1_STATE_PATH = os.path.join(AUTH_DIR, "employer1.storage_state.json")
EMPLOYER2_STATE_PATH = os.path.join(AUTH_DIR, "employer2.storage_state.json")


def login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD):
    """Login to Employer1 using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()

    test_logger.log_keyword_start("Login credentials for Employer1")
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

        page.wait_for_timeout(1000)
        # Try multiple selectors for login button
        login_button = None
        button_selectors = [
            "xpath=/html/body/div/div[2]/main/div/form/button",
            "xpath=//*[@id='root']/div[2]/div[2]/div/div[1]/div/form/div/button",
            "id=theme-button",
            "button[type='submit']",
            "xpath=//button[contains(text(),'Sign')]",
        ]
        for sel in button_selectors:
            try:
                login_button = page.locator(sel)
                if login_button.is_visible(timeout=5000):
                    login_button.click()
                    break
            except Exception:
                continue
        if not login_button or not login_button.is_visible():
            raise PWTimeoutError("Login button not found")
        page.wait_for_timeout(2000)

        try:
            page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass

        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Employer1", "PASS", elapsed=elapsed)
        logger.info("Logged in to Employer1 successfully (Playwright)")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Employer1", "FAIL", elapsed=elapsed)
        logger.error(f"Error during Playwright employer1 login: {e}")
        raise


def login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD):
    """Login to Employer2 using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()

    test_logger.log_keyword_start("Login credentials for Employer2")
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

        page.wait_for_timeout(1000)
        # Try multiple selectors for login button
        login_button = None
        button_selectors = [
            "xpath=/html/body/div/div[2]/main/div/form/button",
            "xpath=//*[@id='root']/div[2]/div[2]/div/div[1]/div/form/div/button",
            "id=theme-button",
            "button[type='submit']",
            "xpath=//button[contains(text(),'Sign')]",
        ]
        for sel in button_selectors:
            try:
                login_button = page.locator(sel)
                if login_button.is_visible(timeout=5000):
                    login_button.click()
                    break
            except Exception:
                continue
        if not login_button or not login_button.is_visible():
            raise PWTimeoutError("Login button not found")
        page.wait_for_timeout(2000)

        try:
            page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass

        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Employer2", "PASS", elapsed=elapsed)
        logger.info("Logged in to Employer2 successfully (Playwright)")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Employer2", "FAIL", elapsed=elapsed)
        logger.error(f"Error during Playwright employer2 login: {e}")
        raise


def _maximize_browser_window(page, context_name="employer"):
    """Maximize browser window using Windows API - ULTRA RELIABLE method"""
    if not MAXIMIZE_BROWSER:
        return False
    
    import subprocess
    import time
    
    # ULTRA RELIABLE PowerShell - finds Chrome by ANY method and maximizes
    maximize_cmd = '''
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Text;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        [DllImport("user32.dll")]
        public static extern int GetClassName(IntPtr hWnd, StringBuilder sb, int nMaxCount);
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int nMaxCount);
    }
"@
    $SW_MAXIMIZE = 3
    $count = 0
    [Win32]::EnumWindows({
        param($hWnd, $lParam)
        if ([Win32]::IsWindowVisible($hWnd)) {
            $sbClass = New-Object System.Text.StringBuilder 256
            $sbTitle = New-Object System.Text.StringBuilder 512
            [Win32]::GetClassName($hWnd, $sbClass, $sbClass.Capacity) | Out-Null
            [Win32]::GetWindowText($hWnd, $sbTitle, $sbTitle.Capacity) | Out-Null
            $class = $sbClass.ToString()
            $title = $sbTitle.ToString()
            # Match Chrome windows - try multiple class names and title patterns
            if ($class -eq "Chrome_WidgetWin_1" -or 
                $class -like "*Chrome*" -or 
                $title -like "*Chrome*" -or 
                $title -like "*jobsnprofiles*" -or
                $title -like "*Browse*" -or
                $title -like "*USA IT Jobs*" -or
                $title -like "*JobS*") {
                [Win32]::ShowWindow($hWnd, $SW_MAXIMIZE) | Out-Null
                $count++
            }
        }
        return $true
    }, [IntPtr]::Zero)
    Write-Output "OK:$count"
    '''
    
    # Try to maximize - with proper delays and multiple attempts
    max_attempts = 8
    for attempt in range(max_attempts):
        try:
            # Wait for window to be ready (longer wait on first few attempts)
            if attempt == 0:
                wait_time = 1500  # First attempt - give it a moment to appear
            elif attempt < 3:
                wait_time = 1500  # Next few attempts
            else:
                wait_time = 1000  # Later attempts
            page.wait_for_timeout(wait_time)
            
            # Execute PowerShell command
            result = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', maximize_cmd],
                timeout=12,
                capture_output=True,
                text=True
            )
            
            # Check result
            if result.returncode == 0:
                output = result.stdout.strip()
                if "OK:" in output:
                    count_str = output.split(":")[1] if ":" in output else "0"
                    try:
                        count = int(count_str)
                        if count > 0:
                            logger.info(f"✓ Browser maximized successfully ({context_name}) - {count} window(s) maximized on attempt {attempt + 1}")
                            page.wait_for_timeout(1200)  # Wait for maximize animation
                            return True
                        elif attempt < max_attempts - 1:
                            logger.debug(f"Attempt {attempt + 1}/{max_attempts}: Found {count} Chrome windows, retrying...")
                    except ValueError:
                        logger.debug(f"Attempt {attempt + 1}: Invalid count format: {count_str}")
                else:
                    logger.debug(f"Attempt {attempt + 1}: Unexpected output: {output[:50]}")
            
            # Wait before next attempt
            if attempt < max_attempts - 1:
                page.wait_for_timeout(800)
                
        except subprocess.TimeoutExpired:
            logger.debug(f"Attempt {attempt + 1}: PowerShell timeout")
            if attempt < max_attempts - 1:
                page.wait_for_timeout(800)
        except Exception as e:
            logger.debug(f"Attempt {attempt + 1} error: {str(e)[:100]}")
            if attempt < max_attempts - 1:
                page.wait_for_timeout(800)
    
    # Fallback: Maximize the foreground/active window (simpler method)
    logger.debug(f"Trying foreground window maximize fallback ({context_name})")
    try:
        # Bring page to front first
        page.bring_to_front()
        page.wait_for_timeout(800)
        
        # Simple PowerShell to maximize foreground window
        fallback_cmd = '''
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32 {
            [DllImport("user32.dll")]
            public static extern IntPtr GetForegroundWindow();
            [DllImport("user32.dll")]
            public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        }
"@
        $SW_MAXIMIZE = 3
        $hwnd = [Win32]::GetForegroundWindow()
        if ($hwnd -ne [IntPtr]::Zero) {
            [Win32]::ShowWindow($hwnd, $SW_MAXIMIZE) | Out-Null
            Write-Output "OK"
        } else {
            Write-Output "FAIL"
        }
        '''
        
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', fallback_cmd],
            timeout=5,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and "OK" in result.stdout:
            logger.info(f"✓ Browser maximized via foreground window method ({context_name})")
            page.wait_for_timeout(1000)
            return True
    except Exception as e:
        logger.debug(f"Foreground window maximize failed: {e}")
    
    logger.warning(f"⚠ Could not maximize browser after {max_attempts} attempts + fallback ({context_name})")
    return False


def ensure_employer1_storage_state(pw_browser) -> str:
    """Create/reuse employer1 storage_state using EMPLOYER1 credentials only."""
    if os.path.exists(EMPLOYER1_STATE_PATH) and os.path.getsize(EMPLOYER1_STATE_PATH) > 0:
        try:
            with open(EMPLOYER1_STATE_PATH, 'r') as f:
                data = json.load(f)
                if data and 'cookies' in data and len(data.get('cookies', [])) > 0:
                    return EMPLOYER1_STATE_PATH
        except Exception:
            pass
        try:
            os.remove(EMPLOYER1_STATE_PATH)
        except Exception:
            pass

    # When maximized, use None for viewport to match actual screen size
    # Always use window size to prevent small viewport
    viewport_size = None
    context = pw_browser.new_context(ignore_https_errors=True, viewport=viewport_size)
    context.set_default_timeout(30000)
    
    # Clear all cookies to ensure fresh session
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session in ensure_employer1_storage_state")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()

    try:
        # Try navigating to Dashboard first - if not logged in, it should redirect to Login
        # This avoids potential issues where accessing EmpLogin directly redirects to Home
        goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        page.wait_for_load_state("domcontentloaded", timeout=10000)  # Faster
        page.wait_for_timeout(500 if FAST_MODE else 1000)  # Reduced wait
        
        # Check if we are on login page (redirected) or dashboard
        if "Empdashboard" in page.url:
            # Already logged in?
            try:
                page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)
                logger.info("Accessing Empdashboard was successful (already logged in?)")
                context.storage_state(path=EMPLOYER1_STATE_PATH)
                return EMPLOYER1_STATE_PATH
            except Exception:
                # On dashboard url but menu not found? might be loading or weird state
                pass

        # If redirected to Home, go to Login
        if page.url.rstrip('/') == EMPLOYER_URL.rstrip('/'):
             logger.debug("Redirected to Home during state creation. Going to Login...")
             goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
             page.wait_for_timeout(1000)

        # Check for toggle and click if present (Login page)
        try:
            tgl = page.locator(".css-1hw9j7s")
            # Wait briefly to see if it appears
            if tgl.count() > 0 and tgl.first.is_visible():
                tgl.first.click()
                page.wait_for_timeout(200 if FAST_MODE else 300)
            elif "EmpLogin" in page.url: # If on login URL but element not found instantly
                 tgl.wait_for(state="visible", timeout=2000)
                 tgl.click()
                 page.wait_for_timeout(200 if FAST_MODE else 300)
        except Exception:
            pass

        # If we are not on login page, force navigation to EmpLogin if needed, 
        # but prefer handling the redirect or using login buttons
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() == 0 or not login_indicator.first.is_visible():
             logger.debug("Not on login page, clicking login or navigating...")
             # Try navigating explicitly if not redirected
             goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
             page.wait_for_timeout(1000)
        
        # Re-check if we are on Dashboard (redirected from EmpLogin)
        if "Empdashboard" in page.url: 
             try:
                 page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)
                 logger.info("Redirected to Empdashboard from Login content (already logged in)")
                 context.storage_state(path=EMPLOYER1_STATE_PATH)
                 return EMPLOYER1_STATE_PATH
             except:
                 pass

        # Only login if inputs are found
        if login_indicator.count() > 0 and login_indicator.first.is_visible():
            login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD)
        elif "EmpLogin" in page.url:
            # Maybe inputs are loading
            try:
                login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD)
            except Exception:
                logger.warning("Failed to login on EmpLogin page (inputs likely missing)")
        
        try:
            page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=30000)  # Reduced from 60000
        except Exception:
            pass
        context.storage_state(path=EMPLOYER1_STATE_PATH)
    finally:
        try:
            context.close()
        except Exception:
            pass
        try:
            time.sleep(0.3)
        except Exception:
            pass
    
    return EMPLOYER1_STATE_PATH


def ensure_employer2_storage_state(pw_browser) -> str:
    """Create/reuse employer2 storage_state using EMPLOYER2 credentials only."""
    if os.path.exists(EMPLOYER2_STATE_PATH) and os.path.getsize(EMPLOYER2_STATE_PATH) > 0:
        try:
            with open(EMPLOYER2_STATE_PATH, 'r') as f:
                data = json.load(f)
                if data and 'cookies' in data and len(data.get('cookies', [])) > 0:
                    return EMPLOYER2_STATE_PATH
        except Exception:
            pass
        try:
            os.remove(EMPLOYER2_STATE_PATH)
        except Exception:
            pass

    # When maximized, use None for viewport to match actual screen size
    # Always use window size to prevent small viewport
    viewport_size = None
    context = pw_browser.new_context(ignore_https_errors=True, viewport=viewport_size)
    context.set_default_timeout(30000)
    
    # Clear all cookies to ensure fresh session
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session in ensure_employer2_storage_state")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()

    try:
        # Try navigating to Dashboard first
        goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        page.wait_for_load_state("domcontentloaded", timeout=10000)  # Faster
        page.wait_for_timeout(500 if FAST_MODE else 1000)  # Reduced wait
        
        # Check if we are on login page (redirected) or dashboard
        if "Empdashboard" in page.url:
             try:
                page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)
                context.storage_state(path=EMPLOYER2_STATE_PATH)
                return EMPLOYER2_STATE_PATH
             except Exception:
                pass

        try:
            tgl = page.locator(".css-1hw9j7s")
            if tgl.count() and tgl.first.is_visible():
                tgl.first.click()
                page.wait_for_timeout(200 if FAST_MODE else 300)  # Reduced wait
        except Exception:
            pass

        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() == 0 or not login_indicator.first.is_visible():
             goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
             page.wait_for_timeout(1000)

        # Re-check if we are on Dashboard (redirected from EmpLogin)
        if "Empdashboard" in page.url:
             try:
                page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)
                context.storage_state(path=EMPLOYER2_STATE_PATH)
                return EMPLOYER2_STATE_PATH
             except Exception:
                pass

        # Only login if inputs are found
        if login_indicator.count() > 0 and login_indicator.first.is_visible():
            login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD)
        elif "EmpLogin" in page.url:
             try:
                 login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD)
             except Exception:
                 pass
                 
        try:
            page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=30000)  # Reduced from 60000
        except Exception:
            pass
        context.storage_state(path=EMPLOYER2_STATE_PATH)
    finally:
        try:
            context.close()
        except Exception:
            pass
        try:
            time.sleep(0.3)
        except Exception:
            pass
    
    return EMPLOYER2_STATE_PATH


# Setup logging on import
setup_employer_logging()

# Import browser fixture from main conftest
from BenchSale_Conftest import pw_browser


@pytest.fixture(scope="function")
def employer1_page(pw_browser, request):
    """
    Authenticated Employer1 page fixture with smart isolation.
    
    Each test gets a fresh, isolated context to prevent test interference.
    """
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    
    # Auto-skip if this is not an employer test file
    if 'test_employer' not in test_file.lower():
        pytest.skip(f"🧠 Smart Framework: Employer1 fixture auto-skipped for non-employer test: {test_name}")
    
    logger.debug(f"Creating employer1_page fixture for test: {test_name}")
    
    # Create fresh context WITHOUT storage_state to ensure clean start
    # When maximized, use None for viewport to match actual screen size
    # Always use window size to prevent small viewport
    viewport_size = None
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport=viewport_size,
        # Don't use storage_state - we want fresh login every time
    )
    context.set_default_timeout(15000 if FAST_MODE else 30000)
    
    # Clear all cookies to ensure fresh session at every test run
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session (employer1)")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()
    
    # Use our robust maximization helper
    if MAXIMIZE_BROWSER:
        logger.debug("Attempting to maximize employer1 browser window...")
        # _maximize_browser_window(page, "employer1")  # Disabled to improve speed, relying on --start-maximized
    
    # Close any popup pages
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
    
    # ALWAYS start with EmpLogin first - don't go to dashboard directly
    # This ensures we have a clean login flow and avoid Jsdashboard redirects
    logger.debug("Navigating to EmpLogin for fresh employer login...")
    goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    page.wait_for_timeout(1000)
    
    # Handle theme toggle if present
    try:
        tgl = page.locator(".css-1hw9j7s")
        if tgl.count() > 0 and tgl.first.is_visible(timeout=2000):
            tgl.first.click()
            page.wait_for_timeout(200 if FAST_MODE else 300)
    except Exception:
        pass
    
    # Perform fresh login
    try:
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() > 0 and login_indicator.first.is_visible(timeout=5000):
            logger.debug("On EmpLogin page. Performing fresh login...")
            login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD)
            page.wait_for_timeout(2000 if FAST_MODE else 3000)
            
            # Verify we're on Empdashboard, not Jsdashboard
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            if "Jsdashboard" in page.url:
                logger.warning(f"WARNING: Redirected to Jsdashboard after login! URL: {page.url}")
                logger.debug("Navigating to EmpLogin again to retry...")
                goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
                page.wait_for_timeout(1000)
                login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD)
                page.wait_for_timeout(2000)
            
            # Navigate to Empdashboard after successful login
            if "Empdashboard" not in page.url:
                logger.debug(f"Not on Empdashboard after login (URL: {page.url}). Navigating to Empdashboard...")
                goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
        else:
            # If already logged in (no login inputs), navigate to dashboard
            logger.debug("Login inputs not found, might already be logged in. Navigating to Empdashboard...")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(1000)
    except Exception as e:
        logger.debug(f"Login flow exception: {e}, navigating to Empdashboard...")
        goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
    
    # Final verification - ensure we're on Empdashboard, not Jsdashboard
    if "Jsdashboard" in page.url:
        logger.error(f"ERROR: Still on Jsdashboard! URL: {page.url}. This should not happen for employer tests.")
        # Force navigate to EmpLogin and retry
        goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
        page.wait_for_timeout(1000)
        try:
            login_employer1_pw(page, user_id=EMP1_ID, password=EMP1_PASSWORD)
            page.wait_for_timeout(2000)
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        except Exception:
            pass
    
    # Final check
    if "Empdashboard" not in page.url:
         logger.warning(f"Final warning: Fixture yielding page at {page.url}, expected Empdashboard")

    # Quick wait for dashboard (non-blocking - don't wait full 60s)
    try:
        page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)  # Reduced from 60000 to 5000
    except Exception:
        pass  # Continue even if dashboard not fully loaded - test will navigate anyway
    
    yield page
    
    # Cleanup
    try:
        page.wait_for_timeout(500)
        for p in context.pages:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
        context.storage_state(path=EMPLOYER1_STATE_PATH)
    except Exception as e:
        logger.debug(f"Error during employer1_page cleanup: {e}")
    finally:
        try:
            context.close()
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")


@pytest.fixture(scope="function")
def employer2_page(pw_browser, request):
    """
    Authenticated Employer2 page fixture with smart isolation.
    
    Each test gets a fresh, isolated context to prevent test interference.
    """
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    
    # Auto-skip if this is not an employer test file
    if 'test_employer' not in test_file.lower():
        pytest.skip(f"🧠 Smart Framework: Employer2 fixture auto-skipped for non-employer test: {test_name}")
    
    logger.debug(f"Creating employer2_page fixture for test: {test_name}")
    
    # Create fresh context WITHOUT storage_state to ensure clean start
    # When maximized, use None for viewport to match actual screen size
    # Always use window size to prevent small viewport
    viewport_size = None
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport=viewport_size,
        # Don't use storage_state - we want fresh login every time
    )
    context.set_default_timeout(15000 if FAST_MODE else 30000)
    
    # Clear all cookies to ensure fresh session at every test run
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session (employer2)")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()
    
    # Use our robust maximization helper
    if MAXIMIZE_BROWSER:
        logger.debug("Attempting to maximize employer2 browser window...")
        _maximize_browser_window(page, "employer2")
    
    # Close any popup pages
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
    
    # ALWAYS start with EmpLogin first - don't go to dashboard directly
    # This ensures we have a clean login flow and avoid Jsdashboard redirects
    logger.debug("Navigating to EmpLogin for fresh employer login...")
    goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    page.wait_for_timeout(1000)
    
    # Handle theme toggle if present
    try:
        tgl = page.locator(".css-1hw9j7s")
        if tgl.count() > 0 and tgl.first.is_visible(timeout=2000):
            tgl.first.click()
            page.wait_for_timeout(200 if FAST_MODE else 300)
    except Exception:
        pass
    
    # Perform fresh login
    try:
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() > 0 and login_indicator.first.is_visible(timeout=5000):
            logger.debug("On EmpLogin page. Performing fresh login...")
            login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD)
            page.wait_for_timeout(2000 if FAST_MODE else 3000)
            
            # Verify we're on Empdashboard, not Jsdashboard
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            if "Jsdashboard" in page.url:
                logger.warning(f"WARNING: Redirected to Jsdashboard after login! URL: {page.url}")
                logger.debug("Navigating to EmpLogin again to retry...")
                goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
                page.wait_for_timeout(1000)
                login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD)
                page.wait_for_timeout(2000)
            
            # Navigate to Empdashboard after successful login
            if "Empdashboard" not in page.url:
                logger.debug(f"Not on Empdashboard after login (URL: {page.url}). Navigating to Empdashboard...")
                goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
        else:
            # If already logged in (no login inputs), navigate to dashboard
            logger.debug("Login inputs not found, might already be logged in. Navigating to Empdashboard...")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(1000)
    except Exception as e:
        logger.debug(f"Login flow exception: {e}, navigating to Empdashboard...")
        goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
    
    # Final verification - ensure we're on Empdashboard, not Jsdashboard
    if "Jsdashboard" in page.url:
        logger.error(f"ERROR: Still on Jsdashboard! URL: {page.url}. This should not happen for employer tests.")
        # Force navigate to EmpLogin and retry
        goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
        page.wait_for_timeout(1000)
        try:
            login_employer2_pw(page, user_id=EMP2_ID, password=EMP2_PASSWORD)
            page.wait_for_timeout(2000)
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
        except Exception:
            pass
    
    # Final check
    if "Empdashboard" not in page.url:
         logger.warning(f"Final warning: Fixture yielding page at {page.url}, expected Empdashboard")
    
    # Quick wait for dashboard (non-blocking - don't wait full 60s)
    try:
        page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul").wait_for(timeout=5000)  # Reduced from 60000 to 5000
    except Exception:
        pass  # Continue even if dashboard not fully loaded - test will navigate anyway
    
    yield page
    
    # Cleanup
    try:
        page.wait_for_timeout(500)
        for p in context.pages:
            try:
                if not p.is_closed():
                    p.close()
            except Exception:
                pass
        context.storage_state(path=EMPLOYER2_STATE_PATH)
    except Exception as e:
        logger.debug(f"Error during employer2_page cleanup: {e}")
    finally:
        try:
            context.close()
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")
