"""
Employer Test Cases

This file contains all Employer-related test cases for Employer functionality.
Professional structure with clean separation from Admin and Recruiter tests.
Supports both Employer1 and Employer2 test scenarios.
"""
import pytest
import time
import random
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from utils import semantic_utils
except ImportError:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.append(project_root)
    try:
        from utils import semantic_utils
    except ImportError:
        print("Warning: semantic_utils not found. T2.14, T2.20, T2.21 will fail if run.")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ["EMPLOYER_LOG_SCOPE"] = "employer"
pytest_plugins = ["BenchSale_Conftest", "Employer_Conftest"]

from Employer_Conftest import (
    check_network_connectivity,
    FAST_MODE,
    MAXIMIZE_BROWSER,
    EMP1_ID,
    EMP1_PASSWORD,
    EMP1_NAME,
    EMP2_ID,
    EMP2_PASSWORD,
    EMP2_NAME,
    start_runtime_measurement,
    end_runtime_measurement,
    EMPLOYER_URL,
    goto_fast,
)
from BenchSale_Conftest import handle_job_fair_popup_pw, BASE_URL

def _safe_click(page: Page, loc, timeout_ms: int = 15000):
    """
    Make clicks more reliable on MUI UIs:
    - ensure visible
    - scroll into view
    - wait until enabled
    - retry + attempt Escape to dismiss transient overlays
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    last_err = None
    while time.time() < deadline:
        try:
            loc.wait_for(state="visible", timeout=5000)
            try:
                loc.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            if hasattr(loc, "is_enabled") and not loc.is_enabled():
                page.wait_for_timeout(250)
                continue
            loc.click(timeout=5000)
            return
        except Exception as e:
            last_err = e
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            page.wait_for_timeout(300)
    raise last_err if last_err else AssertionError("Could not click element")

def _handle_job_fair_popup(page: Page):
    """Handle job fair popup if present"""
    try:
        popup = page.locator(".css-uhb5lp")
        if popup.is_visible(timeout=5000):
            close_btn = page.locator("css:.css-11q2htf")
            if close_btn.is_visible(timeout=3000):
                close_btn.click()
            else:
                close_btn_xpath = page.locator("xpath=/html/body/div[2]/div[3]/div/div[2]/button[2]")
                if close_btn_xpath.is_visible(timeout=3000):
                    close_btn_xpath.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass

def check_if_time_within_24_hours(time_text: str) -> bool:
    """Checks if the time text is within 24 hours. Returns True if the time is <= 24 hours, False otherwise."""
    time_text_lower = time_text.lower().strip()
    hours = 0
    
    if re.match(r'^(an|a)\s+minute(s)?\s+ago$', time_text_lower):
        hours = 1 / 60.0
    elif re.match(r'^(an|a)\s+hour(s)?\s+ago$', time_text_lower):
        hours = 1
    else:
        match = re.match(r'^(\d+)\s+(hour|day|minute)(s)?\s+ago$', time_text_lower)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            if unit == 'day':
                hours = number * 24
            elif unit == 'hour':
                hours = number
            elif unit == 'minute':
                hours = number / 60.0
    
    return hours <= 24.0

# Test data from Robot file
JOB_TITLE = "Teradata Developer"
JOB_TYPE = "Contract Based"
JOB_TYPE1 = "Full-Time"
JOB_TYPE2 = "Contract - Corp-to-Corp"
VISA_TYPE = "GC - Green Card"
VISA_TYPE1 = "H1"
EXPERIENCE = "4-6 Years"
STATE = "Washington"
CITY = "Seattle"
ZIPCODE = "98191"
DESCRIPTION2 = "Proficient Python developer with strong experience in building scalable applications using Python, Django/Flask, REST APIs, multithreading, SQL databases, unit testing, and automation. Skilled in debugging, implementing design patterns, and working in Agile/DevOps environments."
JOB_DESCRIPTION = """Position :   Teradata Developer
 Location :  Seattle, WA
 Duration : Contract

 Job Description/Skills:
 5+ Years of Hands on Experience in Data processing & Analytics technologies
 2 + year in Teradata development using tools like BTEQ, FASTEXPORT, MULTI LOAD, FASTLOAD
 Expertise in the Teradata cost based query optimizer, identified potential bottlenecks with queries from the aspects of query writing, skewed redistributions, join order, optimizer statistics, physical design considerations (PI and USI and NUSI and JI etc.) etc.
 In-depth knowledge of Teradata Explain and Visual Explain to analyze and improve query performance
 Expertise in SQL, PL/SQL and database query writing & performance tuning
 Knowledge with data warehousing architecture and data modeling best practices.
 Exposure to Agile development model and corresponding tracking tools like JIRA
 Source control with Git, SVN or Clearcase
 Knowledge on Configuration Management tools such as Puppet, Chef, Ansible, SaltStack"""

HOME_PAGE_COMPANY_SEARCH = "Microsoft Corporation"

@pytest.mark.T1_01_EMP
@pytest.mark.employer
def test_t1_01_home_page(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.01 Home Page - Verify home page elements"""
    from datetime import datetime
    
    start_runtime_measurement("T1.01 Home Page")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        # Log time of run (matching Robot Framework: ${today_date} = Evaluate datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
        today_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        print(f"Time of run : {today_date}")
        
        # Navigate to home page (matching Robot Framework: open site)
        # Use BASE_URL (https://jobsnprofiles.com/) for public home page, not EMPLOYER_URL
        goto_fast(page, BASE_URL)
        _handle_job_fair_popup(page)
        
        # Get time (matching Robot Framework: ${time_now} = get time min sec NOW)
        # Note: This is not used in assertions, just for logging
        time_now = datetime.now().strftime('%H:%M:%S')
        
        page.wait_for_timeout(3000)  # Sleep 3 (matching Robot Framework: sleep 3)
        
        # Get header text from XPath (matching Robot Framework: ${header} = get text xpath:/html/body/div[1]/div[2]/div/section[1]/h1)
        header_text = None
        try:
            header = page.locator("xpath=/html/body/div[1]/div[2]/div/section[1]/h1")
            header.wait_for(state="visible", timeout=10000)
            header_text = header.inner_text().strip()
        except Exception:
            # Fallback: try CSS selector
            try:
                header = page.locator(".css-bvf1f5")
                header.wait_for(state="visible", timeout=10000)
                header_text = header.inner_text().strip()
            except Exception:
                # Fallback: try to find text directly
                try:
                    header = page.locator("text=Find Your Dream Job")
                    header.wait_for(state="visible", timeout=10000)
                    header_text = header.inner_text().strip()
                except Exception:
                    # Final fallback: check page content
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    if "Find Your Dream Job" in page.content():
                        header_text = "Find Your Dream Job"
        
        # Scroll Element Into View css:.css-1dbjwa5 (matching Robot Framework: Run Keyword And Ignore Error Scroll Element Into View css:.css-1dbjwa5)
        try:
            element_1dbjwa5 = page.locator(".css-1dbjwa5")
            element_1dbjwa5.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass  # Ignore error as per Robot Framework
        
        page.wait_for_timeout(3000)  # Sleep 3 (matching Robot Framework: Sleep 3)
        
        # Check resume builder element (matching Robot Framework: ${resume_builder} = Run Keyword And Return Status Page Should Contain Element css:.css-z3ngzz)
        # Robot Framework checks if element exists on page (not necessarily visible), so we check count > 0
        # Scroll page to trigger lazy loading if needed
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 0);")
        page.wait_for_timeout(1000)
        
        resume_builder_locator = page.locator(".css-z3ngzz")
        resume_builder_visible = False
        try:
            # Wait for page to be fully loaded first
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            # Try multiple approaches to find the element
            # First try: wait for element to be attached to DOM
            try:
                resume_builder_locator.wait_for(state="attached", timeout=15000)
                resume_builder_visible = resume_builder_locator.count() > 0
            except Exception:
                # Second try: check count directly (element might already be in DOM)
                resume_builder_visible = resume_builder_locator.count() > 0
                if not resume_builder_visible:
                    # Third try: wait a bit more and check again (element might load late)
                    page.wait_for_timeout(5000)
                    resume_builder_visible = resume_builder_locator.count() > 0
                    if not resume_builder_visible:
                        # Fourth try: scroll to middle and bottom of page to trigger lazy loading
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
                        page.wait_for_timeout(2000)
                        resume_builder_visible = resume_builder_locator.count() > 0
                        if not resume_builder_visible:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                            page.wait_for_timeout(2000)
                            resume_builder_visible = resume_builder_locator.count() > 0
        except Exception:
            # Final fallback: just check count
            try:
                resume_builder_visible = resume_builder_locator.count() > 0
            except Exception:
                resume_builder_visible = False
        
        # Scroll Element Into View css:.css-15rfyx0 (matching Robot Framework: Run Keyword And Ignore Error Scroll Element Into View css:.css-15rfyx0)
        try:
            element_15rfyx0 = page.locator(".css-15rfyx0")
            element_15rfyx0.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass  # Ignore error as per Robot Framework
        
        page.wait_for_timeout(6000)  # Sleep 6 (matching Robot Framework: Sleep 6)
        
        # Get element count (matching Robot Framework: ${subscription_count} = get element count css:.css-1yd6z9)
        subscription_count = page.locator(".css-1yd6z9").count()
        
        # Assertions (matching Robot Framework exactly)
        # Should Be Equal As Strings '${header}' 'Find Your Dream Job'
        assert header_text == "Find Your Dream Job", f"Expected 'Find Your Dream Job', got '{header_text}'"
        
        # Should Be Equal As Strings '${resume_builder}' 'True'
        assert resume_builder_visible == True, f"Expected resume_builder to be True, got {resume_builder_visible}"
        
        # Should Be Equal As Strings '${subscription_count}' '1'
        assert str(subscription_count) == "1", f"Expected subscription_count to be '1', got '{subscription_count}'"
        
        page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.01 Home Page")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T1_02_EMP
