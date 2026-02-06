"""
Unified Log Viewer - Creates a professional dashboard showing both Admin and Recruiter logs
with test results, screenshots, and impressive UI design.
"""

import os
import re
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from html import escape


# Valid Employer test case names from JnP_final.robot
# These are the only test cases that should appear in the dashboard
VALID_EMPLOYER_TEST_NAMES = {
    # T1.xx tests
    "T1.01 Home Page",
    "T1.02 Home Page- Verify if jobs NOT coming from same company consecutively in 'Browse jobs'",
    "T1.03 Home Page- Verify if jobs are matched with the searched company in 'Browse jobs'",
    "T1.04 Home Page- Verify the job posting time",
    "T1.05 Home Page- Verify 'Book Your Demo'",
    "T1.06 Home Page- No repetition of jobs in 'Similar Jobs'",
    # T2.xx tests
    "T2.01 'Post a Job' verification and verification with Job-Id",
    "T2.02 Verification of applicants and shortlisting in JS",
    "T2.03 Verification of closing a job and checking with Job-Id",
    "T2.04 Verification of AI Search with description",
    "T2.06 Verification of AI search without description and verification of saving a resume",
    "T2.12 Verification of sending email to Contacts in EMP-Contacts",
    "T2.13 Verification of resumes details matched with posted jobs",
    "T2.14 Verification of Advanced AI Semantic Search",
    "T2.15 Verification of job posting by the employer is getting displayed in the JS dashboard or not with the job title in search bar",
    "T2.16 Verification of job posting by the employer is getting displayed in the JS dashboard or not with the job id in search bar",
    "T2.17 Verification of Hot list company daily update in hot list section",
    "T2.18 Verification of Hot list company daily update with their candidate list verfication in hot list section",
    "T2.19 Verification of Hot list company daily update with their candidate list verfication with job title search in hot list search results",
    "T2.20 Verification of AI Search with description for the Boolean search working properly on resumes",
    "T2.21 Verification of Boolean search working properly on resumes with help of initial search bar",
    "T2.22 Verification of Hot list company daily update with their candidate list duplicate candidates checking in hot list section",
}


def _normalize_skills_for_similarity(skills_str: str) -> list:
    """Normalize skills string for similarity comparison"""
    if not skills_str:
        return []
    cleaned = re.sub(r"[^\w\s\-\+#,]", "", str(skills_str)).lower()
    return [s.strip() for s in cleaned.split(",") if s.strip()]


def _calculate_skills_similarity(list1: list, list2: list) -> float:
    """Calculate similarity percentage between two skill lists"""
    if not list1 and not list2:
        return 100.0
    if not list1 or not list2:
        return 0.0
    set1 = set(list1)
    set2 = set(list2)
    intersection = set1.intersection(set2)
    denominator = max(len(set1), len(set2))
    if denominator == 0:
        return 0.0
    return (len(intersection) / denominator) * 100.0


def _should_filter_failure_message(error_msg: str) -> bool:
    """Filter out false positive failures (DB='N/A' and ai_skills >=70% similarity)"""
    if not error_msg:
        return False
    # Filter DB='N/A' false positives
    if "Statename: DB='N/A'" in error_msg or "Cityname: DB='N/A'" in error_msg:
        return True
    # Filter ai_skills false positives (>=70% similarity)
    match = re.search(r"ai_skills:\s*'([^']+)'\s*!=\s*'([^']+)'", error_msg)
    if match:
        db_skills = _normalize_skills_for_similarity(match.group(1))
        solr_skills = _normalize_skills_for_similarity(match.group(2))
        similarity = _calculate_skills_similarity(db_skills, solr_skills)
        if similarity >= 70.0:
            return True
    return False


def is_valid_employer_test(test_name: str) -> bool:
    """Check if a test name is a valid Employer test from JnP_final.robot"""
    # Explicitly exclude invalid test names (not in JnP_final.robot)
    invalid_patterns = [
        'test_e1_01', 'test_e2_01', 'e1_01', 'e2_01',  # E1.01, E2.01 tests (not in JnP_final.robot)
        'employer1_dashboard_verification', 'employer2_dashboard_verification',
        'home_page_verify_recruiter', 'home_page_verification_of_recruiter',
        'home_page_verification_of_custom', 'verification_of_employer_details',
        'verification_of_hotlist', 'verification_of_changes_in_company',
        'verification_of_jobs_under_company'
    ]
    
    test_name_lower = test_name.lower()
    for invalid_pattern in invalid_patterns:
        if invalid_pattern.lower() in test_name_lower:
            return False  # This is an invalid test, exclude it
    
    # Check exact match first
    if test_name in VALID_EMPLOYER_TEST_NAMES:
        return True
    
    # Check if test name contains any valid test identifier (T1.01, T1.02, T2.01, etc.)
    # This handles pytest test names like "test_t1_01_home_page"
    test_pattern = re.compile(r'T[12]\.\d+', re.IGNORECASE)
    match = test_pattern.search(test_name)
    if match:
        test_id = match.group(0).upper()
        # Check if this test ID exists in valid tests
        for valid_name in VALID_EMPLOYER_TEST_NAMES:
            if test_id in valid_name:
                # Extract the test identifier from the test name
                # e.g., "test_t1_01_home_page" -> "T1.01"
                # Check if the test name matches the pattern
                if test_id in test_name.upper() or any(
                    word.lower() in test_name.lower() 
                    for word in valid_name.split() 
                    if len(word) > 3
                ):
                    return True
    
    # Check for pytest function name patterns
    # e.g., "test_t1_01_home_page" should match "T1.01 Home Page"
    for valid_name in VALID_EMPLOYER_TEST_NAMES:
        # Extract key words from valid name
        valid_words = [w.lower() for w in valid_name.split() if len(w) > 3 and w.lower() not in ['the', 'and', 'for', 'with', 'from', 'that', 'this']]
        # Check if test name contains enough matching words
        matching_words = sum(1 for word in valid_words if word in test_name_lower)
        if matching_words >= 2:  # At least 2 key words match
            return True
    
    return False


def parse_test_results_from_log(log_file_path: str):
    """Parse log file to extract test results with PASS/FAIL status."""
    # Get project root for resolving JSON file paths
    project_root = Path(__file__).parent.parent
    
    tests = []
    current_test = None
    
    # Match patterns like:
    # "TEST test_name: PASS" or "TEST test_name: FAIL" or "TEST test_name: SKIP"
    # Also match "Status: PASS", "Status: FAIL", "Status: SKIP" on separate lines
    test_pattern = re.compile(r'TEST\s+([^:]+):\s*(PASS|FAIL|SKIP)', re.IGNORECASE)
    status_pattern = re.compile(r'^Status:\s*(PASS|FAIL|SKIP)', re.IGNORECASE)
    elapsed_pattern = re.compile(
        r"Start\s*/\s*End\s*/\s*Elapsed:\s*[^/]+/\s*[^/]+/\s*([0-9:.]+)",
        re.IGNORECASE
    )
    runtime_seconds_pattern = re.compile(r"Runtime for .*?:\s*([0-9.]+)\s+seconds", re.IGNORECASE)
    
    # Also check for test statistics table format (fallback for collected but not executed tests)
    stats_pattern = re.compile(r'(\d+)\s+tests?\s+total,\s+(\d+)\s+passed,\s+(\d+)\s+failed,\s+(\d+)\s+skipped', re.IGNORECASE)
    total_tests_collected = None
    actual_test_results_found = 0  # Count of actual "TEST <name>: PASS/FAIL/SKIP" entries
    stats_tests_executed = 0
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_no, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Match test result lines like "TEST T1.01 Home Page: PASS" or "TEST test_t1_01_home_page: PASS"
                # Also handle format where TEST and status are on separate lines
                match = test_pattern.search(line)
                if match:
                    test_name = match.group(1).strip()
                    status = match.group(2).upper()
                    
                    # Also check if there's a "Status: FAIL" line right after (within next 5 lines)
                    # This handles cases where status is on a separate line
                    if line_no < len(lines):
                        for next_idx in range(line_no, min(line_no + 5, len(lines))):
                            if next_idx < len(lines):
                                next_line = lines[next_idx].strip()
                                status_match = status_pattern.search(next_line)
                                if status_match:
                                    status = status_match.group(1).upper()
                                    break
                    
                    # Skip invalid Employer tests (not in JnP_final.robot)
                    # Filter out test_e1_01_employer1_dashboard_verification and similar invalid tests
                    test_name_lower = test_name.lower()
                    invalid_patterns = ['test_e1_01', 'test_e2_01', 'e1_01', 'e2_01', 
                                       'employer1_dashboard_verification', 'employer2_dashboard_verification']
                    if any(pattern in test_name_lower for pattern in invalid_patterns):
                        continue  # Skip this invalid test
                    
                    actual_test_results_found += 1
                    
                    # Try to extract additional information from surrounding lines
                    running_time = 'N/A'
                    failure_message = ''
                    failure_location = ''
                    xpath = ''
                    total_jobs = 0
                    error_jobs_count = 0
                    
                    # For db_solr_sync test, search entire log file for job report data (it's logged much later)
                    search_range = len(lines) if 'db_solr_sync' in test_name.lower() else min(line_no + 120, len(lines))
                    
                    # Look ahead for elapsed/runtime + failure details + xpath hint + job report data
                    # This is used for BOTH PASS and FAIL so runtime always shows in the right panel.
                    for i in range(line_no, search_range):
                        if i < len(lines):
                            next_line = lines[i].strip()
                            # Stop if another test starts (but continue for db_solr_sync to find job report data)
                            if i != line_no and test_pattern.search(next_line) and 'db_solr_sync' not in test_name.lower():
                                break
                            # Prefer the elapsed format from test_logger
                            m_elapsed = elapsed_pattern.search(next_line)
                            if m_elapsed and running_time == 'N/A':
                                running_time = m_elapsed.group(1).strip()
                            # Fallback: runtime seconds line from runtime measurement
                            if running_time == 'N/A':
                                m_rt = runtime_seconds_pattern.search(next_line)
                                if m_rt:
                                    running_time = f"{m_rt.group(1).strip()} seconds"
                            
                            # Extract 12hrs job report data for db_solr_sync test
                            if 'db_solr_sync' in test_name.lower():
                                # Look for "Total Jobs Available in DB (last 12h): X" or "Jobs Actually Checked: X"
                                if 'Total Jobs Available in DB' in next_line or 'Jobs Actually Checked:' in next_line:
                                    jobs_match = re.search(r'(?:Total Jobs Available in DB \(last 12h\):|Jobs Actually Checked:)\s*(\d+)', next_line, re.IGNORECASE)
                                    if jobs_match and total_jobs == 0:
                                        total_jobs = int(jobs_match.group(1))
                                # Look for "Total Failures: X" (fallback - will be overridden by JSON if available)
                                if 'Total Failures:' in next_line:
                                    failures_match = re.search(r'Total Failures:\s*(\d+)', next_line, re.IGNORECASE)
                                    if failures_match:
                                        error_jobs_count = int(failures_match.group(1))

                    if status == 'FAIL':
                        # Prefer the "Message:" block written by the test logger / conftest hook.
                        capture = []
                        capture_started = False
                        for i in range(line_no, min(line_no + 120, len(lines))):
                            if i < len(lines):
                                next_line = lines[i].strip()
                                # Stop if another test starts
                                if test_pattern.search(next_line):
                                    break

                                # Capture from "Message:" or "Error details:" onwards
                                if ("Message:" in next_line) or ("Error details:" in next_line) or ("E   " in next_line) or ("Traceback" in next_line):
                                    capture_started = True
                                if capture_started:
                                    # Strip noisy timestamp prefixes if present
                                    cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}.*?:\s*", "", next_line)
                                    capture.append(cleaned)

                                # Extract locator hint if available (we add this in BenchSale_Conftest)
                                if not xpath:
                                    m_hint = re.search(r"Locator/XPath hint:\s*(.+)$", next_line, re.IGNORECASE)
                                    if m_hint:
                                        xpath = m_hint.group(1).strip()
                                if not xpath:
                                    xpath_match = re.search(r"(xpath=[^\s]+)", next_line, re.IGNORECASE)
                                    if xpath_match:
                                        xpath = xpath_match.group(1).strip()

                                # Extract failure location (first "file.py:line:" frame)
                                if not failure_location:
                                    loc_match = re.search(r"([A-Za-z0-9_\\./-]+\.py:\d+:\s+in\s+.+)$", next_line)
                                    if loc_match:
                                        failure_location = loc_match.group(1).strip()

                        if capture:
                            # Keep a readable multi-line failure message
                            # Remove leading "Message:" label if present in first line
                            if capture[0].lower().startswith("message:"):
                                capture[0] = capture[0][len("message:"):].strip()
                            failure_message = "\n".join(capture).strip()

                    # Backward fallback (sometimes elapsed line appears just before TEST ...: PASS/FAIL)
                    if running_time == 'N/A':
                        for back in range(max(0, line_no - 50), line_no):
                            prev = lines[back].strip()
                            m_elapsed = elapsed_pattern.search(prev)
                            if m_elapsed:
                                running_time = m_elapsed.group(1).strip()
                                break
                            m_rt = runtime_seconds_pattern.search(prev)
                            if m_rt:
                                running_time = f"{m_rt.group(1).strip()} seconds"
                                break
                    
                    test_entry = {
                        'name': test_name,
                        'status': status,
                        'line': line_no,
                        'raw_line': line,
                        'running_time': running_time,
                        'failure_message': failure_message,
                        'failure_location': failure_location,
                        'xpath': xpath
                    }
                    
                    # For db_solr_sync test, read filtered count from JSON file (same as log_history_api.py)
                    json_read_success = False
                    if 'db_solr_sync' in test_name.lower():
                        json_failure_path = project_root / 'reports' / 'db_solr_sync_failures.json'
                        if json_failure_path.exists():
                            try:
                                with open(json_failure_path, 'r', encoding='utf-8') as f:
                                    json_data = json.load(f)
                                # Get total jobs from JSON
                                json_total_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
                                if json_total_jobs > 0:
                                    total_jobs = json_total_jobs
                                
                                # Filter failures using same logic as log_history_api.py
                                failures_list = json_data.get('failures', [])
                                filtered_failures = []
                                for f in failures_list:
                                    error_msg = str(f.get('msg', '')).strip()
                                    if not _should_filter_failure_message(error_msg):
                                        filtered_failures.append(f)
                                
                                # Use filtered count instead of unfiltered count from log
                                filtered_error_count = len(filtered_failures)
                                # Always use filtered count (even if 0) to override log file count
                                error_jobs_count = filtered_error_count
                                json_read_success = True
                            except Exception as e:
                                # If JSON read fails, fall back to log file count
                                print(f"Warning: Could not read JSON file for {test_name}: {e}")
                    
                    # Add 12hrs job report data for db_solr_sync test
                    if total_jobs > 0:
                        test_entry['total_jobs'] = total_jobs
                    # For db_solr_sync test, always include error_jobs_count if JSON was read (even if 0)
                    # For other tests, only include if > 0
                    if 'db_solr_sync' in test_name.lower() and json_read_success:
                        test_entry['error_jobs_count'] = error_jobs_count
                    elif error_jobs_count > 0:
                        test_entry['error_jobs_count'] = error_jobs_count
                    
                    tests.append(test_entry)
                
                # Check for test statistics to detect if tests were collected but not executed
                stats_match = stats_pattern.search(line)
                if stats_match:
                    total_tests_collected = int(stats_match.group(1))
                    passed = int(stats_match.group(2))
                    failed = int(stats_match.group(3))
                    skipped = int(stats_match.group(4))
                    stats_tests_executed = passed + failed + skipped
        
        # Only show warning if NO actual test results were found AND statistics show 0 executed
        # This prevents false warnings when tests were actually executed
        if actual_test_results_found == 0 and total_tests_collected and total_tests_collected > 0:
            # Check the last statistics line to see if tests were executed
            if stats_tests_executed == 0:
                tests.append({
                    'name': f'⚠️ {total_tests_collected} tests collected but not executed. Please run the tests to see results.',
                    'status': 'SKIP',
                    'line': 0,
                    'raw_line': f'Status: {total_tests_collected} tests total, 0 passed, 0 failed, 0 skipped'
                })
            
    except Exception as e:
        print(f"Error parsing log file {log_file_path}: {e}")
    
    return tests


def find_screenshots_for_test(test_name: str, reports_dir: Path):
    """Find screenshots associated with a test. Returns only the LATEST screenshot(s) for the test."""
    screenshots = []
    if not reports_dir.exists():
        return screenshots
    
    # Clean test name for matching
    clean_name = re.sub(r'[^\w\s-]', '', test_name).replace(' ', '_').lower()
    
    # Collect all matching PNG files with their modification times
    matching_files = []
    for png_file in reports_dir.glob('*.png'):
        if clean_name in png_file.name.lower() or test_name.replace(' ', '_').lower() in png_file.name.lower():
            # Extract timestamp from filename (format: test_name_YYYYMMDD_HHMMSS.png)
            timestamp_match = re.search(r'_(\d{8}_\d{6})\.png$', png_file.name)
            if timestamp_match:
                # Use timestamp from filename for sorting (more reliable than file mtime)
                timestamp_str = timestamp_match.group(1)
                try:
                    # Parse timestamp: YYYYMMDD_HHMMSS
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    matching_files.append({
                        'path': str(png_file),
                        'url': f"file:///{str(png_file).replace(os.sep, '/')}",
                        'name': png_file.name,
                        'timestamp': timestamp,
                        'mtime': png_file.stat().st_mtime  # Fallback to file modification time
                    })
                except ValueError:
                    # If timestamp parsing fails, use file modification time
                    matching_files.append({
                        'path': str(png_file),
                        'url': f"file:///{str(png_file).replace(os.sep, '/')}",
                        'name': png_file.name,
                        'timestamp': datetime.fromtimestamp(png_file.stat().st_mtime),
                        'mtime': png_file.stat().st_mtime
                    })
            else:
                # No timestamp in filename, use file modification time
                matching_files.append({
                    'path': str(png_file),
                    'url': f"file:///{str(png_file).replace(os.sep, '/')}",
                    'name': png_file.name,
                    'timestamp': datetime.fromtimestamp(png_file.stat().st_mtime),
                    'mtime': png_file.stat().st_mtime
                })
    
    if not matching_files:
        return screenshots
    
    # Sort by timestamp (most recent first)
    matching_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Return only the LATEST screenshot (most recent run)
    # This ensures only the latest test run's screenshot is shown in the dashboard
    latest_file = matching_files[0]
    screenshots.append({
        'path': latest_file['path'],
        'url': latest_file['url'],
        'name': latest_file['name']
    })
    
    return screenshots


