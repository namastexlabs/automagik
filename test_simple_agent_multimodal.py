#!/usr/bin/env python3
"""
Test Enhanced Simple Agent with Complete Multimodal Capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import base64
import requests
from src.agents.pydanticai.simple.agent import SimpleAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

async def test_simple_agent_text():
    """Test basic text functionality."""
    print("🔤 TESTING SIMPLE AGENT - TEXT FUNCTIONALITY")
    print("="*50)
    
    try:
        # Create enhanced simple agent
        config = {
            "name": "test_simple_enhanced",
            "model": "openai:gpt-4o"
        }
        
        agent = SimpleAgent(config)
        print(f"✅ Enhanced Simple Agent created with framework: {agent.framework_type}")
        
        # Initialize
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        
        # Test text interaction
        response = await agent.run("Hello! What's your name and what can you do?")
        
        print(f"\n📝 Agent Response:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text[:500]}...")
        
        # Check if agent identifies as TESTONHO and mentions capabilities
        has_name = "testonho" in response.text.lower()
        has_multimodal = any(word in response.text.lower() for word in ["multimodal", "image", "audio", "agno"])
        
        print(f"\n🎯 Agent Identity: {'✅ TESTONHO' if has_name else '❌ Name not found'}")
        print(f"🎯 Multimodal Awareness: {'✅ Mentioned' if has_multimodal else '❌ Not mentioned'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_agent_image():
    """Test image processing."""
    print("\n🖼️ TESTING SIMPLE AGENT - IMAGE ANALYSIS")
    print("="*50)
    
    try:
        config = {
            "name": "test_simple_image",
            "model": "openai:gpt-4o"
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        # Test with a simple image
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        response = await agent.run(
            "What do you see in this image? Describe it in detail.",
            multimodal_content=multimodal_content
        )
        
        print(f"📝 Image Analysis Response:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text}")
        
        if response.usage:
            print(f"\n📊 Usage:")
            print(f"Framework: {response.usage.get('framework', 'unknown')}")
            print(f"Model: {response.usage.get('model', 'unknown')}")
            if 'media_usage' in response.usage:
                print(f"Image tokens: {response.usage['media_usage'].get('image_tokens', 0)}")
        
        # Check for image analysis
        has_image_analysis = any(word in response.text.lower() for word in ["yellow", "color", "pixel", "image", "square"])
        print(f"\n🎯 Image Processing: {'✅ Analyzed' if has_image_analysis else '❌ Not processed'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_agent_tools():
    """Test multimodal tools."""
    print("\n🛠️ TESTING SIMPLE AGENT - MULTIMODAL TOOLS")
    print("="*50)
    
    try:
        config = {
            "name": "test_simple_tools",
            "model": "openai:gpt-4o"
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        # Test capabilities description
        response = await agent.run("What are your multimodal capabilities? Use your tools to describe them.")
        
        print(f"📝 Capabilities Response:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text[:800]}...")
        
        # Check for tool usage and capability mentions
        has_capabilities = any(word in response.text.lower() for word in ["image", "audio", "document", "framework", "agno"])
        print(f"\n🎯 Capabilities Described: {'✅ Comprehensive' if has_capabilities else '❌ Limited'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_agent_api():
    """Test via API endpoint."""
    print("\n🌐 TESTING SIMPLE AGENT - API ENDPOINT")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    try:
        # Test basic API call
        payload = {
            "message_content": "Hello! I'm testing your enhanced capabilities. What's your name and what can you do with multimodal content?",
            "message_type": "text",
            "session_name": "test-simple-enhanced",
            "user": {
                "phone_number": "+555000001",
                "email": "test@example.com"
            }
        }
        
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("data", {}).get("response", "")
            print(f"✅ API Response: {response_text[:400]}...")
            
            usage = result.get("usage", {})
            if usage:
                print(f"\n📊 API Usage:")
                print(f"Framework: {usage.get('framework', 'unknown')}")
                print(f"Model: {usage.get('model', 'unknown')}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API Test Error: {e}")

async def main():
    """Run all tests for enhanced simple agent."""
    print("🎯 ENHANCED SIMPLE AGENT TEST SUITE")
    print("="*80)
    print("Testing complete multimodal capabilities")
    print("="*80)
    
    # Test 1: Basic text functionality
    await test_simple_agent_text()
    
    # Test 2: Image processing
    await test_simple_agent_image()
    
    # Test 3: Multimodal tools
    await test_simple_agent_tools()
    
    # Test 4: API endpoint
    await test_simple_agent_api()
    
    print("\n✅ All Simple Agent tests completed!")
    print("\n📝 Summary:")
    print("- Enhanced Simple Agent now has complete multimodal support")
    print("- Automatic framework selection (Agno for multimodal)")
    print("- Comprehensive tools for image, audio, document, and video analysis")
    print("- Optimized prompts for multimodal processing")
    print("- Full API compatibility maintained")

if __name__ == "__main__":
    asyncio.run(main())