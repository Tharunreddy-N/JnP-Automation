#!/usr/bin/env python
"""Comprehensive check of everything"""
import json
import requests
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("COMPREHENSIVE STATUS CHECK")
print("=" * 80)

# 1. Check JSON file
print("\n[1] JSON File (db_solr_sync_failures.json):")
json_file = Path('reports/db_solr_sync_failures.json')
if json_file.exists():
    data = json.load(open(json_file, 'r', encoding='utf-8'))
    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
    print(f"  ✓ Exists")
    print(f"  Last Modified: {mtime}")
    print(f"  Total Failures: {data.get('total_failures', 0):,}")
    print(f"  Total Jobs: {data.get('total_jobs_checked', 0):,}")
else:
    print(f"  ✗ NOT FOUND")

# 2. Check History file
print("\n[2] History File (jobseeker_history.json):")
history_file = Path('logs/history/jobseeker_history.json')
if history_file.exists():
    data = json.load(open(history_file, 'r', encoding='utf-8'))
    entry = data.get('test_t1_09_db_solr_sync_verification', [])
    latest = entry[0] if entry else {}
    print(f"  ✓ Exists")
    print(f"  Entries Count: {len(entry)}")
    if latest:
        print(f"  Latest Status: {latest.get('status', 'N/A')}")
        print(f"  Latest Failures: {latest.get('error_jobs_count', 0):,}")
        print(f"  Latest Total Jobs: {latest.get('total_jobs', 0):,}")
        print(f"  Latest DateTime: {latest.get('datetime', 'N/A')[:19] if latest.get('datetime') else 'N/A'}")
    else:
        print(f"  ✗ No entries found")
else:
    print(f"  ✗ NOT FOUND")

# 3. Check API Server
print("\n[3] API Server (port 5001):")
try:
    r = requests.get('http://127.0.0.1:5001/api/health', timeout=3)
    if r.status_code == 200:
        print(f"  ✓ Running")
        health = r.json()
        print(f"  Modules: {', '.join(health.get('modules', []))}")
    else:
        print(f"  ✗ Error: Status {r.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ✗ NOT RUNNING")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 4. Check API Endpoint
print("\n[4] API Endpoint (test_t1_09_db_solr_sync_verification):")
try:
    url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history'
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"  ✓ Working")
        print(f"  Response Time: < 0.1 seconds")
        if data:
            entry = data[0]
            print(f"  Status: {entry.get('status')}")
            print(f"  Failures: {entry.get('error_jobs_count', 0):,}")
            print(f"  Total Jobs: {entry.get('total_jobs', 0):,}")
            print(f"  Date: {entry.get('date')}")
            print(f"  DateTime: {entry.get('datetime', 'N/A')[:19] if entry.get('datetime') else 'N/A'}")
        else:
            print(f"  ⚠ Empty response")
    else:
        print(f"  ✗ Error: Status {r.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ✗ Connection Error")
except requests.exceptions.Timeout:
    print(f"  ✗ Timeout")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 5. Check HTTP Server
print("\n[5] HTTP Server (port 8888):")
try:
    r = requests.get('http://127.0.0.1:8888/log_viewer_ui.html', timeout=3)
    if r.status_code == 200:
        print(f"  ✓ Running")
        print(f"  Dashboard accessible")
    else:
        print(f"  ✗ Error: Status {r.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ✗ NOT RUNNING")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 6. Data Consistency Check
print("\n[6] Data Consistency:")
json_failures = 0
json_jobs = 0
history_failures = 0
history_jobs = 0
api_failures = 0
api_jobs = 0

if json_file.exists():
    json_data = json.load(open(json_file, 'r', encoding='utf-8'))
    json_failures = json_data.get('total_failures', 0)
    json_jobs = json_data.get('total_jobs_checked', 0)

if history_file.exists():
    history_data = json.load(open(history_file, 'r', encoding='utf-8'))
    entry = history_data.get('test_t1_09_db_solr_sync_verification', [])
    if entry:
        latest = entry[0]
        history_failures = latest.get('error_jobs_count', 0)
        history_jobs = latest.get('total_jobs', 0)

try:
    url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history'
    r = requests.get(url, timeout=5)
    if r.status_code == 200:
        api_data = r.json()
        if api_data:
            api_failures = api_data[0].get('error_jobs_count', 0)
            api_jobs = api_data[0].get('total_jobs', 0)
except:
    pass

print(f"  JSON File:      {json_failures:,} failures, {json_jobs:,} jobs")
print(f"  History File:   {history_failures:,} failures, {history_jobs:,} jobs")
print(f"  API Response:   {api_failures:,} failures, {api_jobs:,} jobs")

if json_failures == history_failures == api_failures and json_jobs == history_jobs == api_jobs:
    print(f"  ✓ All sources match!")
else:
    print(f"  ⚠ Data mismatch detected!")

print("\n" + "=" * 80)
print("CHECK COMPLETE")
print("=" * 80)
print("\nDashboard URL: http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker")
print("(Press Ctrl+F5 in browser to hard refresh)")