def find_failure_artifacts_for_test(test_name: str, reports_dir: Path):
    """
    Find the latest (screenshot, html, url.txt) artifacts for a test under reports/failures.
    Returns dict with keys: screenshot_url, html_url, url_txt_url (any may be empty).
    """
    artifacts = {"screenshot_url": "", "html_url": "", "url_txt_url": ""}
    if not reports_dir.exists():
        return artifacts

    clean_name = re.sub(r'[^\w\s-]', '', test_name).replace(' ', '_').lower()

    # Find latest screenshot first (by timestamp if present)
    candidates = []
    for png_file in reports_dir.glob('*.png'):
        if clean_name in png_file.name.lower() or test_name.replace(' ', '_').lower() in png_file.name.lower():
            timestamp_match = re.search(r'_(\d{8}_\d{6})\.png$', png_file.name)
            ts = None
            if timestamp_match:
                try:
                    ts = datetime.strptime(timestamp_match.group(1), '%Y%m%d_%H%M%S')
                except Exception:
                    ts = None
            candidates.append((ts or datetime.fromtimestamp(png_file.stat().st_mtime), png_file))

    if not candidates:
        return artifacts

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_png = candidates[0][1]
    artifacts["screenshot_url"] = f"file:///{str(latest_png).replace(os.sep, '/')}"

    # If we have a timestamp in the filename, prefer matching html/url with same timestamp
    ts_match = re.search(r'_(\d{8}_\d{6})\.png$', latest_png.name)
    if ts_match:
        ts_str = ts_match.group(1)
        # Artifacts from BenchSale_Conftest: <safe_name>_<ts>.html and <safe_name>_<ts>.url.txt
        html_candidates = list(reports_dir.glob(f"*_{ts_str}.html"))
        url_candidates = list(reports_dir.glob(f"*_{ts_str}.url.txt"))
        if html_candidates:
            artifacts["html_url"] = f"file:///{str(html_candidates[0]).replace(os.sep, '/')}"
        if url_candidates:
            artifacts["url_txt_url"] = f"file:///{str(url_candidates[0]).replace(os.sep, '/')}"

    return artifacts


