#!/usr/bin/env python3
"""Test audio functionality for simple agent using Gemini model."""

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

def send_message_with_audio_gemini(message: str, session_name: str, audio_path: str, session_id: str = None):
    """Send a message with audio to the API using Gemini model."""
    
    # Encode audio file
    audio_base64 = encode_audio_file(audio_path)
    audio_data = f"data:audio/wav;base64,{audio_base64}"
    
    payload = {
        "message_content": message,
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
        "session_name": session_name,
        "preserve_system_prompt": False,
        "media_contents": [
            {
                "mime_type": "audio/wav",
                "data": audio_data
            }
        ],
        # Override to use Gemini model for audio support
        "parameters": {
            "model": "gemini:gemini-2.0-flash-exp"
        }
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=60.0  # Longer timeout for audio processing
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Run audio test for simple agent with Gemini."""
    print(f"🚀 AUDIO TEST - {AGENT_NAME.upper()} (GEMINI)")
    print("="*60)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    # Get file size
    file_size = os.path.getsize(audio_file)
    print(f"📁 Audio file size: {file_size / (1024*1024):.2f} MB")
    
    session_name = f"test-{AGENT_NAME}-audio-gemini"
    
    # Send audio for analysis using Gemini
    print(f"\n1. Sending audio to {AGENT_NAME} agent (using Gemini)...")
    result = send_message_with_audio_gemini(
        "Can you help me understand what's being said in this audio?",
        session_name,
        audio_file
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
        
    session_id = result.get('session_id')
    print(f"✅ Response received from session: {session_id}")
    print(f"Response: {result.get('message', '')[:400]}...")
    
    # Check metadata for any additional information
    metadata = result.get('metadata', {})
    if metadata:
        print(f"Metadata: {metadata}")


if __name__ == "__main__":
    main()