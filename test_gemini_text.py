#!/usr/bin/env python3
"""Test if Gemini models work with simple text."""

import requests
import json
import os

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "simple"

def main():
    """Test Gemini models with simple text."""
    print("🚀 GEMINI TEXT TEST")
    print("="*60)
    
    test_cases = [
        {
            "name": "Gemini 2.0 Flash Experimental",
            "model": "gemini:gemini-2.0-flash-exp",
        },
        {
            "name": "Gemini 1.5 Flash", 
            "model": "gemini:gemini-1.5-flash",
        },
        {
            "name": "OpenAI GPT-4o (control)",
            "model": "openai:gpt-4o",
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {test_case['name']}...")
        
        payload = {
            "message_content": "Hello! Can you respond to this simple test message?",
            "message_limit": 100,
            "user": {
                "phone_number": "+555197285829",
                "email": "test@example.com",
                "user_data": {
                    "name": "Test User",
                    "source": "api"
                }
            },
            "message_type": "text",
            "session_name": f"test-{test_case['name'].lower().replace(' ', '-')}",
            "preserve_system_prompt": False,
            "parameters": {"model": test_case["model"]}
        }
        
        try:
            response = requests.post(
                f"{API_URL}/agent/{AGENT_NAME}/run",
                json=payload,
                headers={
                    "x-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', '')
                print(f"   ✅ Success! Response: {message[:100]}...")
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:150]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    main()