def discover_tests_from_code(project_root: Path):
    """Discover all test cases from pytest test files automatically.
    Returns a dict mapping test_name -> {'source': 'Employer'|'Admin'|'Recruiter', 'status': 'NOT_RUN'}"""
    discovered_tests = {}
    
    # Method 1: Direct file parsing (more reliable than pytest collection)
    try:
        # Discover Employer tests
        employer_test_file = project_root / 'tests' / 'employer' / 'test_employer_test_cases.py'
        if employer_test_file.exists():
            with open(employer_test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find all test function definitions
                # Pattern: def test_t1_01_home_page( or def test_t2_03_verification_of_closing_a_job...
                test_pattern = re.compile(r'def\s+(test_\w+)\(', re.MULTILINE)
                for match in test_pattern.finditer(content):
                    test_name = match.group(1)
                    if is_valid_employer_test(test_name):
                        discovered_tests[test_name] = {
                            'name': test_name,
                            'source': 'Employer',
                            'status': 'NOT_RUN',
                            'line': 0,
                            'raw_line': f'Discovered from code: {employer_test_file}',
                            'running_time': 'N/A',
                            'failure_message': '',
                            'failure_location': '',
                            'xpath': ''
                        }
        
        # Discover Admin tests
        admin_test_file = project_root / 'tests' / 'benchsale' / 'test_benchsale_admin_test_cases.py'
        if admin_test_file.exists():
            with open(admin_test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                test_pattern = re.compile(r'def\s+(test_\w+)\(', re.MULTILINE)
                for match in test_pattern.finditer(content):
                    test_name = match.group(1)
                    discovered_tests[test_name] = {
                        'name': test_name,
                        'source': 'Admin',
                        'status': 'NOT_RUN',
                        'line': 0,
                        'raw_line': f'Discovered from code: {admin_test_file}',
                        'running_time': 'N/A',
                        'failure_message': '',
                        'failure_location': '',
                        'xpath': ''
                    }
        
        # Discover Recruiter tests
        recruiter_test_file = project_root / 'tests' / 'benchsale' / 'test_benchsale_recruiter_test_cases.py'
        if recruiter_test_file.exists():
            with open(recruiter_test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                test_pattern = re.compile(r'def\s+(test_\w+)\(', re.MULTILINE)
                for match in test_pattern.finditer(content):
                    test_name = match.group(1)
                    discovered_tests[test_name] = {
                        'name': test_name,
                        'source': 'Recruiter',
                        'status': 'NOT_RUN',
                        'line': 0,
                        'raw_line': f'Discovered from code: {recruiter_test_file}',
                        'running_time': 'N/A',
                        'failure_message': '',
                        'failure_location': '',
                        'xpath': ''
                    }
        
        # Discover Job Seeker tests
        jobseeker_dir = project_root / 'tests' / 'jobseeker'
        if jobseeker_dir.exists():
            for jobseeker_test_file in jobseeker_dir.glob('test_*.py'):
                try:
                    with open(jobseeker_test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        test_pattern = re.compile(r'def\s+(test_\w+)\(', re.MULTILINE)
                        for match in test_pattern.finditer(content):
                            test_name = match.group(1)
                            # Only add if not already discovered (in case of name collisions, though unlikely)
                            if test_name not in discovered_tests:
                                discovered_tests[test_name] = {
                                    'name': test_name,
                                    'source': 'Job Seeker',
                                    'status': 'NOT_RUN',
                                    'line': 0,
                                    'raw_line': f'Discovered from code: {jobseeker_test_file.name}',
                                    'running_time': 'N/A',
                                    'failure_message': '',
                                    'failure_location': '',
                                    'xpath': ''
                                }
                except Exception as e:
                    print(f"Warning: Could not reading jobseeker test file {jobseeker_test_file}: {e}")
    except Exception as e:
        print(f"Warning: Could not discover tests from code: {e}")
    
    return discovered_tests


def generate_unified_dashboard():
    """Generate a unified dashboard HTML showing both Admin and Recruiter logs.
    This function is called automatically after each test run to ensure latest results are shown.
    """
    import time
    import os
    
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / 'logs'
    reports_dir = project_root / 'reports' / 'failures'
    
    admin_log = logs_dir / 'benchsale_admin.log'
    recruiter_log = logs_dir / 'benchsale_recruiter.log'
    employer_log = logs_dir / 'employer.log'
    jobseeker_log = logs_dir / 'jobseeker.log'
    main_log = logs_dir / 'benchsale_test.log'
    
    # CRITICAL: Wait for log files to be fully written before reading
    # This ensures we capture the latest test status (PASS/FAIL)
    time.sleep(2.0)  # Increased to 2 seconds to ensure log files are fully flushed
    
    # Force file system sync to ensure all log files are written
    try:
        # Sync all log files to disk
        for log_file in [admin_log, recruiter_log, employer_log, jobseeker_log, main_log]:
            if log_file.exists():
                try:
                    # Touch the file to ensure it's synced
                    log_file.touch()
                    # Force sync on Windows
                    if sys.platform == 'win32':
                        # On Windows, we can't directly sync, but touching helps
                        pass
                    else:
                        # On Unix, sync the directory
                        os.sync()
                except Exception:
                    pass
    except Exception:
        pass
    
    all_tests = []
    
    # Parse ALL log files to preserve all test results
    # Each entry in all_tests will now also track the file's modification time
    # IMPORTANT: Always use the LATEST test result if a test appears multiple times
    def get_tests_with_mtime(log_path, source):
        if not log_path.exists():
            return []
        
        # Get file modification time BEFORE reading (to detect if file changes during read)
        initial_mtime = log_path.stat().st_mtime
        
        # Read and parse the log file
        results = parse_test_results_from_log(str(log_path))
        
        # Check if file was modified during reading (means new data was written)
        try:
            final_mtime = log_path.stat().st_mtime
            if final_mtime > initial_mtime:
                # File was modified during reading - re-read to get latest data
                time.sleep(2.0)  # Increased wait to ensure write is complete
                results = parse_test_results_from_log(str(log_path))
                final_mtime = log_path.stat().st_mtime
                # If file was modified again, wait once more and re-read
                if log_path.stat().st_mtime > final_mtime:
                    time.sleep(1.0)
                    results = parse_test_results_from_log(str(log_path))
                    final_mtime = log_path.stat().st_mtime
                    # One more check for very recent writes
                    if log_path.stat().st_mtime > final_mtime:
                        time.sleep(0.5)
                        results = parse_test_results_from_log(str(log_path))
                        final_mtime = log_path.stat().st_mtime
        except Exception:
            final_mtime = initial_mtime
        
        return [{**t, 'source': source, 'mtime': final_mtime} for t in results]

    all_tests = []
    all_tests.extend(get_tests_with_mtime(admin_log, 'Admin'))
    all_tests.extend(get_tests_with_mtime(recruiter_log, 'Recruiter'))
    all_tests.extend(get_tests_with_mtime(employer_log, 'Employer'))
    all_tests.extend(get_tests_with_mtime(jobseeker_log, 'Job Seeker'))
    
    # Main log - parse for any extra tests
    if main_log.exists():
        main_results = get_tests_with_mtime(main_log, 'Main')
        all_tests.extend(main_results)
    
    # CRITICAL: Also read from history files to get latest status (for tests that failed during setup)
    # This ensures dashboard shows correct status even when log files don't have recent entries
    try:
        sys.path.insert(0, str(project_root))
        from utils.log_history_api import load_historical_data
        
        # Map log sources to history modules
        history_modules = {
            'Admin': 'benchsale_admin',
            'Recruiter': 'benchsale_recruiter',
            'Employer': 'employer',
            'Job Seeker': 'jobseeker'
        }
        
        # Get latest test status from history for each module
        for source, module in history_modules.items():
            try:
                history = load_historical_data(module, force_reload=False)
                today = datetime.now().strftime('%Y-%m-%d')
                history_count = 0
                for test_name, entries in history.items():
                    if entries:
                        # Get the latest entry (first one is most recent)
                        latest_entry = entries[0]
                        status = latest_entry.get('status', 'NOT_RUN')
                        date = latest_entry.get('date', '')
                        datetime_str = latest_entry.get('datetime', '')
                        running_time = latest_entry.get('running_time', 'N/A')
                        
                        # CRITICAL: Always add today's entries from history, even if log has old entries
                        # Use actual datetime from history entry for proper timestamp comparison
                        if date == today:
                            # Parse datetime from history entry to get accurate timestamp
                            history_datetime_str = latest_entry.get('datetime', '')
                            history_mtime = datetime.now().timestamp()  # Default to now if no datetime
                            
                            if history_datetime_str:
                                try:
                                    # Try to parse ISO format datetime
                                    if 'T' in history_datetime_str or '+' in history_datetime_str:
                                        # ISO format: 2026-02-05T15:58:04.531000 or with timezone
                                        dt_str = history_datetime_str.split('+')[0].split('.')[0]  # Remove timezone and microseconds
                                        if len(dt_str) == 19:  # YYYY-MM-DDTHH:MM:SS
                                            dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                                            history_mtime = dt.timestamp()
                                        else:
                                            # Try with microseconds
                                            dt = datetime.fromisoformat(history_datetime_str.replace('Z', '+00:00'))
                                            history_mtime = dt.timestamp()
                                    else:
                                        # Try other formats
                                        dt = datetime.strptime(history_datetime_str, '%Y-%m-%d %H:%M:%S')
                                        history_mtime = dt.timestamp()
                                except Exception:
                                    # If parsing fails, use current time
                                    history_mtime = datetime.now().timestamp()
                            
                            # Use actual line number from log file if available, otherwise use a reasonable default
                            # We'll compare by mtime and line number, not artificially inflated values
                            test_entry = {
                                'name': test_name,
                                'status': status,
                                'line': 0,  # History entries don't have line numbers - use 0, comparison will use mtime
                                'raw_line': f'TEST {test_name}: {status}',
                                'running_time': running_time,
                                'failure_message': latest_entry.get('failure_message', '') or latest_entry.get('error_details', ''),
                                'source': source,
                                'mtime': history_mtime,  # Use actual datetime from history entry
                                'from_history': True,  # Mark as from history for special handling
                                'history_date': date,  # Store date for comparison
                                'history_datetime': history_datetime_str  # Store original datetime string
                            }
                            all_tests.append(test_entry)
                            history_count += 1
                if history_count > 0:
                    print(f"Added {history_count} test entries from {module} history for today")
            except Exception as e:
                # Log error but continue
                print(f"Warning: Could not load history for {module}: {e}")
                import traceback
                traceback.print_exc()
    except Exception:
        # Silently continue if history import fails
        pass
    
    # Filter out warning messages (collected but not executed tests)
    # Only keep actual test results
    actual_tests = []
    for test in all_tests:
        # Skip warning messages about collected but not executed tests
        if '⚠️' in test['name'] or 'collected but not executed' in test['name']:
            continue
        
        # For Employer tests, only keep tests that are in JnP_final.robot
        # Remove old test cases that are not in the Robot file (like test_e1_01_employer1_dashboard_verification)
        if test.get('source') == 'Employer':
            if not is_valid_employer_test(test['name']):
                continue  # Skip this test - it's not in JnP_final.robot
        
        actual_tests.append(test)
    
    # Discover all tests from code (automatically sync with test files)
    discovered_tests = discover_tests_from_code(project_root)
    
    # Deduplicate tests by (name, source) - keep ONLY the latest result (by line number)
    # This ensures:
    # 1. Admin, Recruiter, and Employer tests all show up (different sources)
    # 2. If same test runs multiple times, only latest status is shown (update in place)
    # 3. No duplicate entries for the same test
    # 4. Old failed tests are automatically replaced by new results (update in place)
    # 5. Only the most recent test result is shown (old results are discarded)
    # 6. Tests discovered from code but not yet run will show as "NOT_RUN"
    test_dict = {}
    
    # First, add all discovered tests from code (as NOT_RUN)
    for test_name, test_info in discovered_tests.items():
        test_key = (test_name, test_info['source'])
        test_dict[test_key] = test_info
    
    # Then, update with actual test results from logs (overwrites NOT_RUN status)
    # CRITICAL: Sort by (from_history flag, line, mtime) descending to process latest results first
    # History entries for today should always be processed first to override old log entries
    # Line number is the most reliable indicator of recency within the same log file
    def sort_key(x):
        from_history = 1 if (x.get('from_history', False) and x.get('history_date', '') == datetime.now().strftime('%Y-%m-%d')) else 0
        # Prioritize: history flag > line number > mtime
        # Higher line number = appears later in log = more recent = should be processed first
        return (from_history, x.get('line', 0), x.get('mtime', 0))
    actual_tests_sorted = sorted(actual_tests, key=sort_key, reverse=True)
    
    for test in actual_tests_sorted:
        test_key = (test['name'], test.get('source', 'Main'))
        
        # IMPROVED DEDUPLICATION LOGIC:
        # Always use the LATEST result to ensure dashboard shows current PASS/FAIL status
        # Since we sorted by (mtime, line) descending, first entry for each test_key is the latest
        existing = test_dict.get(test_key)
        
        # CRITICAL: Compare timestamps when both entries are from today
        # Always prefer the MOST RECENT result, regardless of source (history vs log)
        today = datetime.now().strftime('%Y-%m-%d')
        current_from_history = test.get('from_history', False)
        current_history_date = test.get('history_date', '')
        existing_from_history = existing.get('from_history', False) if existing else False
        existing_history_date = existing.get('history_date', '') if existing else ''
        
        # If both are from today, compare timestamps to find the most recent
        # Only history entries have reliable per-entry dates; log entries do not.
        current_is_today = current_from_history and current_history_date == today
        existing_is_today = (existing_from_history and existing_history_date == today) if existing else False
        
        if current_is_today and existing_is_today:
            # Both are from today - compare timestamps (mtime) to find most recent
            current_mtime = test.get('mtime', 0)
            existing_mtime = existing.get('mtime', 0) if existing else 0
            current_line = test.get('line', 0)
            existing_line = existing.get('line', 0) if existing else 0
            
            # Prefer higher line number first (most reliable indicator of recency)
            if current_line > existing_line:
                test_dict[test_key] = test
                continue
            elif current_line < existing_line:
                continue  # Keep existing
            elif current_mtime > existing_mtime:
                # Same line, but newer mtime
                test_dict[test_key] = test
                continue
            else:
                # Existing is newer or same - keep existing
                continue
        
        # If only current is from today, use it
        if current_is_today and not existing_is_today:
            test_dict[test_key] = test
            continue
        
        # If only existing is from today, keep it
        if existing_is_today and not current_is_today:
            continue
        
        if not existing or existing.get('status') == 'NOT_RUN':
            # No existing result or it's NOT_RUN - always use new result
            test_dict[test_key] = test
        else:
            # Compare mtime and line number - always prefer newer/higher result
            existing_mtime = existing.get('mtime', 0)
            current_mtime = test.get('mtime', 0)
            existing_line = existing.get('line', 0)
            current_line = test.get('line', 0)
            
            # CRITICAL FIX: Always prefer result with higher line number FIRST (appears later in log = more recent)
            # Line number is the most reliable indicator of recency within the same log file
            # Only use mtime as tiebreaker when line numbers are equal
            if current_line > existing_line:
                # Current result appears later in log file = more recent = always use it
                test_dict[test_key] = test
            elif current_line < existing_line:
                # Existing result appears later in log file = more recent = keep existing
                pass
            else:
                # Same line number - use mtime and status as tiebreakers
                time_diff = current_mtime - existing_mtime
                existing_status = existing.get('status', '')
                current_status = test.get('status', '')
                
                # Priority: PASS/FAIL > SKIP (actual execution results are more important than skipped tests)
                if current_status in ['PASS', 'FAIL'] and existing_status == 'SKIP':
                    # Current is actual result (PASS/FAIL), existing is SKIP - prefer current
                    test_dict[test_key] = test
                elif current_status == 'SKIP' and existing_status in ['PASS', 'FAIL']:
                    # Current is SKIP, existing is actual result - keep existing
                    pass
                elif time_diff > 2.0:
                    # Newer file by more than 2 seconds - use this result
                    test_dict[test_key] = test
                elif time_diff < -2.0:
                    # Existing is newer by more than 2 seconds - keep existing
                    pass
                elif current_mtime > existing_mtime:
                    # Same line, same status type, but newer mtime - prefer current
                    test_dict[test_key] = test
                # Otherwise keep existing (same line, same mtime, same status type)

    # Attach latest failure artifacts (screenshot/html/url) from reports/failures
    # so the right-side details panel can open them.
    # IMPORTANT: Only attach screenshots for FAILED tests. For PASSED tests, clear any old screenshots.
    for (tname, _source), tinfo in list(test_dict.items()):
        try:
            test_status = tinfo.get("status", "").upper()
            # Only attach screenshots/artifacts for FAILED tests
            if test_status == "FAIL" or test_status == "FAILED":
                artifacts = find_failure_artifacts_for_test(tname, reports_dir)
                # Keep existing screenshots logic, but also add html/url links
                if artifacts.get("screenshot_url"):
                    tinfo.setdefault("screenshots", [])
                    # Do not duplicate
                    if not tinfo["screenshots"]:
                        tinfo["screenshots"] = [artifacts["screenshot_url"]]
                tinfo["artifacts"] = {
                    "html_url": artifacts.get("html_url", ""),
                    "url_txt_url": artifacts.get("url_txt_url", ""),
                }
            else:
                # For PASS/SKIP/NOT_RUN tests, explicitly clear screenshots and artifacts
                # This ensures old screenshots from previous failed runs are not shown
                tinfo["screenshots"] = []
                tinfo["artifacts"] = {
                    "html_url": "",
                    "url_txt_url": "",
                }
            test_dict[(tname, _source)] = tinfo
        except Exception:
            pass
    
    # Remove tests that are no longer in code
    # This ensures removed tests are automatically removed from dashboard
    # The code is the source of truth - if a test function is deleted, it should be gone from report
    
    # Get all valid test names from code by source
    employer_tests_in_code = {name for name, info in discovered_tests.items() if info['source'] == 'Employer'}
    admin_tests_in_code = {name for name, info in discovered_tests.items() if info['source'] == 'Admin'}
    recruiter_tests_in_code = {name for name, info in discovered_tests.items() if info['source'] == 'Recruiter'}
    jobseeker_tests_in_code = {name for name, info in discovered_tests.items() if info['source'] == 'Job Seeker'}
    
    keys_to_remove = []
    for test_key, test_info in test_dict.items():
        test_name = test_key[0]
        source = test_info.get('source')
        
        # Check Employer tests
        if source == 'Employer':
            if test_name not in employer_tests_in_code:
                keys_to_remove.append(test_key)
                
        # Check Admin tests
        elif source == 'Admin':
            if test_name not in admin_tests_in_code:
                keys_to_remove.append(test_key)
                
        # Check Recruiter tests
        elif source == 'Recruiter':
            if test_name not in recruiter_tests_in_code:
                keys_to_remove.append(test_key)
        
        # Check Job Seeker tests
        elif source == 'Job Seeker':
            if test_name not in jobseeker_tests_in_code:
                keys_to_remove.append(test_key)
    
    for key in keys_to_remove:
        del test_dict[key]
    
    # Convert back to list - sorted by source then name for consistent display
    all_tests = list(test_dict.values())
    all_tests.sort(key=lambda x: (x.get('source', 'Main'), x['name']))
    
    # Calculate statistics
    # For Employer: include NOT_RUN in total to show all tests
    # For BenchSale: exclude NOT_RUN from totals for cleaner stats
    # For Job Seeker: include NOT_RUN in total to show all tests
    employer_tests = [t for t in all_tests if t.get('source') == 'Employer']
    jobseeker_tests = [t for t in all_tests if t.get('source') == 'Job Seeker']
    # BenchSale tests = Admin + Recruiter ONLY (exclude Employer, Job Seeker and Main)
    benchsale_tests = [t for t in all_tests if t.get('source') in ['Admin', 'Recruiter']]
    
    # Employer stats (include NOT_RUN)
    employer_total = len(employer_tests)
    employer_passed = len([t for t in employer_tests if t['status'] == 'PASS'])
    employer_failed = len([t for t in employer_tests if t['status'] == 'FAIL'])
    employer_skipped = len([t for t in employer_tests if t['status'] == 'SKIP'])
    employer_not_run = len([t for t in employer_tests if t.get('status') == 'NOT_RUN'])
    
    # Job Seeker stats (include NOT_RUN)
    jobseeker_total = len(jobseeker_tests)
    jobseeker_passed = len([t for t in jobseeker_tests if t['status'] == 'PASS'])
    jobseeker_failed = len([t for t in jobseeker_tests if t['status'] == 'FAIL'])
    jobseeker_skipped = len([t for t in jobseeker_tests if t['status'] == 'SKIP'])
    jobseeker_not_run = len([t for t in jobseeker_tests if t.get('status') == 'NOT_RUN'])
    
    # BenchSale stats (exclude NOT_RUN and only count Admin + Recruiter)
    benchsale_tests_for_stats = [t for t in benchsale_tests if t.get('status') != 'NOT_RUN']
    total = len(benchsale_tests_for_stats)
    passed = len([t for t in benchsale_tests_for_stats if t['status'] == 'PASS'])
    failed = len([t for t in benchsale_tests_for_stats if t['status'] == 'FAIL'])
    skipped = len([t for t in benchsale_tests_for_stats if t['status'] == 'SKIP'])
    not_run = employer_not_run  # Only show NOT_RUN for Employer
    
    # Find screenshots ONLY for failed tests
    # For passed tests, explicitly set screenshots to empty array to ensure no old screenshots are shown
    for test in all_tests:
        if test['status'] == 'FAIL':
            test['screenshots'] = find_screenshots_for_test(test['name'], reports_dir)
        else:
            # For PASS/SKIP/NOT_RUN tests, ensure no screenshots are shown
            test['screenshots'] = []
    
    # Get last modified time of log files for "Last Updated" display
    # We calculate per-section timestamps AND an overall timestamp
    last_updated = None
    
    # Validation: Only show timestamp if actual tests were executed (status != 'NOT_RUN')
    # This prevents showing a timestamp for a log file that exists but has no valid results
    benchsale_has_run = any(t.get('status') != 'NOT_RUN' for t in benchsale_tests)
    employer_has_run = any(t.get('status') != 'NOT_RUN' for t in employer_tests)
    jobseeker_has_run = any(t.get('status') != 'NOT_RUN' for t in jobseeker_tests)
    
    # BenchSale Timestamp (Admin or Recruiter)
    benchsale_last_updated = None
    if benchsale_has_run:
        if admin_log.exists():
            admin_mtime = datetime.fromtimestamp(admin_log.stat().st_mtime)
            if benchsale_last_updated is None or admin_mtime > benchsale_last_updated:
                benchsale_last_updated = admin_mtime
        if recruiter_log.exists():
            recruiter_mtime = datetime.fromtimestamp(recruiter_log.stat().st_mtime)
            if benchsale_last_updated is None or recruiter_mtime > benchsale_last_updated:
                benchsale_last_updated = recruiter_mtime
            
    # Employer Timestamp
    employer_last_updated = None
    if employer_has_run and employer_log.exists():
        employer_last_updated = datetime.fromtimestamp(employer_log.stat().st_mtime)
        
    # Job Seeker Timestamp
    jobseeker_last_updated = None
    if jobseeker_has_run and jobseeker_log.exists():
        jobseeker_last_updated = datetime.fromtimestamp(jobseeker_log.stat().st_mtime)
        
    # Overall Timestamp (Max of all valid section timestamps)
    # If no sections ran, this stays as datetime.now() (Report Generated Time)
    timestamps = [ts for ts in [benchsale_last_updated, employer_last_updated, jobseeker_last_updated] if ts is not None]
    if timestamps:
        last_updated = max(timestamps)
    
    # Generate HTML
    html_content = generate_dashboard_html(
        all_tests, total, passed, failed, skipped, 
        employer_total, employer_passed, employer_failed, employer_skipped, employer_not_run,
        jobseeker_total, jobseeker_passed, jobseeker_failed, jobseeker_skipped, jobseeker_not_run,
        admin_log, recruiter_log, employer_log, jobseeker_log, main_log, 
        last_updated, benchsale_last_updated, employer_last_updated, jobseeker_last_updated
    )
    
    # Write dashboard HTML (always overwrite to ensure latest content)
    dashboard_path = logs_dir / 'index.html'
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        f.flush()  # Force write to buffer
        try:
            os.fsync(f.fileno())  # Force sync to disk (Unix/Windows)
        except Exception:
            pass  # Some systems don't support fsync
    
    # CRITICAL: Update file timestamp to ensure browser detects the change
    # This forces browser to reload even if cache says file hasn't changed
    try:
        import time
        current_time = time.time()
        os.utime(dashboard_path, (current_time, current_time))  # Update both access and modify time
    except Exception as e:
        print(f"Warning: Could not update dashboard file timestamp: {e}")
    
    # Verify file was written
    if dashboard_path.exists():
        file_size = dashboard_path.stat().st_size
        print(f"Dashboard written: {dashboard_path} (size: {file_size} bytes)")
    
    return str(dashboard_path)


def generate_dashboard_html(tests, total, passed, failed, skipped, 
                            employer_total, employer_passed, employer_failed, employer_skipped, employer_not_run,
                            jobseeker_total, jobseeker_passed, jobseeker_failed, jobseeker_skipped, jobseeker_not_run,
                            admin_log, recruiter_log, employer_log, jobseeker_log, main_log, 
                            last_updated=None, benchsale_ts=None, employer_ts=None, jobseeker_ts=None):
    """Generate the HTML content for the unified dashboard."""
    
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format timestamps
    # Format: 16 Jan 2026, 11:32 AM
    fmt = '%d %b %Y, %I:%M %p'
    last_updated_str = last_updated.strftime(fmt) if last_updated else "Not Run Yet"
    
    benchsale_ts_str = benchsale_ts.strftime(fmt) if benchsale_ts else "Not Run Yet"
    employer_ts_str = employer_ts.strftime(fmt) if employer_ts else "Not Run Yet"
    jobseeker_ts_str = jobseeker_ts.strftime(fmt) if jobseeker_ts else "Not Run Yet"
    
    # Group tests by source - separate BenchSale (Admin + Recruiter) from Employer and Job Seeker
    admin_tests = [t for t in tests if t.get('source') == 'Admin']
    recruiter_tests = [t for t in tests if t.get('source') == 'Recruiter']
    employer_tests = [t for t in tests if t.get('source') == 'Employer']
    jobseeker_tests = [t for t in tests if t.get('source') == 'Job Seeker']
    main_tests = [t for t in tests if t.get('source') == 'Main' or not t.get('source')]
    
    # BenchSale tests = Admin + Recruiter ONLY (exclude Employer, Job Seeker and Main)
    # Main tests are also excluded from BenchSale to keep it clean
    benchsale_tests = [t for t in tests if t.get('source') in ['Admin', 'Recruiter']]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BenchSale Test Dashboard - Unified Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

        :root {{
            --primary: #F97316;
            --primary-dark: #C2410C;
            --primary-light: #FFEDD5;
            --secondary: #F59E0B;
            --accent: #EA580C;
            --dark: #0F172A;
            --light: #F8FAFC;
            --card-bg: #FFFFFF;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --success: #22C55E;
            --success-bg: #F0FDF4;
            --danger: #EF4444;
            --danger-bg: #FEF2F2;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
            --not-run: #94A3B8;
            --not-run-bg: #F8FAFC;
            --glass-border: rgba(226, 232, 240, 0.8);
        }}

        /* Smooth Scrolling */
        html {{
            scroll-behavior: smooth;
            -webkit-text-size-adjust: 100%;
            text-size-adjust: 100%;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
            font-feature-settings: "kern" 1;
            font-kerning: normal;
        }}
        
        body {{
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #F1F5F9;
            min-height: 100vh;
            padding: 0;
            position: relative;
            color: var(--text-primary);
        }}

        /* Animated Bubble Background with HD Colors */
        .background-bubbles {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
            pointer-events: none;
        }}

        .bubble {{
            position: absolute;
            border-radius: 50%;
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(245, 158, 11, 0.2));
            filter: blur(50px);
            animation: floatBubble 25s infinite ease-in-out;
            opacity: 0.7;
            box-shadow: 0 0 40px rgba(249, 115, 22, 0.1);
        }}

        .bubble:nth-child(1) {{ top: -10%; left: -10%; width: 700px; height: 700px; background: radial-gradient(circle, rgba(249, 115, 22, 0.25) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 35s; }}
        .bubble:nth-child(2) {{ bottom: -10%; right: -10%; width: 600px; height: 600px; background: radial-gradient(circle, rgba(245, 158, 11, 0.25) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 40s; animation-delay: -5s; }}
        .bubble:nth-child(3) {{ top: 40%; left: 40%; width: 400px; height: 400px; background: radial-gradient(circle, rgba(234, 88, 12, 0.2) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 30s; animation-delay: -10s; }}
        .bubble:nth-child(4) {{ bottom: 20%; left: 10%; width: 300px; height: 300px; background: radial-gradient(circle, rgba(251, 146, 60, 0.25) 0%, rgba(0, 0, 0, 0) 70%); animation-duration: 25s; animation-delay: -8s; }}

        @keyframes floatBubble {{
            0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }}
            33% {{ transform: translate(40px, -60px) scale(1.1) rotate(5deg); }}
            66% {{ transform: translate(-30px, 30px) scale(0.95) rotate(-5deg); }}
        }}
        
        .container {{
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 15px;
            padding-top: 110px;
            padding-bottom: 30px;
        }}
        
        /* Glassmorphism Header - Fixed at top */
        
        .header {{
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: 0 0 20px 20px;
            padding: 8px 14px;
            box-shadow:
                0 4px 20px -5px rgba(0, 0, 0, 0.08),
                0 2px 10px -2px rgba(249, 115, 22, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 1);
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-top: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: center;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            width: 100%;
            height: 65px;
        }}

        .header-content {{
            flex: 1;
            display: flex;
            align-items: center;
            gap: 15px;
            min-width: 0;
        }}

        .header-home-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            background: white;
            color: var(--primary);
            border-radius: 12px;
            text-decoration: none;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            flex-shrink: 0;
            border: 1.5px solid rgba(249, 115, 22, 0.2);
        }}

        .header-home-btn:hover {{
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 5px 15px rgba(249, 115, 22, 0.2);
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}

        .header-home-btn svg {{
            width: 22px;
            height: 22px;
            stroke-width: 2.5;
        }}
        
        .dashboard-logo {{
            width: 32px;
            height: 32px;
            flex-shrink: 0;
            position: relative;
            filter: drop-shadow(0 0 5px rgba(249, 115, 22, 0.3));
        }}
        
        .dashboard-logo.employer-logo {{
            filter: drop-shadow(0 0 15px rgba(217, 119, 6, 0.4));
        }}
        
        .dashboard-logo.jobseeker-logo {{
            filter: drop-shadow(0 0 15px rgba(22, 163, 74, 0.4));
        }}
        
        .dashboard-logo svg {{
            width: 100%;
            height: 100%;
        }}
        
        .benchsale-logo-svg {{
            animation: rocketPulse 2s ease-in-out infinite, rocketGlow 3s ease-in-out infinite;
        }}
        
        .employer-logo-svg {{
            animation: briefcasePulse 2s ease-in-out infinite, briefcaseGlow 3s ease-in-out infinite;
        }}
        
        .jobseeker-logo-svg {{
            animation: userPulse 2s ease-in-out infinite, userGlow 3s ease-in-out infinite;
        }}
        
        @keyframes rocketPulse {{
            0%, 100% {{
                transform: scale(1) translateY(0);
            }}
            50% {{
                transform: scale(1.1) translateY(-5px);
            }}
        }}
        
        @keyframes rocketGlow {{
            0%, 100% {{
                filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.8)) drop-shadow(0 0 20px rgba(249, 115, 22, 0.4));
            }}
            50% {{
                filter: drop-shadow(0 0 20px rgba(249, 115, 22, 1)) drop-shadow(0 0 30px rgba(249, 115, 22, 0.6)) drop-shadow(0 0 40px rgba(245, 158, 11, 0.4));
            }}
        }}
        
        @keyframes briefcasePulse {{
            0%, 100% {{
                transform: scale(1) rotate(0deg);
            }}
            50% {{
                transform: scale(1.1) rotate(2deg);
            }}
        }}
        
        @keyframes briefcaseGlow {{
            0%, 100% {{
                filter: drop-shadow(0 0 10px rgba(217, 119, 6, 0.8)) drop-shadow(0 0 20px rgba(217, 119, 6, 0.4));
            }}
            50% {{
                filter: drop-shadow(0 0 20px rgba(217, 119, 6, 1)) drop-shadow(0 0 30px rgba(217, 119, 6, 0.6)) drop-shadow(0 0 40px rgba(245, 158, 11, 0.4));
            }}
        }}
        
        @keyframes userPulse {{
            0%, 100% {{
                transform: scale(1) translateY(0);
            }}
            50% {{
                transform: scale(1.1) translateY(-3px);
            }}
        }}
        
        @keyframes userGlow {{
            0%, 100% {{
                filter: drop-shadow(0 0 10px rgba(22, 163, 74, 0.8)) drop-shadow(0 0 20px rgba(22, 163, 74, 0.4));
            }}
            50% {{
                filter: drop-shadow(0 0 20px rgba(22, 163, 74, 1)) drop-shadow(0 0 30px rgba(22, 163, 74, 0.6)) drop-shadow(0 0 40px rgba(34, 197, 94, 0.4));
            }}
        }}
        
        .header h1 {{
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 1.35em;
            font-weight: 700;
            margin: 0;
            margin-bottom: 0;
            background: linear-gradient(135deg, #9a3412 0%, #EA580C 50%, #F59E0B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
            letter-spacing: -0.01em;
            flex: 1;
            min-width: 0; /* Prevent overflow */
            word-wrap: break-word;
            overflow: hidden;
            text-overflow: ellipsis;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-feature-settings: "kern" 1, "liga" 1;
        }}
        
        .header .subtitle {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: var(--text-secondary);
            font-size: 0.75em;
            font-weight: 500;
            opacity: 0.95;
            margin: 0;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            letter-spacing: 0.02em;
        }}
        
         .header .last-updated {{
            color: var(--primary-dark);
            font-size: 0.65em;
            margin-top: 0;
            font-weight: 500;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            letter-spacing: 0.01em;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 8px;
            margin-top: 35px;
        }}

        .stat-card {{
            background: white;
            border-radius: 16px;
            padding: 12px 20px;
            text-align: left;
            flex: 1;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            border: 1px solid rgba(226, 232, 240, 0.8);
            display: flex;
            flex-direction: row;
            justify-content: flex-start;
            align-items: center;
            gap: 15px;
            min-height: 85px;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            border-top: none !important;
            border-left: 5px solid transparent;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
            border-color: rgba(249, 115, 22, 0.3);
        }}
        
        .stat-card .number {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            margin: 0;
            line-height: 1.1;
            letter-spacing: -0.02em;
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(45deg, transparent 0%, rgba(255,255,255,0.4) 100%);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        
        .stat-card:hover::before {{ opacity: 1; }}

        .stat-card.total {{
            border-left-color: var(--primary);
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.08);
        }}

        .stat-card.passed {{
            border-left-color: var(--success);
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.08);
        }}

        .stat-card.failed {{
            border-left-color: var(--danger);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.08);
        }}

        .stat-card.skipped {{
            border-left-color: var(--warning);
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.08);
        }}

        .stat-card.not-run-stat {{
            border-left-color: var(--not-run);
            box-shadow: 0 4px 12px rgba(148, 163, 184, 0.08);
        }}
        
        .stat-card .label {{
            color: var(--text-secondary);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.62rem;
            letter-spacing: 0.8px;
            font-family: 'Poppins', sans-serif;
            opacity: 0.7;
            margin-bottom: 2px;
        }}

        .stat-info {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            flex: 1;
            min-width: 0;
        }}

        .stat-icon {{
            width: 46px;
            height: 46px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }}

        .stat-card.total .stat-icon {{ background: rgba(249, 115, 22, 0.1); color: var(--primary); }}
        .stat-card.passed .stat-icon {{ background: rgba(34, 197, 94, 0.1); color: var(--success); }}
        .stat-card.failed .stat-icon {{ background: rgba(239, 68, 68, 0.1); color: var(--danger); }}
        .stat-card.skipped .stat-icon {{ background: rgba(245, 158, 11, 0.1); color: var(--warning); }}
        .stat-card.not-run-stat .stat-icon {{ background: rgba(148, 163, 184, 0.1); color: var(--not-run); }}

        .stat-icon svg {{
            width: 24px;
            height: 24px;
            stroke-width: 2.5;
        }}

        .stat-card:hover .stat-icon {{
            transform: scale(1.1) rotate(5deg);
        }}
        
        /* Active Filter Effect */
        .stat-card.active-filter {{
            transform: translateY(-4px) scale(1.02);
            border-color: currentColor !important;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1) !important;
        }}

        .stat-card.total.active-filter {{ box-shadow: 0 12px 24px rgba(249, 115, 22, 0.25) !important; }}
        .stat-card.passed.active-filter {{ box-shadow: 0 12px 24px rgba(34, 197, 94, 0.25) !important; }}
        .stat-card.failed.active-filter {{ box-shadow: 0 12px 24px rgba(239, 68, 68, 0.25) !important; }}
        .stat-card.skipped.active-filter {{ box-shadow: 0 12px 24px rgba(245, 158, 11, 0.25) !important; }}
        .stat-card.not-run-stat.active-filter {{ box-shadow: 0 12px 24px rgba(148, 163, 184, 0.25) !important; }}
        
        /* Tabs */
        .tabs {{
            display: flex;
            gap: 12px;
            padding: 0;
            margin-bottom: 20px;
            justify-content: flex-start; /* Left align tabs */
            flex-wrap: wrap;
        }}
        
        .tab {{
            padding: 10px 20px;
            border: 2px solid rgba(249, 115, 22, 0.3);
            background: rgba(255, 255, 255, 0.7);
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            color: var(--primary-dark);
            border-radius: 14px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
            position: relative;
            overflow: hidden;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            letter-spacing: 0.01em;
        }}
        
        .tab::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            transition: left 0.5s;
        }}
        
        .tab:hover::before {{
            left: 100%;
        }}
        
        .tab:hover {{
            background: rgba(255, 255, 255, 0.95);
            color: var(--primary);
            transform: translateY(-3px) scale(1.02);
            border-color: var(--primary);
            box-shadow: 0 8px 20px rgba(249, 115, 22, 0.3);
        }}
        
        .tab.active {{
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
            color: white;
            border-color: var(--primary);
            box-shadow: 0 12px 30px -4px rgba(249, 115, 22, 0.5);
            font-weight: 700;
            transform: translateY(-2px);
        }}
        
        .tab.active:hover {{
            background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 15px 35px -4px rgba(249, 115, 22, 0.6);
        }}
        
        /* Test List Container */
        .test-section {{
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(35px);
            border-radius: 28px;
            padding: 35px;
            box-shadow: 0 30px 60px -15px rgba(0,0,0,0.05);
            border: 1px solid var(--glass-border);
            min-height: 600px;
            display: flex;
            flex-direction: column;
        }}
        
        .test-section-content {{
            display: flex;
            gap: 20px;
            flex: 1;
            min-height: 0;
        }}
        
        .test-list-container {{
            flex: 0 0 50%;
            overflow-y: auto;
            overflow-x: hidden;
            padding-right: 10px;
            max-height: calc(100vh - 400px);
            min-height: 500px;
        }}
        
        .test-list-container::-webkit-scrollbar {{
            width: 8px;
        }}
        
        .test-list-container::-webkit-scrollbar-track {{
            background: rgba(0, 0, 0, 0.05);
            border-radius: 10px;
        }}
        
        .test-list-container::-webkit-scrollbar-thumb {{
            background: rgba(249, 115, 22, 0.3);
            border-radius: 10px;
        }}
        
        .test-list-container::-webkit-scrollbar-thumb:hover {{
            background: rgba(249, 115, 22, 0.5);
        }}
        
        .test-details-panel {{
            flex: 0 0 50%;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(35px);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.1);
            overflow-y: auto;
            overflow-x: hidden;
            border: 1px solid rgba(249, 115, 22, 0.1);
            position: sticky;
            top: 20px;
            align-self: flex-start;
            max-height: calc(100vh - 400px);
            display: flex;
            flex-direction: column;
        }}
        
        .test-details-panel.empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            font-size: 1.1em;
            text-align: center;
            opacity: 0.6;
        }}
        
        /* Ensure panel is visible when content is added */
        .test-details-panel:not(.empty) {{
            display: flex !important;
            opacity: 1 !important;
        }}
        
        .test-details-header {{
            border-bottom: 2px solid rgba(249, 115, 22, 0.2);
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .test-details-title {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 1.15em;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 10px;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            line-height: 1.4;
            letter-spacing: 0.01em;
        }}
        
        .test-details-status {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 10px;
        }}
        
        .test-details-info {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
            flex-shrink: 0;
        }}
        
        .test-details-content {{
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
            padding-right: 5px;
            min-height: 0;
        }}
        
        .test-details-content::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .test-details-content::-webkit-scrollbar-track {{
            background: rgba(0, 0, 0, 0.05);
            border-radius: 10px;
        }}
        
        .test-details-content::-webkit-scrollbar-thumb {{
            background: rgba(249, 115, 22, 0.3);
            border-radius: 10px;
        }}
        
        .test-details-content::-webkit-scrollbar-thumb:hover {{
            background: rgba(249, 115, 22, 0.5);
        }}
        
        .test-details-info-item {{
            background: rgba(249, 115, 22, 0.05);
            padding: 12px;
            border-radius: 12px;
            border-left: 3px solid var(--primary);
        }}
        
        .test-details-info-label {{
            font-size: 0.75em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
            font-weight: 600;
        }}
        
        .test-details-info-value {{
            font-size: 1em;
            color: var(--text-primary);
            font-weight: 600;
        }}
        
        .test-details-screenshot {{
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        
        .test-details-screenshot img {{
            width: 100%;
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.2);
            border: 2px solid rgba(249, 115, 22, 0.2);
            cursor: pointer;
            transition: transform 0.3s ease;
        }}
        
        .test-details-screenshot img:hover {{
            transform: scale(1.02);
        }}
        
        .test-details-failure {{
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid var(--danger);
            padding: 15px;
            border-radius: 12px;
            margin-top: 20px;
        }}
        
        .test-details-failure-title {{
            font-weight: 700;
            color: var(--danger);
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .test-details-failure-content {{
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        
        .test-details-location {{
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3B82F6;
            padding: 15px;
            border-radius: 12px;
            margin-top: 15px;
        }}
        
        .test-details-location-title {{
            font-weight: 700;
            color: #3B82F6;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .test-details-location-content {{
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            word-break: break-all;
        }}
        
        .test-item.active {{
            border-left-width: 6px;
            background: linear-gradient(to right, rgba(249, 115, 22, 0.1), #FFFFFF);
            box-shadow: 0 8px 25px -10px rgba(249, 115, 22, 0.3);
        }}
        
        .test-item {{
            cursor: pointer;
        }}

        .test-section h2 {{
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 2.1em;
            color: var(--dark);
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid rgba(249, 115, 22, 0.1);
            display: flex;
            align-items: center;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            letter-spacing: -0.01em;
            line-height: 1.2;
            font-weight: 700;
            gap: 12px;
        }}
        
        /* Individual Test Items */
        .test-list {{
            display: flex;
            flex-direction: column;
            gap: 12px; /* Reduced gap between testcases for better visual density */
        }}
        
        .test-item {{
            background: white;
            border-radius: 12px;
            padding: 15px 20px;
            border: 1px solid rgba(226, 232, 240, 0.8);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-left: 5px solid transparent;
            display: grid !important;
            grid-template-columns: 1fr 140px !important;
            grid-template-rows: auto auto !important;
            gap: 10px 20px !important;
            align-items: center;
            position: relative;
            overflow: hidden;
        }}
        
        .test-item:hover {{
            transform: translateX(5px) scale(1.01);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
            border-color: rgba(249, 115, 22, 0.2);
            z-index: 2;
        }}
        
        .test-item.active:hover {{
            transform: translateX(5px) scale(1.005);
        }}
        
        /* Color Coding */
        .test-item.pass {{ border-left-color: var(--success); }}
        .test-item.fail {{ border-left-color: var(--danger); background: linear-gradient(to right, #FFF8F8, #FFFFFF); }}
        .test-item.skip {{ border-left-color: var(--warning); }}
        .test-item.not-run {{ border-left-color: var(--not-run); opacity: 0.8; }}

        .test-badge.pass {{ background: var(--success-bg); color: var(--success); }}
        .test-badge.fail {{ background: var(--danger-bg); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.1); }}
        .test-badge.skip {{ background: var(--warning-bg); color: var(--warning); }}
        .test-badge.not-run {{ background: var(--not-run-bg); color: var(--text-secondary); }}

        /* Status-specific Button Colors */
        .test-item.fail .run-test-btn {{
            background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
        }}
        .test-item.fail .run-test-btn:hover {{
            background: linear-gradient(135deg, #F87171 0%, #EF4444 100%);
            box-shadow: 0 6px 15px rgba(239, 68, 68, 0.3);
        }}

        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .test-name {{
            grid-column: 1 / 2 !important;
            grid-row: 1 !important;
            font-family: 'Poppins', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            color: #1E293B;
            line-height: 1.4;
            margin: 0;
            display: block !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .test-badge {{
            grid-column: 2 / 3 !important;
            grid-row: 1 !important;
            padding: 5px 12px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            white-space: nowrap;
            display: flex !important;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 28px;
        }}
        
        .test-source {{
            grid-column: 1 / 2 !important;
            grid-row: 2 !important;
            font-size: 0.78rem;
            color: #64748B;
            font-weight: 500;
            opacity: 0.8;
            margin: 0;
        }}
        
        .test-actions {{
            grid-column: 2 / 3 !important;
            grid-row: 2 !important;
            display: flex !important;
            justify-content: center;
            align-items: center;
            width: 100%;
        }}
        
        .run-test-btn {{
            padding: 6px 14px;
            background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(22, 163, 74, 0.3);
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }}
        
        .run-test-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(22, 163, 74, 0.4);
            background: linear-gradient(135deg, #22C55E 0%, #16A34A 100%);
        }}
        
        .run-test-btn:active {{
            transform: translateY(0);
        }}
        
        .run-test-btn.running {{
            background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
            cursor: not-allowed;
            opacity: 0.8;
        }}
        
        .run-test-btn.running:hover {{
            transform: none;
        }}
        
        /* Notification Banner */
        .notification-banner {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            z-index: 10000;
            display: none;
            align-items: center;
            gap: 12px;
            min-width: 300px;
            max-width: 500px;
            animation: slideInRight 0.3s ease-out;
            border-left: 4px solid;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .notification-banner.show {{
            display: flex;
        }}
        
        .notification-banner.success {{
            border-left-color: #16A34A;
            background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
        }}
        
        .notification-banner.info {{
            border-left-color: #3B82F6;
            background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
        }}
        
        .notification-banner.warning {{
            border-left-color: #F59E0B;
            background: linear-gradient(135deg, #FFFBEB 0%, #FFFFFF 100%);
        }}
        
        .notification-banner.error {{
            border-left-color: #EF4444;
            background: linear-gradient(135deg, #FEF2F2 0%, #FFFFFF 100%);
        }}
        
        .notification-icon {{
            font-size: 24px;
            flex-shrink: 0;
        }}
        
        .notification-content {{
            flex: 1;
        }}
        
        .notification-title {{
            font-weight: 600;
            font-size: 0.95em;
            color: #1F2937;
            margin-bottom: 4px;
        }}
        
        .notification-message {{
            font-size: 0.85em;
            color: #6B7280;
            line-height: 1.4;
        }}
        
        .notification-close {{
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: #9CA3AF;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        
        .notification-close:hover {{
            background: rgba(0,0,0,0.05);
            color: #374151;
        }}
        
        @keyframes slideInRight {{
            from {{
                transform: translateX(100%);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        /* Screenshots Section */
        .screenshots {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(0,0,0,0.06);
        }}
        
        .screenshots h4 {{
            margin-bottom: 8px;
            color: var(--primary-dark);
            font-size: 0.95em;
        }}
        
        .screenshot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); /* Larger thumbnails */
            gap: 15px;
            margin-top: 10px;
        }}
        
        .screenshot-item img {{
            width: 100%;
            border-radius: 14px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
            transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            border: 3px solid white;
        }}
        
        .screenshot-item img:hover {{
            transform: scale(1.05) rotate(1deg);
            box-shadow: 0 15px 35px rgba(249, 115, 22, 0.2);
            z-index: 10;
        }}

        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 12px;
        }}
        ::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.5);
            border-radius: 10px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(to bottom, #F97316, #EA580C);
            border-radius: 10px;
            border: 3px solid transparent;
            background-clip: content-box;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #C2410C;
            border: 3px solid transparent;
            background-clip: content-box;
        }}

        /* Buttons */
        .back-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 18px;
            background: rgba(255, 255, 255, 0.9);
            color: var(--accent);
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            font-size: 0.9em;
            border: 1px solid white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }}
        
        .back-btn:hover {{
            transform: translateY(-3px);
            background: white;
            color: var(--primary);
            box-shadow: 0 10px 25px rgba(249, 115, 22, 0.2);
        }}

        .refresh-btn-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 2px;
            flex-shrink: 0;
            min-width: 100px;
            max-width: 130px;
            justify-content: center;
        }}
        
        .auto-refresh-indicator {{
            font-size: 0.6em;
            color: var(--text-secondary);
            white-space: nowrap;
            text-align: right;
            line-height: 1.2;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            letter-spacing: 0.01em;
        }}
        
        .refresh-btn {{
            display: inline-block;
            padding: 5px 14px;
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 700;
            transition: all 0.3s ease;
            cursor: pointer;
            font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            border: none;
            box-shadow: 0 8px 20px -5px rgba(249, 115, 22, 0.5);
            letter-spacing: 0.8px;
            text-transform: uppercase;
            font-size: 0.75em;
            white-space: nowrap;
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        .refresh-btn:hover {{
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 15px 30px -5px rgba(249, 115, 22, 0.6);
            filter: brightness(1.1);
        }}

        /* Log Links Section */
        .log-links {{
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(35px);
            border-radius: 28px;
            padding: 30px;
            box-shadow: 0 20px 50px -15px rgba(0,0,0,0.05);
            border: 1px solid var(--glass-border);
            margin-top: 30px;
        }}
        
        .log-links h3 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.5em;
            color: var(--dark);
            margin-bottom: 20px;
            font-weight: 700;
        }}
        
        .log-link {{
            display: inline-block;
            padding: 12px 24px;
            margin: 8px;
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.1) 0%, rgba(234, 88, 12, 0.1) 100%);
            color: var(--primary-dark);
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            border: 2px solid rgba(249, 115, 22, 0.2);
            transition: all 0.3s ease;
            font-size: 1em;
        }}
        
        /* Hide employer and jobseeker log links by default (shown via JS for those dashboards) */
        .log-link[href*="module=employer"],
        .log-link[href*="module=jobseeker"] {{
            display: none;
        }}
        
        .log-link:hover {{
            background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
            color: white;
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(249, 115, 22, 0.3);
        }}

        /* Responsive Improvements */
        @media (max-width: 1200px) {{
            .container {{ width: 95%; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 15px; gap: 20px; }}
            .header {{ padding: 25px; text-align: center; }}
            .header-top {{ flex-direction: column; gap: 20px; }}
            .header h1 {{ font-size: 2.2em; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
            .test-item {{ padding: 20px; }}
            .test-header {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
            .test-badge {{ align-self: flex-start; }}
            .test-section {{ padding: 20px; }}
            .test-name {{ font-size: 1.1em; }}
        }}
        /* Modal Styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: rgba(15, 23, 42, 0.85); /* Darker, sleek slate tone */
            backdrop-filter: blur(8px);
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .modal-content {{
            max-width: 80%; /* Not too big as requested */
            max-height: 85vh;
            border-radius: 16px;
            box-shadow: 
                0 0 0 1px rgba(255, 255, 255, 0.1),
                0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: zoomIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            object-fit: contain;
        }}

        .close-modal {{
            position: absolute;
            top: 25px;
            right: 25px;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 2001;
            color: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}

        .close-modal:hover {{
            background: rgba(249, 115, 22, 0.9);
            transform: rotate(90deg) scale(1.1);
            border-color: transparent;
            box-shadow: 0 8px 20px rgba(249, 115, 22, 0.4);
        }}
        
        .close-modal svg {{
            width: 24px;
            height: 24px;
            stroke-width: 2.5;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        @keyframes zoomIn {{
            from {{ transform: scale(0.95); opacity: 0; }}
            to {{ transform: scale(1); opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="background-bubbles">
        <div class="bubble"></div>
        <div class="bubble"></div>
        <div class="bubble"></div>
        <div class="bubble"></div>
    </div>
    <!-- Notification Banner -->
    <div id="notificationBanner" class="notification-banner">
        <div class="notification-icon" id="notificationIcon">ℹ️</div>
        <div class="notification-content">
            <div class="notification-title" id="notificationTitle">Notification</div>
            <div class="notification-message" id="notificationMessage"></div>
        </div>
        <button class="notification-close" onclick="hideNotification()">×</button>
    </div>
    
    <div class="container">
        <div class="header">
            <div class="header-top">
                <div class="header-content">
                    <a href="../dashboard_home.html" class="header-home-btn" title="Back to Home Dashboard">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                    </a>
                    <div class="dashboard-logo" id="dashboard-logo">
                        <!-- BenchSale Logo (default) -->
                        <svg class="benchsale-logo-svg" id="benchsale-logo" xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#F97316" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4.5 16.5c-1-1.5-1-4 0-5.5m5.5 0c1.5-1 4-1 5.5 0m0 0c1 1.5 1 4 0 5.5m-5.5 0c-1.5 1-4 1-5.5 0" stroke="#F97316" fill="rgba(249, 115, 22, 0.1)"/>
                            <path d="M12 2L8 6h8l-4-4z" fill="#F97316" opacity="0.9">
                                <animate attributeName="opacity" values="0.9;1;0.9" dur="1.5s" repeatCount="indefinite"/>
                            </path>
                            <circle cx="12" cy="12" r="2" fill="#F97316">
                                <animate attributeName="r" values="2;3;2" dur="2s" repeatCount="indefinite"/>
                                <animate attributeName="opacity" values="1;0.7;1" dur="2s" repeatCount="indefinite"/>
                            </circle>
                            <path d="M12 6v6m0 0v6" stroke="#F59E0B" stroke-width="1.5">
                                <animate attributeName="stroke-dasharray" values="0,6;3,3;0,6" dur="2s" repeatCount="indefinite"/>
                            </path>
                            <circle cx="8" cy="8" r="1" fill="#F97316" opacity="0.6">
                                <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite"/>
                                <animateTransform attributeName="transform" type="translate" values="0,0; -2,-2; 0,0" dur="2s" repeatCount="indefinite"/>
                            </circle>
                            <circle cx="16" cy="8" r="1" fill="#F59E0B" opacity="0.6">
                                <animate attributeName="opacity" values="0.6;1;0.6" dur="1.8s" repeatCount="indefinite"/>
                                <animateTransform attributeName="transform" type="translate" values="0,0; 2,-2; 0,0" dur="2.2s" repeatCount="indefinite"/>
                            </circle>
                        </svg>
                        <!-- Employer Logo (hidden by default) -->
                        <svg class="employer-logo-svg" id="employer-logo" style="display: none;" xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="7" width="18" height="14" rx="2" ry="2" fill="rgba(217, 119, 6, 0.1)" stroke="#D97706">
                                <animate attributeName="stroke-width" values="2.5;3;2.5" dur="2s" repeatCount="indefinite"/>
                            </rect>
                            <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" stroke="#D97706" fill="rgba(217, 119, 6, 0.2)">
                                <animate attributeName="opacity" values="1;0.8;1" dur="1.5s" repeatCount="indefinite"/>
                            </path>
                            <line x1="12" y1="11" x2="12" y2="17" stroke="#F59E0B" stroke-width="2">
                                <animate attributeName="stroke-dasharray" values="0,6;3,3;0,6" dur="2s" repeatCount="indefinite"/>
                            </line>
                            <circle cx="12" cy="14" r="1.5" fill="#D97706">
                                <animate attributeName="r" values="1.5;2;1.5" dur="2s" repeatCount="indefinite"/>
                            </circle>
                            <line x1="6" y1="10" x2="18" y2="10" stroke="#F59E0B" stroke-width="1" opacity="0.6">
                                <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite"/>
                                <animate attributeName="stroke-width" values="1;1.5;1" dur="2s" repeatCount="indefinite"/>
                            </line>
                            <path d="M3 7 L12 7 L12 9 L3 9 Z" fill="rgba(255, 255, 255, 0.3)">
                                <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2.5s" repeatCount="indefinite"/>
                            </path>
                        </svg>
                        <!-- Job Seeker Logo (hidden by default) -->
                        <svg class="jobseeker-logo-svg" id="jobseeker-logo" style="display: none;" xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <!-- Animated User/Job Seeker Logo -->
                            <circle cx="12" cy="8" r="5" fill="rgba(22, 163, 74, 0.1)" stroke="#16A34A">
                                <animate attributeName="stroke-width" values="2.5;3;2.5" dur="2s" repeatCount="indefinite"/>
                                <animate attributeName="r" values="5;5.5;5" dur="2s" repeatCount="indefinite"/>
                            </circle>
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="#16A34A" fill="rgba(22, 163, 74, 0.1)">
                                <animate attributeName="opacity" values="1;0.8;1" dur="1.5s" repeatCount="indefinite"/>
                            </path>
                            <!-- Glowing particles -->
                            <circle cx="8" cy="6" r="1.5" fill="#16A34A" opacity="0.6">
                                <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite"/>
                                <animateTransform attributeName="transform" type="translate" values="0,0; -2,-2; 0,0" dur="2s" repeatCount="indefinite"/>
                            </circle>
                            <circle cx="16" cy="6" r="1.5" fill="#22C55E" opacity="0.6">
                                <animate attributeName="opacity" values="0.6;1;0.6" dur="1.8s" repeatCount="indefinite"/>
                                <animateTransform attributeName="transform" type="translate" values="0,0; 2,-2; 0,0" dur="2.2s" repeatCount="indefinite"/>
                            </circle>
                            <!-- Shine effect on user -->
                            <path d="M12 3 L12 8 L9 6 Z" fill="rgba(255, 255, 255, 0.3)">
                                <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2.5s" repeatCount="indefinite"/>
                            </path>
                        </svg>
                    </div>
                    <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <h1 id="dashboard-title">Unified Test Report</h1>
                            <div id="server-status-indicator" style="font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.5); padding: 4px 10px; border-radius: 20px;">
                                <span id="server-status-text" style="color: #64748B;">Checking Server...</span>
                                <button id="start-server-btn" onclick="startServer()" style="display: none; background: linear-gradient(135deg, #F97316 0%, #EA580C 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3); transition: all 0.3s ease;">▶ Start Server</button>
                            </div>
                        </div>
                        <div class="subtitle">Auto-generated • Live Status • Last Run: <span id="last-run-time-main">{last_updated_str}</span></div>
                    </div>
                </div>
                <div class="refresh-btn-wrapper">
                    <button class="refresh-btn" onclick="refreshDashboard()">Refresh</button>
                    <span class="auto-refresh-indicator" id="refreshStatus">Auto-updates after each test run</span>
                </div>
            </div>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <!-- Dynamic stats (shown for BenchSale - updates based on active tab) -->
            <div class="stat-card total benchsale-stat" id="stat-total-card" onclick="filterByStatus('all')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Total Tests</div>
                   <div class="number" id="stat-total">0</div>
                </div>
            </div>
            <div class="stat-card passed benchsale-stat" id="stat-passed-card" onclick="filterByStatus('pass')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Passed</div>
                   <div class="number" id="stat-passed">0</div>
                </div>
            </div>
            <div class="stat-card failed benchsale-stat" id="stat-failed-card" onclick="filterByStatus('fail')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Failed</div>
                   <div class="number" id="stat-failed">0</div>
                </div>
            </div>
            <div class="stat-card skipped benchsale-stat" id="stat-skipped-card" onclick="filterByStatus('skip')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Skipped</div>
                   <div class="number" id="stat-skipped">0</div>
                </div>
            </div>
            <div class="stat-card total benchsale-stat not-run-stat" id="stat-not-run-card" onclick="filterByStatus('not-run')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Not Run</div>
                   <div class="number" id="stat-not-run">0</div>
                </div>
            </div>
            <!-- Employer stats (shown when filter=employer) -->
            <div class="stat-card total employer-stat" id="stat-employer-total" style="display: none;" onclick="filterByStatus('all')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Total Tests</div>
                   <div class="number" id="stat-employer-total-num">{employer_total}</div>
                </div>
            </div>
            <div class="stat-card passed employer-stat" id="stat-employer-passed" style="display: none;" onclick="filterByStatus('pass')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Passed</div>
                   <div class="number" id="stat-employer-passed-num">{employer_passed}</div>
                </div>
            </div>
            <div class="stat-card failed employer-stat" id="stat-employer-failed" style="display: none;" onclick="filterByStatus('fail')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Failed</div>
                   <div class="number" id="stat-employer-failed-num">{employer_failed}</div>
                </div>
            </div>
            <div class="stat-card skipped employer-stat" id="stat-employer-skipped" style="display: none;" onclick="filterByStatus('skip')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Skipped</div>
                   <div class="number" id="stat-employer-skipped-num">{employer_skipped}</div>
                </div>
            </div>
            <div class="stat-card total employer-stat not-run-stat" id="stat-employer-not-run" style="display: none;" onclick="filterByStatus('not-run')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Not Run</div>
                   <div class="number" id="stat-employer-not-run-num">{employer_not_run}</div>
                </div>
            </div>
            <!-- Job Seeker stats (shown when filter=jobseeker) -->
            <div class="stat-card total jobseeker-stat" id="stat-jobseeker-total" style="display: none;" onclick="filterByStatus('all')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Total Tests</div>
                   <div class="number" id="stat-jobseeker-total-num">{jobseeker_total}</div>
                </div>
            </div>
            <div class="stat-card passed jobseeker-stat" id="stat-jobseeker-passed" style="display: none;" onclick="filterByStatus('pass')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Passed</div>
                   <div class="number" id="stat-jobseeker-passed-num">{jobseeker_passed}</div>
                </div>
            </div>
            <div class="stat-card failed jobseeker-stat" id="stat-jobseeker-failed" style="display: none;" onclick="filterByStatus('fail')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Failed</div>
                   <div class="number" id="stat-jobseeker-failed-num">{jobseeker_failed}</div>
                </div>
            </div>
            <div class="stat-card skipped jobseeker-stat" id="stat-jobseeker-skipped" style="display: none;" onclick="filterByStatus('skip')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Skipped</div>
                   <div class="number" id="stat-jobseeker-skipped-num">{jobseeker_skipped}</div>
                </div>
            </div>
            <div class="stat-card total jobseeker-stat not-run-stat" id="stat-jobseeker-not-run" style="display: none;" onclick="filterByStatus('not-run')">
                <div class="stat-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div class="stat-info">
                   <div class="label">Not Run</div>
                   <div class="number" id="stat-jobseeker-not-run-num">{jobseeker_not_run}</div>
                </div>
            </div>
        </div>
        
        <div class="tabs" id="tabs-container">
            <!-- BenchSale tabs (shown when filter=all or no filter) -->
            <button class="tab benchsale-tab active" id="tab-all" onclick="showSection('all')">All Tests</button>
            <button class="tab benchsale-tab" id="tab-admin" onclick="showSection('admin')">Admin Tests ({len(admin_tests)})</button>
            <button class="tab benchsale-tab" id="tab-recruiter" onclick="showSection('recruiter')">Recruiter Tests ({len(recruiter_tests)})</button>
            <!-- Employer tab (shown when filter=employer) -->
            <button class="tab employer-tab" id="tab-employer" onclick="showSection('employer')" style="display: none;">Employer Tests ({len(employer_tests)})</button>
            <!-- Job Seeker tab (shown when filter=jobseeker) -->
            <button class="tab jobseeker-tab" id="tab-jobseeker" onclick="showSection('jobseeker')" style="display: none;">Job Seeker Tests ({len(jobseeker_tests)})</button>
        </div>
        
        <div id="all-tests" class="test-section active">
            <h2>
                All Test Results (BenchSale Only - Admin + Recruiter)
                <span class="test-source" style="margin-left: 15px; background: rgba(249, 115, 22, 0.1); color: var(--primary);">Last Run: <span id="last-run-time-benchsale">{benchsale_ts_str}</span></span>
            </h2>
            <div class="test-section-content">
                <div class="test-list-container">
                    {generate_test_list_html(benchsale_tests)}
                </div>
                <div class="test-details-panel empty">
                    <div>Click on a test case to view details</div>
                </div>
            </div>
        </div>
        
        <div id="admin-tests" class="test-section">
            <h2>Admin Test Results</h2>
            <div class="test-section-content">
                <div class="test-list-container">
                    {generate_test_list_html(admin_tests)}
                </div>
                <div class="test-details-panel empty">
                    <div>Click on a test case to view details</div>
                </div>
            </div>
        </div>
        
        <div id="recruiter-tests" class="test-section">
            <h2>Recruiter Test Results</h2>
            <div class="test-section-content">
                <div class="test-list-container">
                    {generate_test_list_html(recruiter_tests)}
                </div>
                <div class="test-details-panel empty">
                    <div>Click on a test case to view details</div>
                </div>
            </div>
        </div>
        
        <div id="employer-tests" class="test-section">
            <h2>
                Employer Test Results
                <span class="test-source" style="margin-left: 15px; background: rgba(217, 119, 6, 0.1); color: #D97706;">Last Run: <span id="last-run-time-employer">{employer_ts_str}</span></span>
            </h2>
            <div class="test-section-content">
                <div class="test-list-container">
                    {generate_test_list_html(employer_tests)}
                </div>
                <div class="test-details-panel empty">
                    <div>Click on a test case to view details</div>
                </div>
            </div>
        </div>
        
        <div id="jobseeker-tests" class="test-section">
            <h2>
                Job Seeker Test Results
                <span class="test-source" style="margin-left: 15px; background: rgba(22, 163, 74, 0.1); color: #16A34A;">Last Run: <span id="last-run-time-jobseeker">{jobseeker_ts_str}</span></span>
            </h2>
            <div class="test-section-content">
                <div class="test-list-container">
                    {generate_test_list_html(jobseeker_tests)}
                </div>
                <div class="test-details-panel empty">
                    <div>Click on a test case to view details</div>
                </div>
            </div>
        </div>
        
        <div class="log-links" id="log-links-section">
            <h3>📋 Detailed Log Files</h3>
            <div id="log-links-content">
                {generate_log_links_html(admin_log, recruiter_log, employer_log, jobseeker_log, main_log)}
            </div>
        </div>
    </div>
    
    <!-- Image Modal -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <div class="close-modal" onclick="closeModal()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </div>
        <img class="modal-content" id="modalImage" onclick="event.stopPropagation()">
    </div>

    <script>
        // Server Status Management
        function checkServerStatus() {{
            const statusIndicator = document.getElementById('server-status-indicator');
            const statusText = document.getElementById('server-status-text');
            const startBtn = document.getElementById('start-server-btn');
            
            if (!statusIndicator) return;

            // Check main server directly on port 8766 (more reliable)
            fetch('http://127.0.0.1:8766/status?t=' + Date.now(), {{
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache',
                headers: {{
                    'Accept': 'application/json'
                }}
            }})
            .then(r => {{
                if (!r.ok) {{
                    throw new Error('Server returned ' + r.status);
                }}
                return r.json();
            }})
            .then(d => {{
                // Server is responding - any response means server is running
                statusText.textContent = 'Server: Running';
                statusText.style.color = '#10B981'; // Green
                if (startBtn) {{
                    startBtn.style.display = 'none';
                    startBtn.disabled = false;
                }}
                console.log('Server status: Running (busy=' + (d.busy || false) + ', queue=' + (d.queue_size || 0) + ')');
            }})
            .catch((error) => {{
                console.log('Server check failed on port 8766:', error.message);
                // Server not responding, try helper server (port 8767) as fallback
                fetch('http://127.0.0.1:8767/status?t=' + Date.now(), {{
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache'
                }})
                .then(response => {{
                    if (!response.ok) throw new Error('Helper server returned ' + response.status);
                    return response.json();
                }})
                .then(data => {{
                    if (data.running) {{
                        statusText.textContent = 'Server: Running';
                        statusText.style.color = '#10B981';
                        if (startBtn) {{
                            startBtn.style.display = 'none';
                            startBtn.disabled = false;
                        }}
                    }} else {{
                        statusText.textContent = 'Server: Stopped';
                        statusText.style.color = '#EF4444'; // Red
                        if (startBtn) {{
                            startBtn.style.display = 'inline-block';
                            startBtn.disabled = false;
                        }}
                    }}
                }})
                .catch((fallbackError) => {{
                    console.log('Both servers not responding:', fallbackError.message);
                    // Both servers not responding
                    statusText.textContent = 'Server: Stopped';
                    statusText.style.color = '#EF4444'; // Red
                    if (startBtn) {{
                        startBtn.style.display = 'inline-block';
                        startBtn.disabled = false;
                    }}
                }});
            }});
        }}

        function startServer() {{
            const startBtn = document.getElementById('start-server-btn');
            if (startBtn) {{
                startBtn.textContent = 'Starting...';
                startBtn.disabled = true;
            }}
            
            // First try helper server (port 8767) if available
            fetch('http://127.0.0.1:8767/start', {{ method: 'POST', timeout: 3000 }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    showNotification('success', 'Server Started', 'Test server is starting... Please wait 5 seconds.', 5000);
                    setTimeout(checkServerStatus, 5000);
                }} else {{
                    showNotification('info', 'Starting Server', 'Server start command sent.', 3000);
                    setTimeout(checkServerStatus, 5000);
                }}
            }})
            .catch(() => {{
                // Helper server not available, show instructions
                const message = `Server cannot be started automatically.\\n\\n` +
                    `Please do ONE of the following:\\n\\n` +
                    `1. Double-click: START_ALWAYS_ON_SERVER.bat\\n` +
                    `2. Or run in terminal: python utils\\\\always_on_server.py\\n\\n` +
                    `The server will run on port 8766.\\n` +
                    `Keep the window open while using the dashboard.`;
                
                showNotification('warning', 'Start Server Manually', message, 10000);
                
                // Copy command to clipboard if possible
                const command = 'python utils\\always_on_server.py';
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(command).then(() => {{
                        console.log('Command copied to clipboard: ' + command);
                    }}).catch(() => {{}});
                }}
                
                if (startBtn) {{
                    startBtn.textContent = 'Start Server';
                    startBtn.disabled = false;
                }}
            }});
        }}

        // Check if page is loaded via file:// protocol (CORS issue)
        // Only show warning once per session to avoid annoying user
        if (window.location.protocol === 'file:') {{
            const httpUrl = 'http://127.0.0.1:8888/logs/index.html' + window.location.search;
            console.warn('⚠️ Dashboard loaded via file:// protocol - CORS will block server status checks!');
            console.warn('💡 For full functionality, use: ' + httpUrl);
            
            // Only show notification once per browser session (check sessionStorage)
            const warningShown = sessionStorage.getItem('fileProtocolWarningShown');
            if (!warningShown) {{
                sessionStorage.setItem('fileProtocolWarningShown', 'true');
                // Show notification about file:// protocol issue (shorter, less intrusive)
                setTimeout(() => {{
                    const message = `Dashboard loaded via file:// protocol.\\n\\n` +
                        `For full functionality, use:\\n` +
                        `http://127.0.0.1:8888/logs/index.html\\n\\n` +
                        `Or run: OPEN_DASHBOARD.bat`;
                    showNotification('warning', 'File Protocol Detected', message, 8000);
                }}, 3000); // Show after 3 seconds, not immediately
            }}
        }}
        
        // Check status on load and every 5 seconds
        document.addEventListener('DOMContentLoaded', function() {{
            // Check server status immediately on page load
            checkServerStatus();
            // Also check after a short delay to ensure everything is ready
            setTimeout(checkServerStatus, 1000);
            // Check server status every 5 seconds (more frequent for better UX)
            setInterval(checkServerStatus, 5000);
        }});
        
        // Global filter state
        let currentStatusFilter = 'all';

        function filterByStatus(status) {{
            currentStatusFilter = status;
            
            // 1. Update Visuals on Cards
            // Remove active class from all
            document.querySelectorAll('.stat-card').forEach(card => {{
                card.classList.remove('active-filter');
            }});
            
            // Add active class to clicked card(s) matching the status
            let selector = '';
            if (status === 'all') selector = '.stat-card.total:not(.not-run-stat)';
            else if (status === 'pass') selector = '.stat-card.passed';
            else if (status === 'fail') selector = '.stat-card.failed';
            else if (status === 'skip') selector = '.stat-card.skipped';
            else if (status === 'not-run') selector = '.stat-card.not-run-stat';
            
            // Only highlight visible cards
            document.querySelectorAll(selector).forEach(card => {{
                if (window.getComputedStyle(card).display !== 'none') {{
                    card.classList.add('active-filter');
                }}
            }});

            // 2. Filter Test Items in current active section
            const activeSection = document.querySelector('.test-section.active');
            if (activeSection) {{
                const items = activeSection.querySelectorAll('.test-item');
                let visibleCount = 0;
                
                items.forEach(item => {{
                    let shouldShow = false;
                    
                    if (status === 'all') {{
                        shouldShow = true;
                    }} else if (status === 'pass' && item.classList.contains('pass')) {{
                        shouldShow = true;
                    }} else if (status === 'fail' && item.classList.contains('fail')) {{
                        shouldShow = true;
                    }} else if (status === 'skip' && item.classList.contains('skip')) {{
                        shouldShow = true;
                    }} else if (status === 'not-run' && (item.classList.contains('not-run') || item.classList.contains('not_run'))) {{
                        shouldShow = true;
                    }}
                    
                    item.style.display = shouldShow ? 'flex' : 'none';
                    if (shouldShow) visibleCount++;
                }});
                
                // Show/Hide "No tests" message
                let noTestsMsg = activeSection.querySelector('.no-tests-message');
                if (visibleCount === 0) {{
                    if (!noTestsMsg) {{
                        noTestsMsg = document.createElement('div');
                        noTestsMsg.className = 'no-tests-message';
                        noTestsMsg.style.textAlign = 'center';
                        noTestsMsg.style.padding = '40px';
                        noTestsMsg.style.color = 'var(--text-secondary)';
                        noTestsMsg.style.fontSize = '1.2em';
                        activeSection.appendChild(noTestsMsg);
                    }}
                    noTestsMsg.textContent = status === 'all' ? 'No tests found in this section.' : 'No ' + status + ' tests found.';
                    noTestsMsg.style.display = 'block';
                }} else {{
                    if (noTestsMsg) noTestsMsg.style.display = 'none';
                }}
            }}
        }}

        function updateStatistics(section) {{
            let visibleTests = [];
            if (section === 'all') {{
                const allSection = document.getElementById('all-tests');
                if (allSection) {{
                    // Search recursively for test items (they're inside .test-list-container)
                    visibleTests = Array.from(allSection.querySelectorAll('.test-item'));
                }}
            }} else {{
                const sectionId = section + '-tests';
                const sectionElement = document.getElementById(sectionId);
                if (sectionElement) {{
                    // Search recursively for test items
                    visibleTests = Array.from(sectionElement.querySelectorAll('.test-item'));
                }}
            }}
            
            let total = visibleTests.length;
            let passed = 0;
            let failed = 0;
            let skipped = 0;
            let notRun = 0;
            
            visibleTests.forEach(test => {{
                if (test.classList.contains('pass')) passed++;
                else if (test.classList.contains('fail')) failed++;
                else if (test.classList.contains('skip')) skipped++;
                else if (test.classList.contains('not-run') || test.classList.contains('not_run')) notRun++;
            }});
            
            const statsGrid = document.getElementById('stats-grid');
            if (section === 'employer') {{
                // Hide BenchSale tabs and stats, show only Employer
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                document.querySelectorAll('.benchsale-stat').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.employer-stat').forEach(el => el.style.display = 'flex');
                document.querySelectorAll('.jobseeker-stat').forEach(el => el.style.display = 'none');
                // Hide all BenchSale and Job Seeker test sections completely
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').style.display = 'none';
                // Show only Employer test section
                document.getElementById('employer-tests').style.display = 'block';
                // Update Employer statistics
                const employerSection = document.getElementById('employer-tests');
                if (employerSection) {{
                    const employerTests = Array.from(employerSection.querySelectorAll('.test-item'));
                    const employerTotal = employerTests.length;
                    const employerPassed = employerTests.filter(t => t.classList.contains('pass')).length;
                    const employerFailed = employerTests.filter(t => t.classList.contains('fail')).length;
                    const employerSkipped = employerTests.filter(t => t.classList.contains('skip')).length;
                    const employerNotRun = employerTests.filter(t => t.classList.contains('not-run') || t.classList.contains('not_run')).length;
                    document.getElementById('stat-employer-total-num').textContent = employerTotal;
                    document.getElementById('stat-employer-passed-num').textContent = employerPassed;
                    document.getElementById('stat-employer-failed-num').textContent = employerFailed;
                    document.getElementById('stat-employer-skipped-num').textContent = employerSkipped;
                    document.getElementById('stat-employer-not-run-num').textContent = employerNotRun;
                }}
                if (statsGrid) statsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))';
            }} else if (section === 'jobseeker') {{
                // Hide BenchSale tabs and stats, show only Job Seeker
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                document.querySelectorAll('.benchsale-stat').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.employer-stat').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.jobseeker-stat').forEach(el => el.style.display = 'flex');
                // Hide all BenchSale and Employer test sections completely
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('employer-tests').style.display = 'none';
                // Show only Job Seeker test section
                document.getElementById('jobseeker-tests').style.display = 'block';
                // Update Job Seeker statistics
                const jobseekerSection = document.getElementById('jobseeker-tests');
                if (jobseekerSection) {{
                    const jobseekerTests = Array.from(jobseekerSection.querySelectorAll('.test-item'));
                    const jobseekerTotal = jobseekerTests.length;
                    const jobseekerPassed = jobseekerTests.filter(t => t.classList.contains('pass')).length;
                    const jobseekerFailed = jobseekerTests.filter(t => t.classList.contains('fail')).length;
                    const jobseekerSkipped = jobseekerTests.filter(t => t.classList.contains('skip')).length;
                    const jobseekerNotRun = jobseekerTests.filter(t => t.classList.contains('not-run') || t.classList.contains('not_run')).length;
                    document.getElementById('stat-jobseeker-total-num').textContent = jobseekerTotal;
                    document.getElementById('stat-jobseeker-passed-num').textContent = jobseekerPassed;
                    document.getElementById('stat-jobseeker-failed-num').textContent = jobseekerFailed;
                    document.getElementById('stat-jobseeker-skipped-num').textContent = jobseekerSkipped;
                    document.getElementById('stat-jobseeker-not-run-num').textContent = jobseekerNotRun;
                }}
                if (statsGrid) statsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))';
            }} else {{
                // Show BenchSale tabs and stats, hide Employer and Job Seeker
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'block');
                document.getElementById('tab-employer').style.display = 'none';
                document.getElementById('tab-jobseeker').style.display = 'none';
                document.querySelectorAll('.benchsale-stat').forEach(el => el.style.display = 'flex');
                document.querySelectorAll('.employer-stat').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.jobseeker-stat').forEach(el => el.style.display = 'none');
                // Hide Employer and Job Seeker test sections completely
                document.getElementById('employer-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').style.display = 'none';
                
                // Update BenchSale stats based on active section
                // Use the already calculated values from the top of the function
                const statTotal = document.getElementById('stat-total');
                const statPassed = document.getElementById('stat-passed');
                const statFailed = document.getElementById('stat-failed');
                const statSkipped = document.getElementById('stat-skipped');
                const statNotRun = document.getElementById('stat-not-run');
                
                if (statTotal) statTotal.textContent = total;
                if (statPassed) statPassed.textContent = passed;
                if (statFailed) statFailed.textContent = failed;
                if (statSkipped) statSkipped.textContent = skipped;
                if (statNotRun) statNotRun.textContent = notRun;
                if (statsGrid) statsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))';
            }}
            
            const titleElement = document.getElementById('dashboard-title');
            const urlParams = new URLSearchParams(window.location.search);
            const filter = urlParams.get('filter');
            
            // Update logo and title based on section
            const benchsaleLogo = document.getElementById('benchsale-logo');
            const employerLogo = document.getElementById('employer-logo');
            const jobseekerLogo = document.getElementById('jobseeker-logo');
            const logoContainer = document.getElementById('dashboard-logo');
            
            if (filter === 'employer' || section === 'employer') {{
                titleElement.textContent = 'Employer Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'none';
                if (employerLogo) employerLogo.style.display = 'block';
                if (jobseekerLogo) jobseekerLogo.style.display = 'none';
                if (logoContainer) logoContainer.className = 'dashboard-logo employer-logo';
            }} else if (filter === 'jobseeker' || section === 'jobseeker') {{
                titleElement.textContent = 'Job Seeker Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'none';
                if (employerLogo) employerLogo.style.display = 'none';
                if (jobseekerLogo) jobseekerLogo.style.display = 'block';
                if (logoContainer) logoContainer.className = 'dashboard-logo jobseeker-logo';
            }} else {{
                titleElement.textContent = 'BenchSale Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'block';
                if (employerLogo) employerLogo.style.display = 'none';
                if (jobseekerLogo) jobseekerLogo.style.display = 'none';
                if (logoContainer) logoContainer.className = 'dashboard-logo';
            }}
        }}
        
        function showSection(section, clickedElement) {{
            // Reset filter when switching sections
            filterByStatus('all');
            
            // Hide/Show tabs and sections based on section
            if (section === 'employer') {{
                // Hide BenchSale tabs when showing Employer
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                document.getElementById('tab-employer').style.display = 'block';
                document.getElementById('tab-jobseeker').style.display = 'none';
                // Hide all BenchSale and Job Seeker test sections completely
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').style.display = 'none';
                // Show only Employer test section
                document.getElementById('employer-tests').style.display = 'block';
                // Show Employer log link, hide BenchSale and Job Seeker log links
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'inline-block';
                    logLinks.querySelectorAll('a[href*="benchsale"]').forEach(link => link.style.display = 'none');
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'none';
                }}
            }} else if (section === 'jobseeker') {{
                // Hide BenchSale tabs when showing Job Seeker
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                document.getElementById('tab-employer').style.display = 'none';
                document.getElementById('tab-jobseeker').style.display = 'block';
                // Hide all BenchSale and Employer test sections completely
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('employer-tests').style.display = 'none';
                // Show only Job Seeker test section
                document.getElementById('jobseeker-tests').style.display = 'block';
                // Show Job Seeker log link, hide BenchSale and Employer log links
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'inline-block';
                    logLinks.querySelectorAll('a[href*="benchsale"]').forEach(link => link.style.display = 'none');
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'none';
                }}
            }} else {{
                // Show BenchSale tabs, hide Employer and Job Seeker tabs
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'block');
                document.getElementById('tab-employer').style.display = 'none';
                document.getElementById('tab-jobseeker').style.display = 'none';
                // Hide Employer and Job Seeker test sections completely
                document.getElementById('employer-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').style.display = 'none';
                
                // Hide Employer and Job Seeker log links in BenchSale dashboard
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'none';
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'none';
                    
                    // Show/hide BenchSale log links based on selected section
                    const adminLogLink = logLinks.querySelector('a[href*="benchsale_admin"]');
                    const recruiterLogLink = logLinks.querySelector('a[href*="benchsale_recruiter"]');
                    const mainLogLink = logLinks.querySelector('a[href*="benchsale_test"]');
                    
                    if (section === 'all') {{
                        // Show all BenchSale log links
                        if (adminLogLink) adminLogLink.style.display = 'inline-block';
                        if (recruiterLogLink) recruiterLogLink.style.display = 'inline-block';
                        if (mainLogLink) mainLogLink.style.display = 'inline-block';
                    }} else if (section === 'admin') {{
                        // Show only Admin log link
                        if (adminLogLink) adminLogLink.style.display = 'inline-block';
                        if (recruiterLogLink) recruiterLogLink.style.display = 'none';
                        if (mainLogLink) mainLogLink.style.display = 'none';
                    }} else if (section === 'recruiter') {{
                        // Show only Recruiter log link
                        if (adminLogLink) adminLogLink.style.display = 'none';
                        if (recruiterLogLink) recruiterLogLink.style.display = 'inline-block';
                        if (mainLogLink) mainLogLink.style.display = 'none';
                    }} else {{
                        // Default: show all BenchSale log links
                        if (adminLogLink) adminLogLink.style.display = 'inline-block';
                        if (recruiterLogLink) recruiterLogLink.style.display = 'inline-block';
                        if (mainLogLink) mainLogLink.style.display = 'inline-block';
                    }}
                }}
                
                // Show/hide BenchSale sections based on selected section
                if (section === 'all') {{
                    // Show only "All Tests" section
                    document.getElementById('all-tests').style.display = 'block';
                    document.getElementById('admin-tests').style.display = 'none';
                    document.getElementById('recruiter-tests').style.display = 'none';
                }} else if (section === 'admin') {{
                    // Show only "Admin Tests" section
                    document.getElementById('all-tests').style.display = 'none';
                    document.getElementById('admin-tests').style.display = 'block';
                    document.getElementById('recruiter-tests').style.display = 'none';
                }} else if (section === 'recruiter') {{
                    // Show only "Recruiter Tests" section
                    document.getElementById('all-tests').style.display = 'none';
                    document.getElementById('admin-tests').style.display = 'none';
                    document.getElementById('recruiter-tests').style.display = 'block';
                }} else {{
                    // Default: show all BenchSale sections
                    document.getElementById('all-tests').style.display = 'block';
                    document.getElementById('admin-tests').style.display = 'block';
                    document.getElementById('recruiter-tests').style.display = 'block';
                }}
            }}

            document.querySelectorAll('.test-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            
            const sectionId = section === 'all' ? 'all-tests' : section + '-tests';
            const sectionElement = document.getElementById(sectionId);
            if (sectionElement) {{
                sectionElement.classList.add('active');
            }}
            
            // Update logo and title based on section
            const titleElement = document.getElementById('dashboard-title');
            const benchsaleLogo = document.getElementById('benchsale-logo');
            const employerLogo = document.getElementById('employer-logo');
            const jobseekerLogo = document.getElementById('jobseeker-logo');
            const logoContainer = document.getElementById('dashboard-logo');
            
            if (section === 'employer') {{
                if (titleElement) titleElement.textContent = 'Employer Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'none';
                if (employerLogo) employerLogo.style.display = 'block';
                if (jobseekerLogo) jobseekerLogo.style.display = 'none';
                if (logoContainer) logoContainer.className = 'dashboard-logo employer-logo';
            }} else if (section === 'jobseeker') {{
                if (titleElement) titleElement.textContent = 'Job Seeker Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'none';
                if (employerLogo) employerLogo.style.display = 'none';
                if (jobseekerLogo) jobseekerLogo.style.display = 'block';
                if (logoContainer) logoContainer.className = 'dashboard-logo jobseeker-logo';
            }} else {{
                if (titleElement) titleElement.textContent = 'BenchSale Test Dashboard';
                if (benchsaleLogo) benchsaleLogo.style.display = 'block';
                if (employerLogo) employerLogo.style.display = 'none';
                if (jobseekerLogo) jobseekerLogo.style.display = 'none';
                if (logoContainer) logoContainer.className = 'dashboard-logo';
            }}
            
            if (clickedElement) {{
                clickedElement.classList.add('active');
            }} else {{
                const buttons = document.querySelectorAll('.tab');
                buttons.forEach(btn => {{
                    const onclickAttr = btn.getAttribute('onclick') || '';
                    const btnText = btn.textContent || '';
                    let shouldActivate = false;
                    if (section === 'all') {{
                        shouldActivate = onclickAttr.includes("'all'") || btnText.includes('All Tests');
                    }} else if (section === 'admin') {{
                        shouldActivate = onclickAttr.includes("'admin'") || btnText.includes('Admin Tests');
                    }} else if (section === 'recruiter') {{
                        shouldActivate = onclickAttr.includes("'recruiter'") || btnText.includes('Recruiter Tests');
                    }} else if (section === 'employer') {{
                        shouldActivate = onclickAttr.includes("'employer'") || btnText.includes('Employer Tests');
                    }} else if (section === 'jobseeker') {{
                        shouldActivate = onclickAttr.includes("'jobseeker'") || btnText.includes('Job Seeker Tests');
                    }}
                    
                    if (shouldActivate) {{
                        btn.classList.add('active');
                    }}
                }});
            }}
            
            setTimeout(() => {{
                updateStatistics(section);
            }}, 100);
            
            try {{
                const url = new URL(window.location);
                url.searchParams.set('filter', section);
                window.history.pushState({{filter: section}}, '', url);
            }} catch(e) {{
                console.log('URL update failed:', e);
            }}
        }}
        
        function showTestDetails(testItem) {{
            // Remove active class from all test items
            document.querySelectorAll('.test-item').forEach(item => {{
                item.classList.remove('active');
            }});
            
            // Add active class to clicked item
            testItem.classList.add('active');
            
            // Get test data from data attribute
            const testDataJson = testItem.getAttribute('data-test-info');
            if (!testDataJson) return;
            
            let testData;
            try {{
                testData = JSON.parse(testDataJson);
            }} catch(e) {{
                console.error('Error parsing test data:', e);
                return;
            }}

            // Special handling for db_solr_sync to extract job report from failure message if not present
            if (testData.name && (testData.name.includes('db_solr_sync') || testData.name.includes('DB Solr Sync')) && (!testData.total_jobs || testData.total_jobs === 0) && testData.failure_message) {{
                 // Newer failure message format: "Solr Sync Failed for X/Y jobs checked"
                 const quickMatch = testData.failure_message.match(/Solr Sync Failed for\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*jobs checked/i);
                 if (quickMatch) {{
                     testData.error_jobs_count = parseInt(quickMatch[1], 10);
                     testData.total_jobs = parseInt(quickMatch[2], 10);
                 }}
                 // Try to find JSON report
                 const jsonMatch = testData.failure_message.match(/JSON_REPORT_START\s*({{[:\s\S]*?}})\s*JSON_REPORT_END/);
                 if (jsonMatch) {{
                     try {{
                         const report = JSON.parse(jsonMatch[1]);
                         if (report.total_jobs) testData.total_jobs = report.total_jobs;
                         if (report.error_jobs_count) testData.error_jobs_count = report.error_jobs_count;
                     }} catch(e) {{}}
                 }}
                 
                 // Try to find text table report
                 if (!testData.total_jobs) {{
                     const tableMatch = testData.failure_message.match(/Total Jobs Checked:\s*(\d+)/);
                     if (tableMatch) {{
                         testData.total_jobs = parseInt(tableMatch[1], 10);
                         const failMatch = testData.failure_message.match(/Failures found:\s*(\d+)/);
                         if (failMatch) {{
                             testData.error_jobs_count = parseInt(failMatch[1], 10);
                         }}
                     }}
                 }}
                 
                 // Try to find older text format
                 if (!testData.total_jobs) {{
                     const oldMatch = testData.failure_message.match(/Total Jobs Available in DB \(last 12h\):\s*(\d+)/);
                     if (oldMatch) {{
                         testData.total_jobs = parseInt(oldMatch[1], 10);
                         const oldFailMatch = testData.failure_message.match(/Total Failures:\s*(\d+)/);
                         if (oldFailMatch) {{
                             testData.error_jobs_count = parseInt(oldFailMatch[1], 10);
                         }}
                     }}
                 }}
            }}
            
            // Find the details panel in the same section
            const testSection = testItem.closest('.test-section');
            const detailsPanel = testSection ? testSection.querySelector('.test-details-panel') : null;
            if (!detailsPanel) return;
            
            // Build details HTML
            const status = testData.status || 'NOT_RUN';
            const statusLower = status.toLowerCase().replace('_', '-');
            const statusDisplay = status.replace('_', ' ');
            
            let detailsHTML = `
                <div class="test-details-header">
                    <div class="test-details-title">${{testData.name || 'Test Case'}}</div>
                    <div class="test-details-status test-badge ${{statusLower}}">${{statusDisplay}}</div>
                </div>
                
                <div class="test-details-info">
                    <div class="test-details-info-item">
                        <div class="test-details-info-label">Source</div>
                        <div class="test-details-info-value">${{testData.source || 'N/A'}}</div>
                    </div>
                    <div class="test-details-info-item">
                        <div class="test-details-info-label">Running Time</div>
                        <div class="test-details-info-value">${{testData.running_time || 'N/A'}}</div>
                    </div>
                    ${{testData.total_jobs ? `
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px;">
                        <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; text-align: center;">
                            <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
                            <div style="font-size: 20px; font-weight: 700; color: #1e293b; margin-bottom: 4px;">${{testData.total_jobs.toLocaleString()}}</div>
                            <div style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Total Jobs Checked</div>
                        </div>
                        ${{testData.error_jobs_count !== undefined ? `
                        <div style="background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 15px; text-align: center;">
                            <div style="font-size: 24px; margin-bottom: 8px;">❌</div>
                            <div style="font-size: 20px; font-weight: 700; color: #dc3545; margin-bottom: 4px;">${{testData.error_jobs_count.toLocaleString()}}</div>
                            <div style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Failures</div>
                        </div>
                        ` : ''}}
                        ${{testData.total_jobs && testData.error_jobs_count !== undefined ? `
                        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 15px; text-align: center;">
                            <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
                            <div style="font-size: 20px; font-weight: 700; color: #10b981; margin-bottom: 4px;">${{((testData.total_jobs - testData.error_jobs_count) / testData.total_jobs * 100).toFixed(2)}}%</div>
                            <div style="font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase;">Success Rate</div>
                        </div>
                        ` : ''}}
                    </div>
                    ` : ''}}
                </div>
                
                <div class="test-details-content">
            `;
            
            // Add screenshot ONLY if test failed and screenshot is available
            // For passed tests, show empty space (no screenshot)
            if ((status === 'FAIL' || status === 'FAILED') && testData.screenshots && testData.screenshots.length > 0) {{
                const screenshotUrl = testData.screenshots[0];
                detailsHTML += `
                    <div class="test-details-screenshot">
                        <h4 style="margin-bottom: 10px; font-weight: 600; color: var(--text-primary);">📸 Screenshot</h4>
                        <img src="${{screenshotUrl}}" alt="Test Screenshot" 
                             onerror="this.parentElement.style.display='none'"
                             onclick="openModal(this.src)">
                    </div>
                `;
            }}

            // Add artifact links if available (HTML snapshot + URL text)
            if (testData.artifacts && (testData.artifacts.html_url || testData.artifacts.url_txt_url)) {{
                detailsHTML += `
                    <div class="test-details-location">
                        <div class="test-details-location-title">🧾 Failure Artifacts</div>
                        <div class="test-details-location-content">
                            ${{testData.artifacts.html_url ? `<a href="${{testData.artifacts.html_url}}" target="_blank">Open HTML snapshot</a>` : ''}}
                            ${{testData.artifacts.html_url && testData.artifacts.url_txt_url ? ' | ' : ''}}
                            ${{testData.artifacts.url_txt_url ? `<a href="${{testData.artifacts.url_txt_url}}" target="_blank">Open URL file</a>` : ''}}
                        </div>
                    </div>
                `;
            }}
            
            // Add failure details if test failed
            if (status === 'FAIL' || status === 'FAILED') {{
                if (testData.failure_message) {{
                    detailsHTML += `
                        <div class="test-details-failure">
                            <div class="test-details-failure-title">❌ Failure Message</div>
                            <div class="test-details-failure-content">${{escapeHtml(testData.failure_message)}}</div>
                        </div>
                    `;
                }}
                
                if (testData.failure_location) {{
                    detailsHTML += `
                        <div class="test-details-location">
                            <div class="test-details-location-title">📍 Failure Location</div>
                            <div class="test-details-location-content">${{escapeHtml(testData.failure_location)}}</div>
                        </div>
                    `;
                }}
                
                if (testData.xpath) {{
                    detailsHTML += `
                        <div class="test-details-location">
                            <div class="test-details-location-title">🔗 XPath / Element Location</div>
                            <div class="test-details-location-content">${{escapeHtml(testData.xpath)}}</div>
                        </div>
                    `;
                }}
            }}
            
            // Close the content div
            detailsHTML += '</div>';
            
            // Update details panel
            detailsPanel.innerHTML = detailsHTML;
            detailsPanel.classList.remove('empty');
            detailsPanel.style.display = 'flex';
            detailsPanel.style.opacity = '1';
            
            // Scroll details content to top
            const contentDiv = detailsPanel.querySelector('.test-details-content');
            if (contentDiv) {{
                contentDiv.scrollTop = 0;
            }}
        }}
        
        function escapeHtml(text) {{
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => {{
                const onclickAttr = tab.getAttribute('onclick');
                if (onclickAttr) {{
                    const match = onclickAttr.match(/showSection\('([^']+)'\)/);
                    if (match) {{
                        const section = match[1];
                        tab.removeAttribute('onclick');
                        tab.addEventListener('click', function(e) {{
                            e.preventDefault();
                            showSection(section, this);
                        }});
                    }}
                }}
            }});
            
            const urlParams = new URLSearchParams(window.location.search);
            const filter = urlParams.get('filter');
            
            if (filter === 'employer') {{
                // Hide all BenchSale tabs (All Tests, Admin Tests, Recruiter Tests)
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                // Hide BenchSale stats
                document.querySelectorAll('.benchsale-stat').forEach(stat => stat.style.display = 'none');
                document.querySelectorAll('.jobseeker-stat').forEach(stat => stat.style.display = 'none');
                // Show only Employer tab
                document.getElementById('tab-employer').style.display = 'block';
                document.getElementById('tab-employer').classList.add('active');
                document.getElementById('tab-jobseeker').style.display = 'none';
                // Hide all BenchSale and Job Seeker test sections completely (not just inactive)
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').style.display = 'none';
                // Show only Employer test section
                document.getElementById('employer-tests').style.display = 'block';
                document.getElementById('employer-tests').classList.add('active');
                // Show Employer log link
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'inline-block';
                    // Hide BenchSale and Job Seeker log links
                    logLinks.querySelectorAll('a[href*="benchsale"]').forEach(link => link.style.display = 'none');
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'none';
                }}
            }} else if (filter === 'jobseeker') {{
                // Hide all BenchSale tabs (All Tests, Admin Tests, Recruiter Tests)
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'none');
                // Hide BenchSale stats
                document.querySelectorAll('.benchsale-stat').forEach(stat => stat.style.display = 'none');
                document.querySelectorAll('.employer-stat').forEach(stat => stat.style.display = 'none');
                // Show only Job Seeker tab
                document.getElementById('tab-jobseeker').style.display = 'block';
                document.getElementById('tab-jobseeker').classList.add('active');
                document.getElementById('tab-employer').style.display = 'none';
                // Hide all BenchSale and Employer test sections completely (not just inactive)
                document.getElementById('all-tests').style.display = 'none';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                document.getElementById('employer-tests').style.display = 'none';
                // Show only Job Seeker test section
                document.getElementById('jobseeker-tests').style.display = 'block';
                document.getElementById('jobseeker-tests').classList.add('active');
                // Show Job Seeker log link
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'inline-block';
                    // Hide BenchSale and Employer log links
                    logLinks.querySelectorAll('a[href*="benchsale"]').forEach(link => link.style.display = 'none');
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'none';
                }}
            }} else {{
                // Show all BenchSale tabs
                document.querySelectorAll('.benchsale-tab').forEach(tab => tab.style.display = 'block');
                // Show BenchSale stats
                document.querySelectorAll('.benchsale-stat').forEach(stat => stat.style.display = 'block');
                // Hide Employer and Job Seeker tabs
                document.getElementById('tab-employer').style.display = 'none';
                document.getElementById('tab-jobseeker').style.display = 'none';
                // Hide Employer and Job Seeker test sections completely
                document.getElementById('employer-tests').style.display = 'none';
                document.getElementById('employer-tests').classList.remove('active');
                document.getElementById('jobseeker-tests').style.display = 'none';
                document.getElementById('jobseeker-tests').classList.remove('active');
                // Initially show only "All Tests" section (will be updated by showSection if filter is set)
                document.getElementById('all-tests').style.display = 'block';
                document.getElementById('admin-tests').style.display = 'none';
                document.getElementById('recruiter-tests').style.display = 'none';
                // Hide Employer and Job Seeker log links in BenchSale dashboard
                const logLinks = document.getElementById('log-links-content');
                if (logLinks) {{
                    const employerLogLink = logLinks.querySelector('a[href*="module=employer"]');
                    if (employerLogLink) employerLogLink.style.display = 'none';
                    const jobseekerLogLink = logLinks.querySelector('a[href*="module=jobseeker"]');
                    if (jobseekerLogLink) jobseekerLogLink.style.display = 'none';
                    
                    // Show all BenchSale log links by default (for "All Tests" view)
                    const adminLogLink = logLinks.querySelector('a[href*="benchsale_admin"]');
                    const recruiterLogLink = logLinks.querySelector('a[href*="benchsale_recruiter"]');
                    const mainLogLink = logLinks.querySelector('a[href*="benchsale_test"]');
                    if (adminLogLink) adminLogLink.style.display = 'inline-block';
                    if (recruiterLogLink) recruiterLogLink.style.display = 'inline-block';
                    if (mainLogLink) mainLogLink.style.display = 'inline-block';
                }}
            }}
            
            if (filter && ['admin', 'recruiter', 'employer', 'jobseeker', 'all'].includes(filter)) {{
                setTimeout(function() {{
                    showSection(filter);
                    setTimeout(function() {{
                    updateStatistics(filter);
                    }}, 100);
                }}, 200);
            }} else {{
                showSection('all');
                setTimeout(function() {{
                updateStatistics('all');
                }}, 300);
            }}
        }});
        
        document.addEventListener('click', function(e) {{
            if (e.target.tagName === 'IMG' && e.target.closest('.screenshot-item')) {{
                openModal(e.target.src);
            }}
        }});
        
        function refreshDashboard() {{
            const statusEl = document.getElementById('refreshStatus');
            if (statusEl) {{
                statusEl.textContent = 'Refreshing...';
                statusEl.style.background = 'rgba(255, 204, 0, 0.2)';
                statusEl.style.color = '#ed8936';
            }}
            // Force a hard reload to clear cache and get fresh data
            setTimeout(function() {{
                location.reload(true);
            }}, 500);
        }}
        
        // Auto-refresh dashboard every 6 hours if page is visible
        // This ensures status updates even if test was run outside the UI
        let autoRefreshInterval = null;
        function startAutoRefresh() {{
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {{
                // Only refresh if page is visible (not in background tab)
                if (!document.hidden) {{
                    // Check if any test is currently running
                    const runningButtons = document.querySelectorAll('.run-test-btn.running');
                    
                    // Check if user is viewing a test case (details panel open)
                    const activeTestItems = document.querySelectorAll('.test-item.active');
                    
                    if (runningButtons.length === 0 && activeTestItems.length === 0) {{
                        // No tests running AND no test details being viewed, safe to refresh
                        console.log('Auto-refreshing dashboard to check for status updates...');
                        location.reload(true);
                    }} else if (activeTestItems.length > 0) {{
                        console.log('Skipping auto-refresh: User is viewing test details');
                    }}
                }}
            }}, 21600000); // Refresh every 6 hours
        }}
        
        // Start auto-refresh when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            const dashboardVersion = '{generated_at}';
            console.log('Dashboard loaded. Last updated: {last_updated_str}');
            console.log('Dashboard generated at: ' + dashboardVersion);
            console.log('Dashboard auto-updates after each test run.');
            console.log('Current browser time: ' + new Date().toISOString());
            startAutoRefresh();
        }});
        // Modal Functions
        function openModal(src) {{
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.style.display = 'flex';
            modalImg.src = src;
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        }}

        function closeModal() {{
            const modal = document.getElementById('imageModal');
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Restore scrolling
        }}

        document.addEventListener('keydown', function(event) {{
            if (event.key === "Escape") {{
                closeModal();
            }}
        }});
        
        // Notification functions
        function showNotification(type, title, message, duration = 5000) {{
            const banner = document.getElementById('notificationBanner');
            if (!banner) {{
                console.warn('Notification banner not found in DOM');
                return;
            }}
            
            const icon = document.getElementById('notificationIcon');
            const titleEl = document.getElementById('notificationTitle');
            const messageEl = document.getElementById('notificationMessage');
            
            if (!icon || !titleEl || !messageEl) {{
                console.warn('Notification elements not found');
                return;
            }}
            
            // Remove all type classes
            banner.classList.remove('success', 'info', 'warning', 'error');
            banner.classList.add(type);
            
            // Set icon based on type
            const icons = {{
                'success': '✅',
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌'
            }};
            icon.textContent = icons[type] || 'ℹ️';
            
            titleEl.textContent = title;
            messageEl.textContent = message;
            
            banner.classList.add('show');
            
            // Auto-hide after duration
            if (duration > 0) {{
                setTimeout(() => {{
                    hideNotification();
                }}, duration);
            }}
        }}
        
        function hideNotification() {{
            const banner = document.getElementById('notificationBanner');
            banner.classList.remove('show');
        }}
        
        // Run test function
        // Track running tests to prevent duplicates
        const runningTests = new Set();
        const buttonClickTimes = new Map(); // Track when button was last clicked
        
        function runTest(testName, event) {{
            // CRITICAL: Prevent default and stop propagation
            if (event) {{
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }}
            
            // CRITICAL: Check if test is already running or queued FIRST (before debounce check)
            if (runningTests.has(testName)) {{
                console.log('Test ' + testName + ' is already running or queued, ignoring duplicate request');
                showNotification('warning', 'Test Already Running', 'Test "' + testName + '" is already running or queued. Please wait for it to complete.', 3000);
                return;
            }}
            
            // CRITICAL: Debounce - prevent rapid clicks (within 3 seconds - increased from 2)
            const now = Date.now();
            const lastClickTime = buttonClickTimes.get(testName) || 0;
            if (now - lastClickTime < 3000) {{
                console.log('Test ' + testName + ' clicked too soon after last click, ignoring');
                showNotification('info', 'Please Wait', 'Test "' + testName + '" was just clicked. Please wait a moment.', 2000);
                return;
            }}
            buttonClickTimes.set(testName, now);
            
            // Mark test as running immediately (before any async operations)
            runningTests.add(testName);
            
            // Find the button that was clicked
            const buttons = document.querySelectorAll('.run-test-btn');
            let clickedButton = null;
            buttons.forEach(btn => {{
                if (btn.textContent.includes('Run Test') || btn.textContent.includes('Running') || btn.textContent.includes('Done')) {{
                    const testItem = btn.closest('.test-item');
                    if (testItem && testItem.getAttribute('data-test-info')) {{
                        try {{
                            const testData = JSON.parse(testItem.getAttribute('data-test-info'));
                            if (testData.name === testName) {{
                                clickedButton = btn;
                            }}
                        }} catch(e) {{
                            // Ignore
                        }}
                    }}
                }}
            }});
            
            if (!clickedButton) {{
                // Fallback: find button by test name in parent
                document.querySelectorAll('.run-test-btn').forEach(btn => {{
                    const onclickAttr = btn.getAttribute('onclick') || '';
                    if (onclickAttr.includes(testName)) {{
                        clickedButton = btn;
                    }}
                }});
            }}
            
            // CRITICAL: Disable button IMMEDIATELY to prevent multiple clicks
            if (clickedButton) {{
                clickedButton.classList.add('running');
                clickedButton.textContent = '⏳ Running...';
                clickedButton.disabled = true;
                clickedButton.style.pointerEvents = 'none'; // Prevent any clicks
                clickedButton.style.opacity = '0.7'; // Visual feedback
                clickedButton.style.cursor = 'not-allowed'; // Show disabled cursor
                
                // Remove onclick to prevent any clicks
                clickedButton.removeAttribute('onclick');
                
                // Also prevent any event listeners
                clickedButton.onclick = function(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    return false;
                }};
            }}
            
            // Try to run via always-on server first (port 8766)
            // Falls back to regular server (port 8765) if needed
            let serverUrl = 'http://127.0.0.1:8766/add-test';
            let isAlwaysOnServer = true;
            
            // Helper function for polling
            let testWasStarted = false; // Track if test actually started
            function startPolling(port) {{
                // Poll for completion - more aggressive polling
                const pollInterval = 1000; // Check every 1 second (faster detection)
                const maxPolls = 600; // 10 minutes max (600 seconds)
                let pollCount = 0;
                let wasBusy = false; // Track if server was ever busy (test was running)
                let notBusyCount = 0; // Count consecutive "not busy" responses
                const requiredNotBusyCount = 3; // Need 3 consecutive "not busy" to confirm test is done
                
                // Wait 2 seconds before starting to poll (give server time to start test and set lock)
                setTimeout(() => {{
                    const timer = setInterval(() => {{
                        pollCount++;
                        fetch(`http://127.0.0.1:${{port}}/status?t=${{Date.now()}}`) // Add cache-busting parameter
                            .then(r => {{
                                if (!r.ok) {{
                                    throw new Error(`Server returned ${{r.status}}`);
                                }}
                                return r.json();
                            }})
                            .then(statusData => {{
                                // Track if server was ever busy (means test was actually running)
                                if (statusData.busy) {{
                                    wasBusy = true;
                                    notBusyCount = 0; // Reset counter when busy
                                    if (pollCount % 10 === 0) {{ // Log every 10 polls to reduce console spam
                                        console.log('Test is running... (poll count: ' + pollCount + ')');
                                    }}
                                }} else {{
                                    // Server is not busy
                                    notBusyCount++;
                                    
                                    // If test was running and we've seen multiple "not busy" responses, test is done
                                    if (wasBusy && notBusyCount >= requiredNotBusyCount) {{
                                        clearInterval(timer);
                                        
                                        // Remove from running set when test completes
                                        runningTests.delete(testName);
                                        
                                        if (clickedButton) {{
                                            clickedButton.textContent = '✅ Done';
                                            clickedButton.classList.remove('running');
                                            clickedButton.style.opacity = '1';
                                            
                                            // Re-enable button after delay
                                            setTimeout(() => {{
                                                clickedButton.disabled = false;
                                                clickedButton.style.pointerEvents = 'auto';
                                                clickedButton.style.cursor = 'pointer';
                                                clickedButton.textContent = '▶ Run Test';
                                                // Restore onclick
                                                clickedButton.setAttribute('onclick', `event.stopPropagation(); runTest('${{testName}}', event)`);
                                                clickedButton.onclick = function(e) {{
                                                    runTest(testName, e);
                                                }};
                                            }}, 3000);
                                        }}
                                        showNotification('success', 'Test Completed', 'Waiting for log file to update, then reloading dashboard...', 3000);
                                        // Wait longer (7 seconds) to ensure log file is written and dashboard is regenerated
                                        setTimeout(() => {{
                                            // Force a hard reload to clear cache and get fresh data
                                            console.log('Reloading dashboard to show updated status...');
                                            location.reload(true);
                                        }}, 7000);
                                    }} else if (!wasBusy && notBusyCount >= 3) {{
                                        // Server was never busy and we've confirmed it multiple times
                                        clearInterval(timer);
                                        if (clickedButton) {{
                                            clickedButton.textContent = '▶ Run Test';
                                            clickedButton.classList.remove('running');
                                            clickedButton.disabled = false;
                                        }}
                                        showNotification('error', 'Test Not Started', 'Server may not be running or test failed to start. Please check server status.', 5000);
                                    }}
                                }}
                            }})
                            .catch(e => {{
                                console.log('Polling error', e);
                                pollCount += 2; // Accelerate timeout on errors
                                
                                // If server is not responding after many attempts, show error
                                if (pollCount > 30) {{
                                    clearInterval(timer);
                                    if (clickedButton) {{
                                        clickedButton.textContent = '▶ Run Test';
                                        clickedButton.classList.remove('running');
                                        clickedButton.disabled = false;
                                    }}
                                    showNotification('error', 'Server Not Responding', 'Cannot connect to test server. Please make sure the server is running.', 5000);
                                }}
                            }});
                             
                        if (pollCount > maxPolls) {{
                            clearInterval(timer);
                            if (clickedButton) {{
                                clickedButton.textContent = '▶ Run Test';
                                clickedButton.classList.remove('running');
                                clickedButton.disabled = false;
                            }}
                            showNotification('warning', 'Timeout', 'Test is taking longer than expected. Reloading dashboard...', 3000);
                            setTimeout(() => {{
                                // Force a hard reload to clear cache and get fresh data
                                location.reload(true);
                            }}, 3000);
                        }}
                    }}, pollInterval);
                }}, 2000); // Wait 2 seconds before starting to poll
            }}
            
            // Also add a fallback: if polling doesn't detect completion, check after a reasonable time
            // This handles cases where status endpoint might not be working correctly
            setTimeout(() => {{
                // After 2 minutes, force a reload to check status (in case polling missed it)
                console.log('Fallback: Checking dashboard status after 2 minutes...');
                // This will be handled by the auto-refresh mechanism
            }}, 120000);
            
            fetch(serverUrl, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{ testName: testName }})
            }})
            .then(response => {{
                if (!response.ok) {{
                    throw new Error(`Server returned ${{response.status}}: ${{response.statusText}}`);
                }}
                return response.json();
            }})
            .then(data => {{
                if (data.success) {{
                    testWasStarted = true; // Mark that test was successfully started
                    if (clickedButton) {{
                        clickedButton.textContent = '✅ Running';
                        clickedButton.style.background = 'linear-gradient(135deg, #16A34A 0%, #15803D 100%)';
                    }}
                    // Show notification
                    showNotification('success', 'Test Started', 'Test "' + testName + '" is running. Dashboard will reload automatically when done.', 5000);
                    
                    // Start polling for completion
                    startPolling(8766);
                }} else {{
                    // Test failed to start - remove from running set
                    runningTests.delete(testName);
                    if (clickedButton) {{
                        clickedButton.disabled = false;
                        clickedButton.style.pointerEvents = 'auto';
                        clickedButton.style.opacity = '1';
                        clickedButton.textContent = '▶ Run Test';
                        clickedButton.classList.remove('running');
                    }}
                    throw new Error(data.error || 'Failed to run test');
                }}
            }})
            .catch(error => {{
                // Remove from running set on error
                runningTests.delete(testName);
                
                // Re-enable button on error
                if (clickedButton) {{
                    clickedButton.disabled = false;
                    clickedButton.style.pointerEvents = 'auto';
                    clickedButton.style.opacity = '1';
                    clickedButton.style.cursor = 'pointer';
                    clickedButton.textContent = '▶ Run Test';
                    clickedButton.classList.remove('running');
                    // Restore onclick
                    clickedButton.setAttribute('onclick', `event.stopPropagation(); runTest('${{testName}}', event)`);
                    clickedButton.onclick = function(e) {{
                        runTest(testName, e);
                    }};
                }}
                
                // If always-on server failed, try regular server as fallback
                if (isAlwaysOnServer) {{
                    isAlwaysOnServer = false;
                    serverUrl = 'http://127.0.0.1:8765/run-test';
                    
                    // Retry with regular server
                    fetch(serverUrl, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ testName: testName }})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            if (clickedButton) {{
                                clickedButton.textContent = '✅ Running';
                                clickedButton.style.background = 'linear-gradient(135deg, #16A34A 0%, #15803D 100%)';
                            }}
                            showNotification('success', 'Test Started', 'Test running. Dashboard will reload shortly.', 4000);
                            
                            // Fallback server might not have status endpoint, wait longer then reload
                            // Wait 15 seconds to ensure test completes and log file is written
                            setTimeout(() => {{
                                // Force a hard reload to clear cache and get fresh data
                                location.reload(true);
                            }}, 15000);
                        }} else {{
                            throw new Error(data.error || 'Failed to run test');
                        }}
                    }})
                    .catch(() => {{
                        // Both servers failed
                        const command = 'python -m pytest -k "' + testName + '" -s -vv';
                        
                        if (navigator.clipboard && navigator.clipboard.writeText) {{
                            navigator.clipboard.writeText(command).catch(() => {{}});
                        }}
                        
                        const serverMessage = `Test server is not running!\\n\\n` +
                            `To start the server:\\n` +
                            `1. Double-click: START_ALWAYS_ON_SERVER.bat\\n` +
                            `2. Or run: python utils\\\\always_on_server.py\\n\\n` +
                            `Keep the server window open while using the dashboard.\\n` +
                            `Server runs on port 8766.`;
                        
                        showNotification(
                            'error',
                            'Server Not Running',
                            serverMessage,
                            10000
                        );
                        
                        if (clickedButton) {{
                            clickedButton.classList.remove('running');
                            clickedButton.textContent = '▶ Run Test';
                            clickedButton.disabled = false;
                        }}
                    }});
                }}
            }});
        }}
    </script>
