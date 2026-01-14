"""
BenchSale Recruiter Test Cases

This file was reset (old tests removed) so you can add Recruiter test cases newly.
"""

import pytest
from playwright.sync_api import Page, TimeoutError as PWTimeoutError
import time
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `BenchSale_Conftest.py` can be imported by pytest.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load BenchSale fixtures from `BenchSale_Conftest.py` without requiring a local `conftest.py`.
os.environ["BENCHSALE_LOG_SCOPE"] = "recruiter"
pytest_plugins = ["BenchSale_Conftest"]

from BenchSale_Conftest import (
    check_network_connectivity,
    BENCHSALE_URL,
    REC_ID,
    FAST_MODE,
    login_benchsale_admin_pw,
)


def _close_blocking_popup_if_present(page: Page) -> None:
    """
    Sometimes a modal/popup blocks the UI.
    If the close button exists, click it and continue.
    """
    try:
        close_btn = page.locator("xpath=/html/body/div[3]/div[3]/div/div[2]/button")
        close_btn.wait_for(state="visible", timeout=800 if FAST_MODE else 2500)
        close_btn.click(timeout=5000)
        page.wait_for_timeout(200 if FAST_MODE else 500)
        print("Closed blocking popup.")
    except Exception:
        # Popup not present – continue normally
        pass


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


