#!/usr/bin/env python
"""Check test status and progress"""
import json
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("TEST STATUS CHECK")
print("=" * 80)

# Check JSON file
json_file = Path('reports/db_solr_sync_failures.json')
if json_file.exists():
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    time_diff = datetime.now() - mtime
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nJSON File Status:")
    print(f"  Last Modified: {mtime}")
    print(f"  Time Since Last Run: {time_diff}")
    print(f"  Total Jobs Checked: {data.get('total_jobs_checked', 0):,}")
    print(f"  Total Failures: {data.get('total_failures', 0)}")
    
    if time_diff.total_seconds() < 300:  # Less than 5 minutes
        print(f"  Status: Test recently completed (within last 5 minutes)")
    elif time_diff.total_seconds() < 3600:  # Less than 1 hour
        print(f"  Status: Test completed {int(time_diff.total_seconds()/60)} minutes ago")
    else:
        print(f"  Status: Test completed {int(time_diff.total_seconds()/3600)} hours ago")
else:
    print("\nJSON file not found - Test may still be running or hasn't started yet")

# Check history
print(f"\nHistory Status:")
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent / 'utils'))
    from log_history_api import load_historical_data
    
    history = load_historical_data('jobseeker')
    test_name = 'test_t1_09_db_solr_sync_verification'
    
    if test_name in history and history[test_name]:
        latest = history[test_name][0]
        print(f"  Latest Entry Found:")
        print(f"    Date: {latest.get('date')}")
        print(f"    DateTime: {latest.get('datetime', 'N/A')}")
        print(f"    Status: {latest.get('status')}")
        print(f"    Total Jobs: {latest.get('total_jobs', 0):,}")
        print(f"    Failures: {latest.get('error_jobs_count', 0)}")
        
        # Compare with JSON
        if json_file.exists():
            json_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
            history_dt = latest.get('datetime', '')
            if history_dt:
                try:
                    hist_dt = datetime.fromisoformat(history_dt.replace('Z', '+00:00') if 'Z' in history_dt else history_dt)
                    if abs((hist_dt - json_mtime).total_seconds()) < 60:
                        print(f"  Status: History and JSON are in sync")
                    else:
                        print(f"  Status: History and JSON times differ by {abs((hist_dt - json_mtime).total_seconds())} seconds")
                except:
                    pass
    else:
        print(f"  No history entry found for {test_name}")
except Exception as e:
    print(f"  Error checking history: {e}")

print("\n" + "=" * 80)
