#!/usr/bin/env python3
"""
Comprehensive API Test for All Media Types (Text, Image, Audio)
Tests usage tracking across different frameworks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import base64
import requests
import time

# Test data
TEST_IMAGES = {
    "yellow_pixel": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
    "red_pixel": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
}

def test_api_text_only():
    """Test text-only API call with usage tracking."""
    print("📝 TESTING API - TEXT ONLY")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    payload = {
        "message_content": "Hello! What's your name and what are your capabilities? Please be detailed about your multimodal abilities.",
        "message_type": "text",
        "session_name": "test-api-text-only",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com"
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=30.0
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Text API call successful!")
            
            response_text = result.get("data", {}).get("response", "")
            print(f"📝 Response preview: {response_text[:300]}...")
            
            # Check usage tracking
            usage = result.get("usage", {})
            if usage:
                print(f"\n📊 Usage Tracking:")
                print(f"  Framework: {usage.get('framework', 'unknown')}")
                print(f"  Model: {usage.get('model', 'unknown')}")
                print(f"  Request tokens: {usage.get('request_tokens', 0)}")
                print(f"  Response tokens: {usage.get('response_tokens', 0)}")
                print(f"  Total tokens: {usage.get('total_tokens', 0)}")
                print(f"  Processing time: {usage.get('processing_time_ms', 0):.0f}ms")
                print(f"  Content types: {usage.get('content_types', [])}")
                
                # Check for proper text framework usage
                expected_framework = "pydantic_ai"  # Should use PydanticAI for text
                actual_framework = usage.get('framework', 'unknown')
                print(f"\n🎯 Framework Check: {'✅' if actual_framework == expected_framework else '❌'} Expected: {expected_framework}, Got: {actual_framework}")
            else:
                print("❌ No usage data returned")
            
            # Check response time
            api_time = (end_time - start_time) * 1000
            processing_time = usage.get('processing_time_ms', 0)
            print(f"\n⏱️ Performance:")
            print(f"  API round-trip: {api_time:.0f}ms")
            print(f"  Agent processing: {processing_time:.0f}ms")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return usage if 'usage' in locals() else None

def test_api_image_analysis():
    """Test image analysis API call with usage tracking."""
    print("\n🖼️ TESTING API - IMAGE ANALYSIS")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    payload = {
        "message_content": "Please analyze this image in detail. What color is it? What do you see?",
        "message_type": "image",
        "session_name": "test-api-image",
        "user": {
            "phone_number": "+555000002", 
            "email": "test@example.com"
        },
        "media_contents": [{
            "mime_type": "image/png",
            "data": f"data:image/png;base64,{TEST_IMAGES['yellow_pixel']}"
        }]
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=45.0
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Image API call successful!")
            
            response_text = result.get("data", {}).get("response", "")
            print(f"📝 Response preview: {response_text[:400]}...")
            
            # Check for image analysis
            image_keywords = ["yellow", "color", "image", "pixel", "bright"]
            has_image_analysis = any(word in response_text.lower() for word in image_keywords)
            print(f"\n🎯 Image Analysis: {'✅ Detected' if has_image_analysis else '❌ Not detected'}")
            
            # Check usage tracking
            usage = result.get("usage", {})
            if usage:
                print(f"\n📊 Usage Tracking:")
                print(f"  Framework: {usage.get('framework', 'unknown')}")
                print(f"  Model: {usage.get('model', 'unknown')}")
                print(f"  Request tokens: {usage.get('request_tokens', 0)}")
                print(f"  Response tokens: {usage.get('response_tokens', 0)}")
                print(f"  Total tokens: {usage.get('total_tokens', 0)}")
                print(f"  Processing time: {usage.get('processing_time_ms', 0):.0f}ms")
                print(f"  Content types: {usage.get('content_types', [])}")
                
                # Check media-specific usage
                media_usage = usage.get('media_usage', {})
                if media_usage:
                    print(f"\n🎭 Media Usage:")
                    print(f"  Image tokens: {media_usage.get('image_tokens', 0)}")
                    print(f"  Text tokens: {media_usage.get('text_tokens', 0)}")
                
                # Framework should be auto-selected (likely PydanticAI for OpenAI vision or Agno)
                actual_framework = usage.get('framework', 'unknown')
                print(f"\n🎯 Framework Used: {actual_framework}")
                
                # Content types should include image
                content_types = usage.get('content_types', [])
                has_image_content = 'image' in content_types
                print(f"🎯 Content Types: {'✅' if has_image_content else '❌'} Expected image in {content_types}")
            else:
                print("❌ No usage data returned")
            
            # Performance check
            api_time = (end_time - start_time) * 1000
            processing_time = usage.get('processing_time_ms', 0) if usage else 0
            print(f"\n⏱️ Performance:")
            print(f"  API round-trip: {api_time:.0f}ms")
            print(f"  Agent processing: {processing_time:.0f}ms")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return usage if 'usage' in locals() else None

def test_api_audio_analysis():
    """Test audio analysis API call with usage tracking."""
    print("\n🎵 TESTING API - AUDIO ANALYSIS")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1" 
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    # Load the Pirarucu audio file
    audio_path = "/mnt/c/Users/cezar/Downloads/Piraruvite-de-Pirarucu.wav"
    if sys.platform == "win32":
        audio_path = "C:\\Users\\cezar\\Downloads\\Piraruvite-de-Pirarucu.wav"
    
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        print("Skipping audio test...")
        return None
    
    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"✅ Loaded audio file: {len(audio_data):,} bytes")
        
        payload = {
            "message_content": "Please transcribe and analyze this audio. What language is being spoken? What is the content about?",
            "message_type": "audio",
            "session_name": "test-api-audio",
            "user": {
                "phone_number": "+555000003",
                "email": "test@example.com"
            },
            "media_contents": [{
                "mime_type": "audio/wav",
                "data": f"data:audio/wav;base64,{audio_base64}"
            }]
        }
        
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=120.0  # Audio processing takes longer
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Audio API call successful!")
            
            response_text = result.get("data", {}).get("response", "")
            print(f"📝 Response preview: {response_text[:500]}...")
            
            # Check for audio analysis
            audio_keywords = ["audio", "pirarucu", "portuguese", "transcrib", "music", "song"]
            has_audio_analysis = any(word in response_text.lower() for word in audio_keywords)
            print(f"\n🎯 Audio Analysis: {'✅ Detected' if has_audio_analysis else '❌ Not detected'}")
            
            # Check usage tracking
            usage = result.get("usage", {})
            if usage:
                print(f"\n📊 Usage Tracking:")
                print(f"  Framework: {usage.get('framework', 'unknown')}")
                print(f"  Model: {usage.get('model', 'unknown')}")
                print(f"  Request tokens: {usage.get('request_tokens', 0)}")
                print(f"  Response tokens: {usage.get('response_tokens', 0)}")
                print(f"  Total tokens: {usage.get('total_tokens', 0)}")
                print(f"  Processing time: {usage.get('processing_time_ms', 0):.0f}ms")
                print(f"  Content types: {usage.get('content_types', [])}")
                
                # Check media-specific usage
                media_usage = usage.get('media_usage', {})
                if media_usage:
                    print(f"\n🎭 Media Usage:")
                    print(f"  Audio seconds: {media_usage.get('audio_seconds', 0)}")
                    print(f"  Text tokens: {media_usage.get('text_tokens', 0)}")
                    print(f"  Preprocessing time: {media_usage.get('preprocessing_ms', 0):.0f}ms")
                
                # Framework should be Agno for audio (best performance)
                actual_framework = usage.get('framework', 'unknown')
                expected_framework = "agno"  # Should use Agno for audio
                print(f"\n🎯 Framework Check: {'✅' if actual_framework == expected_framework else '⚠️'} Expected: {expected_framework}, Got: {actual_framework}")
                
                # Content types should include audio
                content_types = usage.get('content_types', [])
                has_audio_content = 'audio' in content_types
                print(f"🎯 Content Types: {'✅' if has_audio_content else '❌'} Expected audio in {content_types}")
            else:
                print("❌ No usage data returned")
            
            # Performance check 
            api_time = (end_time - start_time) * 1000
            processing_time = usage.get('processing_time_ms', 0) if usage else 0
            print(f"\n⏱️ Performance:")
            print(f"  API round-trip: {api_time:.0f}ms")
            print(f"  Agent processing: {processing_time:.0f}ms")
            print(f"  Audio file size: {len(audio_data):,} bytes")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return usage if 'usage' in locals() else None

def test_usage_comparison():
    """Compare usage tracking across different media types."""
    print("\n📊 USAGE TRACKING COMPARISON")
    print("="*50)
    
    # Run all tests and collect usage data
    text_usage = test_api_text_only()
    image_usage = test_api_image_analysis()
    audio_usage = test_api_audio_analysis()
    
    print("\n📈 FRAMEWORK USAGE SUMMARY")
    print("-" * 30)
    
    tests = [
        ("Text", text_usage),
        ("Image", image_usage), 
        ("Audio", audio_usage)
    ]
    
    for test_name, usage in tests:
        if usage:
            framework = usage.get('framework', 'unknown')
            model = usage.get('model', 'unknown')
            total_tokens = usage.get('total_tokens', 0)
            processing_time = usage.get('processing_time_ms', 0)
            content_types = usage.get('content_types', [])
            
            print(f"\n{test_name}:")
            print(f"  Framework: {framework}")
            print(f"  Model: {model}")
            print(f"  Tokens: {total_tokens}")
            print(f"  Time: {processing_time:.0f}ms")
            print(f"  Content: {content_types}")
        else:
            print(f"\n{test_name}: ❌ No usage data")
    
    print("\n✅ USAGE TRACKING ANALYSIS COMPLETE")
    print("- Text should use PydanticAI framework")
    print("- Image should use PydanticAI or Agno (auto-selected)")
    print("- Audio should use Agno framework (best performance)")
    print("- All should have proper token counting and timing")
    print("- Content types should match media type")

def main():
    """Run comprehensive API tests for all media types."""
    print("🎯 COMPREHENSIVE API MULTIMODAL TEST SUITE")
    print("="*80)
    print("Testing usage tracking across all frameworks and media types")
    print("="*80)
    
    test_usage_comparison()
    
    print(f"\n✅ All API tests completed!")
    print("\n📝 Key Findings:")
    print("- Framework selection should be automatic based on content type")
    print("- Usage tracking should work across PydanticAI and Agno frameworks")
    print("- Multimodal content should show proper media usage metrics")
    print("- Performance should be optimal for each content type")

if __name__ == "__main__":
    main()