#!/usr/bin/env python
"""Verify db_solr_sync test cleanup and data"""
import json
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("VERIFICATION: db_solr_sync Test Data Cleanup")
print("=" * 80)

# Check JSON file
json_file = Path('reports/db_solr_sync_failures.json')
if json_file.exists():
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    print(f"\nJSON File Found:")
    print(f"   Total Jobs Checked: {json_data.get('total_jobs_checked', 0):,}")
    print(f"   Total Failures: {json_data.get('total_failures', 0):,}")
    print(f"   File Modified: {datetime.fromtimestamp(json_file.stat().st_mtime)}")
else:
    print("\nJSON file not found (test may still be running)")

# Check history file
hist_file = Path('logs/history/jobseeker_history.json')
test_key = 'test_t1_09_db_solr_sync_verification'

if hist_file.exists():
    with open(hist_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if test_key in history:
        entries = history[test_key]
        print(f"\nHistory File Status:")
        print(f"   Total Entries: {len(entries)}")
        
        if len(entries) == 0:
            print("   PASS: No old data (history is clean)")
        elif len(entries) == 1:
            latest = entries[0]
            print(f"   PASS: Only ONE entry (latest data only)")
            print(f"   Latest Entry Details:")
            print(f"      - Date: {latest.get('date', 'N/A')}")
            print(f"      - DateTime: {latest.get('datetime', 'N/A')}")
            print(f"      - Status: {latest.get('status', 'N/A')}")
            print(f"      - Total Jobs: {latest.get('total_jobs', 0):,}")
            print(f"      - Error Count: {latest.get('error_jobs_count', 0):,}")
        else:
            print(f"   FAIL: Multiple entries found ({len(entries)})")
            print("   Old data is NOT being cleaned!")
            print("\n   All entries:")
            for i, entry in enumerate(entries, 1):
                print(f"      Entry {i}: Date={entry.get('date')}, Status={entry.get('status')}, Jobs={entry.get('total_jobs', 0)}")
            
            # Show which one is latest
            def sort_key(e):
                return e.get('datetime') or e.get('date', '')
            sorted_entries = sorted(entries, key=sort_key, reverse=True)
            print(f"\n   Latest entry (should be kept): Date={sorted_entries[0].get('date')}")
    else:
        print(f"\nTest key '{test_key}' not found in history")
        print("   (Test may not have run yet or passed with no failures)")
else:
    print("\nHistory file not found")

# Check if conditions are working
print(f"\nCondition Verification:")
print(f"   1. Old data deletion: {'Working' if hist_file.exists() and test_key in history and len(history[test_key]) <= 1 else 'Not Working'}")
print(f"   2. Only latest data: {'Working' if hist_file.exists() and test_key in history and len(history[test_key]) == 1 else 'Not Working'}")
print(f"   3. JSON file exists: {'Working' if json_file.exists() else 'Not Working'}")

print("\n" + "=" * 80)
print("Verification Complete!")
print("=" * 80)
