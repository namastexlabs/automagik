#!/usr/bin/env python3
"""Debug audio functionality to see actual error responses."""

import asyncio
import requests
import json
import base64
import os

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "simple"

def encode_audio_file(file_path: str) -> str:
    """Encode audio file to base64."""
    with open(file_path, "rb") as audio_file:
        audio_data = audio_file.read()
        return base64.b64encode(audio_data).decode('utf-8')

def main():
    """Debug audio test with detailed error reporting."""
    print(f"🚀 AUDIO DEBUG TEST - {AGENT_NAME.upper()}")
    print("="*60)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    # Get file size
    file_size = os.path.getsize(audio_file)
    print(f"📁 Audio file size: {file_size / (1024*1024):.2f} MB")
    
    # Try with smaller file first - encode just first 1MB to test
    with open(audio_file, "rb") as f:
        small_audio = f.read(1024*1024)  # 1MB
    
    audio_base64 = base64.b64encode(small_audio).decode('utf-8')
    audio_data = f"data:audio/wav;base64,{audio_base64}"
    
    payload = {
        "message_content": "What do you hear in this audio file?",
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
        "session_name": "test-audio-debug",
        "preserve_system_prompt": False,
        "media_contents": [
            {
                "mime_type": "audio/wav",
                "data": audio_data
            }
        ]
    }
    
    try:
        print(f"📤 Sending {len(small_audio)} bytes of audio data...")
        response = requests.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
        print(f"📨 Response status: {response.status_code}")
        print(f"📨 Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"❌ Error response body: {response.text}")
        else:
            result = response.json()
            print(f"✅ Success!")
            print(f"Response: {result.get('message', '')[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"Raw response: {response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()