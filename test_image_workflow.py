#!/usr/bin/env python3
"""Test image workflow triggering for flashinho_pro agent."""

import asyncio
import requests
import json
import base64
import os

# API configuration
API_URL = "http://localhost:18881/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "flashinho_pro"

# Test conversation code
CONVERSATION_CODE = "1bl1UKm0JC"

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
            "email": "",
            "user_data": {
                "name": "Cezar Vasconcelos",
                "whatsapp_id": "555197285829@s.whatsapp.net",
                "source": "whatsapp"
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
    """Run image workflow test."""
    print("🚀 IMAGE WORKFLOW TEST")
    print("="*60)
    
    session_name = "test-image-workflow"
    
    # First authenticate
    print("\n1. Sending conversation code to authenticate...")
    auth_result = send_message_with_image(
        f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
        session_name
    )
    
    if "error" in auth_result:
        print(f"❌ Error: {auth_result['error']}")
        return
        
    session_id = auth_result.get('session_id')
    print(f"✅ Authenticated with session: {session_id}")
    print(f"Response: {auth_result.get('message', '')[:100]}...")
    
    # Send image with math problem description
    print("\n2. Sending image with math problem...")
    image_result = send_message_with_image(
        "[Cezar Vasconcelos]: Olha essa questão de matemática que não consigo resolver",
        session_name,
        session_id
    )
    
    if "error" in image_result:
        print(f"❌ Error: {image_result['error']}")
        return
        
    print(f"Response: {image_result.get('message', '')[:200]}...")
    
    # Check if workflow was triggered
    metadata = image_result.get('metadata', {})
    if metadata.get('workflow') == 'flashinho_thinker':
        print("✅ SUCCESS: Math workflow was triggered!")
    else:
        print("❌ FAIL: Workflow not triggered")
        print(f"Metadata: {metadata}")


if __name__ == "__main__":
    main()