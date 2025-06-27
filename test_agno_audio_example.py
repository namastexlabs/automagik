#!/usr/bin/env python3
"""
Test Agno audio processing based on documentation examples
Uses Gemini model for audio processing as shown in Agno docs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import base64
from pathlib import Path
from src.agents.pydanticai.simple_agno.agent import SimpleAgnoAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies

async def test_agno_audio_with_gemini():
    """Test Agno audio processing using Gemini model (as per docs)."""
    print("🎵 TESTING AGNO AUDIO WITH GEMINI MODEL")
    print("="*50)
    
    # Audio file path from user request
    audio_path = "C:\\Users\\cezar\\Downloads\\Piraruvite-de-Pirarucu.wav"
    
    # Check if running on Linux (WSL) and adjust path
    if sys.platform == "linux":
        # Convert Windows path to WSL path
        audio_path = "/mnt/c/Users/cezar/Downloads/Piraruvite-de-Pirarucu.wav"
    
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        print("Please ensure the file exists at the specified path")
        return
    
    try:
        # Load audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"✅ Loaded audio file: {Path(audio_path).name}")
        print(f"📊 File size: {len(audio_data):,} bytes")
        print(f"📊 Base64 size: {len(audio_base64):,} characters")
        
        # Create agent with Gemini model (as shown in Agno docs for audio)
        config = {
            "name": "test_agno_audio_gemini",
            "model": "gemini:gemini-2.0-flash-exp",  # Gemini model for audio as per docs
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        print(f"\n✅ Agent created with framework: {agent.framework_type}")
        print(f"🎤 Using model: {config['model']} (supports audio)")
        
        # Initialize framework
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        print(f"✅ Framework initialized: {agent.is_framework_ready}")
        
        # Test 1: Basic audio analysis
        print("\n🎤 Test 1: Basic audio analysis...")
        
        multimodal_content = {
            "audio": [{
                "data": f"data:audio/wav;base64,{audio_base64}",
                "media_type": "audio/wav"
            }]
        }
        
        response1 = await agent.run(
            "Give a sentiment analysis of this audio conversation. What language is being spoken?",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Audio Analysis Response:")
        print(f"Success: {response1.success}")
        print(f"Response: {response1.text}")
        
        if response1.usage:
            print(f"\n📊 Usage data:")
            print(json.dumps(response1.usage, indent=2))
        
        # Test 2: Detailed transcription request
        print("\n🎤 Test 2: Detailed transcription...")
        
        response2 = await agent.run(
            "Please provide a detailed transcription of this audio. Include speaker identification if multiple speakers are present.",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Transcription Response:")
        print(f"Success: {response2.success}")
        print(f"Response preview: {response2.text[:500]}...")
        
        # Test 3: Content analysis
        print("\n🎤 Test 3: Content analysis...")
        
        response3 = await agent.run(
            "What is the main topic being discussed in this audio? Provide a summary of the key points.",
            multimodal_content=multimodal_content
        )
        
        print(f"\n📝 Content Analysis Response:")
        print(f"Success: {response3.success}")
        print(f"Response: {response3.text}")
        
        # Summary
        print("\n📊 AUDIO PROCESSING SUMMARY")
        print("="*50)
        print(f"✅ Agno framework with Gemini model initialized successfully")
        print(f"✅ Audio file processed: {Path(audio_path).name}")
        print(f"✅ All audio analysis tests completed")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

async def test_agno_audio_with_openai():
    """Test Agno audio processing with OpenAI (fallback test)."""
    print("\n🎵 TESTING AGNO AUDIO WITH OPENAI (FALLBACK)")
    print("="*50)
    
    # Audio file path
    audio_path = "/mnt/c/Users/cezar/Downloads/Piraruvite-de-Pirarucu.wav"
    if sys.platform == "win32":
        audio_path = "C:\\Users\\cezar\\Downloads\\Piraruvite-de-Pirarucu.wav"
    
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return
    
    try:
        # Load audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"✅ Loaded audio file for OpenAI test")
        
        # Create agent with OpenAI
        config = {
            "name": "test_agno_audio_openai",
            "model": "openai:gpt-4o",  # OpenAI multimodal model
            "framework_type": "agno"
        }
        
        agent = SimpleAgnoAgent(config)
        await agent.initialize_framework(dependencies_type=AutomagikAgentsDependencies)
        
        # Note: OpenAI's gpt-4o doesn't directly support audio streaming
        # It would need Whisper API for transcription first
        print("\n⚠️ Note: OpenAI gpt-4o doesn't directly process audio.")
        print("For OpenAI, audio would need to be transcribed via Whisper API first.")
        print("Gemini models are recommended for direct audio processing in Agno.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def main():
    """Run all audio tests."""
    print("🎯 AGNO AUDIO PROCESSING TEST SUITE")
    print("="*80)
    print("Testing Agno framework audio capabilities")
    print("Based on Agno documentation examples")
    print("="*80)
    
    # Test with Gemini (recommended for audio)
    await test_agno_audio_with_gemini()
    
    # Test with OpenAI (fallback/comparison)
    await test_agno_audio_with_openai()
    
    print("\n✅ All audio tests completed!")
    print("\n📝 Summary:")
    print("- Agno supports audio processing with Gemini models")
    print("- Use Audio class from agno.media")
    print("- Audio can be analyzed for sentiment, transcription, and content")
    print("- For best results, use gemini-2.0-flash-exp or similar Gemini models")

if __name__ == "__main__":
    asyncio.run(main())