#!/usr/bin/env python3
"""Test audio functionality by overriding the agent model to use Gemini."""

import asyncio
import requests
import json
import base64
import os

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "simple"

def main():
    """Test audio with model override to Gemini."""
    print(f"🚀 AUDIO TEST WITH MODEL OVERRIDE - {AGENT_NAME.upper()}")
    print("="*60)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    # Get small sample of audio for testing (first 1MB)
    with open(audio_file, "rb") as f:
        small_audio = f.read(1024*1024)  # 1MB sample
    
    audio_base64 = base64.b64encode(small_audio).decode('utf-8')
    audio_data = f"data:audio/wav;base64,{audio_base64}"
    
    # Test different ways to override the model
    test_cases = [
        {
            "name": "Gemini 2.0 Flash Experimental",
            "parameters": {"model": "gemini:gemini-2.0-flash-exp"},
        },
        {
            "name": "Gemini 1.5 Flash", 
            "parameters": {"model": "gemini:gemini-1.5-flash"},
        },
        {
            "name": "GPT-4o (for comparison)",
            "parameters": {"model": "openai:gpt-4o"},
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing with {test_case['name']}...")
        
        payload = {
            "message_content": "What do you hear in this audio file? Please transcribe what is said.",
            "message_limit": 100,
            "user": {
                "phone_number": "+555197285829",
                "email": "test@example.com",
                "user_data": {
                    "name": "Test User",
                    "source": "api"
                }
            },
            "message_type": "audio",
            "session_name": f"test-audio-{test_case['name'].lower().replace(' ', '-')}",
            "preserve_system_prompt": False,
            "media_contents": [
                {
                    "mime_type": "audio/wav",
                    "data": audio_data
                }
            ],
            "parameters": test_case["parameters"]
        }
        
        try:
            response = requests.post(
                f"{API_URL}/agent/{AGENT_NAME}/run",
                json=payload,
                headers={
                    "x-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', '')
                
                if 'Error running agent' in message:
                    print(f"   ❌ Model error: {message[:150]}...")
                else:
                    print(f"   ✅ Success! Response: {message[:150]}...")
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n{'='*60}")
    print("Test completed!")


if __name__ == "__main__":
    main()