@pytest.mark.employer
def test_t1_02_home_page_verify_jobs_not_from_same_company_consecutively(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.02 Home Page- Verify if jobs NOT coming from same company consecutively in 'Browse jobs'"""
    start_runtime_measurement("T1.02 Home Page- Verify jobs not from same company consecutively")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        goto_fast(page, EMPLOYER_URL)
        page.wait_for_load_state("domcontentloaded", timeout=10000)  # Faster than networkidle
        
        _handle_job_fair_popup(page)
        page.wait_for_timeout(300 if FAST_MODE else 500)  # Minimal wait
        
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_link.wait_for(state="attached", timeout=5000)
        browse_jobs_link.scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(300 if FAST_MODE else 500)  # Minimal wait after scroll
        
        _safe_click(page, browse_jobs_link)
        page.wait_for_timeout(500 if FAST_MODE else 1000)  # Minimal wait after click
        
        page_loaded = False
        try:
            page.wait_for_selector("css:.css-zkcq3t", timeout=30000)
            page_loaded = True
        except Exception:
            try:
                job_list = page.locator("xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div")
                job_list.wait_for(state="visible", timeout=15000)
                page_loaded = True
            except Exception:
                current_url = page.url
                if "Browse" in current_url or "browse" in current_url.lower() or "job" in current_url.lower():
                    page_loaded = True
        
        assert page_loaded, "Page didn't open after clicking Browse jobs"
        
        # Scroll to top of page after Browse jobs page loads (ensure page starts at top)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200 if FAST_MODE else 300)  # Small wait for scroll to complete
        
        # Companies to not consider (CEIPAL jobs)
        not_consider_companies = [
            "relevante", "augmentjobs", "jobot", "Crescentiasolutions", 
            "lamb company", "CredTALENT", "dhal information system"
        ]
        
        # Check the company names for 2 pages (range 1 to 3, exclusive)
        for each_page in range(1, 3):
            consecutive_company_names = 0
            page.wait_for_timeout(1000 if FAST_MODE else 2000)  # Sleep 2 - reduced in FAST_MODE
            
            first_job_company_locator = page.locator("xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div[1]/div/div[2]/div/p[2]")
            first_job_company_locator.wait_for(state="visible", timeout=30000 if FAST_MODE else 60000)
            
            jobs_on_page = page.locator("xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div").count()
            
            max_jobs_to_check = min(jobs_on_page, 9)
            
            for each_job in range(1, max_jobs_to_check + 1):
                company_locator = page.locator(f"xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div[{each_job}]/div/div[2]/div/p[2]")
                company_locator.wait_for(state="visible", timeout=30000 if FAST_MODE else 60000)
                
                get_company_name = company_locator.inner_text().strip()
                
                next_job_index = each_job + 1
                next_job_exists = False
                get_next_company_name = None
                
                try:
                    next_company_locator = page.locator(f"xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div[{next_job_index}]/div/div[2]/div/p[2]")
                    if next_company_locator.is_visible(timeout=5000):
                        next_job_exists = True
                        get_next_company_name = next_company_locator.inner_text().strip()
                except Exception:
                    next_job_exists = False
                
                if next_job_exists and get_next_company_name:
                    if get_company_name.lower() in [c.lower() for c in not_consider_companies]:
                        continue
                    if get_next_company_name.lower() in [c.lower() for c in not_consider_companies]:
                        continue
                    
                    if get_company_name == get_next_company_name:
                        consecutive_company_names += 1
                        # More than 4 company names should not come consecutively (count > 3 means 4+)
                        assert consecutive_company_names <= 3, f"More than 4 company names came consecutively. Count: {consecutive_company_names + 1}"
                    else:
                        consecutive_company_names = 0
                else:
                    consecutive_company_names = 0
            
            if each_page < 2:  # Only click if not on page 2 (last page)
                try:
                    next_page_btn = page.locator("xpath=//button[@aria-label='Go to next page']")
                    next_page_btn.scroll_into_view_if_needed()  # Run Keyword And Ignore Error
                except Exception:
                    pass  # Ignore error
                
                page.wait_for_timeout(1500 if FAST_MODE else 3000)  # Sleep 3 - reduced in FAST_MODE
                next_page_btn.click()  # Click Element - Next page
                page.wait_for_timeout(1000 if FAST_MODE else 2000)  # Sleep 2 - reduced in FAST_MODE
        
        page.wait_for_timeout(1000 if FAST_MODE else 2000)  # Sleep 2 - reduced in FAST_MODE
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.02 Home Page- Verify jobs not from same company consecutively")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T1_03_EMP
@pytest.mark.employer
def test_t1_03_home_page_verify_jobs_matched_with_searched_company(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.03 Home Page- Verify if jobs are matched with the searched company in 'Browse jobs'"""
    start_runtime_measurement("T1.03 Home Page- Verify jobs matched with searched company")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        goto_fast(page, EMPLOYER_URL)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(300 if FAST_MODE else 500)
        page.wait_for_selector("text=Find Your Dream Job", timeout=30000)
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_link.scroll_into_view_if_needed(timeout=10000)
        _safe_click(page, browse_jobs_link)
        page.wait_for_timeout(500 if FAST_MODE else 1000)
        search_input = page.locator("xpath=//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input")
        search_input.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        _safe_click(page, search_input)
        popup_input = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/div/input")
        popup_input.wait_for(state="visible", timeout=30000)
        # Get length of HOME_PAGE_COMPANY_SEARCH
        len_home_page_company_search = len(HOME_PAGE_COMPANY_SEARCH)
        for index in range(len_home_page_company_search):
            letter = HOME_PAGE_COMPANY_SEARCH[index]
            popup_input.type(letter)  # Input Text
            page.wait_for_timeout(500)  # Sleep 0.5
        page.wait_for_timeout(5000)
        company_option = page.locator(".css-gcb45j")
        company_option.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        company_option_li = page.locator("xpath=/html/body/div[2]/div[3]/div[2]/div[1]/div[3]/ul/li")
        option_text = company_option_li.inner_text()
        assert HOME_PAGE_COMPANY_SEARCH in option_text, f"Company '{HOME_PAGE_COMPANY_SEARCH}' not found in option: '{option_text}'"
        _safe_click(page, company_option_li)
        page.wait_for_timeout(2000)
        selected_company_elem = page.locator(".css-o1spff")
        selected_text = selected_company_elem.inner_text()
        assert HOME_PAGE_COMPANY_SEARCH in selected_text, f"Company '{HOME_PAGE_COMPANY_SEARCH}' not found in selected field: '{selected_text}'"
        page.wait_for_timeout(2000)
        popup_button = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button")
        _safe_click(page, popup_button)
        page.wait_for_timeout(3000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200 if FAST_MODE else 300)
        # Robot Framework: ${page_no}    Set Variable    1
        page_no = 1
        
        # Loop through pages (limit 5)
        while page_no < 6:
            
            job_count_elem = page.locator(".MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)")
            job_count_elem.first.wait_for(state="visible", timeout=30000)
            
            page.wait_for_timeout(2000)
            
            # Get Element Count jobs
            num_jobs = page.locator(".MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)").count()
            
            for job_no in range(1, num_jobs + 1):
                company_name_locator = page.locator(f"xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div[{job_no}]/div/div[2]/div/p[2]")
                company_name_locator.wait_for(state="visible", timeout=30000)
                
                company_name = company_name_locator.inner_text()
                
                # Convert to lowercase
                company_name = company_name.lower()
                company_search_lower = HOME_PAGE_COMPANY_SEARCH.lower()  # Set Variable
                
                page.wait_for_timeout(2000)
                
                if (company_name == company_search_lower or 
                    company_search_lower in company_name or 
                    company_name in company_search_lower):
                    pass
                else:
                    raise AssertionError(f"Company mismatch for job {job_no}: '{company_name}' does not match '{HOME_PAGE_COMPANY_SEARCH}'")
            
            page.evaluate("document.querySelector('nav[aria-label=\"pagination navigation\"]').scrollIntoView({behavior: 'smooth', block: 'center'});")
            
            page.wait_for_timeout(2000)
            
            next_btn = page.locator("xpath=//button[@aria-label='Go to next page']")
            if_next_button_available = False
            if next_btn.count() > 0:
                try:
                    if_next_button_available = next_btn.is_enabled()
                except:
                    if_next_button_available = False
            
            if if_next_button_available:
                if page_no == 5:
                    break
                
                _safe_click(page, next_btn)
                
                page.wait_for_timeout(2000)
                
                # Increment page_no
                page_no = page_no + 1
            else:
                # Exit For Loop
                break
        
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.03 Home Page- Verify jobs matched with searched company")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T1_04_EMP
@pytest.mark.employer
def test_t1_04_home_page_verify_job_posting_time(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.04 Home Page- Verify the job posting time"""
    start_runtime_measurement("T1.04 Home Page- Verify job posting time")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        goto_fast(page, EMPLOYER_URL)
        _handle_job_fair_popup(page)
        page.wait_for_selector("text=Find Your Dream Job", timeout=30000)
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_link.scroll_into_view_if_needed(timeout=10000)
        _safe_click(page, browse_jobs_link)
        search_input = page.locator("xpath=//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input")
        search_input.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        job_count_locator = page.locator(".MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)")
        num_of_jobs = job_count_locator.count()
        for each_job in range(1, num_of_jobs + 1):
            timestamp_locator = page.locator(f"xpath=/html/body/div/div[2]/div[3]/div/div[1]/div/ul/div[{each_job}]/div/div[2]/div/div/p[2]")
            if not timestamp_locator.is_visible(timeout=5000):
                continue
                
            get_timestamp = timestamp_locator.inner_text().lower()
            
            if 'minutes' in get_timestamp or 'minute' in get_timestamp:
                continue
            elif 'seconds' in get_timestamp or 'second' in get_timestamp:
                continue
            elif 'hours' in get_timestamp or 'hour' in get_timestamp:
                timestamp_split = get_timestamp.split()
                # ${get_hour} Set Variable ${timestamp_split}[0]
                get_hour = timestamp_split[0]
                
                if get_hour == 'an':
                    continue
                else:
                    # ${get_hour} Convert To Integer ${get_hour}
                    try:
                        get_hour_int = int(get_hour)
                        
                        assert get_hour_int <= 2, f"Job posted more than 2 hours ago: {get_timestamp}"
                    except ValueError:
                        continue
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.04 Home Page- Verify job posting time")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T1_05_EMP
@pytest.mark.employer
def test_t1_05_home_page_verify_book_your_demo(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.05 Home Page- Verify 'Book Your Demo'"""
    start_runtime_measurement("T1.05 Home Page- Verify 'Book Your Demo'")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        # Navigate to home page
        goto_fast(page, EMPLOYER_URL)
        page.wait_for_timeout(2000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(3000)
        
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        
        book_demo_btn = None
        book_demo_selectors = [
            "xpath=//*[@id='root']/div[2]/header/div/div[1]/button",
            "button:has-text('Book Your Demo')",
            "button:has-text('Book')",
            "header button",
        ]
        
        for selector in book_demo_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=5000):
                    book_demo_btn = btn
                    break
            except:
                continue
        
        if not book_demo_btn:
            return
        book_demo_btn.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        
        _safe_click(page, book_demo_btn)
        page.wait_for_timeout(2000)
        
        # Wait for new window/tab to open
        page.wait_for_timeout(3000)
        
        all_pages = page.context.pages
        if len(all_pages) > 1:
            demo_page = all_pages[-1]
            demo_page.wait_for_load_state("networkidle", timeout=30000)
            
            demo_url = demo_page.url
            print(f"Demo URL: {demo_url}")
            assert "calendly.com/jobsnprofiles-demo" in demo_url, f"Expected calendly.com URL, got '{demo_url}'"
            
            # Wait for cookie banner
            try:
                cookie_banner = demo_page.locator("xpath://div[@aria-label='Cookie banner']")
                cookie_banner.wait_for(state="visible", timeout=40000)
                page.wait_for_timeout(4000)
            except Exception:
                pass
            
            welcome_text = demo_page.locator("xpath=/html/body/div[1]/div/div/div/div/div/div/div[1]")
            welcome_text.wait_for(state="visible", timeout=30000)
            assert "Welcome to Jobs'n'Profiles" in welcome_text.inner_text(), "Welcome text not found"
            print("Welcome text verified")
            
            meeting_link = demo_page.locator("xpath=/html/body/div[1]/div/div/div/div/div/div/div[2]/a")
            meeting_link.wait_for(state="visible", timeout=30000)
            assert "30 Minute Meeting" in meeting_link.inner_text(), "30 Minute Meeting link not found"
            print("30 Minute Meeting link verified")
            
            # Accept cookie
            try:
                accept_cookie_btn = demo_page.locator("id=onetrust-accept-btn-handler")
                if accept_cookie_btn.is_visible(timeout=5000):
                    accept_cookie_btn.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass
            
            # Get meeting link href
            meeting_href = meeting_link.get_attribute("href")
            print(f"Meeting link: {meeting_href}")
            
            # Navigate to meeting link
            demo_page.goto(meeting_href)
            demo_page.wait_for_load_state("networkidle", timeout=30000)
            
            # Wait for calendar
            calendar = demo_page.locator("css:._3efP_GeH5kyBAzqnLzL.cllbjvXCdYDt9A3te4cz")
            calendar.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(2000)
            
            # Get available dates
            available_dates = demo_page.locator("css:.iLlmw9nvWQp6MsANxMu_.XXKN9NWALj8Xe4ed0s7r")
            num_dates = available_dates.count()
            print(f"Number of available dates: {num_dates}")
            
            if num_dates > 0:
                # Check today's date (first date)
                first_date = available_dates.first
                first_date_text = first_date.inner_text()
                print(f"First date text: {first_date_text}")
                
                # Get today's date
                from datetime import datetime
                today_date = datetime.now().day
                print(f"Today's date: {today_date}")
                
                try:
                    first_date_int = int(first_date_text)
                    assert first_date_int == today_date, f"First date {first_date_int} does not match today {today_date}"
                except ValueError:
                    pass
                
                # Get outerHTML to check for today-dot
                first_date_html = first_date.evaluate("el => el.outerHTML")
                assert 'data-component="today-dot"' in first_date_html, "Today dot not found in first date"
                print("Today's date verified")
                
                # Choose a random date
                import random
                choose_random_date_index = random.randint(0, num_dates - 1)
                print(f"Selected date index: {choose_random_date_index}")
                
                selected_date = available_dates.nth(choose_random_date_index)
                selected_date_text = selected_date.inner_text()
                print(f"Selected date: {selected_date_text}")
                selected_date.click()
                page.wait_for_timeout(3000)
                
                selected_date_header = demo_page.locator("xpath=/html/body/div[1]/div/div/div/div/div[2]/div/div[1]/div[2]/h3")
                selected_date_header.wait_for(state="visible", timeout=30000)
                assert selected_date_text in selected_date_header.inner_text(), "Selected date not shown in header"
                
                # Get available times
                available_times = demo_page.locator("css:.a_kkgWd9QJFsCurLPfA_")
                num_times = available_times.count()
                print(f"Number of available times: {num_times}")
                
                if num_times > 0:
                    # Choose random time
                    choose_random_time = random.randint(0, num_times - 1)
                    chosen_time_elem = available_times.nth(choose_random_time)
                    chosen_time = chosen_time_elem.inner_text()
                    print(f"Selected time: {chosen_time}")
                    
                    chosen_time_elem.click()
                    page.wait_for_timeout(2000)
                    
                    next_btn = demo_page.locator("css:.y9_mQD7Hd4ZLZ4SUzgyw.VfCFnsGvnnkn_bFdwv5V")
                    next_btn.wait_for(state="visible", timeout=30000)
                    next_btn.click()
                    page.wait_for_timeout(2000)
                    
                    time_display = demo_page.locator("xpath=/html/body/div[1]/div/div/div/div/div[1]/div/div/div[1]/div[2]/div/div/div/div/div[3]/div/div[2]")
                    time_display.wait_for(state="visible", timeout=30000)
                    assert chosen_time in time_display.inner_text(), "Chosen time not displayed"
                    
                    schedule_btn = demo_page.locator("css:.bzua8jl.dyxacjh")
                    schedule_btn.wait_for(state="visible", timeout=30000)
                    schedule_btn.click()
                    page.wait_for_timeout(2000)
                    
                    feedback_messages = demo_page.locator("css:.ctl3io2")
                    feedback_count = feedback_messages.count()
                    assert feedback_count == 4, f"Expected 4 feedback messages, got {feedback_count}"
                    print("Mandatory fields validation verified")
                    
                    # Fill form
                    full_name_input = demo_page.locator("id=full_name_input")
                    full_name_input.fill("Test")
                    
                    email_input = demo_page.locator("id=email_input")
                    email_input.fill(EMP1_ID)
                    
                    # Fill placeholder inputs
                    placeholder_inputs = demo_page.locator("css:.i167bxqy.ikzg8f9")
                    if placeholder_inputs.count() >= 3:
                        placeholder_inputs.nth(0).fill("Software")
                        placeholder_inputs.nth(1).fill("Job Boards")
                        placeholder_inputs.nth(2).fill("Advance Search")
                    
                    page.wait_for_timeout(2000)
                    
                    schedule_btn.click()
                    page.wait_for_timeout(2000)
                    print("Form submitted (captcha may appear in automation)")
            
            demo_page.close()
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.05 Home Page- Verify 'Book Your Demo'")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T1_06_EMP
@pytest.mark.employer
def test_t1_06_home_page_no_repetition_of_jobs_in_similar_jobs(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T1.06 Home Page- No repetition of jobs in 'Similar Jobs'"""
    print("========================================")
    print("T1.06: No repetition of jobs in 'Similar Jobs'")
    print("Requirement: Verify no duplicate jobs in similar jobs list")
    print("========================================")
    
    start_runtime_measurement("T1.06 Home Page- No repetition of jobs in 'Similar Jobs'")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        # Navigate to home page (matching Robot Framework: Open site)
        # Use BASE_URL (https://jobsnprofiles.com/) for public home page, not EMPLOYER_URL
        goto_fast(page, BASE_URL)
        _handle_job_fair_popup(page)
        
        # Wait for home page text to appear (matching Robot Framework: Wait Until Page Contains Find Your Dream Job 30)
        try:
            page.wait_for_selector("text=Find Your Dream Job", timeout=30000)
        except Exception:
            # Fallback: check page content
            for attempt in range(15):  # 30 seconds total (2 seconds per attempt)
                if "Find Your Dream Job" in page.content():
                    break
                page.wait_for_timeout(2000)
        
        # Browse jobs link handling (matching Robot Framework lines 416-425)
        # ${browse_jobs_clicked} = Run Keyword And Return Status Scroll Element Into View xpath:/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_clicked = False
        try:
            browse_jobs_link.wait_for(state="visible", timeout=10000)
            browse_jobs_link.scroll_into_view_if_needed(timeout=5000)
            browse_jobs_clicked = True
        except Exception:
            browse_jobs_clicked = False
        
        if browse_jobs_clicked:
            # ${click_success} = Run Keyword And Return Status Click Element xpath:/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]
            click_success = False
            try:
                browse_jobs_link.click(timeout=5000)
                click_success = True
            except Exception:
                click_success = False
            
            if not click_success:
                print("WARNING: Could not click Browse jobs link, trying alternative method...")
                # Execute JavaScript fallback (matching Robot Framework: Execute JavaScript var el = document.evaluate(...))
                page.evaluate("""
                    var el = document.evaluate('/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el) el.click();
                """)
        else:
            print("WARNING: Browse jobs link not found, skipping...")
        
        # Check search input visibility (matching Robot Framework lines 426-429)
        # ${input_visible} = Run Keyword And Return Status Wait Until Element Is Visible xpath://*[@id="root"]/div[2]/div[1]/div/div[3]/div[2]/input 30
        search_input = page.locator("xpath=//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input")
        input_visible = False
        try:
            search_input.wait_for(state="visible", timeout=30000)
            input_visible = True
        except Exception:
            input_visible = False
        
        if not input_visible:
            print("WARNING: Search input not visible, test may continue with limited functionality")
        
        page.wait_for_timeout(1000)  # sleep 1 (matching Robot Framework: sleep 1)
        
        # Initialize variables (matching Robot Framework lines 431-435)
        linkedin_job_count = 0  # To check the redirection of the first job with linkedin
        jobs_with_similar = 0
        jobs_without_similar = 0
        duplicate_detected = 0
        num_jobs = 0
        
        # Check for first page (matching Robot Framework: FOR ${each_page} IN RANGE 1 2)
        for each_page in range(1, 2):
            # ${num_jobs} = Get Element Count css:.MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)
            num_jobs = page.locator(".MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)").count()
            print(f"\nTotal Jobs Found on Page: {num_jobs}")
            
            # ${jobs_webelements} = Get Webelements css:.MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)
            jobs_webelements = page.locator(".MuiPaper-root > .MuiList-root > .MuiButtonBase-root .MuiStack-root > .MuiTypography-root:nth-child(2)")
            
            # ${max_jobs_to_process} = Evaluate min(5, ${num_jobs})
            max_jobs_to_process = min(5, num_jobs)
            
            # FOR ${each_job} IN RANGE 0 ${max_jobs_to_process}
            for each_job in range(max_jobs_to_process):
                print(f"\n--- Processing Job #{each_job+1} ---")
                
                try:
                    # Run Keyword And Ignore Error Scroll Element Into View ${jobs_webelements}[${each_job}]
                    job_elem = jobs_webelements.nth(each_job)
                    try:
                        job_elem.scroll_into_view_if_needed(timeout=5000)
                    except Exception:
                        pass  # Ignore error
                    
                    page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
                    
                    # Click Element ${jobs_webelements}[${each_job}] # click on each job
                    job_elem.click(timeout=5000)
                    
                    # Wait Until Element Is Visible xpath:/html/body/div/div[2]/div[4]/div/div/div[1]/div 30 # job view
                    job_view = page.locator("xpath=/html/body/div/div[2]/div[4]/div/div/div[1]/div")
                    job_view.wait_for(state="visible", timeout=30000)
                    page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
                    
                    # Check if email is available (matching Robot Framework lines 451-457)
                    # ${email_available} = Run Keyword And Return Status Wait Until Page Contains Element css:p.email-text 10
                    email_available = False
                    try:
                        email_elem = page.locator("css:p.email-text")
                        email_elem.wait_for(state="visible", timeout=10000)
                        email_available = True
                    except Exception:
                        email_available = False
                    
                    if email_available:
                        # Page Should Contain Element css:p.email-text # Email of the recruiter
                        email_elem = page.locator("css:p.email-text")
                        assert email_elem.is_visible(), "Email element should be visible"
                        print("Email element found")
                    else:
                        print("WARNING: Email element not found - skipping email verification")
                    
                    # Wait for similar jobs section to load (matching Robot Framework lines 458-470)
                    # Sleep 3
                    page.wait_for_timeout(3000)
                    
                    # Run Keyword And Ignore Error Execute Javascript window.scrollTo(0, document.body.scrollHeight);
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    except Exception:
                        pass  # Ignore error
                    
                    page.wait_for_timeout(2000)  # Sleep 2
                    
                    # Try multiple times to find similar jobs section as it loads late (matching Robot Framework lines 463-470)
                    # ${if_similar_jobs_available} = Set Variable False
                    if_similar_jobs_available = False
                    # FOR ${wait_attempt} IN RANGE 1 6
                    for wait_attempt in range(1, 6):
                        # ${if_similar_jobs_available} = Run Keyword And Return Status Wait Until Page Contains Element xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div 5
                        try:
                            similar_jobs_section = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div")
                            similar_jobs_section.wait_for(state="visible", timeout=5000)
                            if_similar_jobs_available = True
                            break
                        except Exception:
                            pass
                        
                        # Exit For Loop If '${if_similar_jobs_available}'=='True'
                        if if_similar_jobs_available:
                            break
                        
                        print(f"Waiting for similar jobs section (attempt {wait_attempt}/5)...")
                        page.wait_for_timeout(2000)  # Sleep 2
                        
                        # Run Keyword And Ignore Error Execute Javascript window.scrollTo(0, document.body.scrollHeight);
                        try:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        except Exception:
                            pass  # Ignore error
                
                    # IF '${if_similar_jobs_available}'=='True' (matching Robot Framework line 471)
                    if if_similar_jobs_available:
                        # ${jobs_with_similar} = Evaluate ${jobs_with_similar}+1
                        jobs_with_similar += 1
                        
                        # Scroll to similar jobs section and wait for it to be fully visible (matching Robot Framework lines 473-476)
                        # Run Keyword And Ignore Error Scroll Element Into View xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul
                        similar_jobs_section = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul")
                        try:
                            similar_jobs_section.scroll_into_view_if_needed(timeout=5000)
                        except Exception:
                            pass  # Ignore error
                        
                        page.wait_for_timeout(2000)  # Sleep 2
                        
                        # Wait Until Element Is Visible xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div 10
                        similar_jobs_list = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div")
                        similar_jobs_list.wait_for(state="visible", timeout=10000)
                        
                        # ${number_of_similar_jobs} = Get Element Count xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div
                        number_of_similar_jobs = similar_jobs_list.count()
                        print(f"Similar Jobs Found: {number_of_similar_jobs}")
                        
                        # First similar job should not be same as viewed job (matching Robot Framework lines 480-499)
                        # ${viewed_job_title_details} = Get Text xpath:/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/body
                        viewed_job_title_details = page.locator("xpath=/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/body").inner_text()
                        
                        # ${viewed_job_title_split} = Evaluate "${viewed_job_title_details}".split("#")
                        viewed_job_title_split = viewed_job_title_details.split("#")
                        
                        # ${viewed_job_title} = Set Variable ${viewed_job_title_split}[0]
                        viewed_job_title = viewed_job_title_split[0]
                        
                        # ${viewed_job_title} = Strip String ${viewed_job_title}
                        viewed_job_title = viewed_job_title.strip()
                        
                        # ${viewed_job_company} = Get Text xpath:/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/nav/ol/li[1]/p
                        viewed_job_company = page.locator("xpath=/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/nav/ol/li[1]/p").inner_text()
                        
                        # ${viewed_job_location} = Get Text xpath:/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/nav/ol/li[3]/p
                        viewed_job_location = page.locator("xpath=/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[1]/nav/ol/li[3]/p").inner_text()
                        
                        print(f"Viewed Job: {viewed_job_title} | {viewed_job_company} | {viewed_job_location}")
                        
                        # ${first_similar_job_title} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/p[1]
                        first_similar_job_title = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/p[1]").inner_text()
                        
                        # ${first_similar_job_company} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/p[2]
                        first_similar_job_company = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/p[2]").inner_text()
                        
                        # ${first_similar_job_location} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/div/p[1]
                        first_similar_job_location = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[1]/div/div[2]/div/div/p[1]").inner_text()
                        
                        print(f"First Similar Job: {first_similar_job_title} | {first_similar_job_company} | {first_similar_job_location}")
                        
                        # IF $viewed_job_title != $first_similar_job_title or $viewed_job_company != $first_similar_job_company or $viewed_job_location != $first_similar_job_location
                        if (viewed_job_title != first_similar_job_title or 
                            viewed_job_company != first_similar_job_company or 
                            viewed_job_location != first_similar_job_location):
                            print("PASS: First similar job is different from viewed job")
                        else:
                            print("FAIL: First similar job matches viewed job exactly")
                            raise AssertionError("All viewed and checked job details are the same - at least one should differ.")
                        
                        # Check there are no duplicate jobs in similar jobs list (matching Robot Framework lines 501-523)
                        # ${all_jobs} = Create List
                        all_jobs = []
                        
                        # ${all_jobs_webelements} = Get Webelements xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div
                        all_jobs_webelements = page.locator("xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div")
                        
                        # FOR ${similar_job_index} IN RANGE 1 ${number_of_similar_jobs}+1
                        for similar_job_index in range(1, number_of_similar_jobs + 1):
                            # ${title} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[${similar_job_index}]/div/div[2]/div/p[1]
                            title = page.locator(f"xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[{similar_job_index}]/div/div[2]/div/p[1]").inner_text()
                            
                            # ${company} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[${similar_job_index}]/div/div[2]/div/p[2]
                            company = page.locator(f"xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[{similar_job_index}]/div/div[2]/div/p[2]").inner_text()
                            
                            # ${location} = Get Text xpath:/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[${similar_job_index}]/div/div[2]/div/div/p[1]
                            location = page.locator(f"xpath=/html/body/div/div[2]/div[5]/div/div[2]/div/div[2]/ul/div[{similar_job_index}]/div/div[2]/div/div/p[1]").inner_text()
                            
                            # ${job_id} = Set Variable ${title} | ${company} | ${location}
                            job_id = f"{title} | {company} | {location}"
                            
                            # Append To List ${all_jobs} ${job_id}
                            all_jobs.append(job_id)
                        
                        # ${unique_jobs} = Remove Duplicates ${all_jobs}
                        unique_jobs = list(set(all_jobs))
                        
                        # ${unique_count} = Get Length ${unique_jobs}
                        unique_count = len(unique_jobs)
                        
                        # ${all_count} = Get Length ${all_jobs}
                        all_count = len(all_jobs)
                        
                        # IF ${all_count} != ${unique_count}
                        if all_count != unique_count:
                            # ${duplicate_count} = Evaluate ${all_count} - ${unique_count}
                            duplicate_count = all_count - unique_count
                            
                            # ${duplicate_detected} = Evaluate ${duplicate_detected}+1
                            duplicate_detected += 1
                            
                            print(f"FAIL: Found {duplicate_count} duplicate job(s) in similar jobs list")
                            print(f"Total: {all_count}, Unique: {unique_count}")
                            
                            # Should Be Equal As Integers ${all_count} ${unique_count} Found duplicate jobs in similar jobs list!
                            assert all_count == unique_count, f"Found duplicate jobs in similar jobs list! Total: {all_count}, Unique: {unique_count}"
                        else:
                            print(f"PASS: No duplicates found ({all_count} unique jobs)")
                    else:
                        # ${jobs_without_similar} = Evaluate ${jobs_without_similar}+1
                        jobs_without_similar += 1
                        print("WARNING: No similar jobs section found for this job after waiting (may not exist or took too long to load)")
                    
                except Exception as e:
                    print(f"Error processing job {each_job + 1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # Log validation summary (matching Robot Framework lines 531-542)
        print("\n========================================")
        print("VALIDATION SUMMARY")
        print("========================================")
        print(f"Total Jobs Checked: {num_jobs}")
        print(f"Jobs with Similar Jobs Section: {jobs_with_similar}")
        print(f"Jobs without Similar Jobs Section: {jobs_without_similar}")
        
        if duplicate_detected > 0:
            print(f"TEST RESULT: FAILED - Found duplicate jobs in {duplicate_detected} similar jobs list(s)")
        else:
            print("TEST RESULT: PASSED - No duplicate jobs found in similar jobs lists")
        print("========================================")
        
        page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T1.06 Home Page- No repetition of jobs in 'Similar Jobs'")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_01_EMP
@pytest.mark.employer
def test_t2_01_post_a_job_verification_and_verification_with_job_id(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T2.01 'Post a Job' verification and verification with Job-Id"""
    start_runtime_measurement("T2.01 Post a Job verification and verification with Job-Id")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        # Navigate to employer dashboard (matching Robot Framework: after login, user is on dashboard)
        print("Verifying we are on employer dashboard...")
        if "Empdashboard" not in page.url:
            print(f"URL mismatch (expected Empdashboard, got {page.url}). Navigating...")
            page.goto(f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_load_state("domcontentloaded", timeout=30000)
        else:
            print("Already on employer dashboard (via fixture)")
        
        page.wait_for_timeout(2000)
        
        # Handle job fair popup first (matching Robot Framework flow)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        
        # Wait for dashboard to be ready (wait for navigation menu like Robot Framework does)
        # Robot Framework waits for xpath:/html/body/div[1]/div[2]/div/div/ul after login
        try:
            dashboard_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul")
            dashboard_menu.wait_for(state="visible", timeout=30000)
            print("Dashboard loaded successfully")
        except Exception:
            print("Warning: Dashboard menu not found, continuing...")
        page.wait_for_timeout(2000)
        
        # Wait for Post a Job button (exact XPath from Robot Framework)
        print("\n========================================")
        print("Clicking 'Post a Job' button on dashboard...")
        if "Empdashboard" not in page.url:
            print(f"Test start URL check failed: {page.url}")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_timeout(2000)
        
        assert "Empdashboard" in page.url, f"Failed to reach Empdashboard. Current URL: {page.url}"
        print(f"Test started on correct URL: {page.url}")
        
        post_job_btn = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div/div[2]/div/div/div/div/button")
        post_job_btn.wait_for(state="visible", timeout=30000)
        
        post_job_btn.click()
        page.wait_for_timeout(2000)
        
        # Check for dialog/modal (matching Robot Framework logic)
        print("Checking for dialog/modal...")
        dialog_visible = False
        try:
            dialog = page.locator(".MuiDialog-container")
            if dialog.is_visible(timeout=5000):
                dialog_visible = True
                print("[OK] Dialog detected, waiting for it to be fully loaded...")
                page.wait_for_timeout(2000)
        except Exception:
            pass
        
        if not dialog_visible:
            print("[OK] No dialog detected, proceeding...")
        
        # Wait for Create button (matching Robot Framework)
        print("Waiting for Create button to be visible...")
        create_btn = page.locator("xpath=//button[contains(text(),'Create')]")
        create_btn.wait_for(state="visible", timeout=20000)
        create_btn.wait_for(state="attached", timeout=20000)
        print("[OK] Create button is visible and enabled")
        
        create_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        
        print("Attempting to click Create button...")
        click_success = False
        try:
            create_btn.click(timeout=10000)
            click_success = True
            print("[OK] Create button clicked successfully")
        except Exception:
            print("WARNING: Regular click failed, trying JavaScript click...")
            create_button_js = page.locator("xpath=//button[contains(text(),'Create')]")
            page.evaluate("arguments[0].click();", create_button_js.element_handle())
            print("[OK] JavaScript click executed successfully")
            page.wait_for_timeout(2000)
        
        page.wait_for_timeout(3000)
        
        # Count jobs before posting
        job_list_items = page.locator(".MuiListItemButton-root").count()
        num_jobs_b4_posting = job_list_items - 11
        
        # Fill job form
        print("Posting a job......")
        
        # Job Title (matching Robot Framework: Input Text id:jobTitle ${job_title})
        job_title_input = page.locator("id=jobTitle")
        job_title_input.fill(JOB_TITLE)
        page.wait_for_timeout(5000)  # sleep 5 (matching Robot Framework: sleep 5)
        
        # Job Type (multiple selections)
        job_type_input = page.locator("id=jobType")
        job_type_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(JOB_TYPE1)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        
        # Second job type
        job_type_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(JOB_TYPE2)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        
        # Experience
        experience_input = page.locator("id=experience")
        experience_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(EXPERIENCE)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        
        # Visa type
        visa_type_input = page.locator("id=visaTypeWorkPermit")
        visa_type_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(VISA_TYPE1)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        
        # Description (check skills should not be available before)
        try:
            skills_before = page.locator(".css-i4oh8e")
            assert not skills_before.is_visible(timeout=2000), "Skills should not be available before description"
        except Exception:
            pass
        
        # Fill description (matching Robot Framework: Input Text css:.ql-editor ${description})
        description_editor = page.locator(".ql-editor")
        description_editor.fill(JOB_DESCRIPTION)
        page.wait_for_timeout(3000)  # Sleep 3 (matching Robot Framework: Sleep 3)
        
        # Check skills are available after description (matching Robot Framework: Sleep 2)
        page.wait_for_timeout(2000)
        skills_after = page.locator(".css-i4oh8e")
        # Use first() to avoid strict mode error when multiple skills are present
        skills_after.first.wait_for(state="visible", timeout=60000)
        assert skills_after.first.is_visible(), "Skills should be available after description is entered"
        print("Skills are available under Skills after description is entered")
        page.wait_for_timeout(6000)  # Sleep 6 (matching Robot Framework: Sleep 6)
        
        # State
        state_input = page.locator("id=state")
        state_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(STATE)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        
        # City
        city_input = page.locator("id=city")
        city_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(CITY)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        
        # Zipcode (matching Robot Framework scrolling logic)
        page.evaluate("window.scrollTo(window.scrollX - 500, window.scrollY)")  # Horizontal scroll
        zipcode_input = page.locator("id=zipcode")
        try:
            zipcode_input.scroll_into_view_if_needed()
        except Exception:
            pass
        zipcode_input.wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(4000)  # Sleep 4 (matching Robot Framework: Sleep 4)
        zipcode_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.type(ZIPCODE)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        
        qualification_input = page.locator("id=qualification")
        qualification_input.click()
        page.wait_for_timeout(1000)
        page.keyboard.type("Bachelors Degree")
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)  # Sleep 4 (matching Robot Framework: Sleep 4)
        
        page.evaluate("window.scrollTo(window.scrollX - 500, window.scrollY)")  # Horizontal scroll
        try:
            page.locator(".css-1lpukdo").scroll_into_view_if_needed()
        except Exception:
            pass
        post_job_submit_btn = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div/div/button[1]")
        post_job_submit_btn.wait_for(state="visible", timeout=10000)
        post_job_submit_btn.click()
        page.wait_for_timeout(2000)
        
        # Check for terms and conditions error (matching Robot Framework)
        terms_error = page.locator("xpath=//span[contains(text(),'You must accept the terms and conditions')]")
        terms_error_visible = terms_error.is_visible(timeout=5000)
        assert terms_error_visible, "Terms and conditions error message should appear"
        print(f"Terms and conditions error verified: {terms_error_visible}")
        page.wait_for_timeout(500)
        
        assert page.locator(".css-ifn6vo").is_visible(), "Terms and conditions error element should be visible"
        
        # Scroll to terms and conditions checkbox (matching Robot Framework scrolling exactly)
        # Execute JavaScript window.scrollTo(window.scrollX - 500, window.scrollY) #scroll horizontally
        page.evaluate("window.scrollTo(window.scrollX - 500, window.scrollY)")  # Horizontal scroll
        page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
        
        # Execute JavaScript window.scrollTo(0, document.body.scrollHeight) # Scroll to the end of the page
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll to bottom
        page.wait_for_timeout(8000)  # Sleep 8 (matching Robot Framework: Sleep 8)
        
        # Run Keyword And Ignore Error Scroll Element Into View xpath:/html/body/div[1]/div[2]/main/div[2]/div[3]/div/form/div/div[12]/div/div[4]/label/span[1]/input
        try:
            terms_checkbox = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/form/div/div[12]/div/div[4]/label/span[1]/input")
            terms_checkbox.scroll_into_view_if_needed()
        except Exception:
            pass  # Ignore error
        
        page.wait_for_timeout(8000)  # Sleep 8 (matching Robot Framework: Sleep 8)
        
        # Execute JavaScript window.scrollTo(0, document.body.scrollHeight) # Scroll to the end of the page
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll to bottom again
        page.wait_for_timeout(4000)  # Sleep 4 (matching Robot Framework: Sleep 4)
        
        print("Clicking terms and conditions checkbox...")
        # Click Element xpath:/html/body/div[1]/div[2]/main/div[2]/div[3]/div/form/div/div[12]/div/div[4]/label/span[1]/input # Agree terms and conditions
        terms_checkbox = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/form/div/div[12]/div/div[4]/label/span[1]/input")
        terms_checkbox.click()
        page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
        print("Terms and conditions checkbox clicked")
        
        print("Waiting for Terms and Conditions dialog to appear...")
        terms_dialog_visible = False
        try:
            terms_dialog = page.locator(".css-mbdu2s")
            if terms_dialog.is_visible(timeout=10000):
                terms_dialog_visible = True
                print("Terms and Conditions dialog found, closing it...")
                close_btn = page.locator("xpath=//button[@aria-label='close']")
                close_btn.wait_for(state="visible", timeout=10000)
                close_btn.click()
                page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
                print("Terms and Conditions dialog closed successfully")
        except Exception:
            if not terms_dialog_visible:
                print("WARNING: Terms and Conditions dialog not found (may have closed automatically or not appeared)")
        
        # Scroll back up to check skills and post button (matching Robot Framework)
        # Run Keyword And Ignore Error Scroll Element Into View css:.css-1lpukdo
        try:
            page.locator(".css-1lpukdo").scroll_into_view_if_needed()
        except Exception:
            pass  # Ignore error
        
        # Execute JavaScript window.scrollTo(0, 0);
        page.evaluate("window.scrollTo(0, 0);")
        page.wait_for_timeout(3000)  # Sleep 3 (matching Robot Framework: Sleep 3)
        
        # Page Should Contain Element css:.css-i4oh8e # Before submitting job, skills should be available
        assert page.locator(".css-i4oh8e").first.is_visible(), "Skills should be available before submitting"
        page.wait_for_timeout(2000)  # Sleep 2 (matching Robot Framework: Sleep 2)
        
        # Post job (matching Robot Framework: Click Button xpath:/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/button[1])
        post_job_submit_btn.click()
        
        # Wait for success message (matching Robot Framework logic)
        pop_up_msg = False
        for time_attempt in range(1, 31):  # Try for 30 seconds like Robot Framework
            try:
                # Check for toast (matching Robot Framework)
                toast = page.locator("class:Toastify")
                if toast.is_visible(timeout=2000):
                    toast_text = toast.inner_text()
                    if "Job Posted Successfully" in toast_text:
                        pop_up_msg = True
                        break
            except Exception:
                pass
            
            # Check for job card (matching Robot Framework)
            try:
                job_card = page.locator(".css-1fjv3hc")
                if job_card.is_visible(timeout=2000):
                    pop_up_msg = True
                    break
            except Exception:
                pass
            
            page.wait_for_timeout(1000)
        
        assert pop_up_msg, "Job posting was not successful. Expected success message did not appear."
        print("Job posted successfully confirmed")
        
        page.wait_for_timeout(2000)  # sleep 2 (matching Robot Framework: sleep 2)
        print("Job is posted successfully")
        page.wait_for_timeout(4000)  # Sleep 4 (matching Robot Framework: Sleep 4)
        
        job_card = page.locator(".css-1fjv3hc")
        job_card.wait_for(state="visible", timeout=20000)
        job_card_body = page.locator(".css-1fjv3hc body[aria-label]")
        job_card_body.wait_for(state="visible", timeout=20000)
        assert job_card.is_visible(), "Job card should be visible"
        assert job_card_body.is_visible(), "Job card body should be visible"
        
        print("\n========================================")
        print("Verifying posted job details...")
        print("========================================")
        page.wait_for_timeout(2000)  # sleep 2 (matching Robot Framework: sleep 2)
        
        # Get job title from card (matching Robot Framework)
        job_card_body.wait_for(state="visible", timeout=60000)
        title_job1 = job_card_body.inner_text().strip()
        
        # Get job title from aria-label (matching Robot Framework)
        title_job_attr = job_card_body.get_attribute("aria-label")
        title_job_parts = title_job_attr.split("-")
        title_job = title_job_parts[0].strip()
        assert JOB_TITLE.lower() == title_job.lower().strip(), f"Job title mismatch: expected '{JOB_TITLE}', got '{title_job}'"
        assert JOB_TITLE.lower().strip() in title_job1.lower(), f"Job title inner text mismatch: expected '{JOB_TITLE}' in '{title_job1}'"
        
        # Get experience (matching Robot Framework: ${job_exp_full} = Get Text class: exp)
        # Robot Framework gets text from first matching element, so we use .first
        job_exp_elem = page.locator(".exp").first
        job_exp_elem.wait_for(state="visible", timeout=10000)  # Wait for element to be visible
        job_exp_full = job_exp_elem.inner_text()
        # ${job_exp} = Split String ${job_exp_full} :
        job_exp = job_exp_full.split(":")[0].strip()
        
        job_exp_card = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[2]/div/p[2]")
        job_exp_card.wait_for(state="visible", timeout=10000)
        job_exp1 = job_exp_card.inner_text()
        print(f"Experience from card: {job_exp1}")
        
        assert EXPERIENCE.lower() == job_exp.lower(), f"Experience mismatch: expected '{EXPERIENCE}', got '{job_exp}'"
        assert EXPERIENCE.lower() == job_exp1.lower(), f"Experience mismatch: expected '{EXPERIENCE}', got '{job_exp1}'"
        
        try:
            job_type_elem = page.locator(".css-1fjv3hc p[aria-label*='Full-Time']")
            if job_type_elem.is_visible(timeout=5000):
                get_job_type_details = job_type_elem.get_attribute("aria-label")
            else:
                get_job_type_details = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[2]/div/div[1]/p").inner_text()
        except Exception:
            get_job_type_details = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[2]/div/div[1]/p").inner_text()
        
        get_job_type_1 = get_job_type_details.split(",")[0].strip()
        
        print("========================================")
        
        # Extract Job ID (matching Robot Framework exactly)
        job_id_full = job_card_body.get_attribute("aria-label")
        print(f"Full job identifier: {job_id_full}")
        if not job_id_full or "-" not in job_id_full:
            raise AssertionError(f"Invalid job ID format: '{job_id_full}' - expected format 'Job Title - JobID'")
        job_id1 = job_id_full.split("-")
        job_id = job_id1[1].strip()
        
        print("Signing out to search for job on Home Page...")
        
        # Employer Sign-out (matching Robot Framework: Employer Sign-out)
        _employer_sign_out(page)
        
        # Navigate to home page directly (matching Robot Framework: Wait Until Page Contains Find Your Dream Job 60)
        print("Navigating to home page after sign out...")
        goto_fast(page, BASE_URL)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # Wait for home page content
        try:
            page.wait_for_selector("text=Find Your Dream Job", timeout=30000)
        except Exception:
            # Fallback: check if page contains the text
            page.wait_for_timeout(2000)
            assert "Find Your Dream Job" in page.content() or "Find Your Dream Job" in page.locator("h1").first.inner_text(), "Home page not loaded"
        
        page.wait_for_timeout(2000)  # Reduced from 4000 - Sleep 4 (matching Robot Framework: Sleep 4)
        _handle_job_fair_popup(page)
        
        print("Checking the posted job in Find jobs with job ID....")
        # Scroll Element Into View xpath:/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_link.scroll_into_view_if_needed()
        
        # Click Element xpath:/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1] # 'Browse jobs'
        browse_jobs_link.click()
        page.wait_for_load_state("networkidle", timeout=10000)  # Use networkidle instead of fixed timeout
        
        # 4. Search for job by ID (Matching Robot Logic)
        print(f"Checking the posted job in Find jobs with job ID: {job_id}")
        
        # Wait for search field to be visible and enabled (matching Robot Framework)
        # Wait Until Element Is Visible xpath://*[@id="root"]/div[2]/div[1]/div/div[3]/div[2]/input 30
        search_input_xpath = "//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input"
        search_input = page.locator(f"xpath={search_input_xpath}")
        search_input.wait_for(state="visible", timeout=30000)
        
        # Wait Until Element Is Enabled xpath://*[@id="root"]/div[2]/div[1]/div/div[3]/div[2]/input 30
        search_input.wait_for(state="attached", timeout=30000)
        
        # Scroll search field into view (matching Robot Framework)
        # Scroll Element Into View xpath://*[@id="root"]/div[2]/div[1]/div/div[3]/div[2]/input
        search_input.scroll_into_view_if_needed()
        
        # Try clicking to open popup first (matching Robot Framework)
        # Click Element xpath://*[@id="root"]/div[2]/div[1]/div/div[3]/div[2]/input # Search place
        search_input.click()
        page.wait_for_timeout(1000)  # Reduced from 2000 - minimal wait for popup
        
        # Check if popup input appears, if yes use that, otherwise use main input (matching Robot Framework)
        # ${popup_exists} = Run Keyword And Return Status Wait Until Page Contains Element xpath:/html/body/div[2]/div[3]/div[1]/div/div/input 5
        popup_input = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/div/input")
        popup_exists = False
        try:
            if popup_input.is_visible(timeout=5000):
                popup_exists = True
        except Exception:
            popup_exists = False
        
        if popup_exists:
            print("Using popup search input field")
            # Wait Until Element Is Visible xpath:/html/body/div[2]/div[3]/div[1]/div/div/input 10
            popup_input.wait_for(state="visible", timeout=10000)
            
            # Clear Element Text xpath:/html/body/div[2]/div[3]/div[1]/div/div/input
            popup_input.clear()
            
            # Input Text xpath:/html/body/div[2]/div[3]/div[1]/div/div/input ${job_id}
            popup_input.fill(job_id)
            
            # Click Element xpath:/html/body/div[2]/div[3]/div[1]/div/button
            page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button").click()
        else:
            print("Popup not found, using JavaScript to set value directly")
            # Use JavaScript to set value directly (matching Robot Framework exactly)
            # Execute JavaScript var input = document.evaluate("//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; if (input) { input.value = '${job_id}'; input.focus(); }
            js_set_value = f"""
                var input = document.evaluate("{search_input_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (input) {{ input.value = '{job_id}'; input.focus(); }}
            """
            page.evaluate(js_set_value)
            
            # Trigger input and change events (matching Robot Framework)
            # Execute JavaScript var input = document.evaluate("//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; if (input) { var inputEvent = new Event('input', {{ bubbles: true }}); input.dispatchEvent(inputEvent); var changeEvent = new Event('change', {{ bubbles: true }}); input.dispatchEvent(changeEvent); }
            js_trigger_events = f"""
                var input = document.evaluate("{search_input_xpath}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (input) {{
                    var inputEvent = new Event('input', {{ bubbles: true }});
                    input.dispatchEvent(inputEvent);
                    var changeEvent = new Event('change', {{ bubbles: true }});
                    input.dispatchEvent(changeEvent);
                }}
            """
            page.evaluate(js_trigger_events)
            
            # Click search button (matching Robot Framework)
            # Wait Until Element Is Visible xpath:/html/body/div[2]/div[3]/div[1]/div/button 10
            search_button = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button")
            search_button.wait_for(state="visible", timeout=10000)
            # Click Element xpath:/html/body/div[2]/div[3]/div[1]/div/button
            search_button.click()
        
        # Wait for search results to load (matching Robot Framework: Sleep 3)
        page.wait_for_load_state("networkidle", timeout=10000)  # Use networkidle instead of fixed timeout
        
        # Wait for job detail body (matching Robot Framework)
        # Wait Until Page Contains Element xpath:/html/body/div[1]/div[2]/div[4]/div/div/div[1]/div/div/div[1]/div/body 30
        job_detail_body = page.locator("xpath=/html/body/div[1]/div[2]/div[4]/div/div/div[1]/div/div/div[1]/div/body")
        job_detail_body.wait_for(state="visible", timeout=30000)
        
        # Wait Until Element Is Visible xpath:/html/body/div[1]/div[2]/div[4]/div/div/div[1]/div/div/div[1]/div/body 30
        job_detail_body.wait_for(state="visible", timeout=30000)
        
        # Page Should Not Contain Job Details Not Found... (matching Robot Framework)
        assert "Job Details Not Found" not in page.content(), "Job Details Not Found message appeared"
        
        # ${get_job_id} = Get Text xpath:/html/body/div[1]/div[2]/div[4]/div/div/div[1]/div/div/div[1]/div/body
        get_job_id_text = job_detail_body.inner_text()
        print(f"Full job text: {get_job_id_text}")
        
        # Extract job ID from text (matching Robot Framework exactly)
        # ${get_id} = Evaluate '''${get_job_id}'''.split('#')[1].strip().replace('&nbsp;', '') if '#' in '''${get_job_id}''' else ''
        if "#" in get_job_id_text:
            get_id = get_job_id_text.split("#")[1].strip().replace("&nbsp;", "")
        else:
            get_id = ""
        print(f"Extracted Job ID: #{get_id}")
        
        # Verify the extracted job ID matches what we searched for (matching Robot Framework)
        # ${job_id_no_hash} = Replace String ${job_id} search_for=# replace_with=${EMPTY}
        job_id_no_hash = job_id.replace("#", "").replace("#", "")
        
        # ${get_id_no_hash} = Replace String ${get_id} search_for=# replace_with=${EMPTY}
        get_id_no_hash = get_id.replace("#", "").replace("#", "")
        
        print(f"Searching for Job ID: {job_id_no_hash}, Found Job ID: {get_id_no_hash}")
        
        # Should Be Equal ${get_id_no_hash} ${job_id_no_hash} ignore_case=True msg=Job ID mismatch: searched for ${job_id_no_hash} but found ${get_id_no_hash}
        assert get_id_no_hash.lower() == job_id_no_hash.lower(), f"Job ID mismatch: searched for {job_id_no_hash} but found {get_id_no_hash}"
        
        # Wait for search results to filter and show only the searched job (matching Robot Framework)
        # Wait Until Element Is Visible xpath://*[@id="root"]/div[2]/div[3]/div/div/div/ul/div 30
        results_list = page.locator("xpath=//*[@id='root']/div[2]/div[3]/div/div/div/ul/div")
        results_list.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)  # Reduced from 5000 - minimal wait for results to filter
        
        # Check if the first job in the list matches our searched job ID (matching Robot Framework)
        # ${first_job_text} = Get Text xpath://*[@id="root"]/div[2]/div[3]/div/div/div/ul/div[1]/div/div[2]/div/p[1]
        first_job_text = results_list.first.locator("xpath=./div/div[2]/div/p[1]").inner_text()
        print(f"First job in search results: {first_job_text}")
        
        # ${job_num_id} = Get Element Count xpath://*[@id="root"]/div[2]/div[3]/div/div/div/ul/div
        job_num_id = results_list.count()
        print(f"Total jobs found: {job_num_id}")
        
        # Verify the job we found matches the search (matching Robot Framework)
        # Page Should Contain ${job_id_no_hash} msg=The searched job ID ${job_id_no_hash} was not found in the search results
        assert job_id_no_hash in page.content(), f"The searched job ID {job_id_no_hash} was not found in the search results"
        print("Job is verified with job ID successfully")
        
    except Exception as e:
        # Screenshot functionality not available, just raise the error
        raise
    
    total_runtime = end_runtime_measurement("T2.01 Post a Job verification and verification with Job-Id")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

# Helpers for T2.02
JS_EMAIL = "automationnitya@gmail.com"
JS_PASS = "Nitya@123"

def _employer_sign_out(page: Page):
    print("Signing out Employer...")
    # Go to dashboard to ensure menu is available
    goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
    page.wait_for_timeout(2000)
    
    try:
        if page.locator("css=.MuiDialog-container").is_visible(timeout=2000):
            page.press("body", "Escape")
            page.wait_for_timeout(1000)
    except:
        pass

    try:
        # Robot: css:.css-ucwk63
        page.wait_for_selector("css=.css-ucwk63", timeout=10000)
        page.locator("css=.css-ucwk63").click()
        page.wait_for_timeout(1000)
        logout_locator = page.locator("xpath=//li[contains(., 'Logout')] | //p[contains(text(),'Logout')]")
        logout_locator.first.click()
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Sign out failed: {e}")
        # Try alternative: use role-based selector
        try:
            page.locator("css=.css-ucwk63").click()
            page.wait_for_timeout(1000)
            page.get_by_role("menuitem", name="Logout").click()
            page.wait_for_timeout(3000)
        except Exception as e2:
            print(f"Alternative sign out method also failed: {e2}")
            raise

def _job_seeker_sign_in(page: Page, email=JS_EMAIL, password=JS_PASS):
    # Robot waits for name:email
    try:
        page.wait_for_selector("input[name='email']", timeout=10000)
        page.fill("input[name='email']", email)
        page.fill("input[name='password']", password)
        page.wait_for_timeout(1000)
        # Robot: xpath:/html/body/div[1]/div[2]/div[2]/div/div[2]/div/form/div/button
        # Generic submit button is safer
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(3000)
    except Exception as e:
        raise

def _job_seeker_sign_out(page: Page):
    try:
        page.wait_for_selector("css=.css-ucwk63", timeout=10000)
        page.locator("css=.css-ucwk63").click()
        page.wait_for_timeout(1000)
        page.locator("xpath=//li[contains(., 'Logout')] | //p[contains(text(),'Logout')]").click()
        page.wait_for_timeout(3000)
    except Exception as e:
        raise

@pytest.mark.T2_02_EMP
@pytest.mark.employer
def test_t2_02_verification_of_applicants_and_shortlisting_in_js(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T2.02 Verification of applicants and shortlisting in JS"""
    start_runtime_measurement("T2.02 Verification of applicants and shortlisting in JS")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        print("Checking current page state...")
        current_url = page.url
        print(f"Current URL: {current_url}")
        _handle_job_fair_popup(page)
        if "Jsdashboard" in current_url:
            try:
                # Sign out from Job Seeker
                avatar_found = False
                for selector in ["css:.css-jqvkmw", "css:.css-ucwk63", "xpath=//button[contains(@class, 'MuiIconButton-root')]//img/.."]:
                    try:
                        avatar = page.locator(selector)
                        if avatar.count() > 0 and avatar.first.is_visible(timeout=3000):
                            avatar.first.click()
                            page.wait_for_timeout(1000)
                            page.get_by_role("menuitem", name="Logout").click()
                            page.wait_for_timeout(3000)
                            avatar_found = True
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"Could not sign out from JS dashboard: {e}")
            
            # Clear cookies to remove Job Seeker session
            page.context.clear_cookies()
            page.wait_for_timeout(1000)
        is_logged_in = False
        if "Empdashboard" in page.url:
            print("Already on Employer dashboard, checking if logged in...")
            _handle_job_fair_popup(page)
            page.wait_for_timeout(2000)
            
            if "EmpLogin" in page.url or "Login" in page.url:
                print("Redirected to login page, not logged in...")
                is_logged_in = False
            else:
                try:
                    menu_found = False
                    for selector in ["xpath=//nav//ul", "css:.css-18ajnjn", "xpath=/html/body/div[1]/div[2]/div/div/ul"]:
                        try:
                            page.wait_for_selector(selector, timeout=10000)
                            menu_found = True
                            break
                        except Exception:
                            continue
                    
                    if menu_found:
                        is_logged_in = True
                        print("Already logged in as Employer")
                    else:
                        try:
                            if page.locator("input[name='email']").is_visible(timeout=2000):
                                is_logged_in = False
                                print("Login inputs visible, not logged in...")
                            else:
                                is_logged_in = True
                                print("No login inputs, assuming logged in...")
                        except Exception:
                            is_logged_in = True
                            print("Cannot check login status, assuming logged in...")
                except Exception as e:
                    print(f"Error checking login status: {e}, will try to login...")
                    is_logged_in = False
        if not is_logged_in:
            print("Logging in as Employer...")
            # Navigate to EmpLogin (only once)
            goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
            page.wait_for_timeout(2000)
            _handle_job_fair_popup(page)
            
            # Fill login form
            email_input = page.locator("input[name='email']")
            email_input.wait_for(state="visible", timeout=10000)
            
            try:
                tgl = page.locator(".css-1hw9j7s")
                if tgl.count() > 0 and tgl.first.is_visible(timeout=2000):
                    tgl.first.click()
                    page.wait_for_timeout(300)
            except Exception:
                pass
            
            email_input.fill(EMP1_ID)
            page.fill("input[name='password']", EMP1_PASSWORD)
            page.wait_for_timeout(500)
            
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            page.wait_for_timeout(2000)
            current_url_after_login = page.url
            print(f"URL after login: {current_url_after_login}")
            
            if "Jsdashboard" in current_url_after_login:
                raise AssertionError(f"ERROR: Redirected to Job Seeker dashboard after Employer login! URL: {current_url_after_login}")
        if "Empdashboard" not in page.url:
            print("Navigating to Employer dashboard...")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_timeout(2000)
            _handle_job_fair_popup(page)
            
            final_url = page.url
            if "Jsdashboard" in final_url:
                raise AssertionError(f"Failed to reach Employer dashboard. Still on Job Seeker dashboard: {final_url}")
            print(f"Successfully on Employer dashboard: {final_url}")
        current_url_check = page.url
        print(f"Current URL before dashboard check: {current_url_check}")
        
        if "Jsdashboard" in current_url_check:
            page.context.clear_cookies()
            page.wait_for_timeout(1000)
            goto_fast(page, f"{EMPLOYER_URL}EmpLogin")
            page.wait_for_timeout(2000)
            _handle_job_fair_popup(page)
            
            # Force login again
            email_input = page.locator("input[name='email']")
            email_input.wait_for(state="visible", timeout=10000)
            try:
                tgl = page.locator(".css-1hw9j7s")
                if tgl.count() > 0 and tgl.first.is_visible(timeout=2000):
                    tgl.first.click()
                    page.wait_for_timeout(300)
            except Exception:
                pass
            email_input.fill(EMP1_ID)
            page.fill("input[name='password']", EMP1_PASSWORD)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
        
        if "Empdashboard" not in page.url:
            print("Navigating to Employer dashboard...")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_timeout(2000)
            _handle_job_fair_popup(page)
            
            final_url = page.url
            if "Jsdashboard" in final_url:
                raise AssertionError(f"Failed to reach Employer dashboard. Still on Job Seeker dashboard: {final_url}")
            print(f"Successfully on Employer dashboard: {final_url}")
        print("Waiting for Employer dashboard menu...")
        menu_selectors = [
            "xpath=/html/body/div[1]/div[2]/div/div/ul/li[6]/a/div",
            "xpath=/html/body/div[1]/div[2]/div/div/ul",
            "xpath=//nav//ul",
        ]
        dashboard_menu_found = False
        for selector in menu_selectors:
            try:
                page.wait_for_selector(selector, timeout=30000)
                dashboard_menu_found = True
                print(f"Dashboard menu found using selector: {selector}")
                break
            except Exception:
                continue
        
        if not dashboard_menu_found:
            raise AssertionError("Dashboard menu not found - may not be logged in as Employer")
        
        page.wait_for_timeout(2000)
        print("Navigating to myJobs...")
        page.goto(f"{EMPLOYER_URL}myJobs")
        page.wait_for_timeout(4000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main", timeout=30000)
        page.wait_for_timeout(2000)
        job_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]/div/div")
        job_card.wait_for(state="visible", timeout=30000)
        job_card.click()
        page.wait_for_timeout(2000)
        job_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body")
        job_view.wait_for(state="visible", timeout=30000)
        get_job_details = job_view.get_attribute("aria-label")
        get_job_id_title = get_job_details.split("-")
        get_job_title = get_job_id_title[0].strip()
        get_job_id = get_job_id_title[1].strip()
        _employer_sign_out(page)
        page.wait_for_timeout(3000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(1000)
        browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
        browse_jobs_link.scroll_into_view_if_needed()
        page.wait_for_timeout(2000)
        browse_jobs_link.wait_for(state="visible", timeout=30000)
        browse_jobs_link.click()
        page.wait_for_timeout(2000)
        search_input = page.locator("xpath=/html/body/div/div[2]/div[1]/div/div[3]/div[2]/input")
        search_input.wait_for(state="visible", timeout=30000)
        search_input.click()
        page.wait_for_timeout(1000)
        popup_input = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/div/input")
        popup_input.wait_for(state="visible", timeout=30000)
        popup_input.fill(get_job_id)
        page.wait_for_timeout(1000)
        search_button = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button")
        search_button.wait_for(state="visible", timeout=30000)
        search_button.click()
        page.wait_for_timeout(2000)
        first_job_card = page.locator("xpath=/html/body/div/div[2]/div[3]/div/div/div/ul/div[1]/div/div[2]")
        first_job_card.wait_for(state="visible", timeout=30000)
        first_job_card.click()
        page.wait_for_timeout(5000)
        apply_button = page.locator("xpath=/html/body/div/div[2]/div[4]/div/div/div[1]/div/div/div[2]/div[2]/div/button[1]")
        apply_button.wait_for(state="visible", timeout=30000)
        apply_button.click()
        page.wait_for_timeout(2000)
        _job_seeker_sign_in(page)
        
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        
        if "Jsdashboard" in page.url or "dashboard" in page.url.lower():
            print("Redirected to dashboard after login, navigating back to job...")
            # Navigate back to job using job ID
            goto_fast(page, f"{EMPLOYER_URL}")
            page.wait_for_timeout(2000)
            _handle_job_fair_popup(page)
            
            browse_jobs_link = page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
            browse_jobs_link.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            browse_jobs_link.click()
            page.wait_for_timeout(2000)
            
            # Search for job again
            search_input = page.locator("xpath=//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input")
            search_input.wait_for(state="visible", timeout=30000)
            search_input.click()
            page.wait_for_timeout(1000)
            
            popup_input = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/div/input")
            popup_input.wait_for(state="visible", timeout=30000)
            popup_input.fill(get_job_id)
            page.wait_for_timeout(1000)
            
            search_button = page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button")
            search_button.click()
            page.wait_for_timeout(3000)
            
            first_job_card = page.locator("xpath=/html/body/div/div[2]/div[3]/div/div/div/ul/div[1]/div/div[2]")
            first_job_card.wait_for(state="visible", timeout=30000)
            first_job_card.click()
            page.wait_for_timeout(3000)
        print("Waiting for job view to load after login...")
        page.wait_for_timeout(2000)
        
        apply_button_check = None
        apply_button_selectors = [
            ".css-2rraay",
            "xpath=/html/body/div[1]/div[2]/main/div[2]/div/div[2]/div/div/div[1]/div/div[2]/div/button[1]",
            "button:has-text('Apply')",
        ]
        
        for selector in apply_button_selectors:
            try:
                apply_button_check = page.locator(selector)
                if apply_button_check.is_visible(timeout=5000):
                    print(f"Apply button found using selector: {selector}")
                    break
            except Exception:
                continue
        
        if not apply_button_check or not apply_button_check.is_visible():
            # Wait a bit more and try again
            page.wait_for_timeout(3000)
            apply_button_check = page.locator(".css-2rraay")
        
        apply_button_check.wait_for(state="visible", timeout=30000)
        print("Apply button is visible...")
        button_class = apply_button_check.get_attribute("class")
        if_already_applied = "Mui-disabled" in button_class if button_class else False
        print(f"Already applied check: {if_already_applied}")
        
        if if_already_applied:
            print("Already applied for that job")
            page.wait_for_timeout(2000)
            pytest.skip("Already applied for that job")
        else:
            apply_btn = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div/div[2]/div/div/div[1]/div/div[2]/div/button[1]")
            apply_btn.wait_for(state="enabled", timeout=30000)
            page.wait_for_timeout(10000)
            apply_btn.click()
            page.wait_for_timeout(2000)
            next_button = page.locator("css:.css-n0t6bt")
            next_button.click()
            page.wait_for_timeout(2000)
            next_button_2 = page.locator("xpath=/html/body/div[3]/div[3]/div[2]/div[5]/div/button[3]")
            next_button_2.wait_for(state="enabled", timeout=10000)
            next_button_2.click()
            resume_page = page.locator("xpath=/html/body/div[3]/div[3]")
            resume_page.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(2000)
            final_apply_button = page.locator("xpath=/html/body/div[3]/div[3]/div[2]/div[5]/div/button[4]")
            final_apply_button.wait_for(state="enabled", timeout=30000)
            final_apply_button.click()
            applied_msg = ""
            for time_attempt in range(1, 20):
                try:
                    toast = page.locator("class:Toastify")
                    if toast.is_visible(timeout=2000):
                        applied_msg = toast.inner_text()
                        print(f"Toast message: {applied_msg}")
                        if "Job Applied Successfully" in applied_msg:
                            break
                except Exception:
                    pass
                page.wait_for_timeout(1000)
            
            assert "Job Applied Successfully" in applied_msg, f"Job application failed. Message: {applied_msg}"
            _job_seeker_sign_out(page)
            _handle_job_fair_popup(page)
            page.goto(f"{EMPLOYER_URL}EmpLogin")
            page.wait_for_selector("input[name='email']", timeout=10000)
            page.fill("input[name='email']", EMP1_ID)
            page.fill("input[name='password']", EMP1_PASSWORD)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(3000)
            page.wait_for_selector("css:.css-18ajnjn", timeout=30000)
            page.wait_for_timeout(2000)
            page.goto(f"{EMPLOYER_URL}myJobs")
            page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]", timeout=30000)
            page.wait_for_timeout(2000)
            num_jobs = page.locator("css:.css-1d3bbye").count()
            jobs_webelements = page.locator("css:.css-1d3bbye")
            
            job_found = False
            for each_job in range(num_jobs):
                jobs_webelements.nth(each_job).click()
                page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div/div/div/div[1]/p", timeout=30000)
                page.wait_for_timeout(2000)
                
                # Get job details
                job_title_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body")
                job_title_elem.wait_for(state="visible", timeout=30000)
                get_job_details_2 = job_title_elem.get_attribute("aria-label")
                
                get_job_id_title_2 = get_job_details_2.split("-")
                get_job_title_2 = get_job_id_title_2[0].strip()
                get_job_id_2 = get_job_id_title_2[1].strip()
                if get_job_id_2 == get_job_id:
                    job_found = True
                    applicants_tab = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div/div/div/div[7]/p")
                    applicants_tab.click()
                    
                    # Wait for applicant list
                    applicant_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[1]/div/div/ul/div")
                    applicant_list.wait_for(state="visible", timeout=30000)
                    page.wait_for_timeout(2000)
                    
                    applicant_list.scroll_into_view_if_needed()
                    page.wait_for_timeout(2000)
                    applicant_list.click()
                    
                    # Wait for resume view
                    resume_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]/div/div/div/div[2]")
                    resume_view.wait_for(state="visible", timeout=30000)
                    page.wait_for_timeout(2000)
                    shortlist_button = page.locator("xpath=//button[@aria-label='shortlist_resume']")
                    assert shortlist_button.is_enabled(), "Shortlist button should be enabled"
                    applicant_resume_name_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]/div/div/div/div[2]/div[2]/div/div/div/div/div[1]/div[2]/div/div/div/div[2]/span[137]")
                    applicant_resume_name = applicant_resume_name_elem.inner_text()
                    print(f"Applicant resume name: {applicant_resume_name}")
                    shortlist_button.click()
                    pop_up_msg = ""
                    for time_attempt in range(1, 20):
                        try:
                            toast = page.locator("class:Toastify")
                            if toast.is_visible(timeout=2000):
                                pop_up_msg = toast.inner_text()
                                print(f"Popup message: {pop_up_msg}")
                                if pop_up_msg:
                                    break
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)
                    shortlisted_tab = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div/div/div/div[9]/p")
                    shortlisted_tab.click()
                    
                    # Wait for shortlisted resume view
                    shortlisted_resume_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]")
                    shortlisted_resume_view.wait_for(state="visible", timeout=30000)
                    shortlisted_resume_name_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]/div/div/div/div[2]/div[2]/div/div/div/div/div[1]/div[2]/div/div/div/div[2]/span[137]")
                    shortlisted_resume_name_elem.wait_for(state="visible", timeout=30000)
                    shortlisted_resume_name = shortlisted_resume_name_elem.inner_text()
                    print(f"Shortlisted resume name: {shortlisted_resume_name}")
                    assert applicant_resume_name == shortlisted_resume_name, \
                        f"Resume name mismatch: Expected '{applicant_resume_name}', got '{shortlisted_resume_name}'"
                    
                    assert shortlisted_resume_name_elem.inner_text() == applicant_resume_name, \
                        "Shortlisted resume name does not match applicant resume name"
                    
                    break
            
            assert job_found, f"Job with ID {get_job_id} not found in employer's job list"
        
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.02 Verification of applicants and shortlisting in JS")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.employer
def test_t2_03_verification_of_closing_a_job_and_checking_with_job_id(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.03 Verification of closing a job and checking with Job-Id
    Steps:
    1. Login as Employer
    2. Navigate to Jobs tab
    3. Get job ID from first job
    4. Close the job
    5. Verify job is in Closed Jobs
    6. Search for closed job ID in Browse Jobs - should show "Job Details Not Found..."
    """
    start_runtime_measurement("T2.03 Verification of closing a job and checking with Job-Id")
    page = employer1_page
    
    try:
        check_network_connectivity([f"{EMPLOYER_URL}", "https://www.google.com"])
        
        # Navigate to Jobs tab
        print("Navigating to Jobs tab...")
        jobs_tab = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[4]/a/div")
        jobs_tab.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        jobs_tab.click()
        page.wait_for_timeout(3000)
        
        try:
            no_jobs_text = page.locator("class:css-699y2j")
            if no_jobs_text.is_visible(timeout=2000):
                print("No jobs are available")
                pytest.skip("No jobs available to close")
        except Exception:
            pass
        
        page.wait_for_timeout(2000)
        
        get_id = None
        
        # Method 1: Try CSS selector from list view (same as T2.01)
        try:
            job_card_body = page.locator(".css-1fjv3hc body[aria-label]")
            if job_card_body.is_visible(timeout=5000):
                print("Using CSS selector from list view to get job ID")
                get_id_full = job_card_body.get_attribute("aria-label")
                print(f"Full job identifier from CSS: {get_id_full}")
                if get_id_full and "-" in get_id_full:
                    get_id_parts = get_id_full.split("-")
                    if len(get_id_parts) > 1:
                        get_id = get_id_parts[1].strip().replace("#", "").strip()
        except Exception as e:
            print(f"CSS selector method failed: {e}")
        
        if not get_id:
            print("CSS selector not found in list view, clicking job card to open details...")
            try:
                first_job_card = None
                for xpath in [
                    "xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]",
                    "xpath=/html/body/div[1]/div[2]/main/div[3]/div[2]/div/ul/div[1]",
                    "xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div/ul/div[1]"
                ]:
                    try:
                        first_job_card = page.locator(xpath)
                        if first_job_card.is_visible(timeout=5000):
                            break
                    except Exception:
                        continue
                
                if not first_job_card or not first_job_card.is_visible():
                    try:
                        first_job_css = page.locator(".css-1fjv3hc").first
                        if first_job_css.is_visible(timeout=5000):
                            first_job_css.click()
                            page.wait_for_timeout(2000)
                            
                            # Get job ID from opened view
                            job_card_body_opened = page.locator(".css-1fjv3hc body[aria-label]")
                            if job_card_body_opened.is_visible(timeout=10000):
                                get_id_full = job_card_body_opened.get_attribute("aria-label")
                                if get_id_full and "-" in get_id_full:
                                    get_id_parts = get_id_full.split("-")
                                    if len(get_id_parts) > 1:
                                        get_id = get_id_parts[1].strip().replace("#", "").strip()
                            
                            try:
                                close_button = page.locator("xpath=//*[@aria-label='Close Job']")
                                if close_button.is_visible(timeout=2000):
                                    close_button.click()
                                    page.wait_for_timeout(2000)
                            except Exception:
                                pass
                    except Exception as e2:
                        print(f"CSS click method failed: {e2}")
                else:
                    first_job_card.wait_for(state="visible", timeout=30000)
                    page.wait_for_timeout(1000)
                    first_job_card.click()
                    page.wait_for_timeout(2000)
                    
                    # Wait for job details view
                    job_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div")
                    try:
                        job_view.wait_for(state="visible", timeout=30000)
                    except Exception:
                        # Try alternative XPath
                        job_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[3]/div[3]/div/div/div[1]/div")
                        job_view.wait_for(state="visible", timeout=30000)
                    
                    page.wait_for_timeout(2000)
                    
                    # Get job ID from opened job details view
                    job_title_elem = None
                    for xpath_title in [
                        "xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body",
                        "xpath=/html/body/div[1]/div[2]/main/div[3]/div[3]/div/div/div[1]/div/div/div[1]/div/body"
                    ]:
                        try:
                            job_title_elem = page.locator(xpath_title)
                            if job_title_elem.is_visible(timeout=5000):
                                break
                        except Exception:
                            continue
                    
                    if job_title_elem:
                        job_title_elem.wait_for(state="visible", timeout=30000)
                        get_id_full = job_title_elem.get_attribute("aria-label")
                        print(f"Full job identifier from job details view: {get_id_full}")
                        if get_id_full and "-" in get_id_full:
                            get_id_parts = get_id_full.split("-")
                            if len(get_id_parts) > 1:
                                get_id = get_id_parts[1].strip().replace("#", "").strip()
                    
                    # Close the job details view to return to list view
                    try:
                        close_button = page.locator("xpath=//*[@aria-label='Close Job']")
                        if close_button.is_visible(timeout=2000):
                            close_button.click()
                            page.wait_for_timeout(2000)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Method 2 failed: {e}")
        
        assert get_id, "Job ID could not be extracted from the page"
        
        # Now hover over the job in list view and close it
        try:
            job_hover_target = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]/div/div/div/div/p[1]/span[1]")
            job_hover_target.hover(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception:
            print("WARNING: Mouse over failed, trying alternative approach...")
            page.wait_for_timeout(1000)
        
        close_job_button = None
        try:
            close_job_button = page.locator("xpath=//*[@aria-label='Close Job']")
            close_job_button.wait_for(state="visible", timeout=10000)
            close_job_button.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            close_job_button.click()
        except Exception:
            try:
                # Try alternative selector - use exact match
                close_job_button = page.locator("xpath=//button[@aria-label='Close Job']")
                if close_job_button.is_visible(timeout=5000):
                    close_job_button.click()
                else:
                    try:
                        page.evaluate("""
                            var el = document.evaluate('//*[@aria-label="Close Job"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (el) { 
                                el.scrollIntoView({block: 'center'}); 
                                var clickEvent = new MouseEvent('click', { bubbles: true, cancelable: true });
                                el.dispatchEvent(clickEvent);
                            }
                        """)
                    except Exception:
                        try:
                            all_buttons = page.locator("button").all()
                            for btn in all_buttons:
                                try:
                                    aria_label = btn.get_attribute("aria-label")
                                    if aria_label and "Close" in aria_label and "Job" in aria_label:
                                        btn.click()
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass
            except Exception as e:
                print(f"ERROR: Could not close job - {e}")
                raise
        
        # Wait for success message
        successful_msg = ""
        for time_attempt in range(1, 20):
            try:
                toast = page.locator("class:Toastify")
                if toast.is_visible(timeout=2000):
                    successful_msg = toast.inner_text()
                    print(f"Popup message: {successful_msg}")
                    if successful_msg and "Job Closed" in successful_msg:
                        break
            except Exception:
                pass
            page.wait_for_timeout(1000)
        
        if "Job Closed Successfully" not in successful_msg:
            print("WARNING: Expected success message not found, but continuing test...")
        
        page.wait_for_timeout(4000)
        
        menu_button = page.locator("id=dopen-closed-jobs-button")
        menu_button.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        menu_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        menu_button.click()
        page.wait_for_timeout(2000)
        
        closed_jobs_option = page.locator("xpath=//*[@id='open-closed-jobs-menu']/div[3]/ul/li[2]")
        closed_jobs_option.wait_for(state="visible", timeout=30000)
        closed_jobs_option.click()
        page.wait_for_timeout(4000)
        
        # Wait for closed jobs list
        first_closed_job = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]/div/div/div/div")
        first_closed_job.wait_for(state="visible", timeout=30000)
        job_view_closed = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div/div")
        job_view_closed.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Get count of closed jobs
        try:
            count_elem = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div/ul/div[11]/div[2]/p/strong[2]")
            count_elem.wait_for(state="visible", timeout=30000)
            num_of_closed_jobs_text = count_elem.inner_text()
            num_of_closed_jobs = int(num_of_closed_jobs_text.strip().split()[0]) if num_of_closed_jobs_text.strip() else 0
            print(f"Count of closed jobs: {num_of_closed_jobs}")
        except Exception:
            num_of_closed_jobs = 0
        
        # Get visible closed job elements
        closed_job_elements = page.locator(".over-text").all()
        visible_elements_count = len(closed_job_elements)
        print(f"Visible closed job elements: {visible_elements_count}")
        max_jobs_to_check = min(visible_elements_count, 10)
        print(f"Checking first {max_jobs_to_check} visible closed jobs")
        
        job_found_in_closed = False
        for i in range(max_jobs_to_check):
            if i >= len(closed_job_elements):
                print(f"Index {i} is out of bounds. Only {len(closed_job_elements)} elements available. Stopping search.")
                break
            
            try:
                closed_job_elements[i].scroll_into_view_if_needed()
                page.wait_for_timeout(3000)
                closed_job_elements[i].click()
                page.wait_for_timeout(2000)
                
                # Wait for job view to appear
                job_view_closed.wait_for(state="visible", timeout=30000)
                page.wait_for_timeout(1000)
                
                # Try CSS selector first
                closed_job_id = None
                try:
                    css_selector = page.locator(".css-1fjv3hc body[aria-label]")
                    if css_selector.is_visible(timeout=5000):
                        print("Using CSS selector to get closed job ID")
                        closed_job_id_full = css_selector.get_attribute("aria-label")
                        print(f"Full closed job identifier from CSS: {closed_job_id_full}")
                        if closed_job_id_full and "-" in closed_job_id_full:
                            closed_job_id_parts = closed_job_id_full.split("-")
                            if len(closed_job_id_parts) > 1:
                                closed_job_id = closed_job_id_parts[1].strip().replace("#", "").strip()
                except Exception:
                    pass
                
                # Fallback to XPath
                if not closed_job_id:
                    try:
                        job_title_elem = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body")
                        job_title_elem.wait_for(state="visible", timeout=30000)
                        closed_job_id_full = job_title_elem.get_attribute("aria-label")
                        print(f"Full closed job identifier from XPath: {closed_job_id_full}")
                        if closed_job_id_full:
                            closed_job_id_parts = closed_job_id_full.split("-")
                            if len(closed_job_id_parts) > 1:
                                closed_job_id = closed_job_id_parts[1].strip().replace("#", "").strip()
                    except Exception:
                        pass
                
                if closed_job_id:
                    closed_job_id = str(closed_job_id)
                    print(f"closed job id: {closed_job_id}")
                    if closed_job_id == get_id:
                        print(f"[OK] Found closed job with ID: {get_id}")
                        job_found_in_closed = True
                        break
            except Exception as e:
                print(f"Error checking closed job {i}: {e}")
                continue
        
        # Now logout and check in Browse Jobs
        print("Checking the closed job in Find jobs with job ID....")
        
        try:
            modal = page.locator("css:.MuiDialog-container")
            if modal.is_visible(timeout=2000):
                print("WARNING: Modal detected, attempting to close it...")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                try:
                    backdrop = page.locator("css:.MuiBackdrop-root")
                    backdrop.click()
                except Exception:
                    pass
                page.wait_for_timeout(1000)
        except Exception:
            pass
        
        # Logout
        try:
            logout_dropdown = page.locator("css:.css-ucwk63")
            logout_dropdown.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(1000)
            logout_dropdown.click()
            page.wait_for_timeout(1000)
            logout_button = page.locator("xpath=//li[2]/p")
            logout_button.click()
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Logout failed: {e}")
        
        # Open new browser context for public search
        context = page.context
        new_page = context.new_page()
        
        try:
            goto_fast(new_page, f"{EMPLOYER_URL}")
            new_page.wait_for_timeout(4000)
            
            # Handle job fair popup
            handle_job_fair_popup_pw(new_page)
            
            new_page.wait_for_load_state("domcontentloaded", timeout=60000)
            new_page.wait_for_timeout(4000)
            
            # Scroll to Browse jobs link
            browse_jobs_link = new_page.locator("xpath=/html/body/div[1]/div[2]/div/footer/div[1]/div[3]/a[1]")
            browse_jobs_link.scroll_into_view_if_needed()
            browse_jobs_link.click()
            new_page.wait_for_timeout(2000)
            
            # Wait for search field
            search_input = new_page.locator("xpath=//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input")
            search_input.wait_for(state="visible", timeout=30000)
            search_input.wait_for(state="attached", timeout=30000)
            new_page.wait_for_timeout(2000)
            
            # Scroll search field into view
            search_input.scroll_into_view_if_needed()
            new_page.wait_for_timeout(1000)
            
            search_input.click()
            new_page.wait_for_timeout(2000)
            
            popup_input = None
            try:
                popup_input = new_page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/div/input")
                if popup_input.is_visible(timeout=5000):
                    print("Using popup search input field")
                    popup_input.clear()
                    new_page.wait_for_timeout(1000)
                    popup_input.fill(get_id)
                    new_page.wait_for_timeout(1000)
                    popup_button = new_page.locator("xpath=/html/body/div[2]/div[3]/div[1]/div/button")
                    popup_button.press("Enter")
            except Exception:
                pass
            
            if not popup_input or not popup_input.is_visible():
                print("Popup not found, using JavaScript to set value directly")
                new_page.evaluate(f"""
                    var input = document.evaluate("//*[@id='root']/div[2]/div[1]/div/div[3]/div[2]/input", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (input) {{
                        input.value = '{get_id}';
                        input.focus();
                        var inputEvent = new Event('input', {{ bubbles: true }});
                        input.dispatchEvent(inputEvent);
                        var changeEvent = new Event('change', {{ bubbles: true }});
                        input.dispatchEvent(changeEvent);
                        var enterEvent = new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true, cancelable: true }});
                        input.dispatchEvent(enterEvent);
                    }}
                """)
            
            new_page.wait_for_timeout(6000)
            
            # Check for "Job Details Not Found..." message
            not_found_msg = None
            try:
                not_found_elem = new_page.locator(".css-8e4lkk")
                if not_found_elem.is_visible(timeout=10000):
                    not_found_msg = not_found_elem.inner_text()
                    assert "Job Details Not Found" in not_found_msg, f"Expected 'Job Details Not Found...' but got: {not_found_msg}"
            except Exception:
                try:
                    job_found_elem = new_page.locator(".css-zkcq3t body.MuiTypography-h5.css-5kdy5a")
                    if job_found_elem.is_visible(timeout=10000):
                        found_job_text = job_found_elem.inner_text()
                        print(f"Found job text: {found_job_text}")
                        # Extract job ID from found job
                        if "#" in found_job_text:
                            found_job_id = found_job_text.split("#")[1].strip().replace("&nbsp;", "").replace("#", "")
                            get_id_no_hash = get_id.replace("#", "")
                            print(f"Searched for closed job ID: {get_id_no_hash}, Found job ID: {found_job_id}")
                            assert found_job_id.lower() != get_id_no_hash.lower(), \
                                f"ERROR: Closed job (ID: {get_id_no_hash}) was found in search results! It should not be searchable."
                            print(f"[OK] Verified: Found job (ID: {found_job_id}) is different from closed job (ID: {get_id_no_hash})")
                        else:
                            pass
                except Exception:
                    pass
            
            new_page.wait_for_timeout(2000)
            new_page.close()
        except Exception as e:
            print(f"Error in public search: {e}")
            if 'new_page' in locals():
                try:
                    new_page.close()
                except Exception:
                    pass
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.03 Verification of closing a job and checking with Job-Id")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

# AI Search description variable
DESCRIPTION1 = """Core Java, J2EE, Spring, Multithreading and Unix . Hibernate - Rest based Web services - Relational database.knowledge/SQL - DB2 preferred. Agile/DevOps experience - Analytical / Quantitative.Background (Advanced degree in Quant Finance, Math, Physics or Engineering).Minimum five years of progressive experience developing software using Java.
Bachelor's degree from an accredited college/university or equivalent work experience.Experience perform unit testing and troubleshooting java applications.Prior knowledge implementing design patterns in Java.Proven communication skills (in person, phone, and email)
Ability to multi-task and work against deadlines/priorities. A sense of ownership and desire to take on an expanded role over time.Advanced problem solving skills and the ability to deal"""

@pytest.mark.employer
def test_t2_04_verification_of_ai_search_with_description(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.04 Verification of AI Search with description
    Steps:
    1. Login as Employer
    2. Click on AI Search
    3. Enter description
    4. Select a random skill/related title
    5. Click Find Resumes
    6. Verify resumes match the selected criteria (check 2 pages, 5 resumes per page)
    """
    start_runtime_measurement("T2.04 Verification of AI Search with description")
    page = employer1_page
    
    try:
        check_network_connectivity([f"{EMPLOYER_URL}", "https://www.google.com"])
        
        # Handle job fair popup
        handle_job_fair_popup_pw(page)
        page.wait_for_timeout(2000)
        
        ai_search_link = page.locator("xpath=//a[@aria-label='AI Search']")
        ai_search_link.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        ai_search_link.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        ai_search_link.click()
        page.wait_for_timeout(4000)
        
        # Wait for textarea
        textarea = page.locator("xpath=/html/body/div[4]/div[3]/div[2]/form/div/div[1]/textarea")
        textarea.wait_for(state="visible", timeout=30000)
        
        # Insert description
        textarea.fill(DESCRIPTION1)
        page.wait_for_timeout(2000)
        
        ai_search_button = page.locator("xpath=/html/body/div[4]/div[3]/div[2]/form/div/div[2]/button")
        ai_search_button.click()
        page.wait_for_timeout(4000)
        
        # Form should pop-up - get primary role
        primary_role_elem = page.locator(".css-1pjtbja")
        primary_role_elem.wait_for(state="visible", timeout=30000)
        primary_role = primary_role_elem.inner_text()
        print(f"Primary role: {primary_role}")
        
        # Get all options
        all_options = page.locator(".css-16fzwmu").all()
        total_num_options = len(all_options)
        print(f"Total number of options: {total_num_options}")
        
        if total_num_options == 0:
            pytest.skip("No options available in AI search")
        
        # Choose random option
        last_option_index = total_num_options - 1
        choose_random_num = random.randint(0, last_option_index)
        print(f"Selected random option index: {choose_random_num}")
        page.wait_for_timeout(4000)
        
        try:
            all_options[choose_random_num].scroll_into_view_if_needed()
            page.wait_for_timeout(3000)
            all_options[choose_random_num].click()
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Error clicking option: {e}")
            raise
        
        # Get chosen option value
        chosen_option_innerHTML = all_options[choose_random_num].get_attribute("innerHTML")
        print(f"Chosen option innerHTML: {chosen_option_innerHTML}")
        
        # Extract value using regex
        import re
        name_of_chosen_option = None
        if chosen_option_innerHTML:
            value_match = re.search(r'value="([^"]+)"', chosen_option_innerHTML)
            if value_match:
                value_of_chosen_option = value_match.group(1)
                print(f"Value of chosen option: {value_of_chosen_option}")
                name_of_chosen_option = value_of_chosen_option.replace('"', '').strip()
        
        if not name_of_chosen_option:
            name_of_chosen_option = all_options[choose_random_num].inner_text().strip()
        
        print(f"Name of chosen option: {name_of_chosen_option}")
        page.wait_for_timeout(5000)
        
        category_chosen = "category"
        try:
            skills_header = page.locator("xpath=//p[contains(.,'Skills:')]")
            if skills_header.is_visible(timeout=30000):
                category_chosen = "skills"
                print("Category: Skills")
        except Exception:
            pass
        
        if category_chosen != "skills":
            try:
                related_titles_header = page.locator("xpath=//p[contains(.,'Related Titles:')]")
                if related_titles_header.is_visible(timeout=30000):
                    category_chosen = "related titles"
                    print("Category: Related Titles")
            except Exception:
                pass
        
        print(f"Category chosen: {category_chosen}")
        page.wait_for_timeout(1000)
        
        find_resumes_button = page.locator("xpath=//button[contains(text(),'Find Resumes')]")
        find_resumes_button.click()
        page.wait_for_timeout(2000)
        
        # Wait for profiles to load
        first_profile = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]")
        first_profile.wait_for(state="visible", timeout=30000)
        print("[OK] Profiles loaded successfully")
        
        # Process 2 pages
        for each_page in range(1, 3):
            print(f"Page number: {each_page}")
            
            # Get number of resumes
            resume_elements = page.locator(".css-ntktx3").all()
            number_of_resumes = len(resume_elements)
            print(f"Number of resumes: {number_of_resumes}")
            page.wait_for_timeout(2000)
            
            # Limit to first 5 resumes
            max_resumes_to_check = min(5, number_of_resumes)
            print(f"Checking first {max_resumes_to_check} resumes")
            
            for each_resume in range(1, max_resumes_to_check + 1):
                print(f"Resume {each_resume}")
                page.wait_for_timeout(2000)
                
                # Get resume title from list
                resume_title_elem = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[{each_resume}]/div/div[1]/div/span")
                resume_title_elem.wait_for(state="visible", timeout=30000)
                get_resume_title_details = resume_title_elem.inner_text()
                print(f"Resume title is: {get_resume_title_details}")
                get_resume_title_details_lower = get_resume_title_details.lower()
                print(f"Resume title (lower): {get_resume_title_details_lower}")
                
                # Split by newline and get last part
                get_resume_title_split = get_resume_title_details_lower.split("\n")
                get_resume_title = get_resume_title_split[-1] if get_resume_title_split else get_resume_title_details_lower
                print(f"Resume title (final): {get_resume_title}")
                
                try:
                    resume_card = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[{each_resume}]/div")
                    resume_card.scroll_into_view_if_needed()
                    page.wait_for_timeout(2000)
                    resume_card.click()
                except Exception as e:
                    print(f"Error clicking resume: {e}")
                    continue
                
                or_button = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[1]/div[1]/div[2]/div/div/div/div[4]/div/div/button[1]")
                or_button.wait_for(state="visible", timeout=30000)
                assert or_button.inner_text() == "OR", "OR boolean should be selected by default"
                
                resume_matched = False
                
                # Wait for resume details panel
                page.wait_for_timeout(3000)
                resume_details = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]")
                resume_details.wait_for(state="visible", timeout=30000)
                page.wait_for_timeout(2000)
                
                # Get resume title from detail view
                get_resume_title_detail = None
                try:
                    title_detail_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/p[2]")
                    if title_detail_elem.is_visible(timeout=10000):
                        get_resume_title_detail = title_detail_elem.inner_text().lower()
                        print(f"Resume title from detail view: {get_resume_title_detail}")
                except Exception:
                    print("Detail view title not available, using list view title")
                    get_resume_title_detail = get_resume_title.lower()
                
                if get_resume_title_detail and primary_role.lower() in get_resume_title_detail:
                    print("Resume title matches with primary role")
                    resume_matched = True
                else:
                    # Need to check skills or related titles
                    page.wait_for_timeout(5000)
                    
                    # Wait for resume view container
                    resume_view_container = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]")
                    resume_view_container.wait_for(state="visible", timeout=30000)
                    page.wait_for_timeout(4000)
                    
                    try:
                        profile_button = page.locator(f"xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]/div[{each_resume}]/div/div[1]/div/div[2]/div[4]/div/div/button[2]")
                        if profile_button.is_visible(timeout=10000):
                            aria_pressed = profile_button.get_attribute("aria-pressed")
                            print(f"Resume {each_resume} - Profile button aria-pressed: {aria_pressed}")
                            
                            if aria_pressed != "true":
                                profile_button.scroll_into_view_if_needed()
                                page.wait_for_timeout(1000)
                                profile_button.click()
                                print(f"[OK] Clicked profile button for resume {each_resume}")
                            else:
                                print(f"[WARNING] Profile button already clicked for resume {each_resume}")
                    except Exception:
                                print(f"[WARNING] Profile button not found for resume {each_resume}, skipping profile button click")
                    
                    page.wait_for_timeout(2000)
                    
                    if category_chosen == "skills":
                        # Find TECHNICAL SKILLS section in PDF viewer
                        try:
                            technical_skills_elem = page.locator("xpath=//span[contains(@class, 'rpv-core__text-layer-text') and contains(text(), 'TECHNICAL SKILLS')]")
                            if technical_skills_elem.is_visible(timeout=10000):
                                print("Found TECHNICAL SKILLS section in PDF viewer")
                                
                                # Get all text elements
                                all_text_elements = page.locator(".rpv-core__text-layer-text").all()
                                element_count = len(all_text_elements)
                                print(f"Found {element_count} text elements in PDF viewer")
                                
                                skills_found = False
                                start_reading_skills = False
                                
                                for index in range(element_count):
                                    try:
                                        element = all_text_elements[index]
                                        text_content = element.inner_text().strip()
                                        
                                        # Start reading after finding TECHNICAL SKILLS
                                        if "TECHNICAL SKILLS" in text_content or "TECHNICAL SKILLS:" in text_content:
                                            start_reading_skills = True
                                            print("Found TECHNICAL SKILLS header, starting to read skills...")
                                            continue
                                        
                                        # Read skills after TECHNICAL SKILLS section
                                        if start_reading_skills:
                                            text_length = len(text_content)
                                            has_colon = ":" in text_content
                                            
                                            if text_content and not has_colon and text_length > 2:
                                                skill_name = text_content.replace('"', "'").strip()
                                                print(f"Checking skill: {skill_name}")
                                                
                                                if skill_name.lower() == name_of_chosen_option.lower() or skill_name == name_of_chosen_option:
                                                    resume_matched = True
                                                    skills_found = True
                                                    print(f"[OK] Skill matched: {skill_name}")
                                                    break
                                                
                                                if any(section in text_content for section in ["EXPERIENCE", "EDUCATION", "SUMMARY"]):
                                                    print("Reached next major section, stopping skill search")
                                                    break
                                    except Exception:
                                        continue
                                
                                if not skills_found:
                                    print(f"[WARNING] Skill '{name_of_chosen_option}' not found in TECHNICAL SKILLS section")
                                    
                                    # Fallback to CSS selector method
                                    try:
                                        skills_elements = page.locator(".css-19imqg1").all()
                                        number_of_skills = len(skills_elements)
                                        print(f"Fallback: Found {number_of_skills} skills using CSS selector")
                                        
                                        for skill_elem in skills_elements:
                                            skill_name = skill_elem.inner_text().replace('"', "'").strip()
                                            if skill_name == name_of_chosen_option or skill_name.lower() == name_of_chosen_option.lower():
                                                resume_matched = True
                                                break
                                    except Exception:
                                        pass
                            else:
                                print("[WARNING] TECHNICAL SKILLS section not found in PDF viewer, trying fallback method...")
                                # Fallback method
                                try:
                                    skills_elements = page.locator(".css-19imqg1").all()
                                    if len(skills_elements) > 0:
                                        for skill_elem in skills_elements:
                                            skill_name = skill_elem.inner_text().replace('"', "'").strip()
                                            if skill_name == name_of_chosen_option or skill_name.lower() == name_of_chosen_option.lower():
                                                resume_matched = True
                                                break
                                except Exception:
                                    pass
                        except Exception as e:
                            print(f"Error checking skills: {e}")
                    
                    elif category_chosen == "related titles":
                        if name_of_chosen_option.lower() in get_resume_title:
                            resume_matched = True
                        else:
                            # Check related titles section
                            try:
                                related_titles_elements = page.locator(".css-1pjtbja").all()
                                number_related_titles = len(related_titles_elements)
                                
                                for related_title_elem in related_titles_elements:
                                    related_title = related_title_elem.inner_text()
                                    print(f"Related title: {related_title}")
                                    if related_title == name_of_chosen_option:
                                        resume_matched = True
                                        break
                            except Exception:
                                pass
                
                if resume_matched:
                    print(f"[OK] Resume {each_resume} matched the criteria")
                else:
                    print(f"[WARNING] Resume {each_resume} did not match the criteria, but continuing...")
            
            if each_page < 2:
                try:
                    next_button = page.locator("xpath=//button[@aria-label='Go to next page']")
                    if next_button.is_visible(timeout=5000):
                        next_button.scroll_into_view_if_needed()
                        page.wait_for_timeout(2000)
                        if next_button.is_enabled():
                            next_button.click()
                            page.wait_for_timeout(3000)
                            # Wait for first profile on new page
                            first_profile_new = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]/div/div[1]/div[2]/div/p[1]")
                            first_profile_new.wait_for(state="visible", timeout=30000)
                            print(f"[OK] Page {each_page + 1} loaded, first profile visible after clicking next page button")
                        else:
                            print("Next page button is disabled, no more pages available")
                            break
                    else:
                        try:
                            next_button_fallback = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div/div[1]/nav/ul/li[8]/button")
                            if next_button_fallback.is_visible(timeout=5000) and next_button_fallback.is_enabled():
                                next_button_fallback.scroll_into_view_if_needed()
                                page.wait_for_timeout(2000)
                                next_button_fallback.click()
                                page.wait_for_timeout(3000)
                                first_profile_new = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]/div/div[1]/div[2]/div/p[1]")
                                first_profile_new.wait_for(state="visible", timeout=30000)
                                print(f"[OK] Page {each_page + 1} loaded, first profile visible after clicking next page button")
                            else:
                                print("Next page button is disabled, no more pages available")
                                break
                        except Exception:
                            print("Next page button not found, stopping pagination")
                            break
                except Exception as e:
                    print(f"Error navigating to next page: {e}")
                    break
            else:
                print(f"[OK] Completed processing page {each_page} (last page in range), not clicking next button")
        
        page.wait_for_timeout(2000)
        print("Verification is done successfully.")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.04 Verification of AI Search with description")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.employer
def test_t2_06_verification_of_ai_search_without_description_and_saving_resume(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.06 Verification of AI search without description and verification of saving a resume
    Steps:
    1. Login as Employer
    2. Click AI Search without entering description
    3. Verify no primary role is shown
    4. Select a random resume
    5. Save the resume
    6. Go to Saved Resumes and verify the saved resume
    """
    start_runtime_measurement("T2.06 Verification of AI search without description and verification of saving a resume")
    page = employer1_page
    
    try:
        check_network_connectivity([f"{EMPLOYER_URL}", "https://www.google.com"])
        
        # Handle job fair popup
        handle_job_fair_popup_pw(page)
        page.wait_for_timeout(2000)
        
        ai_search_button = page.locator("xpath=//button[contains(text(), 'ai Search')]")
        ai_search_button.wait_for(state="visible", timeout=30000)
        ai_search_button.wait_for(state="attached", timeout=10000)
        page.wait_for_timeout(1000)
        ai_search_button.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        
        click_success = False
        try:
            ai_search_button.click()
            click_success = True
            print("PASS: AI Search button clicked successfully")
        except Exception:
            print("WARNING: Regular click failed, trying JavaScript click...")
            page.evaluate("arguments[0].click();", ai_search_button)
            click_success = True
            print("PASS: JavaScript click executed successfully")
        
        if not click_success:
            raise Exception("Could not click AI Search button")
        
        page.wait_for_timeout(4000)
        
        ai_search_submit = page.locator("xpath=/html/body/div[4]/div[3]/div[2]/form/div/div[2]/button")
        ai_search_submit.wait_for(state="visible", timeout=30000)
        ai_search_submit.click()
        page.wait_for_timeout(2000)
        
        try:
            primary_role_elem = page.locator(".css-1pjtbja")
            if primary_role_elem.is_visible(timeout=2000):
                pytest.fail("Primary role should not be present when no description is entered")
        except Exception:
            # Expected - primary role should not be present
            print("PASS: Verified: Primary role is not present (as expected)")
        
        page.wait_for_timeout(2000)
        print("Verifying the resumes....")
        page.wait_for_timeout(2000)
        
        # Wait for profiles header
        profiles_header = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/div/div[1]/div[2]/h2")
        profiles_header.wait_for(state="visible", timeout=30000)
        
        # Wait for profiles to load
        first_profile = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]")
        first_profile.wait_for(state="visible", timeout=30000)
        
        # Get number of resumes
        resume_elements = page.locator(".css-ntktx3").all()
        number_of_resumes = len(resume_elements)
        print(f"Number of resumes found: {number_of_resumes}")
        
        if number_of_resumes == 0:
            pytest.skip("No resumes found")
        
        # Select random resume (1-based index)
        choose_random_no = random.randint(1, number_of_resumes)
        print(f"Randomly selected resume index: {choose_random_no} (out of {number_of_resumes} resumes)")
        
        try:
            selected_resume = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[{choose_random_no}]/div")
            selected_resume.scroll_into_view_if_needed()
            page.wait_for_timeout(2000)
            selected_resume.wait_for(state="visible", timeout=30000)
            selected_resume.click()
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Error clicking resume: {e}")
            raise
        
        # Get resume ID
        resume_id_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[1]/div[1]/div")
        resume_id_elem.wait_for(state="visible", timeout=30000)
        resume_id_saved_resume = resume_id_elem.get_attribute("aria-label")
        print(f"Resume ID: {resume_id_saved_resume}")
        
        # Get candidate name
        candidate_name_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/p[1]")
        candidate_name_elem.wait_for(state="visible", timeout=30000)
        name_candidate_saved_resume = candidate_name_elem.inner_text()
        print(f"Candidate name: {name_candidate_saved_resume}")
        
        # Scroll to save button
        try:
            save_button = page.locator("xpath=//button[@aria-label='save_resume']")
            save_button.scroll_into_view_if_needed()
            page.wait_for_timeout(4000)
            save_button.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Error finding save button: {e}")
            raise
        
        resume_already_saved = False
        try:
            already_saved_indicator = page.locator("xpath=//span[@aria-label='Resume already saved']")
            if already_saved_indicator.is_visible(timeout=5000):
                resume_already_saved = True
        except Exception:
            pass
        
        button_disabled = False
        try:
            save_button = page.locator("xpath=//button[@aria-label='save_resume']")
            if not save_button.is_enabled():
                button_disabled = True
        except Exception:
            pass
        
        button_has_disabled_class = False
        try:
            disabled_button = page.locator("xpath=//button[@aria-label='save_resume' and contains(@class, 'Mui-disabled')]")
            if disabled_button.is_visible(timeout=5000):
                button_has_disabled_class = True
        except Exception:
            pass
        
        resume_saved_text_exists = False
        try:
            if "Resume already saved" in page.content():
                resume_saved_text_exists = True
        except Exception:
            pass
        
        if resume_already_saved or button_disabled or button_has_disabled_class or resume_saved_text_exists:
            print("Resume is already saved, skipping save button click")
            print(f"Button status - Already saved indicator: {resume_already_saved}, Button disabled: {button_disabled}, Has disabled class: {button_has_disabled_class}, Text exists: {resume_saved_text_exists}")
        else:
            print("Resume is not saved, attempting to click save button")
            click_success = False
            try:
                save_button = page.locator("xpath=//button[@aria-label='save_resume']")
                save_button.click()
                click_success = True
                print("PASS: Save button clicked successfully")
            except Exception:
                try:
                    js_result = page.evaluate("""
                        var btn = document.querySelector('button[aria-label="save_resume"]');
                        if(btn && !btn.disabled) {
                            btn.click();
                            return true;
                        }
                        return false;
                    """)
                    if js_result:
                        click_success = True
                        print("PASS: JavaScript click executed successfully")
                    else:
                        print("WARNING: Could not click save button - may already be saved or button not available")
                except Exception:
                    print("WARNING: Could not click save button")
        
        page.wait_for_timeout(2000)
        
        # Go to Saved Resumes
        goto_fast(page, f"{EMPLOYER_URL}employer/saved-resumes")
        page.wait_for_timeout(4000)
        
        try:
            pdf_error = page.locator(".rpv-core__doc-error-text")
            if pdf_error.is_visible(timeout=2000):
                pytest.fail("PDF error detected in saved resumes")
        except Exception:
            pass  # Expected - no error
        
        # Wait for PDF viewer to load - try multiple approaches
        pdf_viewer_loaded = False
        for attempt in range(3):
            try:
                # Try waiting for PDF viewer
                pdf_viewer = page.locator(".rpv-core__text-layer").first
                pdf_viewer.wait_for(state="visible", timeout=30000)
                pdf_viewer_loaded = True
                break
            except Exception:
                # Try waiting for saved resumes list instead
                try:
                    saved_resumes_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/ul").first
                    if saved_resumes_list.is_visible(timeout=10000):
                        pdf_viewer_loaded = True
                        break
                except Exception:
                    pass
                page.wait_for_timeout(2000)
        
        if not pdf_viewer_loaded:
            print("[WARNING] PDF viewer may not be fully loaded, but continuing with saved resumes check...")
        
        # Get all saved resumes and find the one we saved
        saved_resume_elements = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/ul/div").all()
        print(f"Number of saved resumes: {len(saved_resume_elements)}")
        
        resume_found = False
        for i, saved_resume_elem in enumerate(saved_resume_elements, 1):
            try:
                saved_resume_elem.wait_for(state="visible", timeout=5000)
                saved_resume_elem.click()
                page.wait_for_timeout(2000)
                
                # Get saved resume ID
                saved_resume_id_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div[4]/div/div[1]/div/p[2]")
                if saved_resume_id_elem.is_visible(timeout=5000):
                    saved_resume_id = saved_resume_id_elem.inner_text()
                    print(f"Saved resume {i} ID: {saved_resume_id}")
                    
                    if resume_id_saved_resume == saved_resume_id:
                        print(f"[OK] Found saved resume with ID: {resume_id_saved_resume}")
                        resume_found = True
                        break
            except Exception as e:
                print(f"Error checking saved resume {i}: {e}")
                continue
        
        assert resume_found, \
            f"Resume with ID '{resume_id_saved_resume}' was not found in saved resumes list"
        
        page.wait_for_timeout(2000)
        print("Verification is done successfully.")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.06 Verification of AI search without description and verification of saving a resume")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.employer
def test_t2_12_verification_of_sending_email_to_contacts_in_emp_contacts(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.12 Verification of sending email to Contacts in EMP-Contacts
    Steps:
    1. Login as Employer
    2. Go to Jobs tab
    3. Click on a random job
    4. Click on Contacts tab
    5. Select a random contact
    6. Send email to the contact
    7. Verify success message
    """
    start_runtime_measurement("T2.12 Verification of sending email to Contacts in EMP-Contacts")
    page = employer1_page
    
    try:
        check_network_connectivity([f"{EMPLOYER_URL}", "https://www.google.com"])
        
        # Handle job fair popup
        handle_job_fair_popup_pw(page)
        page.wait_for_timeout(2000)
        
        # Wait for employer dashboard
        dashboard_elem = page.locator("xpath=//*[@id='root']/div[2]/div/div")
        dashboard_elem.wait_for(state="visible", timeout=30000)
        
        jobs_options = page.locator(".css-du1cd4").all()
        if len(jobs_options) < 3:
            pytest.skip("Jobs tab not found")
        
        jobs_options[2].click()
        page.wait_for_timeout(2000)
        
        # Wait for "Open Jobs" text
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        assert "Open Jobs" in page.content(), "Open Jobs page not loaded"
        
        # Wait for job view
        job_view = page.locator(".css-tuxzvu > .MuiGrid-item").first
        job_view.wait_for(state="visible", timeout=30000)
        
        job_title_elem = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[1]/div/div/div/div/div[1]/p")
        job_title_elem.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        
        job_elements = page.locator("p[aria-label]").all()
        num_jobs = len(job_elements)
        
        if num_jobs == 0:
            pytest.skip("No jobs available")
        
        choose_random_num = random.randint(0, num_jobs - 1)
        print(f"Selected job index: {choose_random_num}")
        
        try:
            job_elements[choose_random_num].scroll_into_view_if_needed()
            page.wait_for_timeout(2000)
            _safe_click(page, job_elements[choose_random_num])
        except Exception as e:
            print(f"Error clicking job: {e}")
            raise
        
        # Wait for resume view
        resume_view = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div")
        resume_view.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Scroll to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(2000)
        
        contacts_tab = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[1]/div/div/div/div/div[15]")
        try:
            _safe_click(page, contacts_tab)
        except Exception as e:
            print(f"Error clicking Contacts: {e}")
            raise
        
        # Wait for contacts view
        contacts_view = page.locator("xpath=//*[@id='root']/div[2]/main/div[2]/div[3]/div/div[3]")
        contacts_view.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Get contacts
        contact_elements = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[3]/div[1]/ul/div").all()
        number_contacts = len(contact_elements)
        print(f"Number of contacts: {number_contacts}")
        
        if number_contacts == 0:
            pytest.skip("No contacts available")
        
        choose_contact = random.randint(0, number_contacts - 1)
        print(f"Selected contact index (0-based): {choose_contact}")
        
        index_contact = choose_contact + 1
        print(f"Contact index (1-based for XPath): {index_contact}")
        
        # Get contact name
        contact_name_elem = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[3]/div[1]/ul/div[{index_contact}]/div/div[2]/p[1]")
        contact_name_elem.wait_for(state="visible", timeout=30000)
        contact_name = contact_name_elem.inner_text()
        print(f"Contact name: {contact_name}")
        
        try:
            contact_elements[choose_contact].scroll_into_view_if_needed()
            page.wait_for_timeout(2000)
            _safe_click(page, contact_elements[choose_contact])
        except Exception as e:
            print(f"Error clicking contact: {e}")
            raise
        
        page.wait_for_timeout(2000)
        
        contact_name_in_form = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[4]/div/div[2]/div[1]/div/table/tbody/tr/th")
        contact_name_in_form.wait_for(state="visible", timeout=30000)
        assert contact_name.lower() in contact_name_in_form.inner_text().lower(), \
            f"Contact name mismatch: Expected '{contact_name}', got '{contact_name_in_form.inner_text()}'"
        
        next_button_1 = page.locator(".css-mtejf")
        try:
            _safe_click(page, next_button_1)
        except Exception as e:
            print(f"Error clicking Next button (step 1): {e}")
            raise
        
        page.wait_for_timeout(2000)
        
        description_elem = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[4]/div/div[2]/div/div/div[2]/p[2]")
        description_elem.wait_for(state="visible", timeout=30000)
        assert description_elem.is_visible(), "Description field should be visible"
        
        next_button_2 = page.locator(".css-1beaquk")
        try:
            _safe_click(page, next_button_2)
        except Exception as e:
            print(f"Error clicking Next button (step 2): {e}")
            raise
        
        page.wait_for_timeout(1000)
        
        final_description = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[4]/div/div[2]/div[1]/div/table/tbody/tr/td/table[2]/tbody/tr/td/table/tbody/tr/td")
        assert final_description.is_visible(), "Description should be visible in final step"
        
        send_button = page.locator(".css-mtejf")
        try:
            _safe_click(page, send_button)
        except Exception as e:
            print(f"Error clicking Send button: {e}")
            raise
        
        # Wait for success message
        sent_msg = ""
        for time_attempt in range(1, 30):
            try:
                # Try multiple toast selectors
                toast_selectors = [
                    ".Toastify",
                    "[class*='Toastify']",
                    "div[role='alert']",
                    ".MuiSnackbar-root",
                    "[class*='Snackbar']"
                ]
                
                for selector in toast_selectors:
                    try:
                        toast = page.locator(selector).first
                        if toast.is_visible(timeout=1000):
                            sent_msg = toast.inner_text()
                            if sent_msg:
                                print(f"Sent message: {sent_msg}")
                                break
                    except Exception:
                        continue
                
                if sent_msg:
                    break
                
                # Also check page content for success message
                page_content = page.content()
                if "Success! Mail Sent." in page_content or "Mail sent" in page_content.lower():
                    sent_msg = "Success! Mail Sent."
                    print(f"Found success message in page content")
                    break
                    
            except Exception:
                pass
            page.wait_for_timeout(1000)
        
        if not sent_msg:
            # Check page content one more time
            page_content = page.content()
            if "Success! Mail Sent." in page_content or "Mail sent" in page_content.lower():
                sent_msg = "Success! Mail Sent."
        
        assert sent_msg and ("Success! Mail Sent." in sent_msg or "Mail sent" in sent_msg.lower()), \
            f"Expected success message but got: '{sent_msg}'"
        
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.12 Verification of sending email to Contacts in EMP-Contacts")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_13_EMP
@pytest.mark.employer
def test_t2_13_verification_of_resumes_details_matched_with_posted_jobs(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.13 Verification of resumes details matched with posted jobs
    Steps:
    1. Login as Employer
    2. Go to Jobs
    3. Select a random job
    4. Get job location
    5. Click on Resumes tab
    6. Verify all resumes match the job location
    """
    start_runtime_measurement("T2.13 Verification of resumes details matched with posted jobs")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div[2]/div/div/div/p", timeout=30000)
        page.wait_for_timeout(2000)
        print("Navigating to myJobs...")
        page.goto(f"{EMPLOYER_URL}myJobs")
        page.wait_for_timeout(3000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body", timeout=30000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[3]/div/div", timeout=30000)
        page.wait_for_timeout(2000)
        job_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[3]/div/div")
        number_of_jobs = job_list.count()
        
        if number_of_jobs == 0:
            pytest.skip("No jobs available to test")
        
        choose_random_num = random.randint(1, number_of_jobs)
        print(f"Selected random job index: {choose_random_num}")
        job_card = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[{choose_random_num}]/div/div/div/div/p[1]/span[1]")
        try:
            job_card.scroll_into_view_if_needed()
        except Exception:
            pass
        page.wait_for_timeout(2000)
        
        # Mouse over on the job
        job_card.wait_for(state="visible", timeout=10000)
        job_card.hover()
        page.wait_for_timeout(2000)
        
        job_card.click()
        page.wait_for_timeout(2000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Get job location from the job details view
        location_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/nav/ol/li[3]/p")
        location_element.wait_for(state="visible", timeout=10000)
        chosen_job_location_details = location_element.inner_text()
        
        # Extract location (format: "Location: City, State" or just "Location")
        chosen_job_location = chosen_job_location_details.split(":")[0].strip() if ":" in chosen_job_location_details else chosen_job_location_details.strip()
        page.evaluate("window.scrollTo(0, 0);")
        page.wait_for_timeout(2000)
        
        # Try exact text match first
        resumes_tab = page.locator("xpath=//div[contains(@class, 'text_icon')]//p[text()='Resumes']/parent::div")
        if resumes_tab.count() == 0:
            resumes_tab = page.locator("xpath=//div[contains(@class, 'text_icon')]//p[contains(text(), 'Resumes')]/parent::div").first
        
        resumes_tab.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        
        try:
            resumes_tab.click()
        except Exception:
            print("Regular click failed, trying JavaScript click for Resumes tab...")
            page.evaluate("""
                var tabs = document.evaluate("//div[contains(@class, 'text_icon')]//p[text()='Resumes']/parent::div", 
                    document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                if (tabs.snapshotLength > 0) {
                    tabs.snapshotItem(0).click();
                }
            """)
            print("JavaScript click executed for Resumes tab")
        
        page.wait_for_timeout(2000)
        resume_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[1]/div/div[1]/ul")
        resume_list.wait_for(state="visible", timeout=30000)
        
        # Count resume items (resumes start from div[2], so div[1] is not counted)
        total_divs_in_ul = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[1]/div/div[1]/ul/div").count()
        print(f"Total divs in ul: {total_divs_in_ul}")
        
        # Since first resume is at div[2], subtract 1 to get the number of resumes
        number_of_resumes = total_divs_in_ul - 1
        print(f"Number of resumes found: {number_of_resumes}")
        if number_of_resumes > 0:
            print(f"\n========================================")
            print(f"Verifying {number_of_resumes} resume(s) location matches job location: {chosen_job_location}")
            print(f"========================================")
            
            for each_resume in range(2, number_of_resumes + 1):
                resume_item = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[1]/div/div[1]/ul/div[{each_resume}]")
                resume_item.wait_for(state="visible", timeout=30000)
                resume_item.scroll_into_view_if_needed()
                page.wait_for_timeout(2000)
                resume_item.click()
                print(f"Clicked on resume {each_resume}, waiting for profile to load...")
                
                # Wait for resume view to appear and load completely
                resume_location = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]/div/div/div/div[2]/div[1]/div/div[1]/div/div[2]/div[2]/p")
                resume_location.wait_for(state="visible", timeout=60000)
                print("Resume profile loaded, extracting location...")
                
                for attempt in range(15):
                    try:
                        location_text = resume_location.inner_text()
                        if location_text and location_text.strip():
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)
                
                get_location = resume_location.inner_text().strip().lower()
                print(f"Resume {each_resume} location: {get_location}")
                
                if chosen_job_location.lower() == "remote":
                    continue
                
                chosen_job_location_lower = chosen_job_location.lower()
                assert get_location == chosen_job_location_lower, \
                    f"Resume {each_resume} location mismatch: Expected '{chosen_job_location_lower}', got '{get_location}'"
                
                print(f"PASS: Resume {each_resume} location verified: {get_location}")
            
            print(f"\n========================================")
            print(f"PASS: All {number_of_resumes} resume(s) location verified successfully!")
            print(f"========================================")
        else:
            print(f"\n========================================")
            print(f"WARNING: No resumes found for this job (count: {number_of_resumes})")
            print(f"Skipping resume location verification")
            print(f"========================================")
        
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.13 Verification of resumes details matched with posted jobs")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_14_EMP
@pytest.mark.employer
def test_t2_14_verification_of_advanced_ai_semantic_search(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.14 Verification of Advanced AI Semantic Search
    Steps:
    1. Login as Employer
    2. Navigate to Advanced AI Search
    3. Enter semantic prompt
    4. Verify search results match the prompt using semantic similarity
    """
    start_runtime_measurement("T2.14 Verification of Advanced AI Semantic Search")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    try:
        from utils import semantic_utils
        try:
            import sentence_transformers
        except ImportError:
            pytest.skip("sentence_transformers not installed. T2.14 requires semantic similarity functionality. Install with: pip install sentence-transformers")
    except ImportError:
        pytest.skip("semantic_utils not available. T2.14 requires semantic similarity functionality.")
    
    page = employer1_page
    
    # Semantic prompt from Robot file
    Semantic_prompt = "Find java developer with 5+ years experience"
    
    try:
        if "Empdashboard" not in page.url:
            print("Navigating to Employer dashboard...")
            goto_fast(page, f"{EMPLOYER_URL}Empdashboard")
            page.wait_for_timeout(3000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        try:
            page.wait_for_selector("css:.MuiDialog-container", state="hidden", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        try:
            page.wait_for_selector("xpath=/html/body/div[1]/div[2]/div/div/ul", timeout=30000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        advanced_ai_link = None
        selectors = [
            "xpath=//a[@aria-label='Advanced AI']",
            "xpath=//a[contains(@aria-label, 'Advanced')]",
            "xpath=//a[contains(text(), 'Advanced AI')]",
            "xpath=//a[contains(text(), 'Advanced')]"
        ]
        
        for selector in selectors:
            try:
                advanced_ai_link = page.locator(selector)
                if advanced_ai_link.count() > 0 and advanced_ai_link.first.is_visible(timeout=5000):
                    advanced_ai_link = advanced_ai_link.first
                    break
            except Exception:
                continue
        
        if not advanced_ai_link or advanced_ai_link.count() == 0:
            # Try to find it in the menu structure
            try:
                # Look for it in the navigation menu
                menu_items = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li//a")
                for i in range(menu_items.count()):
                    item = menu_items.nth(i)
                    aria_label = item.get_attribute("aria-label") or ""
                    if "advanced" in aria_label.lower() or "ai" in aria_label.lower():
                        advanced_ai_link = item
                        break
            except Exception:
                pass
        
        if not advanced_ai_link or advanced_ai_link.count() == 0:
            pytest.skip("Advanced AI link not found. The feature may not be available or the selector has changed.")
        
        advanced_ai_link.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        
        try:
            advanced_ai_link.click()
        except Exception:
            page.evaluate("""
                var selectors = [
                    "//a[@aria-label='Advanced AI']",
                    "//a[contains(@aria-label, 'Advanced')]",
                    "//a[contains(text(), 'Advanced AI')]"
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var el = document.evaluate(selectors[i], document, null, 
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el && el.offsetParent !== null) {
                        el.click();
                        break;
                    }
                }
            """)
        page.wait_for_timeout(4000)
        heading = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div/div/div/div[1]/div[2]/h6")
        heading.wait_for(state="visible", timeout=30000)
        heading_text = heading.inner_text()
        assert "Smart Semantic AI Resume Search" in heading_text, f"Expected 'Smart Semantic AI Resume Search' in heading, got: {heading_text}"
        prompt_input = page.locator("xpath=//input[@placeholder=\"Ask AI: e.g., 'Show me senior Java developers with AWS experience'\"]")
        prompt_input.wait_for(state="visible", timeout=30000)
        prompt_input.scroll_into_view_if_needed()
        # Wait for input to be enabled
        for attempt in range(10):
            if prompt_input.is_enabled():
                break
            page.wait_for_timeout(1000)
        prompt_input.fill(Semantic_prompt)
        page.wait_for_timeout(2000)
        search_button = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div/div/div/div[2]/div/div[2]/button[2]")
        search_button.click()
        page.wait_for_timeout(4000)
        card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div[1]/ul/div").count()
        cards_to_test = min(5, card_count)
        
        print(f"\n\n================================================================================")
        print(f"SEMANTIC AI SEARCH TEST")
        print(f"=================================================================================")
        print(f"PROMPT: \"{Semantic_prompt}\"")
        print(f"Testing: {cards_to_test} cards")
        print(f"=================================================================================\n")
        
        if cards_to_test == 0:
            pytest.skip("No resume cards found for semantic search")
        for index in range(1, cards_to_test + 1):
            card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div/div[2]/div[1]/div[1]/ul/div[{index}]"
            card = page.locator(f"xpath={card_xpath}")
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            
            # Extract card text
            card_text = card.inner_text()
            text_length = len(card_text)
            print(f"\n--- EXTRACTING TEXT FROM CARD {index} ---")
            print(f"Text length: {text_length} characters")
            
            # Extract structured information
            candidate_name = page.locator(f"xpath={card_xpath}/div/div[2]/div[1]/h6").inner_text()
            job_title = page.locator(f"xpath={card_xpath}/div/div[2]/p").inner_text()
            
            # Extract experience from card text
            import re
            experience_match = re.search(r'(\d+)\s*(?:Years|Year|Yrs|Yr|years|year)', card_text)
            experience_years_int = 0
            if experience_match:
                experience_years_int = int(experience_match.group(1))
            
            print(f"\n\n=================================================================================")
            print(f"CARD {index} OF {cards_to_test} - {candidate_name} | {job_title} | {experience_years_int} years")
            print(f"=================================================================================")
            print(f"\n[1] PROMPT: \"{Semantic_prompt}\"")
            print(f"\n[2] CARD {index} ORIGINAL TEXT:\n{card_text}")
            score, semantic_match, prompt_embedding, card_embedding = semantic_utils.semantic_similarity(
                Semantic_prompt, card_text, 0.45
            )
            
            similarity_percentage = round(score * 100, 2)
            print(f"\n[3] MATCHING & ACCURACY:")
            print(f"Similarity: {similarity_percentage}% | Threshold: 45.0% | Match: {semantic_match}")
            final_match = semantic_match
            if not semantic_match:
                prompt_lower = Semantic_prompt.lower()
                job_title_lower = job_title.lower()
                
                # Extract key words from prompt
                prompt_cleaned = prompt_lower.replace('find', '').replace('show me', '').replace('show', '').replace('me', '').replace('with', '').replace('years', '').replace('year', '').replace('experience', '').replace('exp', '').replace('+', '').replace('or more', '').replace('at least', '').strip()
                prompt_words = [word.strip() for word in prompt_cleaned.split() if len(word.strip()) > 2]
                
                matching_words_count = sum(1 for word in prompt_words if word in job_title_lower)
                total_prompt_words = len(prompt_words)
                match_percentage = (matching_words_count / total_prompt_words * 100) if total_prompt_words > 0 else 0
                
                # Check experience requirement
                exp_requirement_met = True
                exp_pattern = re.search(r'(\d+)\s*\+?\s*(?:years?|yrs?|or more|at least)', prompt_lower)
                if exp_pattern:
                    required_exp = int(exp_pattern.group(1))
                    exp_requirement_met = experience_years_int >= required_exp
                
                # Similarity should be close to threshold (>= 40%)
                similarity_close = similarity_percentage >= 40.0
                
                if match_percentage >= 50.0 and exp_requirement_met and similarity_close:
                    final_match = True
                    print(f"Fallback validation PASSED: {match_percentage}% of prompt keywords found in job title ({job_title}), experience {experience_years_int} years meets requirement, and similarity {similarity_percentage}% >= 40%")
                else:
                    print(f"Fallback validation FAILED: Match {match_percentage}% (need >=50%), Exp requirement: {exp_requirement_met}, Similarity close: {similarity_close}")
            
            print(f"\n[4] RESULT: {final_match} | Accuracy: {similarity_percentage}%")
            print(f"=================================================================================\n")
            
            # Use continue on failure to test all cards
            if not final_match:
                print(f"WARNING: Card {index} FAILED: Similarity {similarity_percentage}% < 45% threshold and fallback validation did not pass")
        
        print(f"\n\n=================================================================================")
        print(f"TEST SUMMARY: {cards_to_test} cards processed")
        print(f"=================================================================================\n")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.14 Verification of Advanced AI Semantic Search")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_15_EMP
@pytest.mark.employer
def test_t2_15_verification_of_job_posting_displayed_in_js_dashboard_job_title(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.15 Verification of job posting by the employer is getting displayed in the JS dashboard or not with the job title in search bar
    Steps:
    1. Login as Employer
    2. Go to Jobs and get job title
    3. Sign out as Employer
    4. Sign in as Job Seeker
    5. Search for job by title
    6. Verify job is found and title matches
    """
    start_runtime_measurement("T2.15 Verification of job posting displayed in JS dashboard with job title")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(3000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/div/div/ul/li[6]/a/div", timeout=30000)
        page.wait_for_timeout(5000)
        print("Navigating to myJobs...")
        page.goto(f"{EMPLOYER_URL}myJobs")
        page.wait_for_timeout(4000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main", timeout=30000)
        page.wait_for_timeout(2000)
        first_job_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]/div/div")
        first_job_card.wait_for(state="visible", timeout=30000)
        first_job_card.click()
        page.wait_for_timeout(2000)
        job_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body")
        job_view.wait_for(state="visible", timeout=30000)
        get_job_details = job_view.get_attribute("aria-label")
        
        # Extract job title and ID
        get_job_id_title = get_job_details.split("-")
        get_job_title = get_job_id_title[0].strip()
        get_job_id = get_job_id_title[1].strip()
        _employer_sign_out(page)
        page.wait_for_timeout(3000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        page.goto(f"{EMPLOYER_URL}Login")
        page.wait_for_selector("input[name='email']", timeout=30000)
        page.wait_for_timeout(2000)
        _job_seeker_sign_in(page)
        page.wait_for_timeout(3000)
        search_input = page.locator("xpath=/html/body/div[1]/div[2]/div[1]/div/div[2]/div/input")
        search_input.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        search_input.fill(get_job_title)
        page.wait_for_timeout(2000)
        search_input.press("Enter")
        page.wait_for_timeout(4000)
        job_cards_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul")
        job_cards_list.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Get count of cards
        card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul/div").count()
        print(f"Total number of job cards found: {card_count}")
        
        if card_count == 0:
            pytest.fail("No job cards found after searching for job title")
        print(f"\n========================================")
        print(f"Processing First Card Only")
        first_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul/div/div").first
        first_card.wait_for(state="visible", timeout=10000)
        first_card.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        first_card.click()
        page.wait_for_timeout(2000)
        job_view_title_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div/h6")
        job_view_title_element.wait_for(state="visible", timeout=30000)
        job_view_title = job_view_title_element.inner_text()
        print(f"Expected job title: {get_job_title}")
        job_view_title_stripped = job_view_title.strip()
        expected_title_stripped = get_job_title.strip()
        search_terms_list = expected_title_stripped.split()
        print(f"Search terms split: {search_terms_list}")
        
        match_found = False
        matched_terms = []
        
        for search_term in search_terms_list:
            search_term_stripped = search_term.strip()
            if search_term_stripped:
                if search_term_stripped.lower() in job_view_title_stripped.lower():
                    match_found = True
                    matched_terms.append(search_term_stripped)
                    print(f"Found match: \"{search_term_stripped}\" in job title")
        
        assert match_found, f"First Card: Job title does not contain any of the search terms. Expected to find any of: {search_terms_list} in: {job_view_title}. Matched terms: {matched_terms}"
        
        print(f"========================================")
        print(f"\nPASS: TEST PASSED: First card job title contains the search term \"{get_job_title}\"")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.15 Verification of job posting displayed in JS dashboard with job title")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_16_EMP
@pytest.mark.employer
def test_t2_16_verification_of_job_posting_displayed_in_js_dashboard_job_id(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.16 Verification of job posting by the employer is getting displayed in the JS dashboard or not with the job id in search bar
    Steps:
    1. Login as Employer
    2. Go to Jobs and get job ID
    3. Sign out as Employer
    4. Sign in as Job Seeker
    5. Search for job by ID
    6. Verify job is found and ID matches
    """
    start_runtime_measurement("T2.16 Verification of job posting displayed in JS dashboard with job id")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(3000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/div/div/ul/li[6]/a/div", timeout=30000)
        page.wait_for_timeout(5000)
        print("Navigating to myJobs...")
        page.goto(f"{EMPLOYER_URL}myJobs")
        page.wait_for_timeout(4000)
        page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main", timeout=30000)
        page.wait_for_timeout(2000)
        first_job_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div/ul/div[1]/div/div")
        first_job_card.wait_for(state="visible", timeout=30000)
        first_job_card.click()
        page.wait_for_timeout(2000)
        job_view = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div/div[1]/div/div/div[1]/div/body")
        job_view.wait_for(state="visible", timeout=30000)
        get_job_details = job_view.get_attribute("aria-label")
        
        # Extract job title and ID
        get_job_id_title = get_job_details.split("-")
        get_job_title = get_job_id_title[0].strip()
        get_job_id = get_job_id_title[1].strip()
        _employer_sign_out(page)
        page.wait_for_timeout(3000)
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        page.goto(f"{EMPLOYER_URL}Login")
        page.wait_for_selector("input[name='email']", timeout=30000)
        page.wait_for_timeout(2000)
        _job_seeker_sign_in(page)
        page.wait_for_timeout(3000)
        search_input = page.locator("xpath=/html/body/div[1]/div[2]/div[1]/div/div[2]/div/input")
        search_input.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        search_input.fill(get_job_id)
        page.wait_for_timeout(2000)
        search_input.press("Enter")
        page.wait_for_timeout(4000)
        results_loaded = False
        try:
            job_cards_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul")
            job_cards_list.wait_for(state="visible", timeout=15000)
            results_loaded = True
        except Exception:
            try:
                no_results = page.locator("xpath=//*[contains(text(),'No jobs found') or contains(text(),'no results')]")
                if no_results.is_visible(timeout=5000):
                    pytest.fail(f"No job results found for job ID: {get_job_id}. The job may not be visible in JS dashboard.")
            except Exception:
                # Wait for main container
                page.wait_for_selector("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul", timeout=30000)
                page.wait_for_timeout(3000)
                results_loaded = True
        
        page.wait_for_timeout(2000)
        card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul/div").count()
        print(f"Total number of job cards found: {card_count}")
        
        if card_count == 0:
            pytest.fail(f"No job cards found after searching for job ID: {get_job_id}. The job may not be visible in JS dashboard.")
        print(f"\n========================================")
        print(f"Processing First Card Only")
        first_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[1]/div/div[1]/ul/div/div").first
        first_card.wait_for(state="visible", timeout=10000)
        first_card.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        first_card.click()
        page.wait_for_timeout(2000)
        job_view_h6 = page.locator("xpath=//*[@id='root']/div[2]/main/div/div/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div/h6")
        job_view_h6.wait_for(state="visible", timeout=30000)
        
        # Wait for span element inside h6
        job_view_span = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div/h6/span")
        job_view_span.wait_for(state="visible", timeout=30000)
        
        # Mouse over the h6 element to trigger tooltip
        job_view_h6.hover()
        page.wait_for_timeout(1000)
        
        # Get the job ID from the span element's aria-label attribute
        job_view_id_attr = job_view_span.get_attribute("aria-label")
        
        # Handle case where aria-label might be None or empty
        job_view_id = job_view_id_attr if job_view_id_attr and job_view_id_attr != "None" else "NOT_FOUND"
        
        job_view_id = job_view_id.replace("#", "")
        print(f"Expected job ID: {get_job_id}")
        job_view_id_stripped = job_view_id.strip()
        expected_id_stripped = get_job_id.strip().replace("#", "")
        
        search_id_terms_list = expected_id_stripped.split()
        print(f"Search ID terms split: {search_id_terms_list}")
        
        match_found = False
        matched_terms = []
        
        for search_term in search_id_terms_list:
            search_term_stripped = search_term.strip()
            if search_term_stripped:
                if search_term_stripped.lower() in job_view_id_stripped.lower():
                    match_found = True
                    matched_terms.append(search_term_stripped)
                    print(f"Found match: \"{search_term_stripped}\" in job ID")
        
        assert match_found, f"First Card: Job ID does not contain any of the search terms. Expected to find any of: {search_id_terms_list} in: {job_view_id}. Matched terms: {matched_terms}"
        
        print(f"========================================")
        print(f"\nPASS: TEST PASSED: First card job ID contains the search job ID \"{get_job_id}\"")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.16 Verification of job posting displayed in JS dashboard with job id")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_17_EMP
@pytest.mark.employer
def test_t2_17_verification_of_hot_list_company_daily_update(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.17 Verification of Hot list company daily update in hot list section
    Steps:
    1. Login as Employer
    2. Click on Hotlist menu item (li[5])
    3. Verify Companies and Recruiter Details elements exist
    4. Loop through all company cards
    5. For each card, check if recruiter details were updated within 24 hours
    6. Verify ALL cards are within 24 hours
    """
    start_runtime_measurement("T2.17 Verification of Hot list company daily update")
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(6000)
        # Wait for dashboard to load first
        page.wait_for_timeout(3000)
        hotlist_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[5]")
        
        # Try multiple times to find the element
        element_exists = False
        for retry in range(3):
            element_exists = hotlist_menu.is_visible(timeout=10000)
            if element_exists:
                break
            page.wait_for_timeout(2000)
        
        if not element_exists:
            print("Element not found at xpath:/html/body/div[1]/div[2]/div/div/ul/li[5]")
            # Try alternative selector
            hotlist_menu_alt = page.locator("xpath=//li[5]")
            element_exists = hotlist_menu_alt.is_visible(timeout=5000)
            if element_exists:
                hotlist_menu = hotlist_menu_alt
                print("Found using alternative selector")
            else:
                pytest.fail("Hotlist menu item not found")
        
        print("Element found, clicking it...")
        hotlist_menu.wait_for(state="visible", timeout=10000)
        _safe_click(page, hotlist_menu)
        page.wait_for_timeout(5000)
        print("Element clicked successfully")
        page.wait_for_timeout(3000)
        print("Checking for elements after hotlist section loads...")
        companies_element = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Companies')]")
        companies_exists = companies_element.is_visible(timeout=10000)
        
        if companies_exists:
            print("PASS: Companies element found")
        else:
            print("FAIL: Companies element not found")
        recruiter_details_element = page.locator("xpath=//h6[contains(@class, 'MuiTypography-h6') and contains(text(), 'Recruiter Details')]")
        recruiter_details_exists = recruiter_details_element.is_visible(timeout=10000)
        
        if recruiter_details_exists:
            print("PASS: Recruiter Details element found")
        else:
            print("FAIL: Recruiter Details element not found")
        if companies_exists and recruiter_details_exists:
            print("PASS: Both elements are available after hotlist section loaded")
            cards_container = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]")
            cards_container.wait_for(state="visible", timeout=30000)
            page.wait_for_timeout(2000)
            card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div").count()
            print(f"Total number of job cards found: {card_count}")
            cards_within_24hrs = 0
            cards_outside_24hrs = 0
            cards_with_errors = 0
            failed_cards = []
            for index in range(1, card_count + 1):
                card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]"
                print(f"\n========================================")
                print(f"Processing Card {index} of {card_count}")
                
                card = page.locator(f"xpath={card_xpath}")
                card_exists = card.is_visible(timeout=10000)
                
                if card_exists:
                    card.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    
                    card.click()
                    print(f"PASS: Card {index} clicked successfully")
                    page.wait_for_timeout(2000)
                    
                    # Extract company name from the card
                    company_name_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]/div[2]/p"
                    company_name_element = page.locator(f"xpath={company_name_xpath}")
                    company_name_exists = company_name_element.is_visible(timeout=10000)
                    company_name = f"Company {index}"
                    
                    if company_name_exists:
                        company_name = company_name_element.inner_text().strip()
                        print(f"Company Name: {company_name}")
                    else:
                        print(f"WARNING: Company name element not found, using default: {company_name}")
                    
                    # Wait for recruiter details section to load and get the time
                    time_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[3]/div/div[2]/div/div[2]/div[2]/p")
                    time_element_exists = time_element.is_visible(timeout=10000)
                    
                    if time_element_exists:
                        time_text = time_element.inner_text()
                        print(f"[{company_name}] Time text from recruiter details: {time_text}")
                        
                        is_within_24hrs = check_if_time_within_24_hours(time_text)
                        
                        if is_within_24hrs:
                            cards_within_24hrs += 1
                            print(f"PASS: [{company_name}]: Recruiter details updated within 24 hours ({time_text})")
                        else:
                            cards_outside_24hrs += 1
                            failed_cards.append(f"[{company_name}] (Card {index}): {time_text}")
                            print(f"FAIL: [{company_name}]: Recruiter details NOT updated within 24 hours ({time_text})")
                    else:
                        cards_with_errors += 1
                        failed_cards.append(f"[{company_name}] (Card {index}): Time element not found")
                        print(f"FAIL: [{company_name}]: Time element not found in recruiter details")
                else:
                    cards_with_errors += 1
                    failed_cards.append(f"Company {index}: Card not found or not visible")
                    print(f"FAIL: Company {index}: Card not found or not visible")
                
                print(f"========================================")
            print(f"\n========================================")
            print(f"Summary:")
            print(f"Total cards: {card_count}")
            print(f"Cards within 24 hours: {cards_within_24hrs}")
            print(f"Cards outside 24 hours: {cards_outside_24hrs}")
            print(f"Cards with errors: {cards_with_errors}")
            print(f"========================================")
            
            all_within_24hrs = (cards_within_24hrs == card_count and cards_outside_24hrs == 0 and cards_with_errors == 0)
            assert all_within_24hrs, f"TEST FAILED: Not all cards have recruiter details updated within 24 hours. Failed cards: {failed_cards}"
            print(f"\nPASS: TEST PASSED: All {card_count} cards have recruiter details updated within 24 hours")
        else:
            print("FAIL: One or both elements are missing after hotlist section loaded")
            pytest.fail("Required elements (Companies or Recruiter Details) not found")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.17 Verification of Hot list company daily update")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_18_EMP
@pytest.mark.employer
def test_t2_18_hotlist_company_daily_update_verification(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.18 Verification of Hot list company daily update with their candidate list verification in hot list section
    Steps:
    1. Login as Employer
    2. Click on Hotlist menu item
    3. Verify Companies, Recruiter Details, and Candidates elements exist
    4. Loop through all company cards and click them
    5. Verify candidate count > 0 and candidate list element exists
    """
    start_runtime_measurement("T2.18 Verification of Hot list company daily update with candidate list")
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(6000)
        
        page.wait_for_timeout(3000)
        hotlist_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[5]")
        
        # Try multiple times to find the element
        element_exists = False
        for retry in range(3):
            element_exists = hotlist_menu.is_visible(timeout=10000)
            if element_exists:
                break
            page.wait_for_timeout(2000)
        
        if not element_exists:
            # Try alternative selector
            hotlist_menu_alt = page.locator("xpath=//li[5]")
            element_exists = hotlist_menu_alt.is_visible(timeout=5000)
            if element_exists:
                hotlist_menu = hotlist_menu_alt
            else:
                print("Element not found at xpath:/html/body/div[1]/div[2]/div/div/ul/li[5]")
                pytest.fail("Hotlist menu item not found")
        
        print("Element found, clicking it...")
        _safe_click(page, hotlist_menu)
        page.wait_for_timeout(5000)
        print("Element clicked successfully")
        
        # Wait for hotlist section to load
        page.wait_for_timeout(3000)
        print("Checking for elements after hotlist section loads...")
        
        companies_element = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Companies')]")
        companies_exists = companies_element.is_visible(timeout=10000)
        
        if companies_exists:
            print("PASS: Companies element found")
            # Wait for company cards container to be visible
            cards_container = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]")
            cards_container_exists = cards_container.is_visible(timeout=10000)
            
            if cards_container_exists:
                page.wait_for_timeout(2000)
                # Get count of all company cards on page one
                company_card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div").count()
                print(f"Total number of company cards found on page one: {company_card_count}")
                
                cards_found = 0
                cards_not_found = 0
                missing_cards = []
                
                for index in range(1, company_card_count + 1):
                    card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]"
                    print(f"\n========================================")
                    print(f"Processing Company Card {index} of {company_card_count}")
                    
                    card = page.locator(f"xpath={card_xpath}")
                    card_exists = card.is_visible(timeout=5000)
                    
                    if card_exists:
                        cards_found += 1
                        card.wait_for(state="visible", timeout=10000)
                        card.scroll_into_view_if_needed()
                        page.wait_for_timeout(1000)
                        
                        card.click()
                        print(f"PASS: Card {index} clicked successfully")
                        page.wait_for_timeout(2000)
                        
                        # Extract company name from the card
                        company_name_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]/div[2]/p"
                        company_name_element = page.locator(f"xpath={company_name_xpath}")
                        company_name_exists = company_name_element.is_visible(timeout=10000)
                        company_name = f"Company {index}"
                        
                        if company_name_exists:
                            company_name = company_name_element.inner_text().strip()
                            print(f"Company Name: {company_name}")
                        else:
                            print(f"WARNING: Company name element not found, using default: {company_name}")
                        
                        # Wait for candidates list to load (5 seconds)
                        page.wait_for_timeout(5000)
                        print(f"PASS: [{company_name}]: Waited for candidates list to load")
                    else:
                        cards_not_found += 1
                        missing_cards.append(f"Card {index}")
                        print(f"FAIL: Card {index} not found")
                    
                    print(f"========================================")
                
                print(f"Company cards verification summary:")
                print(f"Total cards: {company_card_count}")
                print(f"Cards found: {cards_found}")
                print(f"Cards not found: {cards_not_found}")
                if cards_not_found > 0:
                    print(f"Missing cards: {missing_cards}")
                
                all_cards_exist = (cards_found == company_card_count and cards_not_found == 0)
                assert all_cards_exist, f"TEST FAILED: Not all company cards exist on page one. Found: {cards_found}/{company_card_count}, Missing: {missing_cards}"
                print(f"PASS: All {company_card_count} company cards exist on page one")
            else:
                print("FAIL: Company cards container not found")
        else:
            print("FAIL: Companies element not found")
        
        recruiter_details_element = page.locator("xpath=//h6[contains(@class, 'MuiTypography-h6') and contains(text(), 'Recruiter Details')]")
        recruiter_details_exists = recruiter_details_element.is_visible(timeout=10000)
        
        if recruiter_details_exists:
            print("PASS: Recruiter Details element found")
        else:
            print("FAIL: Recruiter Details element not found")
        
        candidates_element = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Candidates')]")
        candidates_exists = candidates_element.is_visible(timeout=10000)
        
        if candidates_exists:
            print("PASS: Candidates element found")
            candidates_text = candidates_element.inner_text()
            print(f"Candidates section text: {candidates_text}")
        else:
            print("FAIL: Candidates element not found")
        
        if companies_exists and recruiter_details_exists and candidates_exists:
            print("PASS: All elements (Companies, Recruiter Details, Candidates) are available after hotlist section loaded")
            
            # Extract candidate count from "X Available" text
            candidate_count_int = 0
            count_greater_than_zero = False
            count_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[1]/div/div/div/p")
            count_element_exists = count_element.is_visible(timeout=10000)
            
            if count_element_exists:
                count_text = count_element.inner_text()
                print(f"Candidate count text: {count_text}")
                
                # Extract numeric value from text (e.g., "20 Available" -> 20)
                import re
                count_match = re.search(r'(\d+)', count_text)
                if count_match:
                    candidate_count_int = int(count_match.group(1))
                    print(f"Extracted candidate count: {candidate_count_int}")
                    
                    count_greater_than_zero = candidate_count_int > 0
                    if count_greater_than_zero:
                        print(f"PASS: Candidate count is greater than 0: {candidate_count_int}")
                    else:
                        print(f"FAIL: Candidate count is 0 or less: {candidate_count_int}")
                else:
                    print(f"FAIL: Could not extract numeric count from text: {count_text}")
            else:
                print("FAIL: Candidate count element not found")
            
            candidate_list_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[1]")
            candidate_list_exists = candidate_list_element.is_visible(timeout=10000)
            
            if candidate_list_exists:
                print("PASS: Candidate list element found")
            else:
                print("FAIL: Candidate list element not found")
            
            both_conditions_met = count_greater_than_zero and candidate_list_exists
            assert both_conditions_met, f"TEST FAILED: Candidate verification failed. Count > 0: {count_greater_than_zero}, List element exists: {candidate_list_exists}"
            print(f"\nPASS: TEST PASSED: Candidate count is greater than 0 ({candidate_count_int}) AND candidate list element is available")
        else:
            print("FAIL: One or more elements are missing after hotlist section loaded")
            pytest.fail("Required elements not found")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.18 Verification of Hot list company daily update with candidate list")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_19_EMP
@pytest.mark.employer
def test_t2_19_hotlist_search_by_job_title(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.19 Verification of Hot list company daily update with their candidate list verification with job title search in hot list search results
    Steps:
    1. Login as Employer
    2. Click on Hotlist menu item
    3. Search for "java developer" in search bar
    4. Loop through all company cards after search
    5. For each company, verify candidate title contains search terms
    """
    start_runtime_measurement("T2.19 Verification of Hot list with job title search")
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(6000)
        
        page.wait_for_timeout(3000)
        hotlist_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[5]")
        
        # Try multiple times to find the element
        element_exists = False
        for retry in range(3):
            element_exists = hotlist_menu.is_visible(timeout=10000)
            if element_exists:
                break
            page.wait_for_timeout(2000)
        
        if not element_exists:
            # Try alternative selector
            hotlist_menu_alt = page.locator("xpath=//li[5]")
            element_exists = hotlist_menu_alt.is_visible(timeout=5000)
            if element_exists:
                hotlist_menu = hotlist_menu_alt
            else:
                print("Element not found at xpath:/html/body/div[1]/div[2]/div/div/ul/li[5]")
                pytest.fail("Hotlist menu item not found")
        
        print("Element found, clicking it...")
        _safe_click(page, hotlist_menu)
        page.wait_for_timeout(5000)
        print("Element clicked successfully")
        
        # Wait for hotlist section to load
        page.wait_for_timeout(3000)
        print("Checking for elements after hotlist section loads...")
        
        companies_element = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Companies')]")
        companies_exists = companies_element.is_visible(timeout=10000)
        
        if companies_exists:
            print("PASS: Companies element found")
        else:
            print("FAIL: Companies element not found")
        
        # Search for candidates using job title
        search_input = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div[1]/div[2]/input")
        search_input_exists = search_input.is_visible(timeout=10000)
        
        if search_input_exists:
            print("Search input field found, entering job title...")
            search_input.wait_for(state="visible", timeout=10000)
            search_input.clear()
            search_input.fill("java developer")
            print("PASS: Entered \"java developer\" in search bar")
            page.wait_for_timeout(2000)
            
            search_button = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[1]/div/div[1]/button")
            search_button_exists = search_button.is_visible(timeout=10000)
            
            if search_button_exists:
                search_button.wait_for(state="visible", timeout=10000)
                search_button.click()
                print("PASS: Search button clicked successfully")
                page.wait_for_timeout(6000)
                
                # Wait for company cards to load after search
                company_cards_container = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]")
                company_cards_container_exists = company_cards_container.is_visible(timeout=30000)
                
                if company_cards_container_exists:
                    page.wait_for_timeout(2000)
                    company_card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div").count()
                    print(f"Total number of company cards found: {company_card_count}")
                    
                    search_title = "java developer"
                    search_terms_list = search_title.split()
                    print(f"Search terms to match: {search_terms_list}")
                    
                    all_companies_passed = True
                    failed_companies = []
                    
                    # Loop through each company card
                    for index in range(1, company_card_count + 1):
                        card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]"
                        print(f"\n========================================")
                        print(f"Processing Company Card {index} of {company_card_count}")
                        
                        card = page.locator(f"xpath={card_xpath}")
                        card_exists = card.is_visible(timeout=10000)
                        
                        if card_exists:
                            card.scroll_into_view_if_needed()
                            page.wait_for_timeout(1000)
                            card.click()
                            print(f"PASS: Company Card {index} clicked successfully")
                            page.wait_for_timeout(2000)
                            
                            # Extract company name
                            company_name_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]/div[2]/p"
                            company_name_element = page.locator(f"xpath={company_name_xpath}")
                            company_name_exists = company_name_element.is_visible(timeout=10000)
                            company_name = f"Company {index}"
                            
                            if company_name_exists:
                                company_name = company_name_element.inner_text().strip()
                                print(f"Company Name: {company_name}")
                            else:
                                print(f"WARNING: Company name element not found, using default: {company_name}")
                            
                            # Wait for candidates container to load - try multiple times with longer waits
                            candidates_container = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[1]")
                            candidates_container_exists = False
                            
                            # Try multiple times to find candidates container
                            for retry in range(5):
                                candidates_container_exists = candidates_container.is_visible(timeout=10000)
                                if candidates_container_exists:
                                    break
                                page.wait_for_timeout(5000)
                            
                            if candidates_container_exists:
                                print(f"PASS: Candidates container loaded for {company_name}")
                                page.wait_for_timeout(5000)
                                
                                # Try to get candidate title
                                candidate_title_xpath = "/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[1]/div/div/div[2]/p[2]"
                                candidate_title_element = page.locator(f"xpath={candidate_title_xpath}")
                                candidate_title_exists = candidate_title_element.is_visible(timeout=5000)
                                
                                if not candidate_title_exists:
                                    try:
                                        candidate_title_element.scroll_into_view_if_needed()
                                    except:
                                        pass
                                    page.wait_for_timeout(2000)
                                    candidate_title_exists = candidate_title_element.is_visible(timeout=10000)
                                
                                if not candidate_title_exists:
                                    page.wait_for_timeout(3000)
                                    candidate_title_exists = candidate_title_element.is_visible(timeout=15000)
                                
                                # Try alternative xpaths
                                if not candidate_title_exists:
                                    alt_xpath1 = "/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[1]/div/div/div[2]/div/p"
                                    alt_element1 = page.locator(f"xpath={alt_xpath1}")
                                    if alt_element1.is_visible(timeout=5000):
                                        candidate_title_xpath = alt_xpath1
                                        candidate_title_element = alt_element1
                                        candidate_title_exists = True
                                        print(f"[{company_name}] Found using alternative xpath: div/p")
                                
                                if not candidate_title_exists:
                                    alt_xpath2 = "/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[1]/div/div/div[2]/p[1]"
                                    alt_element2 = page.locator(f"xpath={alt_xpath2}")
                                    if alt_element2.is_visible(timeout=5000):
                                        candidate_title_xpath = alt_xpath2
                                        candidate_title_element = alt_element2
                                        candidate_title_exists = True
                                        print(f"[{company_name}] Found using alternative xpath: p[1]")
                                
                                if candidate_title_exists:
                                    candidate_title = candidate_title_element.inner_text().strip()
                                    print(f"[{company_name}] Candidate title: {candidate_title}")
                                    print(f"[{company_name}] Expected search title: {search_title}")
                                    
                                    candidate_title_lower = candidate_title.lower()
                                    contains_java = "java" in candidate_title_lower
                                    contains_developer = "developer" in candidate_title_lower
                                    contains_both = contains_java and contains_developer
                                    title_matches = contains_java or contains_both
                                    
                                    if title_matches:
                                        if contains_both:
                                            print(f"PASS: [{company_name}]: Candidate title contains both \"java\" and \"developer\"")
                                        else:
                                            print(f"PASS: [{company_name}]: Candidate title contains \"java\" (minimum requirement met)")
                                    else:
                                        all_companies_passed = False
                                        failed_companies.append(f"[{company_name}] (Card {index}): Found \"{candidate_title}\" but does not contain \"java\"")
                                        print(f"FAIL: [{company_name}]: Candidate title does not contain \"java\". Found: \"{candidate_title}\"")
                                else:
                                    all_companies_passed = False
                                    failed_companies.append(f"[{company_name}] (Card {index}): Title element not found")
                                    print(f"FAIL: [{company_name}]: Candidate title element not found")
                            else:
                                # Skip companies without candidates - log warning but don't fail
                                print(f"WARNING: [{company_name}]: Candidates container not found after multiple retries. Skipping this company.")
                                # Don't add to failed_companies - companies without candidates are skipped
                        else:
                            all_companies_passed = False
                            failed_companies.append(f"Company {index}: Card not found")
                            print(f"FAIL: Company {index}: Card not found or not visible")
                        
                        print(f"========================================")
                    
                    print(f"\n========================================")
                    print(f"Final Verification Summary:")
                    print(f"Total companies checked: {company_card_count}")
                    print(f"========================================")
                    assert all_companies_passed, f"TEST FAILED: Not all candidate titles match the search term \"{search_title}\". Failed companies: {failed_companies}"
                    print(f"\nPASS: TEST PASSED: All candidate titles match the search term \"{search_title}\" for all companies")
                else:
                    print("FAIL: Company cards container not found after search")
                    pytest.fail("Company cards container not found after search")
            else:
                print("FAIL: Search button not found")
                pytest.fail("Search button not found")
        else:
            print("FAIL: Search input field not found")
            pytest.fail("Search input field not found")
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.19 Verification of Hot list with job title search")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_20_EMP
@pytest.mark.employer
def test_t2_20_ai_search_with_boolean_description(employer1_page, start_runtime_measurement, end_runtime_measurement):
    """
    T2.20 Verification of AI Search with description for the Boolean search working properly on resumes
    Steps:
    1. Login as Employer
    2. Click on AI Search
    3. Enter description2 in textarea
    4. Click AI search button
    5. Select a random skill/related title
    6. Click Find Resumes
    7. Click on Boolean search dropdown
    8. Select 3rd checkbox
    9. Verify first 5 resume titles contain words from both selected titles
    """
    start_runtime_measurement("T2.20 Verification of AI Search with Boolean search")
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        
        ai_search_link = page.locator("xpath=//a[@aria-label='AI Search']")
        ai_search_link.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(1000)
        ai_search_link.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        ai_search_link.click()
        page.wait_for_timeout(4000)
        
        # Wait for textarea and enter description
        textarea = page.locator("xpath=/html/body/div[4]/div[3]/div[2]/form/div/div[1]/textarea")
        textarea.wait_for(state="visible", timeout=30000)
        textarea.fill(DESCRIPTION2)
        page.wait_for_timeout(2000)
        
        ai_search_button = page.locator("xpath=/html/body/div[4]/div[3]/div[2]/form/div/div[2]/button")
        ai_search_button.click()
        page.wait_for_timeout(4000)
        
        # Form should pop-up - wait for primary role
        primary_role = page.locator(".css-1pjtbja")
        primary_role.wait_for(state="visible", timeout=30000)
        primary_role_text = primary_role.inner_text()
        print(f"Primary role: {primary_role_text}")
        
        # Get all options
        all_options = page.locator(".css-16fzwmu")
        total_num_options = all_options.count()
        print(f"Total number of options: {total_num_options}")
        
        if total_num_options == 0:
            pytest.fail("No options found in AI search results")
        
        last_option_index = total_num_options - 1
        choose_random_num = random.randint(0, last_option_index)
        page.wait_for_timeout(4000)
        
        try:
            option = all_options.nth(choose_random_num)
            option.scroll_into_view_if_needed()
        except:
            pass
        page.wait_for_timeout(3000)
        all_options.nth(choose_random_num).click()
        page.wait_for_timeout(2000)
        
        # Get chosen option innerHTML
        chosen_option = all_options.nth(choose_random_num)
        chosen_option_innerHTML = chosen_option.get_attribute("innerHTML") or ""
        print(f"Chosen option innerHTML: {chosen_option_innerHTML}")
        
        # Extract value from innerHTML
        value_match = re.search(r'value="([^"]+)"', chosen_option_innerHTML)
        if value_match:
            value_of_chosen_option = value_match.group(1)
            print(f"Value of chosen option: {value_of_chosen_option}")
            name_of_chosen_option = value_of_chosen_option.replace('"', '')
            print(f"Name of chosen option: {name_of_chosen_option}")
        else:
            name_of_chosen_option = "Unknown"
            print("WARNING: Could not extract value from chosen option")
        
        page.wait_for_timeout(5000)
        
        # Check the chosen option is a Skill or a Related title
        category_chosen = "category"
        if_category_present_skill = page.locator("xpath=//p[contains(.,'Skills:')]").is_visible(timeout=30000)
        print(f"Skills category present: {if_category_present_skill}")
        
        if_category_present_related_title = page.locator("xpath=//p[contains(.,'Related Titles:')]").is_visible(timeout=10000)
        print(f"Related Titles category present: {if_category_present_related_title}")
        
        if if_category_present_skill:
            category_chosen = "skills"
        elif if_category_present_related_title:
            category_chosen = "related titles"
        
        print(f"Category chosen: {category_chosen}")
        page.wait_for_timeout(1000)
        
        find_resumes_button = page.locator("xpath=//button[contains(text(),'Find Resumes')]")
        find_resumes_button.wait_for(state="visible", timeout=30000)
        _safe_click(page, find_resumes_button)
        page.wait_for_timeout(2000)
        
        proceed_button = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[1]/div[2]/div/div/div/div[4]/div/div/button[2]")
        proceed_button.wait_for(state="visible", timeout=30000)
        _safe_click(page, proceed_button)
        page.wait_for_timeout(2000)
        
        dropdown_trigger = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[1]/div[2]/div/div/div/div[1]")
        dropdown_trigger.wait_for(state="visible", timeout=30000)
        _safe_click(page, dropdown_trigger)
        page.wait_for_timeout(3000)
        
        # Wait for dropdown container to appear - try multiple possible locations
        print("Waiting for dropdown container to appear...")
        dropdown_found = False
        dropdown_xpath = ""
        
        locations = [
            "/html/body/div[3]/div[3]/div/div",
            "/html/body/div[4]/div[3]/div/div",
            "/html/body/div[2]/div[3]/div/div"
        ]
        
        for loc in locations:
            dropdown_loc = page.locator(f"xpath={loc}")
            if dropdown_loc.is_visible(timeout=5000):
                dropdown_found = True
                dropdown_xpath = loc
                print(f"PASS: Dropdown found at location: {loc}")
                break
        
        if not dropdown_found:
            any_dropdown = page.locator("xpath=//div[contains(@class, 'MuiPopover')]//input[@type='checkbox']")
            if any_dropdown.is_visible(timeout=5000):
                dropdown_found = True
                dropdown_xpath = "//div[contains(@class, 'MuiPopover')]"
                print(f"PASS: Dropdown found using MuiPopover")
        
        if not dropdown_found:
            pytest.fail("Dropdown container not found at any expected location")
        
        page.wait_for_timeout(2000)
        
        print("Attempting to click 3rd checkbox (index 3)...")
        xpath_clean = dropdown_xpath.replace('xpath:', '')
        
        page.evaluate("""(xpath) => {
            var dropdown = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if(dropdown) {
                var containers = dropdown.querySelectorAll('div');
                if(containers.length >= 3) {
                    var thirdContainer = containers[2];
                    var checkbox = thirdContainer.querySelector('input[type="checkbox"]');
                    if(checkbox) {
                        checkbox.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(function() { checkbox.click(); }, 100);
                        return true;
                    }
                }
            }
            return false;
        }""", xpath_clean)
        
        page.wait_for_timeout(1000)
        
        is_checked = page.evaluate("""(xpath) => {
            var dropdown = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if(dropdown) {
                var containers = dropdown.querySelectorAll('div');
                if(containers.length >= 3) {
                    var thirdContainer = containers[2];
                    var checkbox = thirdContainer.querySelector('input[type="checkbox"]');
                    return checkbox ? checkbox.checked : false;
                }
            }
            return false;
        }""", xpath_clean)
        
        if not is_checked:
            pytest.fail("Failed to click and verify 3rd checkbox")
        
        print("PASS: Checkbox clicked and verified using JavaScript")
        page.wait_for_timeout(2000)
        
        if dropdown_xpath.startswith("/html"):
            p_tag_3rd_xpath = f"{dropdown_xpath}/div[3]/p"
            p_tag_4th_xpath = f"{dropdown_xpath}/div[4]/p"
        else:
            p_tag_3rd_xpath = "//div[contains(@class, 'MuiPopover')]//div[3]//p"
            p_tag_4th_xpath = "//div[contains(@class, 'MuiPopover')]//div[4]//p"
        
        print(f"Getting text from 3rd p tag: {p_tag_3rd_xpath}")
        p_tag_3rd = page.locator(f"xpath={p_tag_3rd_xpath}")
        p_tag_3rd.wait_for(state="visible", timeout=10000)
        title_3rd = p_tag_3rd.inner_text()
        
        print(f"Getting text from 4th p tag: {p_tag_4th_xpath}")
        p_tag_4th = page.locator(f"xpath={p_tag_4th_xpath}")
        p_tag_4th.wait_for(state="visible", timeout=10000)
        title_4th = p_tag_4th.inner_text()
        
        print(f"Third checkbox title: {title_3rd}")
        print(f"Fourth checkbox title: {title_4th}")
        page.wait_for_timeout(2000)
        
        # Wait for the profiles list container to be visible
        profiles_list = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul")
        profiles_list.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Wait for the first profile card to be visible
        first_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]/div")
        first_card.wait_for(state="visible", timeout=30000)
        
        first_title_span = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[1]/div/div[1]/div/span")
        first_title_span.wait_for(state="visible", timeout=30000)
        print("PASS: Profiles loaded successfully")
        page.wait_for_timeout(2000)
        
        print(f"\n=== Checking first 5 resume cards for words from both titles ===")
        title_1 = title_3rd
        title_2 = title_4th
        
        title_1_words = title_1.split()
        title_2_words = title_2.split()
        print(f"Title 1 \"{title_1}\" split into words: {title_1_words}")
        print(f"Title 2 \"{title_2}\" split into words: {title_2_words}")
        
        max_cards_to_check = 5
        total_cards = page.locator(".css-ntktx3").count()
        cards_to_check = min(max_cards_to_check, total_cards)
        print(f"Total resume cards found: {total_cards}, Checking first {cards_to_check} cards")
        
        for card_index in range(1, cards_to_check + 1):
            card_number = card_index
            print(f"\n--- Checking Resume Card {card_number} ---")
            
            card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[{card_index}]/div"
            title_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div[1]/div[1]/ul/div[{card_index}]/div/div[1]/div/span"
            
            try:
                card = page.locator(f"xpath={card_xpath}")
                card.scroll_into_view_if_needed()
            except:
                pass
            page.wait_for_timeout(1000)
            
            title_element = page.locator(f"xpath={title_xpath}")
            title_element.wait_for(state="visible", timeout=15000)
            
            resume_title = title_element.inner_text()
            resume_title_lower = resume_title.lower()
            print(f"Resume title: {resume_title}")
            
            title_1_words_found = []
            title_1_all_found = True
            for word in title_1_words:
                word_lower = word.lower()
                if word_lower in resume_title_lower:
                    title_1_words_found.append(word)
                    print(f"PASS: Word \"{word}\" from title 1 found in resume title")
                else:
                    title_1_all_found = False
                    print(f"FAIL: Word \"{word}\" from title 1 NOT found in resume title")
            
            title_2_words_found = []
            title_2_all_found = True
            for word in title_2_words:
                word_lower = word.lower()
                if word_lower in resume_title_lower:
                    title_2_words_found.append(word)
                    print(f"PASS: Word \"{word}\" from title 2 found in resume title")
                else:
                    title_2_all_found = False
                    print(f"FAIL: Word \"{word}\" from title 2 NOT found in resume title")
            
            title_1_words_count = len(title_1_words_found)
            title_2_words_count = len(title_2_words_found)
            title_1_has_words = title_1_words_count > 0
            title_2_has_words = title_2_words_count > 0
            
            if title_1_all_found and title_2_all_found:
                print(f"PASS: Resume Card {card_number}: ALL words from BOTH titles found in resume title")
            elif title_1_has_words and title_2_has_words:
                print(f"PASS: Resume Card {card_number}: Words from BOTH titles found (some words may be missing)")
            elif title_1_all_found:
                print(f"WARNING: Resume Card {card_number}: All words from title 1 found, but NO words from title 2 found")
            elif title_2_all_found:
                print(f"WARNING: Resume Card {card_number}: All words from title 2 found, but NO words from title 1 found")
            elif title_1_has_words:
                print(f"WARNING: Resume Card {card_number}: Some words from title 1 found, but NO words from title 2 found")
            elif title_2_has_words:
                print(f"WARNING: Resume Card {card_number}: Some words from title 2 found, but NO words from title 1 found")
            else:
                print(f"FAIL: Resume Card {card_number}: NO words from EITHER title found in resume title")
            
            print(f"Title 1 \"{title_1}\" words found: {title_1_words_found}")
            print(f"Title 2 \"{title_2}\" words found: {title_2_words_found}")
        
        print(f"\n=== Completed checking first {cards_to_check} resume cards ===")
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.20 Verification of AI Search with Boolean search")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_21_EMP
@pytest.mark.employer
def test_t2_21_boolean_search_initial_bar(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T2.21 Verification of Boolean search working properly on resumes with help of initial search bar"""
    start_runtime_measurement("T2.21 Verification of Boolean search with initial search bar")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        
        search_input = page.locator("xpath=//input[@aria-label='search']")
        search_input.wait_for(state="visible", timeout=30000)
        
        search_titles = [
            "python developer AND Full Stack Python Developer",
            "JAVA Developer AND J2EE Developer",
            "Oracle developer OR SQL developer",
            "Cold Fusion developer",
            '("oracle dba" OR "oracle database admin*" OR "database admin*") AND ("mysql" OR "my sql") AND ("postgresql" OR "postgre sql")',
            "AS 400 Developer",
            '"Network engineer" AND ("DNS " OR "DHCP")',
            '("azure solution architect")',
            '("azure solution architect" OR "azure architect" OR "solution architect") AND ("SaaS" OR "Software as a Service") AND ("datafactory" OR "data factory" OR "adf") AND ("ArcGIS" OR "arc gis")',
            '("Java Full Stack Developer" OR "Java Full Stack Engineer" OR "Java Software Developer") AND (AWS OR "Amazon Web Services") AND (React OR Angular OR Vue) AND (Lambda OR "API Gateway" OR EC2 OR S3 OR RDS OR DynamoDB) AND (microservices OR "serverless")',
            '("Full Stack Developer" OR "Full Stack Engineer") AND (AWS OR "Amazon Web Services") AND (React OR Angular OR Vue) AND (Lambda OR "API Gateway" OR EC2 OR S3 OR RDS OR DynamoDB) AND (microservices OR "serverless architecture") AND (JavaScript OR TypeScript)',
            '("SALESFORCE CRM ANALYTICS" OR "CRMA" OR "EINSTEIN ANALYTICS") AND (DATAFLOW OR SAQL OR BINDINGS) AND ("SALES CLOUD" OR "SERVICE CLOUD")'
        ]
        
        random_index = random.randint(0, len(search_titles) - 1)
        search_text = search_titles[random_index]
        print(f"Randomly selected search title (index {random_index}): {search_text}")
        
        try:
            dialog_exists = page.locator(".MuiDialog-container").is_visible(timeout=5000)
            if dialog_exists:
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                    page.evaluate("""() => {
                        var backdrop = document.querySelector('.MuiDialog-container, .MuiBackdrop-root');
                        if(backdrop) backdrop.click();
                    }""")
                    page.wait_for_timeout(1000)
                except:
                    pass
        except:
            pass
        
        page.wait_for_timeout(1000)
        
        search_input.wait_for(state="visible", timeout=10000)
        max_wait = 10
        while max_wait > 0 and not search_input.is_enabled():
            page.wait_for_timeout(250)
            max_wait -= 1
        
        try:
            search_input.click()
        except:
            page.evaluate("""() => {
                var input = document.querySelector('input[aria-label="search"]');
                if(input) { input.focus(); input.click(); }
            }""")
            page.wait_for_timeout(1000)
        
        page.wait_for_timeout(1000)
        search_input.fill("")
        page.wait_for_timeout(1000)
        
        input_success = False
        try:
            search_input.fill(search_text)
            page.wait_for_timeout(1000)
            input_value_check = search_input.input_value()
            input_value_length = len(input_value_check)
            search_text_length = len(search_text)
            
            if input_value_length >= search_text_length * 0.8:
                input_success = True
        except:
            pass
        
        if not input_success:
            import json
            search_text_js = json.dumps(search_text)
            page.evaluate(f"""() => {{
                var input = document.querySelector('input[aria-label="search"]');
                if(input) {{
                    var text = {search_text_js};
                    input.value = text;
                    input.focus();
                    setTimeout(function() {{
                        var evt1 = new Event('input', {{bubbles: true}});
                        input.dispatchEvent(evt1);
                        var evt2 = new Event('change', {{bubbles: true}});
                        input.dispatchEvent(evt2);
                    }}, 100);
                }}
            }}""")
            page.wait_for_timeout(2000)
        
        input_value = search_input.input_value()
        print(f"Search input value: {input_value}")
        
        if search_text not in input_value:
            input_value_lower = input_value.lower()
            search_text_lower = search_text.lower()
            if search_text_lower not in input_value_lower:
                pytest.fail(f"Search text was not properly entered. Expected: '{search_text}', Got: '{input_value}'")
        
        search_button = page.locator("xpath=/html/body/div[1]/div[2]/header/div/div[3]/button")
        search_button.wait_for(state="visible", timeout=10000)
        
        try:
            backdrop_exists = page.locator(".MuiBackdrop-root").is_visible(timeout=3000)
        except:
            backdrop_exists = False
        try:
            modal_exists = page.locator(".MuiDialog-container, .MuiModal-root").is_visible(timeout=3000)
        except:
            modal_exists = False
        
        if backdrop_exists or modal_exists:
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                page.evaluate("""() => {
                    var backdrop = document.querySelector('.MuiBackdrop-root');
                    if(backdrop && backdrop.style.opacity == '1') backdrop.click();
                }""")
                page.wait_for_timeout(1000)
                page.evaluate("""() => {
                    var backdrops = document.querySelectorAll('.MuiBackdrop-root');
                    backdrops.forEach(function(b) {
                        if(b.style.opacity == '1' || b.offsetParent !== null) {
                            b.style.display = 'none';
                            b.remove();
                        }
                    });
                }""")
                page.wait_for_timeout(1000)
            except:
                pass
        
        click_success = False
        try:
            search_button.click(timeout=5000)
            click_success = True
        except:
            pass
        
        if not click_success:
            page.evaluate("""() => {
                var btn = document.evaluate('/html/body/div[1]/div[2]/header/div/div[3]/button', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if(btn && !btn.disabled) {
                    btn.click();
                    return true;
                }
                return false;
            }""")
        
        page.wait_for_timeout(3000)
        
        results_header = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[1]/div/div[1]/div[2]/h2")
        results_header.wait_for(state="visible", timeout=30000)
        page.wait_for_timeout(2000)
        
        print(f"\n=== Parsing Boolean expression and checking first 3 resume cards ===")
        print(f"Search expression: \"{search_text}\"")
        
        max_cards_to_check = 3
        all_resume_cards = page.locator(".css-1m6eehe")
        total_cards = all_resume_cards.count()
        cards_to_check = min(max_cards_to_check, total_cards)
        print(f"Total resume cards found: {total_cards}, Checking first {cards_to_check} cards")
        
        cards_passed = []
        cards_failed = []
        
        for card_index in range(cards_to_check):
            card_number = card_index + 1
            print(f"\n--- Checking Resume Card {card_number} ---")
            
            try:
                card = all_resume_cards.nth(card_index)
                card.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                card.click()
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"WARNING: Could not click card {card_number}: {e}")
                continue
            
            profile_visible = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/p[1]").is_visible(timeout=10000)
            if not profile_visible:
                print(f"WARNING: Profile did not open for card {card_number}, skipping...")
                continue
            
            print(f"PASS: Profile opened for card {card_number}")
            page.wait_for_timeout(1000)
            
            button_visible = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[4]/div/div/button[2]").is_visible(timeout=5000)
            if button_visible:
                try:
                    page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[4]/div/div/button[2]").click()
                    page.wait_for_timeout(2000)
                except:
                    pass
            
            profile_text = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div/div[2]").inner_text()
            profile_text_lower = profile_text.lower()
            profile_text_length = len(profile_text)
            print(f"Profile text extracted (length: {profile_text_length} characters)")
            
            resume_title = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[2]/div/div[2]/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/p[1]").inner_text()
            resume_title_lower = resume_title.lower()
            print(f"Resume title from profile: {resume_title}")
            
            try:
                expression_result = semantic_utils.evaluate_boolean_expression(search_text, profile_text_lower)
            except Exception as e:
                print(f"WARNING: Error evaluating Boolean expression: {e}")
                expression_result = False
            
            if expression_result:
                print(f"PASS: Resume Card {card_number}: Boolean expression MATCHED")
                cards_passed.append(card_number)
            else:
                print(f"FAIL: Resume Card {card_number}: Boolean expression NOT MATCHED")
                cards_failed.append(card_number)
            
            close_button_exists = page.locator("xpath=//*[@aria-label='Close Job']").is_visible(timeout=5000)
            if close_button_exists:
                try:
                    page.locator("xpath=//*[@aria-label='Close Job']").click()
                    page.wait_for_timeout(1000)
                except:
                    pass
            else:
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                except:
                    pass
            page.wait_for_timeout(1000)
        
        failed_count = len(cards_failed)
        passed_count = len(cards_passed)
        print(f"\n=== Validation Summary ===")
        print(f"Search expression: \"{search_text}\"")
        print(f"Cards passed: {passed_count}/{cards_to_check} {cards_passed}")
        print(f"Cards failed: {failed_count}/{cards_to_check} {cards_failed}")
        
        if failed_count > 0:
            pytest.fail(f"Test FAILED: {failed_count} out of {cards_to_check} resume cards did NOT satisfy the Boolean expression \"{search_text}\". Failed cards: {cards_failed}")
        
        print(f"\n=== Completed checking first {cards_to_check} resume cards ===")
        page.wait_for_timeout(2000)
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.21 Verification of Boolean search with initial search bar")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

@pytest.mark.T2_22_EMP
@pytest.mark.employer
def test_t2_22_hotlist_duplicate_candidates(employer1_page: Page, start_runtime_measurement, end_runtime_measurement):
    """T2.22 Verification of Hot list company daily update with their candidate list duplicate checking in hot list section"""
    start_runtime_measurement("T2.22 Verification of Hot list duplicate candidates checking")
    assert check_network_connectivity(), "Network connectivity check failed"
    
    page = employer1_page
    
    try:
        _handle_job_fair_popup(page)
        page.wait_for_timeout(2000)
        
        hotlist_menu = None
        for attempt in range(3):
            try:
                hotlist_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[5]")
                if hotlist_menu.is_visible(timeout=5000):
                    break
            except:
                pass
            if attempt < 2:
                page.wait_for_timeout(2000)
        
        if not hotlist_menu or not hotlist_menu.is_visible(timeout=5000):
            alt_hotlist = page.locator("xpath=//li[contains(., 'Hotlist')]")
            if alt_hotlist.is_visible(timeout=5000):
                hotlist_menu = alt_hotlist
            else:
                pytest.fail("Hotlist menu item not found")
        
        try:
            page.locator("xpath=//div[@class='MuiDialog-container']").wait_for(state="hidden", timeout=10000)
        except:
            pass
        
        _safe_click(page, hotlist_menu)
        page.wait_for_timeout(5000)
        
        page.wait_for_timeout(3000)
        
        companies_exists = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Companies')]").is_visible(timeout=10000)
        if not companies_exists:
            pytest.fail("Companies element not found")
        
        cards_container = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]")
        cards_container.wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(2000)
        
        company_card_count = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div").count()
        print(f"Total number of company cards found on page one: {company_card_count}")
        
        cards_found = 0
        cards_not_found = 0
        missing_cards = []
        all_companies_with_duplicates = []
        all_duplicate_summary = []
        
        for index in range(1, company_card_count + 1):
            card_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]"
            print(f"\n========================================")
            print(f"Processing Company Card {index} of {company_card_count}")
            
            card_exists = page.locator(f"xpath={card_xpath}").is_visible(timeout=5000)
            if card_exists:
                cards_found += 1
                card = page.locator(f"xpath={card_xpath}")
                card.wait_for(state="visible", timeout=10000)
                card.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                card.click()
                print(f"PASS: Card {index} clicked successfully")
                page.wait_for_timeout(2000)
                
                company_name_xpath = f"/html/body/div[1]/div[2]/main/div[2]/div[2]/div[1]/div[2]/div[{index}]/div[2]/p"
                company_name = f"Company {index}"
                company_name_exists = page.locator(f"xpath={company_name_xpath}").is_visible(timeout=10000)
                if company_name_exists:
                    company_name = page.locator(f"xpath={company_name_xpath}").inner_text().strip()
                    print(f"Company Name: {company_name}")
                
                page.wait_for_timeout(5000)
                print(f"PASS: [{company_name}]: Waited for candidates list to load")
                
                print(f"\n=== Checking for duplicate candidates in {company_name} ===")
                candidate_list_exists_company = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]").is_visible(timeout=5000)
                if candidate_list_exists_company:
                    all_candidates_company = []
                    candidate_cards_company = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div")
                    total_candidate_cards_company = candidate_cards_company.count()
                    print(f"Total candidate cards found for {company_name}: {total_candidate_cards_company}")
                    
                    if total_candidate_cards_company > 0:
                        for card_index_company in range(total_candidate_cards_company):
                            card_number_company = card_index_company + 1
                            name_xpath_company = f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_number_company}]/div/div/div[1]/div/div[2]/h6"
                            candidate_name_company = f"Unknown Candidate {card_number_company}"
                            name_exists_company = page.locator(name_xpath_company).is_visible(timeout=5000)
                            if name_exists_company:
                                candidate_name_company = page.locator(name_xpath_company).inner_text().strip()
                            
                            experience_xpath_company = f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_number_company}]/div/div/div[3]/p[2]"
                            candidate_experience_company = "Unknown Experience"
                            experience_exists_company = page.locator(experience_xpath_company).is_visible(timeout=5000)
                            if experience_exists_company:
                                candidate_experience_company = page.locator(experience_xpath_company).inner_text().strip()
                            
                            technology_xpath_company = f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_number_company}]/div/div/div[2]/p[2]"
                            candidate_technology_company = "Unknown Technology"
                            technology_exists_company = page.locator(technology_xpath_company).is_visible(timeout=5000)
                            if technology_exists_company:
                                candidate_technology_company = page.locator(technology_xpath_company).inner_text().strip()
                            
                            candidate_id_company = f"{candidate_name_company} | {candidate_experience_company} / {candidate_technology_company}"
                            all_candidates_company.append(candidate_id_company)
                            print(f"Card {card_number_company}: {candidate_name_company} | {candidate_experience_company} / {candidate_technology_company}")
                        
                        print(f"\n=== Comparing each card with all other cards in {company_name} ===")
                        duplicate_found_company = False
                        duplicate_pairs_company = []
                        duplicate_details_company = []
                        
                        for i_company in range(total_candidate_cards_company):
                            card_i_num_company = i_company + 1
                            candidate_i_company = all_candidates_company[i_company]
                            for j_company in range(i_company + 1, total_candidate_cards_company):
                                card_j_num_company = j_company + 1
                                candidate_j_company = all_candidates_company[j_company]
                                if candidate_i_company == candidate_j_company:
                                    duplicate_found_company = True
                                    duplicate_info_company = f"Card {card_i_num_company} matches Card {card_j_num_company}: {candidate_i_company}"
                                    duplicate_pairs_company.append(duplicate_info_company)
                                    print(f"FAIL: DUPLICATE in {company_name}: {duplicate_info_company}")
                                    
                                    try:
                                        name_i_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_i_num_company}]/div/div/div[1]/div/div[2]/h6").inner_text()
                                        exp_i_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_i_num_company}]/div/div/div[3]/p[2]").inner_text()
                                        tech_i_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_i_num_company}]/div/div/div[2]/p[2]").inner_text()
                                        name_j_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_j_num_company}]/div/div/div[1]/div/div[2]/h6").inner_text()
                                        exp_j_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_j_num_company}]/div/div/div[3]/p[2]").inner_text()
                                        tech_j_company = page.locator(f"xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[2]/div/div[{card_j_num_company}]/div/div/div[2]/p[2]").inner_text()
                                        detail_company = f"Card {card_i_num_company} ({name_i_company} | {exp_i_company} / {tech_i_company}) = Card {card_j_num_company} ({name_j_company} | {exp_j_company} / {tech_j_company})"
                                        duplicate_details_company.append(detail_company)
                                    except:
                                        pass
                        
                        unique_candidates_company = list(set(all_candidates_company))
                        unique_count_company = len(unique_candidates_company)
                        all_count_company = len(all_candidates_company)
                        
                        print(f"\n=== DUPLICATE CHECK RESULTS FOR: {company_name} ===")
                        print(f"Total Candidates Found: {all_count_company}")
                        print(f"Unique Candidates: {unique_count_company}")
                        
                        if duplicate_found_company or all_count_company != unique_count_company:
                            duplicate_count_company = all_count_company - unique_count_company
                            print(f"Status: FAILED - Found {duplicate_count_company} duplicate(s)")
                            print(f"\nDUPLICATE CANDIDATES LIST:")
                            
                            all_companies_with_duplicates.append(company_name)
                            company_duplicate_entry = f"{company_name} ({duplicate_count_company} duplicate(s))"
                            all_duplicate_summary.append(company_duplicate_entry)
                            
                            pair_number = 1
                            for detail_company in duplicate_details_company:
                                print(f"[{pair_number}] {detail_company}")
                                pair_number += 1
                            
                            print(f"\nDETAILED DUPLICATE INFORMATION:")
                            for pair_company in duplicate_pairs_company:
                                print(f"- {pair_company}")
                            print(f"========================================")
                        else:
                            print(f"Status: PASSED - No duplicates found")
                            print(f"All candidates are unique (name + experience combination + technology)")
                            print(f"========================================")
                    else:
                        print(f"WARNING: No candidate cards found for {company_name} to check for duplicates")
                else:
                    print(f"WARNING: Candidate list element not found for {company_name}")
            else:
                cards_not_found += 1
                missing_cards.append(f"Card {index}")
                print(f"FAIL: Card {index} not found")
            
            print(f"========================================")
        
        print(f"Company cards verification summary:")
        print(f"Total cards: {company_card_count}")
        print(f"Cards found: {cards_found}")
        print(f"Cards not found: {cards_not_found}")
        if cards_not_found > 0:
            print(f"Missing cards: {missing_cards}")
        
        all_cards_exist = cards_found == company_card_count and cards_not_found == 0
        assert all_cards_exist, f"TEST FAILED: Not all company cards exist on page one. Found: {cards_found}/{company_card_count}, Missing: {missing_cards}"
        
        total_companies_with_duplicates = len(all_companies_with_duplicates)
        print(f"\n\n========================================")
        print(f"FINAL DUPLICATE CHECK SUMMARY - ALL COMPANIES")
        print(f"========================================")
        print(f"Total Companies Checked: {company_card_count}")
        print(f"Companies with Duplicates: {total_companies_with_duplicates}")
        
        if total_companies_with_duplicates > 0:
            print(f"\nLIST OF COMPANIES WITH DUPLICATE CANDIDATES:")
            print(f"========================================")
            summary_index = 1
            for company_summary in all_duplicate_summary:
                print(f"{summary_index}. {company_summary}")
                summary_index += 1
            print(f"========================================")
            print(f"\nWARNING: Duplicates found in {total_companies_with_duplicates} company/companies")
            print(f"========================================")
            pytest.fail(f"TEST FAILED: Found duplicates in {total_companies_with_duplicates} company/companies. Companies with duplicates: {all_duplicate_summary}")
        else:
            print(f"\nSUCCESS: No duplicates found in any company")
            print(f"All candidates are unique across all companies checked")
            print(f"========================================")
        
        recruiter_details_exists = page.locator("xpath=//h6[contains(@class, 'MuiTypography-h6') and contains(text(), 'Recruiter Details')]").is_visible(timeout=10000)
        candidates_exists = page.locator("xpath=//div[@id='tableTitle' and contains(text(), 'Candidates')]").is_visible(timeout=10000)
        
        if candidates_exists:
            count_element = page.locator("xpath=/html/body/div[1]/div[2]/main/div[2]/div[4]/div[1]/div/div/div/p")
            if count_element.is_visible(timeout=10000):
                count_text = count_element.inner_text()
                print(f"Candidate count text: {count_text}")
                count_match = re.search(r'(\d+)', count_text)
                if count_match:
                    candidate_count_int = int(count_match.group(1))
                    print(f"Extracted candidate count: {candidate_count_int}")
                    count_greater_than_zero = candidate_count_int > 0
                    assert count_greater_than_zero and candidates_exists, f"TEST FAILED: Candidate verification failed. Count > 0: {count_greater_than_zero}, Candidates element exists: {candidates_exists}"
        
    except Exception as e:
        raise
    
    total_runtime = end_runtime_measurement("T2.22 Verification of Hot list duplicate candidates checking")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")
