"""
Run all employer test cases one by one sequentially.
Each test will run completely before the next one starts.
Dashboard will be updated after each test.
"""
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent

# All employer test cases from test_employer_test_cases.py
EMPLOYER_TESTS = [
    'test_t1_01_home_page',
    'test_t1_02_home_page_verify_jobs_not_from_same_company_consecutively',
    'test_t1_03_home_page_verify_jobs_matched_with_searched_company',
    'test_t1_04_home_page_verify_job_posting_time',
    'test_t1_05_home_page_verify_book_your_demo',
    'test_t1_06_home_page_no_repetition_of_jobs_in_similar_jobs',
    'test_t2_01_post_a_job_verification_and_verification_with_job_id',
    'test_t2_02_verification_of_applicants_and_shortlisting_in_js',
    'test_t2_03_verification_of_closing_a_job_and_checking_with_job_id',
    'test_t2_04_verification_of_ai_search_with_description',
    'test_t2_06_verification_of_ai_search_without_description_and_saving_resume',
    'test_t2_12_verification_of_sending_email_to_contacts_in_emp_contacts',
    'test_t2_13_verification_of_resumes_details_matched_with_posted_jobs',
    'test_t2_14_verification_of_advanced_ai_semantic_search',
    'test_t2_15_verification_of_job_posting_displayed_in_js_dashboard_job_title',
    'test_t2_16_verification_of_job_posting_displayed_in_js_dashboard_job_id',
    'test_t2_17_verification_of_hot_list_company_daily_update',
    'test_t2_18_hotlist_company_daily_update_verification',
    'test_t2_19_hotlist_search_by_job_title',
    'test_t2_20_ai_search_with_boolean_description',
    'test_t2_21_boolean_search_initial_bar',
    'test_t2_22_hotlist_duplicate_candidates',
]


def run_test(test_name: str, test_num: int, total_tests: int):
    """Run a single test and return success status."""
    print(f"\n{'='*80}")
    print(f"[{test_num}/{total_tests}] Running: {test_name}")
    print(f"{'='*80}\n")
    
    cmd = [
        sys.executable,
        '-m', 'pytest',
        f'tests/employer/test_employer_test_cases.py::{test_name}',
        '-v',
        '--tb=short',
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            timeout=1800  # 30 minutes max per test
        )
        elapsed = time.time() - start_time
        
        status = "PASSED" if result.returncode == 0 else "FAILED"
        print(f"\n[{status}] Test '{test_name}' completed in {elapsed:.2f} seconds")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] Test '{test_name}' exceeded 30 minutes")
        return False
    except Exception as e:
        print(f"\n[ERROR] Failed to run test '{test_name}': {e}")
        return False


def refresh_dashboard():
    """Refresh dashboard to show latest results."""
    try:
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'refresh_dashboard.py')],
            cwd=PROJECT_ROOT,
            timeout=60,
            capture_output=True
        )
    except Exception:
        pass  # Don't fail if dashboard refresh fails


def main():
    """Run all employer tests sequentially."""
    print("="*80)
    print("Running All Employer Tests Sequentially")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total tests: {len(EMPLOYER_TESTS)}")
    print("="*80)
    print()
    
    results = {
        'passed': 0,
        'failed': 0,
        'total': len(EMPLOYER_TESTS)
    }
    
    for idx, test_name in enumerate(EMPLOYER_TESTS, 1):
        success = run_test(test_name, idx, len(EMPLOYER_TESTS))
        
        if success:
            results['passed'] += 1
        else:
            results['failed'] += 1
        
        # Small delay between tests
        time.sleep(2)
        
        # Refresh dashboard after each test (non-blocking)
        try:
            refresh_dashboard()
        except:
            pass
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    print("="*80)
    print()
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Check logs\\employer.log for detailed results")
    print("Check logs\\index.html for dashboard")
    print()


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
