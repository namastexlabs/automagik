#!/usr/bin/env python3
"""
Test Simple Agno Agent Multimodal Functionality

Tests the simple_agno agent specifically to ensure:
1. Image processing is working correctly
2. Audio processing is working 
3. Multimodal usage tracking is working
4. Comparison with regular simple agent
"""

import requests
import json
import base64
import os
import time
from typing import Dict, Any

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")

def test_simple_agno_text() -> Dict[str, Any]:
    """Test simple_agno agent with text input."""
    print("\n📝 TESTING SIMPLE_AGNO TEXT")
    print("="*50)
    
    payload = {
        "message_content": "Hello! Can you tell me about multimodal AI capabilities in exactly 30 words?",
        "message_type": "text",
        "session_name": "test-simple-agno-text",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Agno Test"}
        }
    }
    
    start_time = time.time()
    
    try:
        print(f"🚀 Sending text request to simple_agno agent...")
        response = requests.post(
            f"{API_URL}/agent/simple_agno/run",
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
                "agent": "simple_agno",
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
                "agent": "simple_agno",
                "test_type": "text",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "agent": "simple_agno",
            "test_type": "text",
            "error": str(e),
            "processing_time": processing_time
        }

def test_simple_agno_image() -> Dict[str, Any]:
    """Test simple_agno agent with image input."""
    print("\n🖼️ TESTING SIMPLE_AGNO IMAGE PROCESSING")
    print("="*50)
    
    # Create a simple test image (1x1 pixel PNG)
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    payload = {
        "message_content": "Please analyze this image in detail. Describe what you see, including colors, objects, and any patterns. Be specific about what's in the image.",
        "message_type": "image",
        "session_name": "test-simple-agno-image",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Agno Test"}
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
        print(f"🚀 Sending image request to simple_agno agent...")
        response = requests.post(
            f"{API_URL}/agent/simple_agno/run",
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
            
            # Check if response mentions image analysis
            response_text = result.get("data", {}).get("response", "")
            if any(word in response_text.lower() for word in ["image", "picture", "visual", "see", "color", "pixel"]):
                print("🎯 Response contains image analysis - multimodal processing working!")
            else:
                print("⚠️ Response doesn't mention image content - multimodal processing may not be working")
            
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
                "agent": "simple_agno",
                "test_type": "image",
                "processing_time": processing_time,
                "usage": usage,
                "response_content": response_text[:200] + "...",
                "has_image_analysis": any(word in response_text.lower() for word in ["image", "picture", "visual", "see", "color", "pixel"])
            }
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "agent": "simple_agno",
                "test_type": "image",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "agent": "simple_agno",
            "test_type": "image",
            "error": str(e),
            "processing_time": processing_time
        }

