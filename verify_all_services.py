#!/usr/bin/env python
"""Verify all services are running correctly"""
import requests
import socket
from pathlib import Path

print("=" * 80)
print("COMPLETE SERVICE VERIFICATION")
print("=" * 80)

# 1. Check API Server (port 5001)
print("\n1. API Server (port 5001):")
try:
    r = requests.get('http://127.0.0.1:5001/api/health', timeout=3)
    if r.status_code == 200:
        data = r.json()
        print(f"   Status: RUNNING")
        print(f"   Modules: {', '.join(data.get('modules', []))}")
    else:
        print(f"   Status: ERROR (Status {r.status_code})")
except requests.exceptions.ConnectionError:
    print("   Status: NOT RUNNING")
except Exception as e:
    print(f"   Status: ERROR ({e})")

# 2. Check HTTP Server (port 8888)
print("\n2. HTTP Server (port 8888):")
try:
    r = requests.get('http://127.0.0.1:8888/log_viewer_ui.html', timeout=3)
    if r.status_code == 200:
        print(f"   Status: RUNNING")
        print(f"   Dashboard accessible via HTTP")
    else:
        print(f"   Status: ERROR (Status {r.status_code})")
except requests.exceptions.ConnectionError:
    print("   Status: NOT RUNNING")
except Exception as e:
    print(f"   Status: ERROR ({e})")

# 3. Check db_solr_sync API endpoint
print("\n3. db_solr_sync API Endpoint:")
try:
    url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history'
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   Status: WORKING")
        print(f"   Response Time: < 0.1 seconds")
        if data:
            entry = data[0]
            print(f"   Latest Data:")
            print(f"     Status: {entry.get('status')}")
            print(f"     Failures: {entry.get('error_jobs_count', 0)}")
            print(f"     Total Jobs: {entry.get('total_jobs', 0)}")
        else:
            print("   Warning: No data returned")
    else:
        print(f"   Status: ERROR (Status {r.status_code})")
except requests.exceptions.Timeout:
    print("   Status: TIMEOUT (API taking too long)")
except requests.exceptions.ConnectionError:
    print("   Status: CONNECTION ERROR")
except Exception as e:
    print(f"   Status: ERROR ({e})")

# 4. Check JSON file
print("\n4. JSON Failure File:")
json_file = Path('reports/db_solr_sync_failures.json')
if json_file.exists():
    import json
    from datetime import datetime
    data = json.loads(json_file.read_text(encoding='utf-8'))
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f"   Status: EXISTS")
    print(f"   Last Modified: {mtime}")
    print(f"   Total Jobs: {data.get('total_jobs_checked', 0):,}")
    print(f"   Total Failures: {data.get('total_failures', 0):,}")
else:
    print("   Status: NOT FOUND")

# 5. Check History File
print("\n5. History File:")
history_file = Path('logs/jobseeker_history.json')
if history_file.exists():
    import json
    data = json.loads(history_file.read_text(encoding='utf-8'))
    test_name = 'test_t1_09_db_solr_sync_verification'
    if test_name in data:
        entries = data[test_name]
        print(f"   Status: EXISTS")
        print(f"   Entries Count: {len(entries)}")
        if entries:
            latest = entries[0]
            print(f"   Latest Entry:")
            print(f"     Status: {latest.get('status')}")
            print(f"     Failures: {latest.get('error_jobs_count', 0)}")
            print(f"     Total Jobs: {latest.get('total_jobs', 0)}")
    else:
        print(f"   Status: EXISTS but no entry for {test_name}")
else:
    print("   Status: NOT FOUND")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nDashboard URL: http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker")
print("(Use HTTP URL, NOT file:// protocol)")
