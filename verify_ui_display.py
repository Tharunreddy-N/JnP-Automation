"""Verify UI and history display for db_solr_sync test"""
import json
from pathlib import Path

print("="*80)
print("VERIFYING UI AND HISTORY DISPLAY")
print("="*80)

# Check JSON report
json_path = Path('reports/db_solr_sync_failures.json')
json_total = 0
json_failures = 0
if json_path.exists():
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    json_total = json_data.get('total_jobs_checked', 0)
    json_failures = json_data.get('total_failures', 0)

# Check History
history_path = Path('logs/history/jobseeker_history.json')
history_total = 0
history_failures = 0
history_status = 'N/A'
history_date = 'N/A'
history_failure_msg = 'N/A'
if history_path.exists():
    with open(history_path, 'r', encoding='utf-8') as f:
        history_data = json.load(f)
    
    test_entry = history_data.get('test_t1_09_db_solr_sync_verification', [])
    if test_entry:
        latest = test_entry[0] if isinstance(test_entry, list) else test_entry
        history_total = latest.get('total_jobs', 0)
        history_failures = latest.get('error_jobs_count', 0)
        history_status = latest.get('status', 'N/A')
        history_date = latest.get('date', 'N/A')
        history_failure_msg = latest.get('failure_message', 'N/A')
        if history_failure_msg == 'N/A' or not history_failure_msg:
            history_failure_msg = 'NOT SET'

print("\n[1. JSON REPORT DATA]")
print(f"   Total Jobs: {json_total}")
print(f"   Failures: {json_failures}")

print("\n[2. HISTORY FILE DATA]")
print(f"   Status: {history_status}")
print(f"   Date: {history_date}")
print(f"   Total Jobs: {history_total}")
print(f"   Failures: {history_failures}")
print(f"   Failure Message: {history_failure_msg[:100] if history_failure_msg != 'NOT SET' else 'NOT SET'}...")

print("\n[3. DATA MATCHING]")
print(f"   Total Jobs Match: {json_total == history_total} ({'OK' if json_total == history_total else 'MISMATCH'})")
print(f"   Failures Match: {json_failures == history_failures} ({'OK' if json_failures == history_failures else 'MISMATCH'})")
print(f"   Failure Message Set: {history_failure_msg != 'NOT SET' and history_failure_msg != 'N/A'} ({'OK' if history_failure_msg != 'NOT SET' and history_failure_msg != 'N/A' else 'MISSING'})")

print("\n[4. UI DISPLAY CHECK]")
print("   Dashboard should show:")
print(f"   - Status: {history_status}")
print(f"   - Total Jobs: {history_total}")
print(f"   - Failures: {history_failures}")
if history_failure_msg != 'NOT SET' and history_failure_msg != 'N/A':
    print(f"   - Failure Message: {history_failure_msg[:80]}...")
else:
    print("   - Failure Message: [MISSING - needs to be set]")

print("\n" + "="*80)
if json_total == history_total and json_failures == history_failures:
    if history_failure_msg != 'NOT SET' and history_failure_msg != 'N/A':
        print("[OK] All data is correct and failure message is set!")
    else:
        print("[WARNING] Data matches but failure_message is missing in history")
else:
    print("[ERROR] Data mismatch between JSON and History!")
