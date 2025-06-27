#!/usr/bin/env python3
"""
Debug Multimodal Content Flow
Traces exactly what happens to multimodal content through the entire pipeline
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

async def debug_direct_agent():
    """Debug multimodal content processing directly with the agent."""
    print("🔍 DEBUGGING DIRECT AGENT MULTIMODAL PROCESSING")
    print("="*60)
    
    try:
        # Create agent with auto framework
        config = {
            "name": "debug_multimodal",
            "model": "openai:gpt-4o",
            "framework_type": "auto"
        }
        
        agent = SimpleAgent(config)
        print(f"✅ Agent created with framework: {agent.framework_type}")
        
        # Initialize framework
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        print(f"✅ Actual framework class: {type(agent.ai_framework).__name__}")
        
        # Test multimodal content
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        print(f"\n🔍 Testing with multimodal content: {list(multimodal_content.keys())}")
        
        # Update context to include message_type
        agent.update_context({"message_type": "image"})
        
        # Call run method directly
        response = await agent.run(
            "What color is this image? Describe it in detail.",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 RESPONSE:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text}")
        print(f"Usage: {json.dumps(response.usage, indent=2) if response.usage else 'None'}")
        
        # Check response content
        has_image_analysis = any(word in response.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
        if response.usage:
            framework = response.usage.get('framework', 'unknown')
            content_types = response.usage.get('content_types', [])
            print(f"🎯 Framework Used: {framework}")
            print(f"🎯 Content Types: {content_types}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def debug_agent_process_message():
    """Debug using process_message method (API path)."""
    print("\n🔍 DEBUGGING PROCESS_MESSAGE METHOD")
    print("="*60)
    
    try:
        config = {
            "name": "debug_process_message",
            "model": "openai:gpt-4o",
            "framework_type": "auto"
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        # Create context similar to API
        context = {
            "message_type": "image",
            "multimodal_content": {
                "images": [{
                    "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                    "media_type": "image/png"
                }]
            }
        }
        
        print(f"🔍 Context keys: {list(context.keys())}")
        print(f"🔍 Multimodal content: {list(context['multimodal_content'].keys())}")
        
        # Call process_message (API path)
        response = await agent.process_message(
            user_message="What color is this image? Please describe it.",
            context=context
        )
        
        print(f"\n📝 PROCESS_MESSAGE RESPONSE:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text}")
        print(f"Usage: {json.dumps(response.usage, indent=2) if response.usage else 'None'}")
        
        # Check response content
        has_image_analysis = any(word in response.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
        if response.usage:
            framework = response.usage.get('framework', 'unknown')
            content_types = response.usage.get('content_types', [])
            print(f"🎯 Framework Used: {framework}")
            print(f"🎯 Content Types: {content_types}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def debug_api_request():
    """Debug API request to see what's sent."""
    print("\n🔍 DEBUGGING API REQUEST")
    print("="*60)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    payload = {
        "message_content": "What color is this image? Please be very specific.",
        "message_type": "image",
        "session_name": "debug-api-flow",
        "user": {
            "phone_number": "+555000005",
            "email": "debug@example.com"
        },
        "media_contents": [{
            "mime_type": "image/png",
            "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }]
    }
    
    print(f"🔍 Payload keys: {list(payload.keys())}")
    print(f"🔍 Message type: {payload['message_type']}")
    print(f"🔍 Media contents count: {len(payload['media_contents'])}")
    print(f"🔍 Media MIME type: {payload['media_contents'][0]['mime_type']}")
    
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
            
            print(f"\n📝 API RESPONSE:")
            print(f"Response preview: {response_text[:300]}...")
            print(f"Framework: {usage.get('framework', 'unknown')}")
            print(f"Content types: {usage.get('content_types', [])}")
            
            # Check response content
            has_image_analysis = any(word in response_text.lower() for word in ["yellow", "color", "image", "pixel"])
            print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
            
            if usage.get('media_usage'):
                print(f"🎯 Media Usage: {usage['media_usage']}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def debug_agno_directly():
    """Debug Agno framework directly to see if it can process images."""
    print("\n🔍 DEBUGGING AGNO FRAMEWORK DIRECTLY")
    print("="*60)
    
    try:
        from src.agents.models.ai_frameworks.agno import AgnoFramework
        from src.agents.models.ai_frameworks.base import AgentConfig
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create Agno framework directly
        config = AgentConfig(
            model="openai:gpt-4o",
            temperature=0.7,
            retries=3,
            tools=[],
            model_settings={}
        )
        
        agno = AgnoFramework(config)
        deps = AutomagikAgentsDependencies({})
        
        await agno.initialize([], AutomagikAgentsDependencies)
        print(f"✅ Agno framework initialized: {agno.is_initialized}")
        
        # Create multimodal input in Agno format
        multimodal_input = [
            "What color is this image? Describe it in detail.",
            {
                "type": "image",
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            }
        ]
        
        print(f"🔍 Agno input format: {type(multimodal_input)}, length: {len(multimodal_input)}")
        
        # Run Agno directly
        result = await agno.run(
            user_input=multimodal_input,
            dependencies=deps
        )
        
        print(f"\n📝 AGNO DIRECT RESPONSE:")
        print(f"Success: {result.success}")
        print(f"Text: {result.text}")
        print(f"Usage: {json.dumps(result.usage, indent=2) if result.usage else 'None'}")
        
        # Check response content
        has_image_analysis = any(word in result.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run comprehensive multimodal debugging."""
    print("🐛 COMPREHENSIVE MULTIMODAL DEBUGGING")
    print("="*80)
    print("Tracing multimodal content through the entire pipeline")
    print("="*80)
    
    # Debug 1: Direct agent call
    await debug_direct_agent()
    
    # Debug 2: Process message method (API path)
    await debug_agent_process_message()
    
    # Debug 3: API request
    debug_api_request()
    
    # Debug 4: Agno framework directly
    await debug_agno_directly()
    
    print("\n" + "="*80)
    print("🔍 DEBUGGING COMPLETE")
    print("="*80)
    print("Check the output above to identify where multimodal processing breaks down")

if __name__ == "__main__":
    asyncio.run(main())