def test_simple_agno_audio() -> Dict[str, Any]:
    """Test simple_agno agent with audio input."""
    print("\n🎵 TESTING SIMPLE_AGNO AUDIO PROCESSING")
    print("="*50)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return {
            "success": False,
            "agent": "simple_agno",
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
            "agent": "simple_agno",
            "test_type": "audio",
            "error": f"Failed to load audio: {e}",
            "processing_time": 0
        }
    
    payload = {
        "message_content": "Please transcribe this audio file and provide a detailed analysis of what you hear, including any speech, sounds, music, or background noise.",
        "message_type": "audio",
        "session_name": "test-simple-agno-audio",
        "user": {
            "phone_number": "+555000001",
            "email": "test@example.com",
            "user_data": {"name": "Agno Test"}
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
        print(f"🚀 Sending audio request to simple_agno agent...")
        response = requests.post(
            f"{API_URL}/agent/simple_agno/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
        
        processing_time = time.time() - start_time
        print(f"⏱️ Request completed in {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Audio request successful!")
            
            # Check if response mentions audio analysis
            response_text = result.get("data", {}).get("response", "")
            if any(word in response_text.lower() for word in ["audio", "sound", "hear", "voice", "speech", "transcrib"]):
                print("🎯 Response contains audio analysis - multimodal processing working!")
            else:
                print("⚠️ Response doesn't mention audio content - multimodal processing may not be working")
            
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
                "agent": "simple_agno",
                "test_type": "audio",
                "processing_time": processing_time,
                "usage": usage,
                "response_content": response_text[:200] + "...",
                "has_audio_analysis": any(word in response_text.lower() for word in ["audio", "sound", "hear", "voice", "speech", "transcrib"])
            }
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "agent": "simple_agno",
                "test_type": "audio",
                "error": f"HTTP {response.status_code}: {response.text}",
                "processing_time": processing_time
            }
            
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Request failed with exception: {e}")
        return {
            "success": False,
            "agent": "simple_agno",
            "test_type": "audio",
            "error": str(e),
            "processing_time": processing_time
        }

def compare_agents(simple_results: list, agno_results: list) -> None:
    """Compare results between simple and simple_agno agents."""
    print("\n" + "="*80)
    print("📊 AGENT COMPARISON: SIMPLE vs SIMPLE_AGNO")
    print("="*80)
    
    successful_simple = [r for r in simple_results if r.get("success", False)]
    successful_agno = [r for r in agno_results if r.get("success", False)]
    
    print(f"\n🎯 Success Rate:")
    print(f"  Simple Agent: {len(successful_simple)}/{len(simple_results)} ({len(successful_simple)/len(simple_results)*100:.1f}%)")
    print(f"  Simple_Agno Agent: {len(successful_agno)}/{len(agno_results)} ({len(successful_agno)/len(agno_results)*100:.1f}%)")
    
    if successful_simple and successful_agno:
        print(f"\n📋 Detailed Comparison:")
        print(f"{'Type':<10} {'Agent':<12} {'Framework':<12} {'Model':<20} {'Tokens':<10} {'Content Types':<20} {'Multimodal':<12}")
        print("-" * 110)
        
        for result in successful_simple:
            usage = result.get("usage", {})
            test_type = result["test_type"]
            framework = usage.get("framework", "unknown")
            model = usage.get("model", "unknown")
            tokens = usage.get("total_tokens", 0)
            content_types = ", ".join(usage.get("content_types", [])) if usage.get("content_types") else "none"
            multimodal = "✅" if result.get("has_image_analysis") or result.get("has_audio_analysis") else "❌"
            
            print(f"{test_type:<10} {'simple':<12} {framework:<12} {model:<20} {tokens:<10} {content_types:<20} {multimodal:<12}")
        
        for result in successful_agno:
            usage = result.get("usage", {})
            test_type = result["test_type"]
            framework = usage.get("framework", "unknown")
            model = usage.get("model", "unknown")
            tokens = usage.get("total_tokens", 0)
            content_types = ", ".join(usage.get("content_types", [])) if usage.get("content_types") else "none"
            multimodal = "✅" if result.get("has_image_analysis") or result.get("has_audio_analysis") else "❌"
            
            print(f"{test_type:<10} {'simple_agno':<12} {framework:<12} {model:<20} {tokens:<10} {content_types:<20} {multimodal:<12}")
        
        # Framework analysis
        simple_frameworks = [r.get("usage", {}).get("framework") for r in successful_simple]
        agno_frameworks = [r.get("usage", {}).get("framework") for r in successful_agno]
        
        print(f"\n🔧 Framework Usage:")
        print(f"  Simple Agent: {set(simple_frameworks)}")
        print(f"  Simple_Agno Agent: {set(agno_frameworks)}")
        
        # Multimodal capability analysis
        simple_multimodal = sum(1 for r in successful_simple if r.get("has_image_analysis") or r.get("has_audio_analysis"))
        agno_multimodal = sum(1 for r in successful_agno if r.get("has_image_analysis") or r.get("has_audio_analysis"))
        
        print(f"\n🎭 Multimodal Processing:")
        print(f"  Simple Agent: {simple_multimodal}/{len(successful_simple)} requests processed multimodal content")
        print(f"  Simple_Agno Agent: {agno_multimodal}/{len(successful_agno)} requests processed multimodal content")
        
        if agno_multimodal > simple_multimodal:
            print("✅ Simple_Agno shows better multimodal capabilities!")
        elif agno_multimodal == simple_multimodal:
            print("⚖️ Both agents have similar multimodal capabilities")
        else:
            print("⚠️ Simple agent shows better multimodal capabilities than Simple_Agno")

def main():
    """Run comprehensive simple_agno agent tests."""
    print("🧪 SIMPLE_AGNO AGENT MULTIMODAL TEST")
    print("="*80)
    print("Testing simple_agno agent multimodal capabilities and usage tracking")
    print("="*80)
    
    agno_results = []
    
    # Test simple_agno agent
    print("\n🚀 TESTING SIMPLE_AGNO AGENT")
    print("="*50)
    
    # Test 1: Text input
    text_result = test_simple_agno_text()
    agno_results.append(text_result)
    
    # Small delay between requests
    time.sleep(2)
    
    # Test 2: Image input
    image_result = test_simple_agno_image()
    agno_results.append(image_result)
    
    # Small delay between requests
    time.sleep(2)
    
    # Test 3: Audio input
    audio_result = test_simple_agno_audio()
    agno_results.append(audio_result)
    
    # For comparison, also test regular simple agent
    print("\n🔄 TESTING REGULAR SIMPLE AGENT FOR COMPARISON")
    print("="*50)
    
    simple_results = []
    
    # Quick test of simple agent with image
    simple_image_payload = {
        "message_content": "Please analyze this image in detail.",
        "message_type": "image",
        "session_name": "test-simple-comparison",
        "user": {"phone_number": "+555000001", "email": "test@example.com"},
        "media_contents": [{"mime_type": "image/png", "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}]
    }
    
    try:
        response = requests.post(f"{API_URL}/agent/simple/run", json=simple_image_payload, headers={"x-api-key": API_KEY}, timeout=30.0)
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("data", {}).get("response", "")
            simple_results.append({
                "success": True,
                "agent": "simple",
                "test_type": "image",
                "usage": result.get("usage", {}),
                "has_image_analysis": any(word in response_text.lower() for word in ["image", "picture", "visual", "see", "color", "pixel"])
            })
        else:
            simple_results.append({"success": False, "agent": "simple", "test_type": "image", "error": f"HTTP {response.status_code}"})
    except Exception as e:
        simple_results.append({"success": False, "agent": "simple", "test_type": "image", "error": str(e)})
    
    # Analysis
    compare_agents(simple_results, agno_results)
    
    # Final summary
    print(f"\n🎉 SIMPLE_AGNO MULTIMODAL TEST COMPLETE!")
    
    successful_agno = [r for r in agno_results if r.get("success", False)]
    multimodal_working = sum(1 for r in successful_agno if r.get("has_image_analysis") or r.get("has_audio_analysis"))
    
    print(f"\n📊 Results Summary:")
    print(f"✅ Simple_Agno Success Rate: {len(successful_agno)}/{len(agno_results)}")
    print(f"🎭 Multimodal Processing: {multimodal_working}/{len(successful_agno)} requests")
    
    # Check if Agno framework is being used
    agno_frameworks = [r.get("usage", {}).get("framework") for r in successful_agno]
    using_agno = "agno" in agno_frameworks
    
    if using_agno:
        print("✅ Simple_Agno is correctly using Agno framework!")
    else:
        print("⚠️ Simple_Agno is not using Agno framework - may need configuration check")
    
    # Check usage tracking
    has_usage_data = all(r.get("usage") for r in successful_agno)
    if has_usage_data:
        print("✅ Usage tracking working for Simple_Agno!")
    else:
        print("⚠️ Usage tracking incomplete for Simple_Agno")

if __name__ == "__main__":
    main()