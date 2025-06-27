#!/usr/bin/env python3
"""Test multimodal functionality for discord agent."""

import asyncio
import requests
import json
import base64
import os

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "discord"

# Sample image data (base64 encoded 1x1 pixel PNG for testing)
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def send_message_with_image(message: str, session_name: str, session_id: str = None):
    """Send a message with image to the API."""
    
    # Prepare image content
    image_data = f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}"
    
    payload = {
        "message_content": message,
        "message_limit": 100,
        "user": {
            "phone_number": "+555197285829",
            "email": "test@example.com",
            "user_data": {
                "name": "Test User",
                "source": "discord"
            }
        },
        "message_type": "image",
        "session_name": session_name,
        "preserve_system_prompt": False,
        "media_contents": [
            {
                "mime_type": "image/png",
                "data": image_data
            }
        ]
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
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}


def main():
    """Run multimodal test for discord agent."""
    print(f"🚀 MULTIMODAL TEST - {AGENT_NAME.upper()}")
    print("="*60)
    
    session_name = f"test-{AGENT_NAME}-multimodal"
    
    # Send image with test message
    print(f"\n1. Sending image to {AGENT_NAME} agent...")
    result = send_message_with_image(
        "Can you help me analyze this image?",
        session_name
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
        
    session_id = result.get('session_id')
    print(f"✅ Response received from session: {session_id}")
    print(f"Response: {result.get('message', '')[:200]}...")
    
    # Check metadata for any additional information
    metadata = result.get('metadata', {})
    if metadata:
        print(f"Metadata: {metadata}")


if __name__ == "__main__":
    main()