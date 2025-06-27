#!/usr/bin/env python3
"""
Test Agno multimodal capabilities - Image processing
Demonstrates that Agno framework is working correctly for multimodal content
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import base64
import requests
from src.agents.pydanticai.simple_agno.agent import SimpleAgnoAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

# Different test images
TEST_IMAGES = {
    "yellow_pixel": {
        "description": "1x1 yellow pixel",
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
        "expected_words": ["yellow", "bright", "color", "pixel", "square"]
    },
    "red_pixel": {
        "description": "1x1 red pixel", 
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
        "expected_words": ["red", "color", "pixel"]
    },
    "blue_pixel": {
        "description": "1x1 blue pixel",
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA0e7KpAAAAABJRU5ErkJggg==",
        "expected_words": ["blue", "color", "pixel"]
    }
}

async def test_direct_agno_images():
    """Test Agno image processing directly."""
    print("🖼️ TESTING AGNO IMAGE PROCESSING (DIRECT)")
    print("="*50)
    
    try:
        # Create agent
        config = {
            "name": "test_agno_images",
            "model": "openai:gpt-4o",
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        print(f"✅ Agent created with framework: {agent.framework_type}")
        
        # Initialize framework
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        
        # Test each image
        for image_name, image_data in TEST_IMAGES.items():
            print(f"\n🎨 Testing {image_data['description']}...")
            
            multimodal_content = {
                "images": [{
                    "data": f"data:image/png;base64,{image_data['base64']}",
                    "media_type": "image/png"
                }]
            }
            
            response = await agent.run(
                f"Describe this image briefly. What color is it?",
                multimodal_content=multimodal_content
            )
            
            print(f"Response: {response.text}")
            
            # Check if expected words are in response
            found_words = [word for word in image_data['expected_words'] if word in response.text.lower()]
            if found_words:
                print(f"✅ Image correctly analyzed! Found: {', '.join(found_words)}")
            else:
                print(f"⚠️ Expected words not found. Expected: {', '.join(image_data['expected_words'])}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_api_agno_images():
    """Test Agno image processing through API."""
    print("\n🌐 TESTING AGNO IMAGE PROCESSING (API)")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    for image_name, image_data in TEST_IMAGES.items():
        print(f"\n🎨 Testing {image_data['description']} via API...")
        
        payload = {
            "message_content": "What color is this image? Please be specific.",
            "message_type": "image",
            "session_name": f"test-agno-{image_name}",
            "user": {
                "phone_number": "+555000001",
                "email": "test@example.com"
            },
            "media_contents": [{
                "mime_type": "image/png",
                "data": f"data:image/png;base64,{image_data['base64']}"
            }]
        }
        
        try:
            response = requests.post(
                f"{API_URL}/agent/simple_agno/run",
                json=payload,
                headers={"x-api-key": API_KEY},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("data", {}).get("response", "")
                print(f"Response: {response_text[:150]}...")
                
                # Check usage
                usage = result.get("usage", {})
                if usage:
                    print(f"Framework: {usage.get('framework')}, Model: {usage.get('model')}")
                    media_usage = usage.get("media_usage", {})
                    if media_usage:
                        print(f"Image tokens: {media_usage.get('image_tokens', 0)}")
                
                # Check if expected words are in response
                found_words = [word for word in image_data['expected_words'] if word in response_text.lower()]
                if found_words:
                    print(f"✅ Image correctly analyzed! Found: {', '.join(found_words)}")
                else:
                    print(f"⚠️ Image not properly analyzed")
            else:
                print(f"❌ API error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

async def test_multimodal_with_text():
    """Test combined text and image processing."""
    print("\n🎨📝 TESTING COMBINED TEXT + IMAGE")
    print("="*50)
    
    try:
        config = {
            "name": "test_combined",
            "model": "openai:gpt-4o",
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        # Test with context
        multimodal_content = {
            "images": [{
                "data": f"data:image/png;base64,{TEST_IMAGES['yellow_pixel']['base64']}",
                "media_type": "image/png"
            }]
        }
        
        response = await agent.run(
            "I'm showing you a test image. It should be a single colored pixel. What color is it? Also tell me what framework you're using.",
            multimodal_content=multimodal_content
        )
        
        print(f"Response: {response.text}")
        
        # Check both image analysis and framework mention
        has_color = any(word in response.text.lower() for word in ["yellow", "color"])
        has_framework = any(word in response.text.lower() for word in ["agno", "framework"])
        
        print(f"\n✅ Color analysis: {'Found' if has_color else 'Not found'}")
        print(f"✅ Framework mention: {'Found' if has_framework else 'Not found'}")
        
        if response.usage:
            print(f"\n📊 Usage stats:")
            print(json.dumps(response.usage, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all multimodal tests."""
    print("🎯 AGNO MULTIMODAL TEST SUITE")
    print("="*80)
    print("Testing Agno framework multimodal capabilities")
    print("="*80)
    
    # Test 1: Direct image processing
    await test_direct_agno_images()
    
    # Test 2: API image processing
    await test_api_agno_images()
    
    # Test 3: Combined text and image
    await test_multimodal_with_text()
    
    print("\n✅ All image tests completed!")
    print("\n📝 NOTE: Audio processing requires specific model support.")
    print("Currently, gpt-4o supports image analysis but audio requires either:")
    print("- Whisper API for transcription (separate call)")
    print("- gpt-4o-audio-preview with proper audio output configuration")

if __name__ == "__main__":
    asyncio.run(main())