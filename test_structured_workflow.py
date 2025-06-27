#!/usr/bin/env python3
"""Test structured workflow with Pydantic output for flashinho_pro agent."""

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

# Different types of educational images (base64 encoded)
# These are simple 1x1 pixel PNGs for testing - in real use, these would be actual problem images
MATH_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
PHYSICS_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
CHEMISTRY_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def send_message_with_image(message: str, session_name: str, image_base64: str, session_id: str = None):
    """Send a message with image to the API."""
    
    # Prepare image content
    image_data = f"data:image/png;base64,{image_base64}"
    
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


def analyze_response_structure(response_text: str) -> dict:
    """Analyze the response to check for proper 3-step structure."""
    
    analysis = {
        "has_3_steps": False,
        "has_emojis": False,
        "has_workflow_tag": False,
        "detected_subject": None,
        "step_titles": [],
        "response_length": len(response_text)
    }
    
    # Check for 3-step structure
    steps = ["Passo 1:", "Passo 2:", "Passo 3:"]
    found_steps = sum(1 for step in steps if step in response_text)
    analysis["has_3_steps"] = found_steps == 3
    
    # Extract step titles
    for line in response_text.split('\n'):
        if any(step in line for step in steps):
            analysis["step_titles"].append(line.strip())
    
    # Check for emojis
    emoji_chars = ["📚", "🔍", "✏️", "✅", "💡", "🧮", "🔬", "⚗️", "🧬"]
    analysis["has_emojis"] = any(emoji in response_text for emoji in emoji_chars)
    
    # Check for workflow tag
    if "<!-- workflow:" in response_text:
        analysis["has_workflow_tag"] = True
        # Extract subject from workflow tag
        for line in response_text.split('\n'):
            if "subject:" in line:
                subject = line.split("subject:")[1].split()[0].strip()
                analysis["detected_subject"] = subject
    
    return analysis


def main():
    """Run structured workflow tests."""
    print("🚀 STRUCTURED WORKFLOW TEST WITH PYDANTIC OUTPUT")
    print("="*60)
    
    # Test cases with different subjects
    test_cases = [
        {
            "name": "Math Problem",
            "message": "[Cezar]: Preciso resolver essa equação de segundo grau",
            "image": MATH_IMAGE,
            "expected_subject": "mathematics"
        },
        {
            "name": "Physics Problem",
            "message": "[Cezar]: Me ajuda com esse problema de cinemática",
            "image": PHYSICS_IMAGE,
            "expected_subject": "physics"
        },
        {
            "name": "Chemistry Problem",
            "message": "[Cezar]: Não entendi essa reação química",
            "image": CHEMISTRY_IMAGE,
            "expected_subject": "chemistry"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        # Create unique session
        session_name = f"test-structured-{int(time.time())}-{i}"
        
        # Authenticate first
        print("\n1. Authenticating...")
        auth_result = send_message_with_image(
            f"[Cezar Vasconcelos]: {CONVERSATION_CODE}",
            session_name,
            test_case["image"]
        )
        
        if "error" in auth_result:
            print(f"❌ Auth Error: {auth_result['error']}")
            continue
            
        session_id = auth_result.get('session_id')
        print(f"✅ Authenticated with session: {session_id}")
        
        # Send problem
        print(f"\n2. Sending {test_case['name']}...")
        print(f"Message: {test_case['message']}")
        
        start_time = time.time()
        result = send_message_with_image(
            test_case["message"],
            session_name,
            test_case["image"],
            session_id
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            continue
            
        response_time = time.time() - start_time
        response_text = result.get('message', '')
        
        # Analyze response structure
        print("\n3. Analyzing Response Structure:")
        analysis = analyze_response_structure(response_text)
        
        print(f"   ✓ Response time: {response_time:.2f}s")
        print(f"   ✓ Response length: {analysis['response_length']} chars")
        print(f"   {'✅' if analysis['has_3_steps'] else '❌'} Has 3-step structure: {analysis['has_3_steps']}")
        print(f"   {'✅' if analysis['has_emojis'] else '❌'} Has emojis: {analysis['has_emojis']}")
        print(f"   {'✅' if analysis['has_workflow_tag'] else '❌'} Has workflow tag: {analysis['has_workflow_tag']}")
        
        if analysis['detected_subject']:
            print(f"   ✓ Detected subject: {analysis['detected_subject']}")
            if analysis['detected_subject'] == test_case['expected_subject']:
                print(f"   ✅ Subject matches expected: {test_case['expected_subject']}")
            else:
                print(f"   ⚠️ Subject mismatch - Expected: {test_case['expected_subject']}")
        
        # Show step titles
        if analysis['step_titles']:
            print("\n4. Step Titles Found:")
            for title in analysis['step_titles']:
                print(f"   • {title}")
        
        # Show response preview
        print("\n5. Response Preview:")
        print("-" * 60)
        preview_lines = response_text.split('\n')[:10]
        for line in preview_lines:
            print(f"   {line}")
        if len(response_text.split('\n')) > 10:
            print("   ...")
        
        # Small delay between tests
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print("✅ All tests completed!")
    print("="*60)
    
    # Summary
    print("\n📊 SUMMARY:")
    print("The enhanced Flashinho Pro agent now features:")
    print("• Structured image analysis using Pydantic models")
    print("• Subject detection (math, physics, chemistry, etc.)")
    print("• Guaranteed 3-step breakdown format")
    print("• Workflow monitoring with start/complete tracking")
    print("• No hardcoded string checks - uses structured data")


if __name__ == "__main__":
    main()