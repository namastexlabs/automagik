#!/usr/bin/env python3
"""
Debug test for Agno multimodal processing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from src.agents.pydanticai.simple_agno.agent import SimpleAgnoAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

async def test_agno_multimodal_debug():
    """Test Agno multimodal with detailed debugging."""
    print("🧪 AGNO MULTIMODAL DEBUG TEST")
    print("="*50)
    
    try:
        # Create agent
        config = {
            "name": "test_agno_debug",
            "model": "openai:gpt-4o",
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        print(f"✅ Agent created with framework: {agent.framework_type}")
        
        # Initialize framework
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        
        # Test multimodal input through API format
        print("\n🖼️ Testing multimodal via process_message (API style)...")
        
        # Create multimodal context similar to what the API creates
        context = {
            "multimodal_content": {
                "images": [{
                    "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                    "media_type": "image/png"
                }]
            }
        }
        
        # Call process_message like the API does
        response = await agent.process_message(
            user_message="Please describe this image in detail. What color is it?",
            context=context
        )
        
        print(f"\n📝 Response via process_message:")
        print(f"Success: {response.success}")
        print(f"Text: {response.text[:200]}...")
        print(f"Usage: {json.dumps(response.usage, indent=2) if response.usage else 'None'}")
        
        # Check if image was processed
        has_color_mention = any(word in response.text.lower() for word in ["yellow", "color", "bright", "image", "pixel", "square"])
        print(f"\n🎯 Image analysis detected: {'✅' if has_color_mention else '❌'}")
        
        # Now test direct run method
        print("\n🖼️ Testing multimodal via direct run method...")
        
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        direct_response = await agent.run(
            "Please describe this image. What color do you see?",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Response via direct run:")
        print(f"Success: {direct_response.success}")
        print(f"Text: {direct_response.text[:200]}...")
        
        # Check if image was processed
        has_color_mention = any(word in direct_response.text.lower() for word in ["yellow", "color", "bright", "image", "pixel", "square"])
        print(f"\n🎯 Image analysis detected: {'✅' if has_color_mention else '❌'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    asyncio.run(test_agno_multimodal_debug())

if __name__ == "__main__":
    main()