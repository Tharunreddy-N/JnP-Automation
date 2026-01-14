"""
Pytest configuration and fixtures for Job Seeker automation tests
Separate conftest for Job Seeker test cases
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
    BASE_URL as JOBSEEKER_URL,
    FAST_MODE,
    MAXIMIZE_BROWSER,
    check_network_connectivity,
    goto_fast,
    start_runtime_measurement,
    end_runtime_measurement,
    logger,
)

# Configure logging for job seeker tests
def _detect_jobseeker_scope() -> str:
    """Detect whether running Job Seeker tests."""
    env_scope = os.getenv("JOBSEEKER_LOG_SCOPE", "").strip().lower()
    if env_scope in ("jobseeker", "js"):
        return env_scope
    argv = " ".join(sys.argv or []).lower()
    if "test_jobseeker_test_cases.py".lower() in argv:
        return "jobseeker"
    return "jobseeker"


def setup_jobseeker_logging():
    """Setup logging configuration for job seeker tests."""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    scope = _detect_jobseeker_scope()
    log_name = "jobseeker.log"
    
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


# Job Seeker credentials - can be overridden via environment variables
JS_EMAIL = os.getenv("JS_EMAIL", "evon@gmail.com")
JS_PASSWORD = os.getenv("JS_PASSWORD", "Evon@1234")
JS_NAME = os.getenv("JS_NAME", "Job Seeker")

# Resume Builder variables for T1.07 test case
RB_JOB_TITLE = os.getenv("RB_JOB_TITLE", "Sr. Python Developer")
RB_PHONE = os.getenv("RB_PHONE", "(469) 731-7955")
RB_SUMMARY = os.getenv("RB_SUMMARY", "Experienced software developer with expertise in Python, JavaScript, and full-stack development. Skilled in building scalable applications and working with modern frameworks.")
RB_PROJECT_TITLE_1 = os.getenv("RB_PROJECT_TITLE_1", "Web development")
RB_PROJECT_ROLE_1 = os.getenv("RB_PROJECT_ROLE_1", "Sr. Python Developer")
RB_PROJECT_ROLES_1 = os.getenv("RB_PROJECT_ROLES_1", "Created Stored Procedures, Functions, Triggers, Tables, Views, SQL joins, and T-SQL, and PL-SQL Queries to implement business rules and created data sets required for Power BI reports and OBIEE reporting. Developed calculated columns and measures using DAX in Power BI.")

# Resume file path for T1.06 test case
# Using PDF file directly: "Deepika Kashni.pdf"
# Get the absolute path to ensure it works from any directory
_project_root = Path(__file__).parent.absolute()
DEFAULT_RESUME_PATH = str(_project_root / "Deepika Kashni.pdf")
# Allow overriding from environment. Tests may generate a resume dynamically at runtime.
RESUME_PATH = os.getenv("RESUME_PATH", DEFAULT_RESUME_PATH)

# Storage state paths
AUTH_DIR = os.path.join(os.path.dirname(__file__), '.auth')
os.makedirs(AUTH_DIR, exist_ok=True)
JOBSEEKER_STATE_PATH = os.path.join(AUTH_DIR, "jobseeker.storage_state.json")


def login_jobseeker_pw(page, user_id=JS_EMAIL, password=JS_PASSWORD):
    """Login to Job Seeker using Playwright"""
    from utils.test_logger import get_test_logger
    test_logger = get_test_logger()

    test_logger.log_keyword_start("Login credentials for Job Seeker")
    start_time = time.time()
    try:
        # Some builds have a toggle between Employer/JobSeeker on Login.
        # Click it if present to ensure JobSeeker form is active.
        try:
            tgl = page.locator(".css-1hw9j7s").first
            if tgl.count() > 0 and tgl.is_visible(timeout=2000):
                tgl.click()
                page.wait_for_timeout(300)
        except Exception:
            pass

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
            "xpath=/html/body/div[1]/div[2]/div[2]/div/div[2]/div/form/div/button",
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
        page.wait_for_timeout(1500)

        # Verify login actually succeeded (sometimes click returns but session stays on Login).
        # Accept either URL change away from /Login or dashboard navigation presence.
        try:
            page.wait_for_url(lambda url: "Login" not in url, timeout=20000)
        except Exception:
            pass
        try:
            # If we are still on login, surface any visible error/toast before failing.
            if "Login" in (page.url or ""):
                err = ""
                try:
                    toast = page.locator(".Toastify, [class*='Toastify']").first
                    if toast.count() > 0 and toast.is_visible(timeout=1000):
                        err = (toast.inner_text() or "").strip()
                except Exception:
                    pass
                raise PWTimeoutError(f"Login did not complete; still on {page.url}. {('Toast: ' + err) if err else ''}".strip())
        except Exception:
            raise

        try:
            page.on("dialog", lambda dialog: dialog.accept())
        except Exception:
            pass

        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Job Seeker", "PASS", elapsed=elapsed)
        logger.info("Logged in to Job Seeker successfully (Playwright)")
    except Exception as e:
        elapsed = time.time() - start_time
        test_logger.log_keyword_end("Login credentials for Job Seeker", "FAIL", elapsed=elapsed)
        logger.error(f"Error during Playwright job seeker login: {e}")
        raise


def ensure_jobseeker_storage_state(pw_browser) -> str:
    """Create/reuse job seeker storage_state using JOBSEEKER credentials only."""
    if os.path.exists(JOBSEEKER_STATE_PATH) and os.path.getsize(JOBSEEKER_STATE_PATH) > 0:
        try:
            with open(JOBSEEKER_STATE_PATH, 'r') as f:
                data = json.load(f)
                if data and 'cookies' in data and len(data.get('cookies', [])) > 0:
                    return JOBSEEKER_STATE_PATH
        except Exception:
            pass
        try:
            os.remove(JOBSEEKER_STATE_PATH)
        except Exception:
            pass

    # When maximized, use None for viewport to match actual screen size
    viewport_size = None
    context = pw_browser.new_context(ignore_https_errors=True, viewport=viewport_size)
    context.set_default_timeout(30000)
    
    # Clear all cookies to ensure fresh session
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session in ensure_jobseeker_storage_state")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()

    try:
        # Try navigating to Dashboard first - if not logged in, it should redirect to Login
        goto_fast(page, f"{JOBSEEKER_URL}Jsdashboard")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(500 if FAST_MODE else 1000)
        
        # Check if we are on login page (redirected) or dashboard
        if "Jsdashboard" in page.url:
            # Already logged in?
            try:
                # Wait for dashboard navigation menu or account summary
                page.locator("xpath=/html/body/div[1]/div[2]/nav/div/div/div/ul/li[1]/div").wait_for(timeout=5000)
                logger.info("Accessing Jsdashboard was successful (already logged in?)")
                context.storage_state(path=JOBSEEKER_STATE_PATH)
                return JOBSEEKER_STATE_PATH
            except Exception:
                pass

        # If redirected to Home, go to Login
        if page.url.rstrip('/') == JOBSEEKER_URL.rstrip('/'):
             logger.debug("Redirected to Home during state creation. Going to Login...")
             goto_fast(page, f"{JOBSEEKER_URL}Login")
             page.wait_for_timeout(1000)

        # Check for toggle and click if present (Login page)
        try:
            tgl = page.locator(".css-1hw9j7s")
            if tgl.count() > 0 and tgl.first.is_visible():
                tgl.first.click()
                page.wait_for_timeout(200 if FAST_MODE else 300)
            elif "Login" in page.url:
                 tgl.wait_for(state="visible", timeout=2000)
                 tgl.click()
                 page.wait_for_timeout(200 if FAST_MODE else 300)
        except Exception:
            pass

        # If we are not on login page, force navigation to Login if needed
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() == 0 or not login_indicator.first.is_visible():
             logger.debug("Not on login page, navigating to Login...")
             goto_fast(page, f"{JOBSEEKER_URL}Login")
             page.wait_for_timeout(1000)
        
        # Re-check if we are on Dashboard (redirected from Login)
        if "Jsdashboard" in page.url: 
             try:
                 page.locator("xpath=/html/body/div[1]/div[2]/nav/div/div/div/ul/li[1]/div").wait_for(timeout=5000)
                 logger.info("Redirected to Jsdashboard from Login content (already logged in)")
                 context.storage_state(path=JOBSEEKER_STATE_PATH)
                 return JOBSEEKER_STATE_PATH
             except:
                 pass

        # Only login if inputs are found
        if login_indicator.count() > 0 and login_indicator.first.is_visible():
            login_jobseeker_pw(page, user_id=JS_EMAIL, password=JS_PASSWORD)
        elif "Login" in page.url:
            try:
                login_jobseeker_pw(page, user_id=JS_EMAIL, password=JS_PASSWORD)
            except Exception:
                logger.warning("Failed to login on Login page (inputs likely missing)")
        
        # Wait for dashboard to load
        try:
            page.locator("xpath=/html/body/div[1]/div[2]/nav/div/div/div/ul/li[1]/div").wait_for(timeout=30000)
        except Exception:
            pass
        context.storage_state(path=JOBSEEKER_STATE_PATH)
    finally:
        try:
            context.close()
        except Exception:
            pass
        try:
            time.sleep(0.3)
        except Exception:
            pass
    
    return JOBSEEKER_STATE_PATH


# Setup logging on import
setup_jobseeker_logging()

# Import browser fixture from main conftest
from BenchSale_Conftest import pw_browser


@pytest.fixture(scope="function")
def jobseeker_page(pw_browser, request):
    """
    Authenticated Job Seeker page fixture with smart isolation.
    
    Each test gets a fresh, isolated context to prevent test interference.
    """
    test_name = request.node.name
    test_file = str(request.node.fspath) if hasattr(request.node, 'fspath') else ""
    
    # Auto-skip if this is not a job seeker test file
    if 'test_jobseeker' not in test_file.lower():
        pytest.skip(f"🧠 Smart Framework: JobSeeker fixture auto-skipped for non-jobseeker test: {test_name}")
    
    logger.debug(f"Creating jobseeker_page fixture for test: {test_name}")
    
    state_path = ensure_jobseeker_storage_state(pw_browser)
    viewport_size = None
    context = pw_browser.new_context(
        ignore_https_errors=True,
        viewport=viewport_size,
        storage_state=state_path,
    )
    context.set_default_timeout(15000 if FAST_MODE else 30000)
    
    # Clear all cookies to ensure fresh session at every test run
    try:
        context.clear_cookies()
        logger.debug("Cleared all cookies for fresh session (jobseeker)")
    except Exception as e:
        logger.debug(f"Error clearing cookies: {e}")
    
    page = context.new_page()
    
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
    
    # Navigate and verify authentication (fast)
    goto_fast(page, f"{JOBSEEKER_URL}Jsdashboard")
    page.wait_for_load_state("domcontentloaded", timeout=10000)
    page.wait_for_timeout(300 if FAST_MODE else 500)
    
    # Ensure we are actually on the dashboard or login page
    if "Jsdashboard" not in page.url:
        logger.debug(f"Not on Dashboard (URL: {page.url}). Checking for login redirection or Home page...")
        
        # Check if we got redirected to Home
        if page.url.rstrip('/') == JOBSEEKER_URL.rstrip('/'):
             logger.debug("Redirected to Home. Session likely expired/invalid. Navigating to Login to re-authenticate...")
             goto_fast(page, f"{JOBSEEKER_URL}Login")
             page.wait_for_timeout(1000)
    
    # Quick check if redirected to login page (or we navigated there above)
    try:
        login_indicator = page.locator("input[name='email'], input[type='email'], [id=':r0:']")
        if login_indicator.count() > 0 and login_indicator.first.is_visible(timeout=3000):
            logger.debug("On Login page. Re-logging in...")
            try:
                tgl = page.locator(".css-1hw9j7s")
                if tgl.count() and tgl.first.is_visible():
                    tgl.first.click()
                    page.wait_for_timeout(200 if FAST_MODE else 300)
            except Exception:
                pass
            login_jobseeker_pw(page, user_id=JS_EMAIL, password=JS_PASSWORD)
            page.wait_for_timeout(1000 if FAST_MODE else 1500)
            context.storage_state(path=JOBSEEKER_STATE_PATH)
            
            # Post-login verification
            page.wait_for_timeout(2000)
            if "Jsdashboard" not in page.url:
                 logger.debug(f"Still not on Dashboard after login (URL: {page.url}). Navigating...")
                 goto_fast(page, f"{JOBSEEKER_URL}Jsdashboard")
    except Exception as e:
        logger.debug(f"Login check exception: {e}")
    
    # Final check
    if "Jsdashboard" not in page.url:
         logger.warning(f"Final warning: Fixture yielding page at {page.url}, expected Jsdashboard")

    # Quick wait for dashboard (non-blocking)
    try:
        page.locator("xpath=/html/body/div[1]/div[2]/nav/div/div/div/ul/li[1]/div").wait_for(timeout=5000)
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
        context.storage_state(path=JOBSEEKER_STATE_PATH)
    except Exception as e:
        logger.debug(f"Error during jobseeker_page cleanup: {e}")
    finally:
        try:
            context.close()
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Error closing context: {e}")
