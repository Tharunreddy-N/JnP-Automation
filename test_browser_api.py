#!/usr/bin/env python
"""Test API from browser perspective"""
import requests
import json

def test_api():
    # Test the exact URL the browser would call
    url = 'http://127.0.0.1:5001/api/modules/jobseeker/test-cases/test_t1_09_db_solr_sync_verification/history?_refresh=1234567890&_force=1'
    
    print("=" * 80)
    print("TESTING API FROM BROWSER PERSPECTIVE")
    print("=" * 80)
    print(f"\nURL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower() or 'content-type' in key.lower():
                print(f"  {key}: {value}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse Data Count: {len(data)}")
            if data:
                entry = data[0]
                print(f"\nLatest Entry:")
                print(f"  Status: {entry.get('status')}")
                print(f"  Failures: {entry.get('error_jobs_count', 0):,}")
                print(f"  Total Jobs: {entry.get('total_jobs', 0):,}")
                print(f"  Date: {entry.get('date')}")
                print(f"  DateTime: {entry.get('datetime', 'N/A')[:19]}")
            else:
                print("\nWARNING: Empty response!")
        else:
            print(f"\nERROR: Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to API server")
        print("Is the API server running on port 5001?")
    except requests.exceptions.Timeout:
        print("\nERROR: Request timed out")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_api()
