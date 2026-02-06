"""Check UI and history data for db_solr_sync test"""
import json
from pathlib import Path

# Check JSON report
json_path = Path('reports/db_solr_sync_failures.json')
if json_path.exists():
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    print("="*80)
    print("JSON REPORT (reports/db_solr_sync_failures.json)")
    print("="*80)
    print(f"Total Jobs Available: {json_data.get('total_jobs_available', 0)}")
    print(f"Total Jobs Checked: {json_data.get('total_jobs_checked', 0)}")
    print(f"Total Failures: {json_data.get('total_failures', 0)}")
    print()

# Check History
history_path = Path('logs/history/jobseeker_history.json')
if history_path.exists():
    with open(history_path, 'r', encoding='utf-8') as f:
        history_data = json.load(f)
    
    test_entry = history_data.get('test_t1_09_db_solr_sync_verification', [])
    if test_entry:
        latest = test_entry[0] if isinstance(test_entry, list) else test_entry
        print("="*80)
        print("HISTORY FILE (logs/history/jobseeker_history.json)")
        print("="*80)
        print(f"Test Name: {latest.get('test_name', 'N/A')}")
        print(f"Status: {latest.get('status', 'N/A')}")
        print(f"Date: {latest.get('date', 'N/A')}")
        print(f"DateTime: {latest.get('datetime', 'N/A')}")
        print(f"Total Jobs: {latest.get('total_jobs', 0)}")
        print(f"Error Jobs Count: {latest.get('error_jobs_count', 0)}")
        print(f"Running Time: {latest.get('running_time', 'N/A')}")
        print()
        
        # Check if data matches
        json_total = json_data.get('total_jobs_checked', 0) if json_path.exists() else 0
        json_failures = json_data.get('total_failures', 0) if json_path.exists() else 0
        history_total = latest.get('total_jobs', 0)
        history_failures = latest.get('error_jobs_count', 0)
        
        print("="*80)
        print("DATA COMPARISON")
        print("="*80)
        print(f"JSON Total Jobs: {json_total}")
        print(f"History Total Jobs: {history_total}")
        print(f"Match: {json_total == history_total}")
        print()
        print(f"JSON Failures: {json_failures}")
        print(f"History Failures: {history_failures}")
        print(f"Match: {json_failures == history_failures}")
        print()
        
        if json_total == history_total and json_failures == history_failures:
            print("[OK] History matches JSON report - Data is correct!")
        else:
            print("[X] History does NOT match JSON report - Need to update!")
    else:
        print("No test entry found in history")
else:
    print("History file not found")
