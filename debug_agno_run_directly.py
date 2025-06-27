#!/usr/bin/env python3
"""
Debug Agno Run Method Directly
Call the actual agno.run() method to see the debug output
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_agno_run_directly():
    """Test calling agno.run() directly with the converted input."""
    print("🔍 TESTING AGNO RUN METHOD DIRECTLY")
    print("="*60)
    
    try:
        from src.agents.pydanticai.simple.agent import SimpleAgent
        from src.agents.models.dependencies import AutomagikAgentsDependencies
        
        # Create agent with Agno framework
        config = {
            "name": "debug_agno_run",
            "model": "openai:gpt-4o",
            "framework_type": "agno"  # Force Agno
        }
        
        agent = SimpleAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        print(f"✅ Agent created with framework: {type(agent.ai_framework).__name__}")
        
        # Create multimodal content exactly as AutomagikAgent does
        multimodal_content = {
            "images": [{
                "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
                "media_type": "image/png"
            }]
        }
        
        # Convert to Agno format
        agno_input = agent._process_multimodal_input_for_agno(
            "What color is this image?",
            multimodal_content
        )
        
        print(f"🔍 Agno input format: {type(agno_input)}, length: {len(agno_input)}")
        for i, item in enumerate(agno_input):
            print(f"  Item {i}: {type(item)} - {item if isinstance(item, str) else list(item.keys())}")
        
        # Call agno.run() directly to see the debug output
        print(f"\n🚀 Calling agno.run() with debug output enabled...")
        
        result = await agent.ai_framework.run(
            user_input=agno_input,
            dependencies=agent.dependencies
        )
        
        print(f"\n📝 AGNO RUN RESULT:")
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
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run direct Agno testing."""
    await test_agno_run_directly()

if __name__ == "__main__":
    asyncio.run(main())