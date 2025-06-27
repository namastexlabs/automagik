#!/usr/bin/env python3
"""
Test Simple Agent with Different Input Types

Tests the simple agent with three different input types to validate
our simplified usage tracking system:
1. Text input
2. Image input  
3. Audio input
"""

import requests
import json
import base64
import os
import time
from typing import Dict, Any

# API configuration
API_URL = "http://localhost:18881/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")

def test_text_input() -> Dict[str, Any]:
    """Test simple agent with text-only input."""
    print("\n📝 TESTING TEXT INPUT")
    print("="*50)
    
    payload = {
        "message_content": "Explain the concept of machine learning in exactly 50 words.",
        "message_type": "text",
        "session_name": "test-simple-text-usage",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Usage Test"}
        }
    }
    
    start_time = time.time()
    
    try:
        print(f"🚀 Sending text request to simple agent...")
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        processing_time = time.time() - start_time
        print(f"⏱️ Request completed in {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Text request successful!")
            
            # Extract and display usage data
            usage = result.get("usage", {})
            if usage:
                print("\n📊 Usage Data:")
                print(f"  🔧 Framework: {usage.get('framework', 'unknown')}")
                print(f"  🤖 Model: {usage.get('model', 'unknown')}")
                print(f"  📥 Input Tokens: {usage.get('request_tokens', 0)}")
                print(f"  📤 Output Tokens: {usage.get('response_tokens', 0)}")
                print(f"  📊 Total Tokens: {usage.get('total_tokens', 0)}")
                print(f"  🎯 Content Types: {usage.get('content_types', [])}")
                print(f"  ⏱️ Processing Time: {usage.get('processing_time_ms', 0):.0f}ms")
            
            return {
                "success": True,
                "test_type": "text",
                "processing_time": processing_time,
                "usage": usage,
                "response_content": result.get("data", {}).get("response", "")[:100] + "..."
            }
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "test_type": "text",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "test_type": "text",
            "error": str(e),
            "processing_time": processing_time
        }

def test_image_input() -> Dict[str, Any]:
    """Test simple agent with image input."""
    print("\n🖼️ TESTING IMAGE INPUT")
    print("="*50)
    
    # Create a simple test image (1x1 pixel PNG)
    # This is a minimal PNG file in base64
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    payload = {
        "message_content": "Please describe this image and tell me what you can see.",
        "message_type": "image",
        "session_name": "test-simple-image-usage",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Usage Test"}
        },
        "media_contents": [
            {
                "mime_type": "image/png",
                "data": f"data:image/png;base64,{test_image_base64}"
            }
        ]
    }
    
    start_time = time.time()
    
    try:
        print(f"🚀 Sending image request to simple agent...")
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
        processing_time = time.time() - start_time
        print(f"⏱️ Request completed in {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Image request successful!")
            
            # Extract and display usage data
            usage = result.get("usage", {})
            if usage:
                print("\n📊 Usage Data:")
                print(f"  🔧 Framework: {usage.get('framework', 'unknown')}")
                print(f"  🤖 Model: {usage.get('model', 'unknown')}")
                print(f"  📥 Input Tokens: {usage.get('request_tokens', 0)}")
                print(f"  📤 Output Tokens: {usage.get('response_tokens', 0)}")
                print(f"  📊 Total Tokens: {usage.get('total_tokens', 0)}")
                print(f"  🎯 Content Types: {usage.get('content_types', [])}")
                print(f"  ⏱️ Processing Time: {usage.get('processing_time_ms', 0):.0f}ms")
                
                # Check for multimodal usage
                media_usage = usage.get("media_usage", {})
                if media_usage:
                    print(f"\n🎭 Media Usage:")
                    print(f"  - Text Tokens: {media_usage.get('text_tokens', 0)}")
                    print(f"  - Image Tokens: {media_usage.get('image_tokens', 0)}")
                    print(f"  - Audio Seconds: {media_usage.get('audio_seconds', 0)}")
            
            return {
                "success": True,
                "test_type": "image",
                "processing_time": processing_time,
                "usage": usage,
                "response_content": result.get("data", {}).get("response", "")[:100] + "..."
            }
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "test_type": "image",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "test_type": "image",
            "error": str(e),
            "processing_time": processing_time
        }

def test_audio_input() -> Dict[str, Any]:
    """Test simple agent with audio input."""
    print("\n🎵 TESTING AUDIO INPUT")
    print("="*50)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return {
            "success": False,
            "test_type": "audio",
            "error": f"Audio file not found: {audio_file}",
            "processing_time": 0
        }
    
    # Load and encode audio file
    try:
        with open(audio_file, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"📂 Loaded audio file: {len(audio_data)} bytes")
    except Exception as e:
        print(f"❌ Failed to load audio file: {e}")
        return {
            "success": False,
            "test_type": "audio",
            "error": f"Failed to load audio: {e}",
            "processing_time": 0
        }
    
    payload = {
        "message_content": "Please transcribe this audio and tell me what you hear.",
        "message_type": "audio",
        "session_name": "test-simple-audio-usage",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Usage Test"}
        },
        "media_contents": [
            {
                "mime_type": "audio/wav",
                "data": f"data:audio/wav;base64,{audio_base64}"
            }
        ]
    }
    
    start_time = time.time()
    
    try:
        print(f"🚀 Sending audio request to simple agent...")
        response = requests.post(
            f"{API_URL}/agent/simple/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=90.0
        )
        
        processing_time = time.time() - start_time
        print(f"⏱️ Request completed in {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Audio request successful!")
            
            # Extract and display usage data
            usage = result.get("usage", {})
            if usage:
                print("\n📊 Usage Data:")
                print(f"  🔧 Framework: {usage.get('framework', 'unknown')}")
                print(f"  🤖 Model: {usage.get('model', 'unknown')}")
                print(f"  📥 Input Tokens: {usage.get('request_tokens', 0)}")
                print(f"  📤 Output Tokens: {usage.get('response_tokens', 0)}")
                print(f"  📊 Total Tokens: {usage.get('total_tokens', 0)}")
                print(f"  🎯 Content Types: {usage.get('content_types', [])}")
                print(f"  ⏱️ Processing Time: {usage.get('processing_time_ms', 0):.0f}ms")
                
                # Check for multimodal usage
                media_usage = usage.get("media_usage", {})
                if media_usage:
                    print(f"\n🎭 Media Usage:")
                    print(f"  - Text Tokens: {media_usage.get('text_tokens', 0)}")
                    print(f"  - Image Tokens: {media_usage.get('image_tokens', 0)}")
                    print(f"  - Audio Seconds: {media_usage.get('audio_seconds', 0)}")
            
            return {
                "success": True,
                "test_type": "audio",
                "processing_time": processing_time,
                "usage": usage,
                "response_content": result.get("data", {}).get("response", "")[:100] + "..."
            }
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "test_type": "audio",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "test_type": "audio",
            "error": str(e),
            "processing_time": processing_time
        }

