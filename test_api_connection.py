#!/usr/bin/env python
"""Test API connection"""
import requests

try:
    # Test health endpoint
    r = requests.get('http://127.0.0.1:5001/api/health', timeout=5)
    print(f"API Health Status: {r.status_code}")
    print(f"Response: {r.json()}")
    
    # Test db_solr_sync history endpoint
    url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history'
    r = requests.get(url, timeout=10)
    print(f"\nTest History API Status: {r.status_code}")
    data = r.json()
    print(f"Data Count: {len(data)}")
    if data:
        latest = data[0]
        print(f"Latest Entry:")
        print(f"  Status: {latest.get('status')}")
        print(f"  Failures: {latest.get('error_jobs_count', 0)}")
        print(f"  Total Jobs: {latest.get('total_jobs', 0)}")
        print(f"  Date: {latest.get('date')}")
        print(f"  DateTime: {latest.get('datetime', 'N/A')}")
    else:
        print("No data returned")
        
except requests.exceptions.ConnectionError:
    print("ERROR: API Server is not running on port 5001")
    print("Please start it with: python -m utils.log_history_api")
except Exception as e:
    print(f"ERROR: {e}")
