#!/usr/bin/env python
"""Seriously verify if the data is current or old"""
import json
from pathlib import Path
from datetime import datetime, timedelta

print("=" * 80)
print("SERIOUS VERIFICATION: Is This Current or Old Data?")
print("=" * 80)

json_file = Path('reports/db_solr_sync_failures.json')

if not json_file.exists():
    print("\nERROR: JSON file not found!")
    print("This means the test has NOT run yet or the file was deleted.")
    exit(1)

# Get file modification time
mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
now = datetime.now()
age = now - mtime

print(f"\n1. FILE TIMESTAMP CHECK:")
print(f"   JSON File Last Modified: {mtime}")
print(f"   Current Time: {now}")
print(f"   Age: {age}")
print(f"   Hours Ago: {age.total_seconds()/3600:.2f} hours")
print(f"   Days Ago: {age.days} days")

# Read JSON data
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

total_jobs = data.get('total_jobs_checked', data.get('total_jobs_available', 0))
total_failures = data.get('total_failures', 0)
test_date = data.get('test_date', 'N/A')
last_updated = data.get('last_updated', 'N/A')

print(f"\n2. JSON DATA CONTENT:")
print(f"   Total Jobs Checked: {total_jobs:,}")
print(f"   Total Failures: {total_failures}")
print(f"   Test Date in JSON: {test_date}")
print(f"   Last Updated in JSON: {last_updated}")

# Check if data is recent (within last 24 hours)
is_recent = age.total_seconds() < 86400  # 24 hours

print(f"\n3. DATA FRESHNESS ANALYSIS:")
if is_recent:
    print(f"   Status: RECENT DATA (modified within last 24 hours)")
    print(f"   This is CURRENT data, not old data.")
else:
    print(f"   Status: OLD DATA (modified more than 24 hours ago)")
    print(f"   This data is {age.days} days old.")
    print(f"   WARNING: This might be outdated!")

# Check database for actual current job count (last 24 hours)
print(f"\n4. DATABASE VERIFICATION:")
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from tests.jobseeker.test_t1_09_db_solr_sync import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get jobs modified in last 24 hours
    query = """
        SELECT COUNT(*) as count
        FROM jobs
        WHERE modified_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        AND status = 1
    """
    cursor.execute(query)
    result = cursor.fetchone()
    db_job_count = result[0] if result else 0
    
    print(f"   Current DB Jobs (last 24h): {db_job_count:,}")
    print(f"   JSON Jobs Checked: {total_jobs:,}")
    
    if abs(db_job_count - total_jobs) < 100:
        print(f"   Status: MATCH - Data is current!")
    else:
        diff = db_job_count - total_jobs
        print(f"   Status: MISMATCH - Difference of {diff:,} jobs")
        print(f"   This suggests the JSON data might be outdated.")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"   Error checking database: {e}")
    print(f"   Cannot verify against current DB state")

# Check history file
print(f"\n5. HISTORY FILE CHECK:")
try:
    sys.path.insert(0, str(Path(__file__).parent / 'utils'))
    from log_history_api import load_historical_data
    
    history = load_historical_data('jobseeker')
    test_name = 'test_t1_09_db_solr_sync_verification'
    
    if test_name in history and history[test_name]:
        latest = history[test_name][0]
        hist_date = latest.get('date', 'N/A')
        hist_datetime = latest.get('datetime', 'N/A')
        hist_status = latest.get('status', 'N/A')
        hist_jobs = latest.get('total_jobs', 0)
        hist_failures = latest.get('error_jobs_count', 0)
        
        print(f"   History Date: {hist_date}")
        print(f"   History DateTime: {hist_datetime}")
        print(f"   History Status: {hist_status}")
        print(f"   History Jobs: {hist_jobs:,}")
        print(f"   History Failures: {hist_failures}")
        
        # Compare
        if hist_jobs == total_jobs and hist_failures == total_failures:
            print(f"   Status: History matches JSON - Data is consistent")
        else:
            print(f"   Status: History and JSON differ!")
            print(f"   This might indicate data inconsistency")
except Exception as e:
    print(f"   Error checking history: {e}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

# Final verdict
print(f"\nFINAL VERDICT:")
if is_recent and age.total_seconds() < 3600:  # Less than 1 hour
    print(f"   This is CURRENT data (modified less than 1 hour ago)")
elif is_recent:
    print(f"   This is RECENT data (modified within last 24 hours)")
    print(f"   But it's {age.total_seconds()/3600:.1f} hours old")
    print(f"   Consider running a fresh test to get latest data")
else:
    print(f"   This is OLD data (modified {age.days} days ago)")
    print(f"   You should run a fresh test to get current data")

print("\n")
