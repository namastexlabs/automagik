#!/usr/bin/env python3
"""
Debug API vs Direct Agno Calls
Compare what happens when calling Agno through API vs directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import logging
import requests

# Set up logging to see debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_direct_automagik_agent():
    """Test AutomagikAgent directly with multimodal content."""
    print("🔍 TESTING AUTOMAGIK AGENT DIRECTLY")
    print("="*60)
    
    try:
        from src.agents.pydanticai.simple.agent import SimpleAgent
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create agent with auto framework
        config = {
            "name": "debug_api_vs_direct",
            "model": "openai:gpt-4o",
            "framework_type": "auto"
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        print(f"✅ Agent created with framework: {agent.framework_type}")
        
        # Create context with multimodal content (as API does)
        context = {
            "message_type": "image",
            "multimodal_content": {
                "images": [{
                    "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                    "media_type": "image/png"
                }]
            }
        }
        
        print(f"🔍 Context contains: {list(context.keys())}")
        print(f"🔍 Multimodal content: {list(context['multimodal_content'].keys())}")
        
        # Call process_message like the API does
        result = await agent.process_message(
            user_message="What color is this image? Please describe it in detail.",
            context=context
        )
        
        print(f"\n📝 DIRECT AUTOMAGIK RESULT:")
        print(f"Success: {result.success}")
        print(f"Text preview: {result.text[:200]}...")
        
        if result.usage:
            print(f"\n📊 Usage:")
            print(f"  Framework: {result.usage.get('framework')}")
            print(f"  Content types: {result.usage.get('content_types')}")
            print(f"  Image tokens: {result.usage.get('media_usage', {}).get('image_tokens', 0)}")
        
        # Check for image analysis
        has_image_analysis = any(word in result.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_api_call():
    """Test API call with same multimodal content."""
    print("\n🔍 TESTING API CALL")
    print("="*60)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    payload = {
        "message_content": "What color is this image? Please describe it in detail.",
        "message_type": "image",
        "session_name": "debug-api-vs-direct",
        "user": {
            "phone_number": "+555000010",
            "email": "debug@example.com"
        },
        "media_contents": [{
            "mime_type": "image/png",
            "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }]
    }
    
    print(f"🔍 API payload contains: {list(payload.keys())}")
    print(f"🔍 Media contents count: {len(payload['media_contents'])}")
    
    try:
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("data", {}).get("response", "")
            usage = result.get("usage", {})
            
            print(f"\n📝 API RESULT:")
            print(f"Response preview: {response_text[:200]}...")
            
            if usage:
                print(f"\n📊 Usage:")
                print(f"  Framework: {usage.get('framework')}")
                print(f"  Content types: {usage.get('content_types')}")
                print(f"  Image tokens: {usage.get('media_usage', {}).get('image_tokens', 0)}")
            
            # Check for image analysis
            has_image_analysis = any(word in response_text.lower() for word in ["yellow", "color", "image", "pixel"])
            print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
            
            return result
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def compare_results():
    """Compare results from both approaches."""
    print("\n🔍 COMPARING RESULTS")
    print("="*60)
    
    # Test 1: Direct AutomagikAgent call
    direct_result = await test_direct_automagik_agent()
    
    # Test 2: API call
    api_result = test_api_call()
    
    print(f"\n📊 COMPARISON SUMMARY:")
    print("-" * 40)
    
    if direct_result and direct_result.usage:
        direct_framework = direct_result.usage.get('framework', 'unknown')
        direct_content_types = direct_result.usage.get('content_types', [])
        direct_image_tokens = direct_result.usage.get('media_usage', {}).get('image_tokens', 0)
        
        print(f"Direct AutomagikAgent:")
        print(f"  Framework: {direct_framework}")
        print(f"  Content types: {direct_content_types}")
        print(f"  Image tokens: {direct_image_tokens}")
    else:
        print(f"Direct AutomagikAgent: ❌ Failed or no usage data")
    
    if api_result and api_result.get("usage"):
        api_usage = api_result["usage"]
        api_framework = api_usage.get('framework', 'unknown')
        api_content_types = api_usage.get('content_types', [])
        api_image_tokens = api_usage.get('media_usage', {}).get('image_tokens', 0)
        
        print(f"API Call:")
        print(f"  Framework: {api_framework}")
        print(f"  Content types: {api_content_types}")
        print(f"  Image tokens: {api_image_tokens}")
    else:
        print(f"API Call: ❌ Failed or no usage data")
    
    # Analysis
    print(f"\n🎯 ANALYSIS:")
    if (direct_result and direct_result.usage and 
        api_result and api_result.get("usage")):
        
        direct_working = 'image' in direct_result.usage.get('content_types', [])
        api_working = 'image' in api_result["usage"].get('content_types', [])
        
        if direct_working and not api_working:
            print("✅ Direct AutomagikAgent works, API pipeline has issues")
        elif not direct_working and not api_working:
            print("❌ Both approaches have issues - problem is deeper")
        elif direct_working and api_working:
            print("✅ Both approaches work - earlier test was anomaly")
        else:
            print("⚠️  API works but direct doesn't - unexpected")
    else:
        print("❌ Cannot compare - one or both tests failed")

async def main():
    """Run comparison testing."""
    print("🔍 API vs DIRECT AUTOMAGIK AGENT COMPARISON")
    print("="*80)
    
    await compare_results()
    
    print("\n" + "="*80)
    print("🔍 COMPARISON COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())