</body>
</html>"""
    
    return html


def shorten_test_name(name: str) -> str:
    """Shorten test name for display by removing 'test_' prefix and converting underscores to spaces."""
    # Remove 'test_' prefix if present
    if name.startswith('test_'):
        name = name[5:]
    # Convert underscores to spaces and capitalize words
    name = name.replace('_', ' ')
    # Capitalize first letter of each word
    words = name.split()
    name = ' '.join(word.capitalize() for word in words)
    return name


def generate_test_list_html(tests):
    """Generate HTML for test list."""
    try:
        if not tests:
            return '<div class="no-tests">No tests found</div>'
        
        html_items = []
        for test in tests:
            status = test.get('status', 'NOT_RUN').upper()
            # Normalize status for CSS class
            status_lower = status.lower().replace('_', '-')
            # Shorten test name for cleaner display
            original_name = test['name']
            display_name = shorten_test_name(original_name)
            name = escape(display_name)
            source = test.get('source', 'Main')
            
            # Get test data for details panel
            running_time = test.get('running_time', 'N/A')
            failure_message = test.get('failure_message', '')
            failure_location = test.get('failure_location', '')
            xpath = test.get('xpath', '')
            screenshots = test.get('screenshots', [])
            artifacts = test.get('artifacts', {}) or {}
            total_jobs = test.get('total_jobs', 0)  # For db_solr_sync test - 12hrs job report
            error_jobs_count = test.get('error_jobs_count', 0)  # For db_solr_sync test - failures count
            is_db_solr_sync = 'db_solr_sync' in original_name.lower()
            
            # Ensure screenshots is a list
            if not isinstance(screenshots, list):
                screenshots = []
            
            # Prepare data attributes (escape JSON for HTML)
            import json
            try:
                test_data = {
                    'name': original_name,
                    'status': status,
                    'source': source,
                    'running_time': str(running_time) if running_time else 'N/A',
                    'failure_message': str(failure_message) if failure_message else '',
                    'failure_location': str(failure_location) if failure_location else '',
                    'xpath': str(xpath) if xpath else '',
                    'screenshots': [s.get('url', s) if isinstance(s, dict) else str(s) for s in screenshots] if screenshots else [],
                    'artifacts': {
                        'html_url': artifacts.get('html_url', ''),
                        'url_txt_url': artifacts.get('url_txt_url', '')
                    }
                }
                # Add 12hrs job report data for db_solr_sync test
                if total_jobs > 0:
                    test_data['total_jobs'] = int(total_jobs)
                # For db_solr_sync test, always include error_jobs_count if it was set (even if 0)
                # For other tests, only include if > 0
                if is_db_solr_sync and 'error_jobs_count' in test:
                    test_data['error_jobs_count'] = int(error_jobs_count)
                elif error_jobs_count > 0:
                    test_data['error_jobs_count'] = int(error_jobs_count)
                test_data_json = escape(json.dumps(test_data))
                # Escape quotes in JSON for HTML attribute
                test_data_json_escaped = test_data_json.replace('"', '&quot;')
            except Exception as e:
                # If JSON encoding fails, use minimal data
                print(f"Warning: Failed to encode test data for {original_name}: {e}")
                test_data_json_escaped = escape(json.dumps({'name': original_name, 'status': status, 'source': source}))
            
            # Display status text (replace NOT_RUN with "Not Run")
            status_display = status.replace('_', ' ')
            
            # Escape the original test name for use in JavaScript
            original_name_escaped = escape(original_name).replace("'", "\\'")
            
            html_items.append(f'''
                <div class="test-item {status_lower}" data-test-info="{test_data_json_escaped}" onclick="showTestDetails(this)">
                    <div class="test-name">{name}</div>
                    <div class="test-badge {status_lower}">{status_display}</div>
                    <div class="test-source">Source: {source}</div>
                    <div class="test-actions">
                        <button class="run-test-btn" onclick="event.stopPropagation(); runTest('{original_name_escaped}', event)" title="Run this test">
                            ▶ Run Test
                        </button>
                    </div>
                </div>
            ''')
        
        return f'<div class="test-list">{"".join(html_items)}</div>'
    except Exception as e:
        print(f"Error generating test list HTML: {e}")
        import traceback
        traceback.print_exc()
        return f'<div class="no-tests">Error loading tests: {str(e)}</div>'


def generate_log_links_html(admin_log, recruiter_log, employer_log, jobseeker_log, main_log):
    """Generate HTML for log file links."""
    links = []
    
    if admin_log and admin_log.exists():
        admin_html = admin_log.parent / 'benchsale_admin.html'
        if admin_html.exists():
            links.append(f'<a href="../log_viewer_ui.html?module=benchsale_admin&hideModules=true" class="log-link" target="_blank">📊 Admin Log History</a>')
    
    if recruiter_log and recruiter_log.exists():
        recruiter_html = recruiter_log.parent / 'benchsale_recruiter.html'
        if recruiter_html.exists():
            links.append(f'<a href="../log_viewer_ui.html?module=benchsale_recruiter&hideModules=true" class="log-link" target="_blank">📊 Recruiter Log History</a>')
    
    if employer_log and employer_log.exists():
        links.append(f'<a href="../log_viewer_ui.html?module=employer&hideModules=true" class="log-link" target="_blank">📊 Employer Log History</a>')
    
    if jobseeker_log and jobseeker_log.exists():
        links.append(f'<a href="../log_viewer_ui.html?module=jobseeker&hideModules=true" class="log-link" target="_blank">📊 Job Seeker Log History</a>')
    
    # Main Test Log History button removed as requested
    
    return ''.join(links) if links else '<p>No log files available</p>'


if __name__ == '__main__':
    dashboard_path = generate_unified_dashboard()
    print(f"Unified dashboard generated: {dashboard_path}")
