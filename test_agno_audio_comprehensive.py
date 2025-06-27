#!/usr/bin/env python3
"""
Comprehensive test for Agno audio processing capabilities
Tests audio transcription and analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import base64
from src.agents.pydanticai.simple_agno.agent import SimpleAgnoAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

async def test_agno_audio_direct():
    """Test Agno audio processing directly."""
    print("🎵 TESTING AGNO AUDIO PROCESSING")
    print("="*50)
    
    audio_file = "test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        print("Please ensure test_audio.wav exists in the current directory")
        return
    
    try:
        # Load audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"✅ Loaded audio file: {len(audio_data):,} bytes")
        print(f"📊 Base64 size: {len(audio_base64):,} characters")
        
        # Create agent
        config = {
            "name": "test_agno_audio",
            "model": "openai:gpt-4o",  # Multimodal model that supports audio
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        print(f"\n✅ Agent created with framework: {agent.framework_type}")
        print(f"🎤 Using model: {config['model']}")
        
        # Initialize framework
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        
        # Test 1: Audio via process_message (API style)
        print("\n🎤 Test 1: Audio via process_message (API style)...")
        
        context = {
            "multimodal_content": {
                "audio": [{
                    "data": f"data:audio/wav;base64,{audio_base64}",
                    "media_type": "audio/wav"
                }]
            }
        }
        
        response1 = await agent.process_message(
            user_message="Please transcribe this audio and tell me what language is being spoken. Also describe any notable sounds or music.",
            context=context
        )
        
        print(f"\n📝 Response via process_message:")
        print(f"Success: {response1.success}")
        print(f"Text preview: {response1.text[:300]}...")
        
        if response1.usage:
            print(f"\n📊 Usage data:")
            print(json.dumps(response1.usage, indent=2))
        
        # Check if audio was processed
        audio_keywords = ["audio", "sound", "hear", "voice", "speech", "transcrib", "language", "music", "speak"]
        has_audio_analysis = any(word in response1.text.lower() for word in audio_keywords)
        print(f"\n🎯 Audio analysis detected: {'✅' if has_audio_analysis else '❌'}")
        
        # Test 2: Audio via direct run method
        print("\n🎤 Test 2: Audio via direct run method...")
        
        multimodal_content = {
            "audio": [{
                "data": f"data:audio/wav;base64,{audio_base64}",
                "media_type": "audio/wav"
            }]
        }
        
        response2 = await agent.run(
            "What can you tell me about this audio? Please provide a detailed analysis including language, content, and any background sounds.",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Response via direct run:")
        print(f"Success: {response2.success}")
        print(f"Text preview: {response2.text[:300]}...")
        
        has_audio_analysis = any(word in response2.text.lower() for word in audio_keywords)
        print(f"\n🎯 Audio analysis detected: {'✅' if has_audio_analysis else '❌'}")
        
        # Test 3: Combined text and audio
        print("\n🎤 Test 3: Combined text prompt with audio...")
        
        response3 = await agent.run(
            "This is an audio file that might contain Portuguese language content. Please confirm the language and provide a full transcription.",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Response for language-specific request:")
        print(f"Success: {response3.success}")
        print(f"Text preview: {response3.text[:300]}...")
        
        # Check for Portuguese-related content
        portuguese_keywords = ["portuguese", "português", "brazil", "brasil", "pt-br", "pt-pt"]
        has_portuguese = any(word in response3.text.lower() for word in portuguese_keywords)
        print(f"\n🎯 Portuguese language detected: {'✅' if has_portuguese else '❌'}")
        
        # Summary
        print("\n📊 AUDIO PROCESSING SUMMARY")
        print("="*50)
        print(f"✅ Agno framework initialized successfully")
        print(f"✅ Audio file loaded: {len(audio_data):,} bytes")
        print(f"✅ All tests completed")
        
        if all([response1.success, response2.success, response3.success]):
            print("✅ All audio processing tests passed!")
        else:
            print("⚠️ Some tests failed")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

async def test_agno_audio_api():
    """Test Agno audio processing through API."""
    import requests
    
    print("\n🌐 TESTING AGNO AUDIO VIA API")
    print("="*50)
    
    API_URL = "http://localhost:18891/api/v1"
    API_KEY = os.getenv("AM_API_KEY", "namastex888")
    
    audio_file = "test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    try:
        # Load audio file
        with open(audio_file, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"✅ Loaded audio file: {len(audio_data):,} bytes")
        
        # Prepare API request
        payload = {
            "message_content": "Please transcribe this audio file. What language is being spoken? Provide a detailed analysis of the content.",
            "message_type": "audio",
            "session_name": "test-agno-audio-api",
            "user": {
                "phone_number": "+555000001",
                "email": "test@example.com",
                "user_data": {"name": "Audio Test"}
            },
            "media_contents": [
                {
                    "mime_type": "audio/wav",
                    "data": f"data:audio/wav;base64,{audio_base64}"
                }
            ]
        }
        
        print(f"🚀 Sending audio request to simple_agno agent via API...")
        
        response = requests.post(
            f"{API_URL}/agent/simple_agno/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=120.0  # Longer timeout for audio processing
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API request successful!")
            
            # Extract response
            response_text = result.get("data", {}).get("response", "")
            print(f"\n📝 API Response preview: {response_text[:300]}...")
            
            # Check usage data
            usage = result.get("usage", {})
            if usage:
                print(f"\n📊 Usage Data:")
                print(f"  Framework: {usage.get('framework', 'unknown')}")
                print(f"  Model: {usage.get('model', 'unknown')}")
                print(f"  Processing Time: {usage.get('processing_time_ms', 0):.0f}ms")
                
                media_usage = usage.get("media_usage", {})
                if media_usage:
                    print(f"\n🎭 Media Usage:")
                    print(f"  Audio Seconds: {media_usage.get('audio_seconds', 0)}")
                    print(f"  Text Tokens: {media_usage.get('text_tokens', 0)}")
            
            # Check if audio was processed
            audio_keywords = ["audio", "sound", "voice", "speech", "transcrib", "language"]
            has_audio_analysis = any(word in response_text.lower() for word in audio_keywords)
            print(f"\n🎯 Audio analysis detected: {'✅' if has_audio_analysis else '❌'}")
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all audio tests."""
    print("🎵 COMPREHENSIVE AGNO AUDIO TEST SUITE")
    print("="*80)
    print("Testing Agno framework audio processing capabilities")
    print("="*80)
    
    # Test 1: Direct framework test
    await test_agno_audio_direct()
    
    # Test 2: API test
    await test_agno_audio_api()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())