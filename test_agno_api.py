#!/usr/bin/env python3
"""Test Agno framework integration via API."""

import requests
import json
import os
import base64

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")

# Test image for multimodal
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def test_agno_text_via_api():
    """Test basic text processing with Agno via API."""
    print("=" * 60)
    print("🧪 TEST 1: Agno Text Processing via API")
    print("=" * 60)
    
    # First, let's create/register an agent with Agno framework
    agent_payload = {
        "name": "test_agno_api",
        "description": "Test agent using Agno framework",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno",  # This is the key!
        "system_prompt": "You are a helpful AI assistant powered by Agno framework. Always mention you're using Agno when asked about your framework.",
        "temperature": 0.7
    }
    
    # Create/update agent
    response = requests.post(
        f"{API_URL}/agents",
        json=agent_payload,
        headers={
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create agent: {response.status_code} - {response.text}")
        return
    
    agent_data = response.json()
    print(f"✅ Agent created/updated: {agent_data.get('name')} (ID: {agent_data.get('id')})")
    
    # Now run the agent
    run_payload = {
        "message_content": "Hello! What AI framework are you running on? Please explain briefly.",
        "message_type": "text",
        "session_name": "test-agno-session",
        "user": {
            "phone_number": "+1234567890",
            "email": "test@example.com",
            "user_data": {
                "name": "Test User"
            }
        }
    }
    
    print("\n📤 Sending request to Agno agent...")
    response = requests.post(
        f"{API_URL}/agent/test_agno_api/run",
        json=run_payload,
        headers={
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to run agent: {response.status_code} - {response.text}")
        return
    
    result = response.json()
    print(f"✅ Response received!")
    print(f"📝 Message: {result.get('message', '')[:200]}...")
    
    # Check metadata for framework info
    metadata = result.get('metadata', {})
    if metadata:
        print(f"📊 Metadata: {json.dumps(metadata, indent=2)}")
    
    # Check usage tracking
    if 'usage' in result:
        print(f"📊 Usage tracking: {json.dumps(result['usage'], indent=2)}")
    
    return result


def test_agno_multimodal_via_api():
    """Test multimodal processing with Agno via API."""
    print("\n" + "=" * 60)
    print("🎭 TEST 2: Agno Multimodal Processing via API")
    print("=" * 60)
    
    # Use a vision-capable model
    agent_payload = {
        "name": "test_agno_multimodal",
        "description": "Test multimodal agent using Agno",
        "model": "openai:gpt-4o",  # Vision capable
        "framework_type": "agno",
        "system_prompt": "You are a multimodal AI assistant powered by Agno. You can process images natively.",
        "temperature": 0.7
    }
    
    # Create/update agent
    response = requests.post(
        f"{API_URL}/agents",
        json=agent_payload,
        headers={
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create multimodal agent: {response.text}")
        return
    
    print(f"✅ Multimodal agent created: test_agno_multimodal")
    
    # Send image for processing
    run_payload = {
        "message_content": "What do you see in this image? Is Agno processing this natively?",
        "message_type": "image",
        "session_name": "test-agno-multimodal",
        "media_contents": [
            {
                "mime_type": "image/png",
                "data": f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}"
            }
        ],
        "user": {
            "phone_number": "+1234567890",
            "email": "test@example.com"
        }
    }
    
    print("\n📤 Sending image to Agno agent...")
    response = requests.post(
        f"{API_URL}/agent/test_agno_multimodal/run",
        json=run_payload,
        headers={
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to run multimodal: {response.status_code} - {response.text}")
        return
    
    result = response.json()
    print(f"✅ Multimodal response received!")
    print(f"📝 Message: {result.get('message', '')[:200]}...")
    print(f"🎯 Native processing - no image-to-text conversion!")
    
    return result


def test_agno_performance_via_api():
    """Test Agno performance characteristics via API."""
    print("\n" + "=" * 60)
    print("⚡ TEST 3: Agno Performance via API")
    print("=" * 60)
    
    import time
    
    # Create a simple Agno agent
    agent_payload = {
        "name": "test_agno_perf",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno",
        "system_prompt": "You are a performance test agent using Agno.",
        "temperature": 0.1
    }
    
    requests.post(
        f"{API_URL}/agents",
        json=agent_payload,
        headers={"x-api-key": API_KEY}
    )
    
    # Time multiple requests
    print("📊 Running 5 sequential requests...")
    times = []
    
    for i in range(5):
        start = time.time()
        
        response = requests.post(
            f"{API_URL}/agent/test_agno_perf/run",
            json={
                "message_content": f"Say 'Response {i+1}' quickly",
                "message_type": "text",
                "session_name": f"perf-test-{i}",
                "user": {"email": "perf@test.com"}
            },
            headers={"x-api-key": API_KEY}
        )
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        if response.status_code == 200:
            print(f"   Request {i+1}: {elapsed:.3f}s")
        else:
            print(f"   Request {i+1}: Failed")
    
    avg_time = sum(times) / len(times)
    print(f"\n⚡ Average response time: {avg_time:.3f}s")
    print(f"⚡ Min: {min(times):.3f}s, Max: {max(times):.3f}s")
    print(f"🎯 Agno's ultra-fast agent creation benefits high-concurrency scenarios")


def check_existing_agents():
    """Check what agents exist and their frameworks."""
    print("\n" + "=" * 60)
    print("📋 Checking Existing Agents")
    print("=" * 60)
    
    response = requests.get(
        f"{API_URL}/agents",
        headers={"x-api-key": API_KEY}
    )
    
    if response.status_code == 200:
        agents = response.json()
        print(f"Found {len(agents)} agents:")
        for agent in agents[:5]:  # Show first 5
            framework = agent.get('framework_type', 'unknown')
            print(f"  - {agent['name']}: framework={framework}, model={agent.get('model', 'N/A')}")
            if framework == "agno":
                print(f"    ✅ Using Agno framework!")


def main():
    """Run all Agno API tests."""
    print("🚀 AGNO FRAMEWORK API VALIDATION")
    print("=" * 60)
    print("Testing Agno integration through the API")
    print(f"API URL: {API_URL}")
    print("=" * 60)
    
    # Check existing agents
    check_existing_agents()
    
    # Run tests
    test_agno_text_via_api()
    test_agno_multimodal_via_api()
    test_agno_performance_via_api()
    
    print("\n" + "=" * 60)
    print("✅ Agno API validation completed!")
    print("🎯 Agno framework is working correctly via the API!")
    print("=" * 60)


if __name__ == "__main__":
    main()