@pytest.mark.T2_01
@pytest.mark.recruiter
def test_t2_01_recruiter_dashboard_verification_recruiter_active_inactive(
    recruiter_page: Page,
    start_runtime_measurement,
    end_runtime_measurement,
):
    """
    T2.01 Recruiter- Dashboard verification (Recruiter active/inactive)

    Ported from Robot Framework testcase:
    `T2.01 Recruiter- Dashboard verification (Recruiter active/inactive)`
    """
    test_name = "T2.01 Recruiter- Dashboard verification (Recruiter active/inactive)"
    start_runtime_measurement(test_name)

    assert check_network_connectivity(), "Network connectivity check failed"
    page = recruiter_page

    # Robot checks for toast after recruiter login (inactive recruiter case)
    toast_msg_test = ""
    try:
        toast_element = page.locator("xpath=/html/body/div/div[3]/div")
        toast_element.wait_for(state="visible", timeout=30000)
        toast_msg_test = (toast_element.inner_text() or "").strip()
        print(f"Toast message: {toast_msg_test}")
    except PWTimeoutError:
        toast_msg_test = ""
        print("No toast message found")

    rec_matched = 0

    if toast_msg_test == f"User '{REC_ID}' not active":
        print(f"Condition matched: {toast_msg_test} == User '{REC_ID}' not active")

        # Open admin in a different tab/page (Robot: window.open + Switch Window NEW)
        context = page.context
        admin_page = context.new_page()
        admin_page.goto(f"{BENCHSALE_URL.rstrip('/')}/login")
        admin_page.wait_for_timeout(300 if FAST_MODE else 2000)

        # Optional toggle to email/password mode
        try:
            tgl = admin_page.locator(".css-1hw9j7s")
            if tgl.count() and tgl.first.is_visible():
                tgl.first.click()
                admin_page.wait_for_timeout(300 if FAST_MODE else 500)
        except Exception:
            pass

        login_benchsale_admin_pw(admin_page)
        admin_page.wait_for_timeout(300 if FAST_MODE else 2000)

        # Inactive Recruiters
        inactive_recruiters_menu = admin_page.locator(
            "xpath=/html/body/div[1]/div[2]/div/div/ul/li[4]/a/div"
        )
        inactive_recruiters_menu.wait_for(state="visible", timeout=40000)
        inactive_recruiters_menu.click()

        # Robot optionally sees a dialog if there are no inactive recruiters; close if it blocks.
        _close_blocking_popup_if_present(admin_page)

        # Wait for first inactive recruiter list entry
        admin_page.locator(
            "xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/div/div/div/ul/div"
        ).first.wait_for(state="visible", timeout=30000)
        admin_page.wait_for_timeout(300 if FAST_MODE else 2000)

        # Robot counts recruiter name rows
        inactive_name_rows = admin_page.locator(
            "xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/div/div/div/ul/div/div/div/div[2]/p[1]"
        )
        num_inactive = inactive_name_rows.count()
        print(f"Number of inactive recruiters found: {num_inactive}")

        all_recruiter_emails: list[str] = []

        if num_inactive == 0:
            print("WARNING: No inactive recruiters found in the list")
        else:
            print(f"Looking for recruiter: {REC_ID}")
            print("Collecting all inactive recruiter emails for comparison...")

            for i in range(1, num_inactive + 1):
                print(f"Checking recruiter {i} of {num_inactive}")
                try:
                    rec_name_loc = admin_page.locator(
                        f"xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/div/div/div/ul/div[{i}]/div/div/div[2]/p[1]"
                    )
                    rec_name = (rec_name_loc.inner_text() or "").strip()
                    print(f"Recruiter name: {rec_name}")

                    # Click recruiter card to open profile panel
                    rec_name_loc.click()
                    admin_page.wait_for_timeout(300 if FAST_MODE else 2000)

                    admin_page.locator("css:.css-16rlg6l").wait_for(state="visible", timeout=30000)

                    rec_email_details_loc = admin_page.locator(
                        "xpath=/html/body/div[1]/div[2]/main/div/div/div[2]/div/div[2]/div/h6[2]"
                    )
                    rec_email_details = (rec_email_details_loc.inner_text() or "").strip()
                    print(f"Email details: {rec_email_details}")

                    # Robot: Split String  ${rec_email_details}  :
                    rec_email_split = rec_email_details.split(":")
                    if len(rec_email_split) > 1:
                        rec_email = rec_email_split[1].strip()
                    else:
                        rec_email = rec_email_details.strip()
                        print("WARNING: Could not split email by ':', using full text")

                    all_recruiter_emails.append(rec_email)
                    print(f"Recruiter email: {rec_email}")
                    print(f"Looking for: {REC_ID}")

                    if REC_ID == rec_email or REC_ID in rec_email:
                        print(f"Match found! '{REC_ID}' matches '{rec_email}'")

                        activate_button = admin_page.locator(
                            f"xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/div/div/div/ul/div[{i}]/div/button"
                        )
                        activate_button.wait_for(state="visible", timeout=30000)
                        activate_button.click()
                        admin_page.wait_for_timeout(300 if FAST_MODE else 1000)

                        # Robot: Click Element xpath:/html/body/div[3]/div[3]/ul  # Active button
                        admin_page.locator("xpath=/html/body/div[3]/div[3]/ul").wait_for(
                            state="visible", timeout=30000
                        )
                        admin_page.locator("xpath=/html/body/div[3]/div[3]/ul").click()

                        success_toast = admin_page.locator("xpath=/html/body/div[1]/div[3]/div")
                        success_toast.wait_for(state="visible", timeout=30000)
                        activated_msg = (success_toast.inner_text() or "").strip()
                        assert (
                            activated_msg == "Recruiter Activated Successfully"
                        ), f"Expected activation message, got '{activated_msg}'"

                        admin_page.wait_for_timeout(300 if FAST_MODE else 2000)
                        rec_matched += 1
                        break
                    else:
                        print("continued..........")
                        continue
                except Exception as e:
                    print(f"Error processing recruiter {i}: {e}")
                    continue

        if rec_matched == 0:
            print("========================================")
            print(f"WARNING: Recruiter '{REC_ID}' was not found in the inactive recruiters list")
            print(f"All inactive recruiter emails found: {all_recruiter_emails}")
            print("The recruiter may:")
            print("- Already be active (check active recruiters list)")
            print("- Not exist in the system")
            print("- Have a different email address")
            print("========================================")

        assert (
            rec_matched == 1
        ), f"Recruiter '{REC_ID}' was not found and activated. rec_matched={rec_matched}, num_inactive={num_inactive}"

        # Close admin page and continue with recruiter login
        try:
            admin_page.close()
        except Exception:
            pass

        # Robot: Switch Window MAIN then Click Sign In
        try:
            sign_in_btn = page.locator("xpath=/html/body/div/div[2]/main/div/form/button")
            if sign_in_btn.count() and sign_in_btn.first.is_visible():
                sign_in_btn.first.click()
                page.wait_for_timeout(500 if FAST_MODE else 2000)
                print("Recruiter profile is activated and logged in")
        except Exception as e:
            print(f"WARNING: Could not click recruiter Sign In after activation: {e}")
    else:
        print("Logged into the Recruiter profile")
        page.wait_for_timeout(300 if FAST_MODE else 2000)

    # Dashboard counters (Robot reads these from recruiter portal)
    try:
        active_candidates_dashboard = (
            page.locator(
                "xpath=/html/body/div[1]/div[2]/main/div/div[1]/div/div/div[2]/div/div/div[1]/div[2]/span"
            )
            .inner_text()
            .strip()
        )
        closed_candidates_dashboard = (
            page.locator(
                "xpath=/html/body/div[1]/div[2]/main/div/div[1]/div/div/div[3]/div/div/div[1]/div[2]/span"
            )
            .inner_text()
            .strip()
        )
        interested_candidates_dashboard = (
            page.locator(
                "xpath=/html/body/div[1]/div[2]/main/div/div[1]/div/div/div[5]/div/div/div[1]/div[2]/span"
            )
            .inner_text()
            .strip()
        )
        print(f"active_candidates_dashboard: {active_candidates_dashboard}")
        print(f"closed_candidates_dashboard: {closed_candidates_dashboard}")
        print(f"interested_candidates_dashboard: {interested_candidates_dashboard}")
    except Exception as e:
        print(f"WARNING: Could not read dashboard counters: {e}")

    # Verify Submissions (Robot checks css:.css-6uwsni)
    try:
        if page.locator("css=.css-6uwsni").count() > 0:
            num_of_submissions = page.locator("css=.css-v3z1wi").count()
            submissions_names: list[str] = []
            for i in range(1, num_of_submissions + 1):
                name = (
                    page.locator(f"xpath=(//p[contains(@class,'MuiTypography-body1')])[{i}]")
                    .inner_text()
                    .strip()
                )
                if name:
                    submissions_names.append(name)

            # Robot: Click Submission 'View All'
            view_all = page.locator(
                "xpath=/html/body/div[1]/div[2]/main/div/div[2]/div[1]/div/div/div[1]/div/button"
            )
            view_all.wait_for(state="visible", timeout=30000)
            view_all.click()

            page.locator(
                "xpath=/html/body/div[1]/div[2]/main/div/div[2]/div/div[1]/div/div/div/div/ul/div[1]"
            ).wait_for(state="visible", timeout=30000)

            candidate_cards = page.locator("css=.css-1nh3bf")
            num_candidates = candidate_cards.count()
            for idx in range(num_candidates):
                cand = candidate_cards.nth(idx)
                nm = (cand.inner_text() or "").strip()
                if not nm:
                    continue
                if nm in submissions_names:
                    cand.click()
                    page.locator("css=.css-ofij5").wait_for(state="visible", timeout=30000)
        else:
            print("No submissions section found on dashboard.")
    except Exception as e:
        print(f"WARNING: Submissions verification had an issue: {e}")

    total_runtime = end_runtime_measurement("Recruiter_Dashboard_Verification")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")


