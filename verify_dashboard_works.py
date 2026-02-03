#!/usr/bin/env python
"""Verify dashboard actually works by testing the exact API call the browser makes"""
import requests
import json
from pathlib import Path

print("=" * 80)
print("VERIFYING DASHBOARD API CALL")
print("=" * 80)

# Test the exact URL the browser would call
test_case = "test_t1_09_db_solr_sync_verification"
module_id = "jobseeker"
cache_buster = f"?_refresh=1234567890&_force=1"  # FIX: Use ? for first parameter
url = f"http://127.0.0.1:5001/api/modules/{module_id}/test-cases/{test_case}/history{cache_buster}"

print(f"\nTesting URL: {url}")

try:
    response = requests.get(url, timeout=30, headers={
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Accept': 'application/json'
    })
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        if 'access-control' in key.lower() or 'content-type' in key.lower():
            print(f"  {key}: {value}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse Data:")
        print(f"  Count: {len(data)}")
        if data:
            entry = data[0]
            print(f"  Status: {entry.get('status')}")
            print(f"  Failures: {entry.get('error_jobs_count', 0):,}")
            print(f"  Total Jobs: {entry.get('total_jobs', 0):,}")
            print(f"  Date: {entry.get('date')}")
            print(f"  DateTime: {entry.get('datetime', 'N/A')[:19] if entry.get('datetime') else 'N/A'}")
            print(f"\n✅ API is working correctly!")
            print(f"✅ Dashboard should be able to load this data")
        else:
            print(f"\n⚠️ Empty response - no data returned")
    else:
        print(f"\n❌ Error: Status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print(f"\n❌ ERROR: Request timed out after 30 seconds")
    print(f"This might be why the dashboard shows 'API Connection Error'")
except requests.exceptions.ConnectionError:
    print(f"\n❌ ERROR: Could not connect to API server")
    print(f"Is the API server running on port 5001?")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
