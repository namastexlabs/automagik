#!/usr/bin/env python3
"""
Debug Agno Framework Processing
Specifically debug what happens in the multimodal processing pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import logging

# Enable debug logging for our modules
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_agno_processing():
    """Debug the exact processing flow in Agno."""
    print("🔍 DEBUGGING AGNO MULTIMODAL PROCESSING FLOW")
    print("="*60)
    
    try:
        from src.agents.models.ai_frameworks.agno import AgnoFramework
        from src.agents.models.ai_frameworks.base import AgentConfig
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create configuration
        config = AgentConfig(
            model="openai:gpt-4o",
            temperature=0.7,
            retries=3,
            tools=[],
            model_settings={}
        )
        
        # Initialize Agno framework
        agno = AgnoFramework(config)
        deps = AutomagikAgentsDependencies({})
        
        await agno.initialize([], AutomagikAgentsDependencies)
        print(f"✅ Agno framework initialized: {agno.is_ready}")
        
        # Test multimodal input exactly as AutomagikAgent creates it
        test_input = [
            "What color is this image? Describe it in detail.",
            {
                "type": "image",
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            }
        ]
        
        print(f"🔍 Input format: {type(test_input)}")
        print(f"🔍 Input length: {len(test_input)}")
        print(f"🔍 First item: {type(test_input[0])}")
        print(f"🔍 Second item: {type(test_input[1])}")
        print(f"🔍 Second item keys: {list(test_input[1].keys())}")
        
        # Add debug logging to see what happens inside Agno
        import logging
        agno_logger = logging.getLogger("src.agents.models.ai_frameworks.agno")
        agno_logger.setLevel(logging.DEBUG)
        
        # Run Agno with debug enabled
        print(f"\n🚀 Running Agno with multimodal input...")
        result = await agno.run(
            user_input=test_input,
            dependencies=deps
        )
        
        print(f"\n📝 AGNO RESULT:")
        print(f"Success: {result.success}")
        print(f"Text: {result.text}")
        
        if result.usage:
            print(f"\n📊 Usage:")
            print(f"  Framework: {result.usage.get('framework')}")
            print(f"  Content types: {result.usage.get('content_types')}")
            print(f"  Image tokens: {result.usage.get('media_usage', {}).get('image_tokens')}")
        
        # Check if image analysis was detected
        has_image_analysis = any(word in result.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def debug_automagik_processing():
    """Debug what AutomagikAgent actually sends to Agno."""
    print("\n🔍 DEBUGGING AUTOMAGIK AGENT PROCESSING")
    print("="*60)
    
    try:
        from src.agents.pydanticai.simple.agent import SimpleAgent
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create agent with Agno framework
        config = {
            "name": "debug_automagik",
            "model": "openai:gpt-4o",
            "framework_type": "agno"  # Force Agno
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        print(f"✅ Agent created with framework: {agent.framework_type}")
        print(f"✅ Framework class: {type(agent.ai_framework).__name__}")
        
        # Multimodal content in AutomagikAgent format
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        print(f"🔍 Multimodal content format: {list(multimodal_content.keys())}")
        print(f"🔍 Images count: {len(multimodal_content['images'])}")
        
        # Test the _process_multimodal_input_for_agno method directly
        processed_input = agent._process_multimodal_input_for_agno(
            "What color is this image?",
            multimodal_content
        )
        
        print(f"\n🔍 Processed input for Agno:")
        print(f"  Type: {type(processed_input)}")
        print(f"  Length: {len(processed_input)}")
        for i, item in enumerate(processed_input):
            print(f"  Item {i}: {type(item)} - {item if isinstance(item, str) else list(item.keys())}")
        
        # Now run it through Agno directly
        print(f"\n🚀 Running processed input through Agno directly...")
        
        result = await agent.ai_framework.run(
            user_input=processed_input,
            dependencies=agent.dependencies
        )
        
        print(f"\n📝 RESULT:")
        print(f"Success: {result.success}")
        print(f"Text preview: {result.text[:200]}...")
        
        if result.usage:
            print(f"\n📊 Usage:")
            print(f"  Framework: {result.usage.get('framework')}")
            print(f"  Content types: {result.usage.get('content_types')}")
            print(f"  Image tokens: {result.usage.get('media_usage', {}).get('image_tokens')}")
        
        # Check if image analysis was detected
        has_image_analysis = any(word in result.text.lower() for word in ["yellow", "color", "image", "pixel"])
        print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run targeted debugging."""
    # Test 1: Agno framework directly
    await debug_agno_processing()
    
    # Test 2: AutomagikAgent processing
    await debug_automagik_processing()
    
    print("\n" + "="*60)
    print("🔍 DEBUGGING COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())