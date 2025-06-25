#!/usr/bin/env python3
"""Test enhanced student problem workflow for flashinho_pro agent."""

import requests
import json
import base64
import os
import time

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


def test_different_subjects():
    """Test workflow with different subject contexts."""
    
    test_cases = [
        {
            "subject": "física",
            "message": "[Cezar]: Me ajuda com esse exercício de cinemática que não consigo resolver",
            "session": f"test-physics-{int(time.time())}"
        },
        {
            "subject": "química",
            "message": "[Cezar]: Essa reação química tá difícil, pode me explicar?",
            "session": f"test-chemistry-{int(time.time())}"
        },
        {
            "subject": "biologia",
            "message": "[Cezar]: Não entendi esse diagrama sobre fotossíntese",
            "session": f"test-biology-{int(time.time())}"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Testing {test['subject'].upper()} Problem")
        print(f"Session: {test['session']}")
        
        # First authenticate
        auth_result = send_message_with_image(
            f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
            test['session']
        )
        
        if "error" in auth_result:
            print(f"❌ Auth Error: {auth_result['error']}")
            continue
            
        session_id = auth_result.get('session_id')
        
        # Send subject-specific problem
        print(f"\nSending {test['subject']} problem...")
        result = send_message_with_image(
            test['message'],
            test['session'],
            session_id
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            continue
            
        response_text = result.get('message', '')
        print(f"\nResponse preview: {response_text[:300]}...")
        
        # Check for 3-step structure
        if all(step in response_text for step in ["Passo 1:", "Passo 2:", "Passo 3:"]):
            print("✅ SUCCESS: Response contains 3-step structure!")
        else:
            print("⚠️ WARNING: 3-step structure not clearly visible")
        
        # Small delay between tests
        time.sleep(2)


def main():
    """Run enhanced student problem tests."""
    print("🚀 ENHANCED STUDENT PROBLEM WORKFLOW TEST")
    print("="*60)
    
    # Test with new session to avoid cache
    unique_session = f"test-student-{int(time.time())}"
    
    print(f"\n1. Testing with fresh session: {unique_session}")
    
    # Authenticate first
    auth_result = send_message_with_image(
        f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
        unique_session
    )
    
    if "error" in auth_result:
        print(f"❌ Error: {auth_result['error']}")
        return
        
    session_id = auth_result.get('session_id')
    print(f"✅ Authenticated with session: {session_id}")
    
    # Send generic student problem
    print("\n2. Sending generic student problem...")
    result = send_message_with_image(
        "[Cezar]: Preciso de ajuda com esse exercício que o professor passou!",
        unique_session,
        session_id
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
        
    response_text = result.get('message', '')
    print(f"\nFull Response:\n{response_text}")
    
    # Test different subjects
    print("\n\n3. Testing different subjects...")
    test_different_subjects()


if __name__ == "__main__":
    main()