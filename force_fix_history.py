#!/usr/bin/env python
"""Force fix history for db_solr_sync test"""
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent / 'utils'))
from log_history_api import load_historical_data, save_historical_data

MODULE_NAME = 'jobseeker'
TEST_CASE_NAME = 'test_t1_09_db_solr_sync_verification'
JSON_FAILURE_PATH = Path('reports/db_solr_sync_failures.json')

print("=" * 80)
print("FORCE FIX HISTORY FOR db_solr_sync")
print("=" * 80)

# Load history
history = load_historical_data(MODULE_NAME)

# Read JSON file
if not JSON_FAILURE_PATH.exists():
    print("ERROR: JSON file not found!")
    exit(1)

with open(JSON_FAILURE_PATH, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

total_failures = json_data.get('total_failures', 0)
total_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
failures_list = json_data.get('failures', [])

# Get file modification time
file_mtime = datetime.fromtimestamp(JSON_FAILURE_PATH.stat().st_mtime)
stable_datetime = file_mtime.isoformat()
test_date = file_mtime.strftime('%Y-%m-%d')

print(f"\nJSON Data:")
print(f"  Total Jobs: {total_jobs:,}")
print(f"  Total Failures: {total_failures}")
print(f"  File Modified: {file_mtime}")

# Build failure message
structured_msg = "=" * 120 + "\n"
structured_msg += "SOLR SYNC FAILURE SUMMARY\n"
structured_msg += "=" * 120 + "\n"
if total_jobs > 0:
    structured_msg += f"Total Jobs Available in DB (last 24h): {total_jobs}\n"
structured_msg += f"Jobs Actually Checked: {total_jobs}\n"
structured_msg += f"Total Failures: {total_failures}\n"
if total_failures > 0 and total_jobs > 0:
    success_rate = ((total_jobs - total_failures) / total_jobs * 100) if total_jobs > 0 else 0
    structured_msg += f"Success Rate: {success_rate:.2f}%\n"
structured_msg += "=" * 120 + "\n"
structured_msg += f"\n📄 Complete failure details saved in: reports/db_solr_sync_failures.json\n"

# Create new entry
new_entry = {
    'test_name': TEST_CASE_NAME,
    'status': 'FAIL' if total_failures > 0 else 'PASS',
    'date': test_date,
    'datetime': stable_datetime,
    'start_time': file_mtime.strftime('%Y%m%d %H:%M:%S'),
    'end_time': '',
    'running_time': 'N/A',
    'line_no': 0,
    'total_jobs': total_jobs,
    'error_jobs_count': total_failures,
    'error_jobs': [
        {
            'id': str(f.get('id', 'N/A')),
            'title': str(f.get('db_title', 'N/A'))[:100],
            'error': str(f.get('msg', 'N/A'))[:500]
        }
        for f in failures_list[:total_failures]
    ],
    'failure_message': structured_msg[:2000],
    'error_details': structured_msg[:2000]
}

# Force replace - clear all old entries
history[TEST_CASE_NAME] = [new_entry]

# Save
save_historical_data(MODULE_NAME, history)

print(f"\nHistory Updated:")
print(f"  Status: {new_entry['status']}")
print(f"  Total Jobs: {new_entry['total_jobs']:,}")
print(f"  Failures: {new_entry['error_jobs_count']}")
print(f"  DateTime: {new_entry['datetime']}")

# Verify
verify_history = load_historical_data(MODULE_NAME)
if TEST_CASE_NAME in verify_history:
    verify_entry = verify_history[TEST_CASE_NAME][0] if verify_history[TEST_CASE_NAME] else {}
    print(f"\nVerification:")
    print(f"  Status: {verify_entry.get('status')}")
    print(f"  Total Jobs: {verify_entry.get('total_jobs', 0):,}")
    print(f"  Failures: {verify_entry.get('error_jobs_count', 0)}")
    print(f"  Entries Count: {len(verify_history[TEST_CASE_NAME])}")

print("\n" + "=" * 80)
print("DONE!")
print("=" * 80)
