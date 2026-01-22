"""
Simple script to test if the always-on server is running and responding.
Run this to verify the server is accessible.
"""
import requests
import json
import sys

SERVER_URL = "http://localhost:8766"

def test_server():
    """Test if server is running and responding."""
    print("=" * 60)
    print("Testing Always-On Server Connection")
    print("=" * 60)
    
    # Test 1: Check if server is running (GET /)
    print("\n1. Testing server health check (GET /)...")
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"   [OK] Server is running!")
            print(f"   Response: {response.text}")
        else:
            print(f"   [ERROR] Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   [ERROR] Cannot connect to server at {SERVER_URL}")
        print(f"   Make sure the server is running (run START_ALWAYS_ON_SERVER.bat)")
        return False
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False
    
    # Test 2: Check server status (GET /status)
    print("\n2. Testing server status endpoint (GET /status)...")
    try:
        response = requests.get(f"{SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Status endpoint working!")
            print(f"   Server busy: {data.get('busy', 'unknown')}")
            print(f"   Queue size: {data.get('queue_size', 0)}")
        else:
            print(f"   [ERROR] Status endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    # Test 3: Test adding a test to queue (POST /add-test)
    print("\n3. Testing add test endpoint (POST /add-test)...")
    try:
        test_data = {
            "testName": "test_example_test"
        }
        response = requests.post(
            f"{SERVER_URL}/add-test",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Add test endpoint working!")
            print(f"   Response: {data.get('message', 'No message')}")
        else:
            print(f"   [ERROR] Add test endpoint returned: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    print("\n" + "=" * 60)
    print("Server connection test completed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)
