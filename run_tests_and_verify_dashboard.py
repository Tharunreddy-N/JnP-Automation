"""
Run tests one by one and verify dashboard updates after each test.
Runs: Employer -> Job Seeker -> Bench Sale tests
After each test, checks if status is updated in dashboard.
"""
import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict
import re

PROJECT_ROOT = Path(__file__).parent
DASHBOARD_PATH = PROJECT_ROOT / 'logs' / 'index.html'

# Test cases to run (one from each category first)
TEST_CASES = {
    'employer': [
        'test_t1_01_home_page',
        'test_t1_02_home_page_verify_jobs_not_from_same_company_consecutively',
        'test_t2_01_post_a_job_verification_and_verification_with_job_id',
    ],
    'jobseeker': [
        'test_t1_01_verify_if_a_job_can_be_applied_by_a_js_from_home_page',
        'test_t1_02_verification_of_a_saved_job_from_home_page_in_js',
        'test_t1_03_verification_of_filters_in_traditional_search_in_js_dashboard',
    ],
    'benchsale': [
        'test_t1_01_admin_verification_of_favourite_button_under_companies_in_benchsale',
        'test_t2_01_recruiter_dashboard_verification_recruiter_active_inactive',
    ]
}


def run_test(test_name: str) -> Tuple[bool, str]:
    """Run a single test and return (success, output)."""
    print(f"\n{'='*80}")
    print(f"Running test: {test_name}")
    print(f"{'='*80}\n")
    
    cmd = [
        sys.executable,
        '-m', 'pytest',
        '-k', test_name,
        '-v',
        '--tb=short',
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes max per test
        )
        elapsed = time.time() - start_time
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        status = "PASSED" if success else "FAILED"
        print(f"\n[{status}] Test '{test_name}' completed in {elapsed:.2f} seconds")
        
        return success, output
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] Test '{test_name}' exceeded 30 minutes")
        return False, "Test execution timeout"
    except Exception as e:
        print(f"\n[ERROR] Failed to run test '{test_name}': {e}")
        return False, str(e)


def refresh_dashboard():
    """Refresh the dashboard to get latest test results."""
    print("\n[INFO] Refreshing dashboard...")
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'refresh_dashboard.py')],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("[OK] Dashboard refreshed successfully")
            return True
        else:
            print(f"[WARNING] Dashboard refresh had issues: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to refresh dashboard: {e}")
        return False