def analyze_usage_comparison(results: list) -> None:
    """Analyze usage patterns across different input types."""
    print("\n" + "="*80)
    print("📊 USAGE TRACKING ANALYSIS")
    print("="*80)
    
    successful_results = [r for r in results if r.get("success", False)]
    
    if not successful_results:
        print("❌ No successful requests to analyze")
        return
    
    print(f"\n🎯 Summary: {len(successful_results)}/{len(results)} requests successful")
    
    # Create comparison table
    print(f"\n📋 Usage Comparison:")
    print(f"{'Type':<10} {'Framework':<12} {'Model':<20} {'Tokens':<10} {'Content Types':<20} {'Time':<8}")
    print("-" * 85)
    
    total_tokens = 0
    frameworks = set()
    models = set()
    content_types = set()
    
    for result in successful_results:
        usage = result.get("usage", {})
        
        test_type = result["test_type"]
        framework = usage.get("framework", "unknown")
        model = usage.get("model", "unknown")
        tokens = usage.get("total_tokens", 0)
        content_list = usage.get("content_types", [])
        content_str = ", ".join(content_list) if content_list else "none"
        processing_time = result["processing_time"]
        
        print(f"{test_type:<10} {framework:<12} {model:<20} {tokens:<10} {content_str:<20} {processing_time:<7.2f}s")
        
        # Collect stats
        total_tokens += tokens
        frameworks.add(framework)
        models.add(model)
        content_types.update(content_list)
    
    # Analysis
    print(f"\n💡 Analysis:")
    print(f"  📊 Total Tokens Used: {total_tokens}")
    print(f"  🔧 Frameworks Used: {', '.join(frameworks)}")
    print(f"  🤖 Models Used: {', '.join(models)}")
    print(f"  🎭 Content Types: {', '.join(content_types)}")
    
    # Check if usage tracking is working
    tracking_issues = []
    
    for result in successful_results:
        usage = result.get("usage", {})
        test_type = result["test_type"]
        
        if not usage:
            tracking_issues.append(f"{test_type}: No usage data")
        elif not usage.get("framework"):
            tracking_issues.append(f"{test_type}: Missing framework")
        elif not usage.get("model"):
            tracking_issues.append(f"{test_type}: Missing model")
        elif not usage.get("content_types"):
            tracking_issues.append(f"{test_type}: Missing content types")
    
    if tracking_issues:
        print(f"\n⚠️ Usage Tracking Issues:")
        for issue in tracking_issues:
            print(f"  - {issue}")
    else:
        print(f"\n✅ Usage tracking working perfectly!")
        print(f"✅ All requests have complete usage data")
        print(f"✅ Framework, model, and content types all tracked")
        
        # Check multimodal awareness
        multimodal_results = [r for r in successful_results if r["test_type"] in ["image", "audio"]]
        if multimodal_results:
            multimodal_with_tracking = [
                r for r in multimodal_results 
                if r.get("usage", {}).get("media_usage")
            ]
            if multimodal_with_tracking:
                print(f"✅ Multimodal usage tracking working: {len(multimodal_with_tracking)}/{len(multimodal_results)} requests")
            else:
                print(f"⚠️ Multimodal usage tracking missing")

def main():
    """Run all three test scenarios."""
    print("🧪 SIMPLE AGENT USAGE TRACKING TEST")
    print("="*80)
    print("Testing text, image, and audio inputs with simplified usage tracking")
    print("="*80)
    
    results = []
    
    # Test 1: Text input
    text_result = test_text_input()
    results.append(text_result)
    
    # Small delay between requests
    time.sleep(2)
    
    # Test 2: Image input
    image_result = test_image_input()
    results.append(image_result)
    
    # Small delay between requests
    time.sleep(2)
    
    # Test 3: Audio input
    audio_result = test_audio_input()
    results.append(audio_result)
    
    # Analyze results
    analyze_usage_comparison(results)
    
    print(f"\n🎉 SIMPLE AGENT USAGE TEST COMPLETE!")
    print("This validates our simplified usage tracking system focusing on:")
    print("✅ Token counting (input/output/total)")
    print("✅ Model identification per request")
    print("✅ Content type attribution (text/image/audio)")
    print("✅ Framework tracking (PydanticAI vs Agno)")
    print("🚫 No pricing calculations - pure usage metrics!")

if __name__ == "__main__":
    main()