#!/usr/bin/env python3
"""
Direct test of Agno framework integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from src.agents.pydanticai.simple_agno.agent import SimpleAgnoAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

async def test_agno_directly():
    """Test Agno framework directly."""
    print("🧪 TESTING AGNO FRAMEWORK DIRECTLY")
    print("="*50)
    
    try:
        # Create simple_agno agent
        print("🚀 Creating SimpleAgnoAgent...")
        config = {
            "name": "test_agno_direct",
            "model": "openai:gpt-4o",
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        print(f"✅ Agent created successfully")
        print(f"  Framework type: {agent.framework_type}")
        print(f"  Model: {agent.config.model}")
        
        # Initialize framework
        print("\n🔧 Initializing framework...")
        success = await agent.initialize_framework(
            dependencies_type=AutomagikAgentsDependencies
        )
        
        if success:
            print("✅ Framework initialized successfully!")
            print(f"  Framework ready: {agent.is_framework_ready}")
            print(f"  AI Framework: {type(agent.ai_framework).__name__}")
        else:
            print("❌ Framework initialization failed")
            return
        
        # Test text processing
        print("\n📝 Testing text processing...")
        response = await agent.run(
            "What AI framework are you using? Be specific about your capabilities."
        )
        
        print(f"✅ Text response received:")
        print(f"  Success: {response.success}")
        print(f"  Text: {response.text[:200]}...")
        if response.usage:
            print(f"  Framework: {response.usage.get('framework', 'unknown')}")
            print(f"  Model: {response.usage.get('model', 'unknown')}")
            print(f"  Tokens: {response.usage.get('total_tokens', 0)}")
        
        # Test multimodal processing (image)
        print("\n🖼️ Testing image processing...")
        image_input = [
            "Please analyze this small test image and describe what you see.",
            {"type": "image", "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}
        ]
        
        image_response = await agent.run(image_input)
        
        print(f"✅ Image response received:")
        print(f"  Success: {image_response.success}")
        print(f"  Text: {image_response.text[:200]}...")
        if image_response.usage:
            print(f"  Framework: {image_response.usage.get('framework', 'unknown')}")
            print(f"  Model: {image_response.usage.get('model', 'unknown')}")
            print(f"  Tokens: {image_response.usage.get('total_tokens', 0)}")
        
        # Check if image analysis worked
        if any(word in image_response.text.lower() for word in ["image", "pixel", "color", "visual", "see"]):
            print("🎯 Image analysis working - multimodal processing successful!")
        else:
            print("⚠️ No image analysis detected - multimodal processing may not be working")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run direct Agno test."""
    print("🔍 DIRECT AGNO FRAMEWORK TEST")
    print("="*80)
    print("Testing Agno framework integration outside of API")
    print("="*80)
    
    asyncio.run(test_agno_directly())

if __name__ == "__main__":
    main()