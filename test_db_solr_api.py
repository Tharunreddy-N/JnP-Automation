#!/usr/bin/env python
"""Test db_solr_sync API endpoint"""
import requests
import json
import time

url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history'

print("Testing db_solr_sync API endpoint...")
print(f"URL: {url}")
print("-" * 80)

start_time = time.time()
try:
    r = requests.get(url, timeout=15)
    elapsed = time.time() - start_time
    
    print(f"Status Code: {r.status_code}")
    print(f"Response Time: {elapsed:.2f} seconds")
    
    if r.status_code == 200:
        data = r.json()
        print(f"Data Count: {len(data)}")
        if data:
            entry = data[0]
            print(f"\nLatest Entry:")
            print(f"  Status: {entry.get('status')}")
            print(f"  Failures: {entry.get('error_jobs_count', 0)}")
            print(f"  Total Jobs: {entry.get('total_jobs', 0)}")
            print(f"  Date: {entry.get('date')}")
            print(f"  DateTime: {entry.get('datetime', 'N/A')}")
        else:
            print("No data returned")
    else:
        print(f"Error Response: {r.text}")
        
except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 15 seconds")
    print("The update_historical_data function is taking too long")
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to API server")
    print("Make sure the server is running on port 5001")
except Exception as e:
    print(f"ERROR: {e}")
