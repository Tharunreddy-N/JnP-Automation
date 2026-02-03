#!/usr/bin/env python
"""Verify current database state vs JSON data"""
import json
from pathlib import Path
from datetime import datetime
from utils.connections import connections
import mysql.connector

print("=" * 80)
print("DATABASE vs JSON VERIFICATION")
print("=" * 80)

# Get JSON data
json_file = Path('reports/db_solr_sync_failures.json')
if not json_file.exists():
    print("ERROR: JSON file not found!")
    exit(1)

json_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
with open(json_file, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

json_jobs = json_data.get('total_jobs_checked', json_data.get('total_jobs_available', 0))
json_failures = json_data.get('total_failures', 0)

print(f"\nJSON File Data:")
print(f"  Last Modified: {json_mtime}")
print(f"  Total Jobs: {json_jobs:,}")
print(f"  Total Failures: {json_failures}")

# Get current DB data
print(f"\nChecking Current Database State...")
try:
    creds = connections()
    if not creds:
        print("ERROR: Failed to get credentials")
        exit(1)
    
    mysql_cred = creds.get('mysql_cred')
    if not mysql_cred:
        print("ERROR: MySQL credentials not found")
        exit(1)
    
    conn = mysql.connector.connect(
        host=mysql_cred['host'],
        user=mysql_cred['user'],
        password=mysql_cred['password'],
        database="jobsnprofiles_2022"
    )
    cursor = conn.cursor(dictionary=True)
    
    # Get jobs modified in last 24 hours
    query = """
        SELECT COUNT(*) as count
        FROM jobsnprofiles_2022.jnp_jobs 
        WHERE modified >= NOW() - INTERVAL 1 DAY
        AND status = 1
    """
    cursor.execute(query)
    result = cursor.fetchone()
    db_job_count = result['count'] if result else 0
    
    print(f"\nCurrent Database State:")
    print(f"  Jobs Modified (last 24h): {db_job_count:,}")
    
    # Compare
    print(f"\nComparison:")
    diff = db_job_count - json_jobs
    print(f"  JSON Jobs: {json_jobs:,}")
    print(f"  DB Jobs (current): {db_job_count:,}")
    print(f"  Difference: {diff:,} jobs")
    
    if abs(diff) < 100:
        print(f"\n  Status: MATCH - JSON data is CURRENT!")
        print(f"  The data is accurate and up-to-date.")
    elif diff > 0:
        print(f"\n  Status: JSON is OLD - Database has {diff:,} MORE jobs now")
        print(f"  This means new jobs were added since the test ran.")
        print(f"  You should run a fresh test to get current data.")
    else:
        print(f"\n  Status: JSON has MORE jobs than current DB")
        print(f"  This might indicate jobs were deleted or status changed.")
    
    # Check when test was run
    age_hours = (datetime.now() - json_mtime).total_seconds() / 3600
    print(f"\nTest Age:")
    print(f"  Test ran: {age_hours:.2f} hours ago")
    if age_hours < 1:
        print(f"  Status: VERY RECENT - Data is current")
    elif age_hours < 6:
        print(f"  Status: RECENT - Data is still relevant")
    elif age_hours < 24:
        print(f"  Status: MODERATE - Consider running fresh test")
    else:
        print(f"  Status: OLD - Should run fresh test")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\nERROR: Could not check database: {e}")
    print(f"Cannot verify against current DB state")

print("\n" + "=" * 80)
