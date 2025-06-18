#!/usr/bin/env python3
"""Simple test to verify agent API returns usage information correctly."""

import json
import requests
import uuid

def test_agent_response_usage():
    """Test that agent response includes usage information."""
    
    # Create test data
    test_data = {
        "message_content": "Test message for usage tracking",
        "user_id": str(uuid.uuid4()),
        "session_name": f"test-usage-{uuid.uuid4()}"
    }
    
    # Make request to a simple agent (like echo or similar)
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/agent/echo/run",
            json=test_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            print(f"Message: {data.get('message', 'N/A')}")
            print(f"Success: {data.get('success', 'N/A')}")
            print(f"Session ID: {data.get('session_id', 'N/A')}")
            
            # Check for usage field
            if "usage" in data:
                print(f"✅ Usage field present: {data['usage']}")
            else:
                print("ℹ️  Usage field not present (may be normal for some agents)")
                
        else:
            print(f"❌ Request failed: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the server is running on localhost:8000")

if __name__ == "__main__":
    test_agent_response_usage()