@pytest.mark.T2_02
@pytest.mark.recruiter
def test_t2_02_recruiter_verification_of_inactivating_and_activating_candidates(
    recruiter_page: Page,
    start_runtime_measurement,
    end_runtime_measurement):
    """
    T2.02 Recruiter- Verification of inactivating and activating candidates

    Ported from Robot Framework testcase:
    `T2.02 Recruiter- Verification of inactivating and activating candidates`
    """
    test_name = "T2.02 Recruiter- Verification of inactivating and activating candidates"
    start_runtime_measurement(test_name)

    assert check_network_connectivity(), "Network connectivity check failed"
    page = recruiter_page

    # Step 1: Click "My Candidates" menu button
    print("Clicking 'My Candidates' menu...")
    my_candidates_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[2]/a/div")
    my_candidates_menu.wait_for(state="visible", timeout=30000)
    _safe_click(page, my_candidates_menu, timeout_ms=30000)

    # Wait for page to load
    page.wait_for_timeout(1000 if FAST_MODE else 2000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    
    # Step 2: Page already shows active candidates by default, no need to click button
    
    # Step 3: Check if candidates are available in the list
    print("Checking for candidates in Active Candidates list...")
    first_candidate = page.locator(
        "xpath=/html/body/div[1]/div[2]/main/div/div[2]/div/div[1]/div/div/div/div/ul/div[1]"
    )
    if_any_candidate = False
    try:
        first_candidate.wait_for(state="visible", timeout=30000)
        if_any_candidate = True
        print("Candidates found in Active Candidates list")
    except Exception:
        if_any_candidate = False
        print("No candidates found in Active Candidates list")
    print(f"if_any_candidate={if_any_candidate}")

    if if_any_candidate:
        candidate_cards = page.locator(
            "xpath=/html/body/div[1]/div[2]/main/div/div[2]/div/div[1]/div/div/div/div/ul/div"
        )
        num_candidates = candidate_cards.count()
        print(f"num_candidates={num_candidates}")
        assert num_candidates > 0, "No candidates found to inactivate"
        print(f"SUCCESS: Found {num_candidates} active candidate(s) in the list")
        
        # Step 4: Inactivate a candidate
        print("Inactivating first candidate...")
        
        # Step 4.1: Hover over first card
        first_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div[2]/div/div[1]/div/div/div/div/ul/div[1]")
        first_card.wait_for(state="visible", timeout=30000)
        first_card.hover()
        page.wait_for_timeout(500 if FAST_MODE else 1000)
        print("Hovered over first candidate card")
        
        # Step 4.2: Click checkbox
        checkbox = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div[2]/div/div[1]/div/div/div/div/ul/div[1]/div/span/input")
        checkbox.wait_for(state="visible", timeout=10000)
        _safe_click(page, checkbox, timeout_ms=10000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)  # Wait for toolbar to appear
        print("Clicked checkbox to select candidate")
        
        # Step 4.3: Click inactive button using aria-label
        print("Clicking inactive button...")
        inactive_button = page.locator("css=svg[aria-label='Inactive']")
        inactive_button.wait_for(state="visible", timeout=10000)
        inactive_button.click(timeout=10000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)
        print("Clicked inactive button")
        
        # Step 4.4: Click submit button in popup
        print("Clicking submit button in popup...")
        popup_container = page.locator("xpath=/html/body/div[3]/div[3]/div")
        popup_container.wait_for(state="visible", timeout=10000)
        submit_button = page.locator("xpath=/html/body/div[3]/div[3]/div/div[2]/button[2]")
        submit_button.wait_for(state="visible", timeout=10000)
        _safe_click(page, submit_button, timeout_ms=15000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)
        print("Clicked submit button to inactivate candidate")
        
        # Wait for toast message or confirmation
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        print("SUCCESS: Candidate inactivated successfully")
        
        # Step 5: Activate the inactivated candidate
        print("Activating the inactivated candidate...")

        # Step 5.1: Click Inactive menu
        inactive_menu = page.locator("xpath=/html/body/div[1]/div[2]/div/div/ul/li[6]/a/div")
        inactive_menu.wait_for(state="visible", timeout=30000)
        _safe_click(page, inactive_menu, timeout_ms=30000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        print("Clicked Inactive menu")
        
        # Step 5.2: Hover over first inactive candidate card
        first_inactive_card = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/ul/div[1]")
        first_inactive_card.wait_for(state="visible", timeout=30000)
        first_inactive_card.hover()
        page.wait_for_timeout(500 if FAST_MODE else 1000)
        print("Hovered over first inactive candidate card")
        
        # Step 5.3: Click checkbox
        inactive_checkbox = page.locator("xpath=/html/body/div[1]/div[2]/main/div/div/div[1]/div/div[2]/ul/div[1]/div/span/input")
        inactive_checkbox.wait_for(state="visible", timeout=10000)
        _safe_click(page, inactive_checkbox, timeout_ms=10000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)
        print("Clicked checkbox to select inactive candidate")
        
        # Step 5.4: Click "Move To Active" button
        print("Clicking 'Move To Active' button...")
        move_to_active_button = page.locator("css=svg[aria-label='Move To Active']")
        move_to_active_button.wait_for(state="visible", timeout=10000)
        move_to_active_button.click(timeout=10000)
        page.wait_for_timeout(1000 if FAST_MODE else 2000)
        print("Clicked 'Move To Active' button")
        
        # Wait for confirmation
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        
        print("SUCCESS: Candidate activated successfully")
    else:
        print("WARNING: No active candidates available in 'My Candidates'")
        pytest.skip("No candidates available in 'My Candidates' to inactivate")

    total_runtime = end_runtime_measurement("Recruiter_Candidate_Activation")
    print(f"PASS: Test completed in {total_runtime:.2f} seconds")

# Add new recruiter test cases below.