def check_test_status_in_dashboard(test_name: str) -> Dict:
    """
    Check if test status is updated in dashboard.
    Returns dict with status info.
    """
    if not DASHBOARD_PATH.exists():
        return {
            'found': False,
            'status': None,
            'message': 'Dashboard file not found'
        }
    
    try:
        with open(DASHBOARD_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert test function name to display name
        # e.g., "test_t1_01_home_page" -> "T1.01 Home Page"
        display_name = convert_test_name_to_display(test_name)
        
        # Look for test in dashboard HTML
        # Check for PASS/FAIL status indicators
        found = False
        status = None
        message = None
        
        # Search for test name in various formats
        search_patterns = [
            re.escape(test_name),
            re.escape(display_name),
            test_name.replace('_', ' '),
            display_name.replace(' ', '.*'),
        ]
        
        for pattern in search_patterns:
            # Look for status indicators near test name
            # Pattern: test name followed by status (PASS/FAIL/SKIP)
            status_pattern = rf'{pattern}.*?(?:PASS|FAIL|SKIP|passed|failed|skipped)'
            match = re.search(status_pattern, content, re.IGNORECASE)
            if match:
                found = True
                # Extract status
                if re.search(r'\bPASS\b|\bpassed\b', match.group(0), re.IGNORECASE):
                    status = 'PASS'
                elif re.search(r'\bFAIL\b|\bfailed\b', match.group(0), re.IGNORECASE):
                    status = 'FAIL'
                elif re.search(r'\bSKIP\b|\bskipped\b', match.group(0), re.IGNORECASE):
                    status = 'SKIP'
                break
        
        # Also check for test in JSON data if present
        json_match = re.search(r'var\s+testData\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if json_match and not found:
            try:
                json_str = json_match.group(1)
                test_data = json.loads(json_str)
                for test in test_data:
                    if test_name.lower() in str(test).lower() or display_name.lower() in str(test).lower():
                        found = True
                        status = test.get('status', 'UNKNOWN').upper()
                        break
            except:
                pass
        
        return {
            'found': found,
            'status': status,
            'message': f"Status: {status}" if status else "Test not found in dashboard"
        }
        
    except Exception as e:
        return {
            'found': False,
            'status': None,
            'message': f'Error reading dashboard: {e}'
        }


def convert_test_name_to_display(test_name: str) -> str:
    """Convert pytest test function name to display name."""
    # Remove 'test_' prefix
    name = test_name.replace('test_', '')
    
    # Extract test ID (T1.01, T2.01, etc.)
    test_id_match = re.search(r'(t[12]_\d+)', name, re.IGNORECASE)
    if test_id_match:
        test_id = test_id_match.group(1).upper().replace('_', '.')
        # Get rest of name
        rest = name.replace(test_id_match.group(1), '').replace('_', ' ').strip()
        # Capitalize words
        rest = ' '.join(word.capitalize() for word in rest.split())
        return f"{test_id} {rest}"
    
    # Fallback: just replace underscores and capitalize
    return ' '.join(word.capitalize() for word in name.replace('_', ' ').split())


def verify_dashboard_update(test_name: str, test_success: bool, max_wait: int = 30) -> bool:
    """
    Verify that dashboard is updated after test run.
    Waits up to max_wait seconds and checks multiple times.
    """
    print(f"\n[VERIFY] Checking if dashboard is updated for '{test_name}'...")
    
    for attempt in range(1, max_wait + 1):
        # Refresh dashboard first
        refresh_dashboard()
        time.sleep(2)  # Wait for file to be written
        
        # Check status
        status_info = check_test_status_in_dashboard(test_name)
        
        if status_info['found']:
            print(f"[OK] Test found in dashboard with status: {status_info['status']}")
            
            # Verify status matches test result
            if test_success and status_info['status'] == 'PASS':
                print(f"[VERIFIED] Dashboard correctly shows PASS for successful test")
                return True
            elif not test_success and status_info['status'] == 'FAIL':
                print(f"[VERIFIED] Dashboard correctly shows FAIL for failed test")
                return True
            else:
                print(f"[WARNING] Status mismatch: Test {'PASSED' if test_success else 'FAILED'}, Dashboard shows {status_info['status']}")
                return False
        else:
            if attempt < max_wait:
                print(f"[WAIT] Dashboard not updated yet (attempt {attempt}/{max_wait}), waiting...")
                time.sleep(2)
            else:
                print(f"[FAILED] Dashboard not updated after {max_wait} seconds")
                print(f"         Message: {status_info['message']}")
                return False
    
    return False


def main():
    """Main function to run tests and verify dashboard updates."""
    print("="*80)
    print("Test Execution and Dashboard Verification")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'employer': [],
        'jobseeker': [],
        'benchsale': []
    }
    
    total_tests = sum(len(tests) for tests in TEST_CASES.values())
    current_test = 0
    
    # Run tests by category
    for category in ['employer', 'jobseeker', 'benchsale']:
        print(f"\n{'#'*80}")
        print(f"# Running {category.upper()} Tests")
        print(f"{'#'*80}\n")
        
        for test_name in TEST_CASES[category]:
            current_test += 1
            print(f"\n[{current_test}/{total_tests}] Processing {category} test: {test_name}")
            
            # Run test
            test_success, test_output = run_test(test_name)
            
            # Wait a bit for logs to be written
            time.sleep(3)
            
            # Verify dashboard update
            dashboard_updated = verify_dashboard_update(test_name, test_success)
            
            # Record result
            result = {
                'test_name': test_name,
                'category': category,
                'test_success': test_success,
                'dashboard_updated': dashboard_updated,
                'timestamp': datetime.now().isoformat()
            }
            results[category].append(result)
            
            # Print summary
            print(f"\n[SUMMARY] Test: {test_name}")
            print(f"          Test Result: {'PASSED' if test_success else 'FAILED'}")
            print(f"          Dashboard Updated: {'YES' if dashboard_updated else 'NO'}")
            print()
            
            # Wait before next test
            time.sleep(2)
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    total_passed = 0
    total_failed = 0
    dashboard_ok = 0
    dashboard_failed = 0
    
    for category, category_results in results.items():
        print(f"\n{category.upper()} Tests:")
        for result in category_results:
            status = "PASS" if result['test_success'] else "FAIL"
            dash = "OK" if result['dashboard_updated'] else "NO UPDATE"
            print(f"  {result['test_name']}: Test={status}, Dashboard={dash}")
            
            if result['test_success']:
                total_passed += 1
            else:
                total_failed += 1
            
            if result['dashboard_updated']:
                dashboard_ok += 1
            else:
                dashboard_failed += 1
    
    print(f"\n{'='*80}")
    print(f"Total Tests: {total_tests}")
    print(f"Tests Passed: {total_passed}")
    print(f"Tests Failed: {total_failed}")
    print(f"Dashboard Updates: {dashboard_ok} OK, {dashboard_failed} Failed")
    print(f"{'='*80}\n")
    
    # Save results to file
    results_file = PROJECT_ROOT / 'test_verification_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_file}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test execution stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
