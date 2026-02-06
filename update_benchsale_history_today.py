"""
Manually update BenchSale history for today's failed tests
This script adds entries for tests that failed during setup (before they could be logged)
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.log_history_api import load_historical_data, save_historical_data

# List of admin tests that failed today (from the test run)
failed_tests = [
    'test_t1_01_admin_verification_of_favourite_button_under_companies_in_benchsale',
    'test_t1_02_admin_verification_of_adding_recruiter_in_benchsale',
    'test_t1_03_admin_verification_of_adding_candidates_in_benchsale',
    'test_t1_04_admin_verification_of_allocating_candidate_under_recruiter_in_benchsale',
    'test_t1_05_admin_verification_of_sources_in_benchsale',
    'test_t1_08_admin_verification_of_inactivating_and_activating_recruiter_in_benchsale',
    'test_t1_09_admin_verification_of_inactivating_and_activating_candidate_in_benchsale',
    'test_t1_10_admin_verification_of_deleting_a_recruiter_in_benchsale',
    'test_t1_11_admin_verification_of_deleting_a_candidate_in_benchsale',
    'test_t1_12_admin_verification_of_allocating_candidate_under_recruiter_and_verify_in_recruiter_profile',
    'test_t1_13_admin_verification_of_candidates_in_submission_job_flow'
]

module = 'benchsale_admin'
today = datetime.now().strftime('%Y-%m-%d')
current_time = datetime.now().isoformat()

# Load existing history
history = load_historical_data(module)

print(f"Updating history for {len(failed_tests)} failed tests on {today}...")

for test_name in failed_tests:
    if test_name not in history:
        history[test_name] = []
    
    # Remove any existing entry for today
    history[test_name] = [e for e in history[test_name] if e.get('date') != today]
    
    # Create new entry for today's failure
    new_entry = {
        'test_name': test_name,
        'status': 'FAIL',
        'date': today,
        'datetime': current_time,
        'start_time': datetime.now().strftime('%Y%m%d %H:%M:%S'),
        'end_time': '',
        'running_time': 'N/A',
        'line_no': 0,
        'error_jobs_count': 0,
        'error_jobs': [],
        'failure_message': 'Test failed during setup: Email input not found during login',
        'error_details': 'Error during Playwright login: Email input not found (tried name/email/type/email/:r0:)'
    }
    
    # Add at the beginning (most recent first)
    history[test_name].insert(0, new_entry)
    
    # Keep only last 7 days
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    history[test_name] = [e for e in history[test_name] if e.get('date', '') >= cutoff_date]
    
    print(f"  Added/Updated: {test_name} - FAIL")

# Save updated history
save_historical_data(module, history)

print(f"\n[OK] History updated successfully for {module}")
print(f"  Total tests updated: {len(failed_tests)}")
print(f"  Date: {today}")
