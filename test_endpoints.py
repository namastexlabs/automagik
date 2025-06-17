#!/usr/bin/env python3
"""Test script for async-code compatibility endpoints."""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8002"
API_KEY = "namastex888"
HEADERS = {"x-api-key": API_KEY}

def test_endpoint(path, method="GET", data=None):
    """Test an endpoint and return the response."""
    url = f"{BASE_URL}{path}"
    print(f"Testing {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        else:
            print(f"Unsupported method: {method}")
            return None
            
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response text: {response.text}")
        print("-" * 50)
        return response
    except Exception as e:
        print(f"Error: {e}")
        print("-" * 50)
        return None

def main():
    """Test all async-code compatibility endpoints."""
    print("Testing Async-Code Compatibility Endpoints")
    print("=" * 50)
    
    # Test root health endpoint (should work)
    test_endpoint("/health")
    
    # Test async-code endpoints
    test_endpoint("/api/v1/health")
    test_endpoint("/api/v1/projects")
    test_endpoint("/api/v1/tasks")
    
    # Test with invalid task ID
    test_endpoint("/api/v1/tasks/invalid-id/status")
    
    # Test task creation (should fail with 501)
    task_data = {
        "agent": "builder",
        "prompt": "Test task",
        "max_turns": 5
    }
    test_endpoint("/api/v1/tasks", "POST", task_data)

if __name__ == "__main__":
    main()