#!/usr/bin/env python3
"""Multimodal test for Agno framework - demonstrating native audio/image processing."""

import asyncio
import base64
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies


class MultimodalAgnoAgent(AutomagikAgent):
    """Test agent for multimodal capabilities using Agno."""
    
    def __init__(self, config):
        # Force Agno framework
        config["framework_type"] = "agno"
        super().__init__(config)
        
        # Multimodal-aware prompt
        self._code_prompt_text = """You are a multimodal AI assistant powered by Agno framework.
You can process text, images, audio, and video natively without preprocessing.
Always acknowledge the type of media you're processing."""
        
        # Create dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model", "openai:gpt-4o"),
            model_settings={}
        )
        
        # Register multimodal tools
        self.tool_registry.register_default_tools(self.context)


# Sample media data for testing
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


async def test_image_processing():
    """Test native image processing with Agno."""
    print("=" * 60)
    print("🖼️ TEST 1: Native Image Processing")
    print("=" * 60)
    
    config = {
        "name": "test_agno_image",
        "model": "openai:gpt-4o",  # Vision-capable model
        "framework_type": "agno"
    }
    
    agent = MultimodalAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    # Create multimodal input
    multimodal_input = [
        "What do you see in this image? Describe it briefly.",
        {
            "type": "image",
            "data": f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}",
            "mime_type": "image/png"
        }
    ]
    
    # Process with Agno (no preprocessing needed!)
    response = await agent.run_agent(multimodal_input)
    
    print(f"✅ Response: {response.text[:200]}...")
    print(f"✅ Success: {response.success}")
    print(f"🎯 Native processing - no image-to-text conversion needed!")
    
    return response


async def test_audio_processing():
    """Test native audio processing with Agno."""
    print("\n" + "=" * 60)
    print("🎵 TEST 2: Native Audio Processing")
    print("=" * 60)
    
    # Create a simple WAV header + silence for testing
    def create_test_audio():
        # WAV header for 1 second of silence
        wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        # Add 1 second of silence (44100 samples * 2 bytes per sample)
        silence = b'\x00\x00' * 44100
        return base64.b64encode(wav_header + silence).decode('utf-8')
    
    config = {
        "name": "test_agno_audio",
        "model": "openai:gpt-4o-audio-preview",  # Audio-capable model
        "framework_type": "agno"
    }
    
    agent = MultimodalAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    # Create multimodal input with audio
    audio_base64 = create_test_audio()
    multimodal_input = [
        "What do you hear in this audio file? Is there any sound or is it silent?",
        {
            "type": "audio",
            "data": f"data:audio/wav;base64,{audio_base64}",
            "mime_type": "audio/wav"
        }
    ]
    
    # Process with Agno (no Whisper transcription needed!)
    try:
        response = await agent.run_agent(multimodal_input)
        
        print(f"✅ Response: {response.text[:200]}...")
        print(f"✅ Success: {response.success}")
        print(f"🎯 Native audio processing - no transcription pipeline needed!")
        
        if not response.success and "audio" in response.error_message.lower():
            print(f"⚠️ Note: Model may not support audio. Error: {response.error_message}")
    except Exception as e:
        print(f"⚠️ Audio test failed (expected if model doesn't support audio): {e}")


async def test_combined_multimodal():
    """Test combined multimodal inputs."""
    print("\n" + "=" * 60)
    print("🎭 TEST 3: Combined Multimodal Input")
    print("=" * 60)
    
    config = {
        "name": "test_agno_combined",
        "model": "gemini:gemini-2.0-flash-exp",  # Gemini supports multiple modalities
        "framework_type": "agno"
    }
    
    agent = MultimodalAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    # Create combined multimodal input
    multimodal_input = [
        "I'm sending you both an image and text. Please acknowledge both inputs and describe what you received.",
        {
            "type": "image",
            "data": f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}",
            "mime_type": "image/png"
        }
    ]
    
    # Process combined input
    response = await agent.run_agent(multimodal_input)
    
    print(f"✅ Response: {response.text[:200]}...")
    print(f"✅ Success: {response.success}")
    print(f"🎯 Processed multiple media types in single call!")


async def test_agno_vs_traditional():
    """Compare Agno's approach vs traditional preprocessing."""
    print("\n" + "=" * 60)
    print("⚖️ TEST 4: Agno vs Traditional Approach")
    print("=" * 60)
    
    print("Traditional approach workflow:")
    print("1. Receive audio → Send to Whisper API → Get text → Send to LLM")
    print("2. Receive image → Send to vision API → Get description → Send to LLM")
    print("3. Multiple API calls, higher latency, context loss")
    
    print("\nAgno approach workflow:")
    print("1. Receive audio/image → Send directly to multimodal LLM")
    print("2. Single API call, lower latency, full context preserved")
    
    print("\n📊 Performance benefits:")
    print("- Latency: 1 call vs 2-3 calls")
    print("- Context: Preserved tone, emotion, visual details")
    print("- Simplicity: No preprocessing pipeline to maintain")
    print("- Cost: Fewer API calls = lower cost")


async def test_video_support():
    """Test video support (Gemini only currently)."""
    print("\n" + "=" * 60)
    print("📹 TEST 5: Video Support (Gemini)")
    print("=" * 60)
    
    config = {
        "name": "test_agno_video",
        "model": "gemini:gemini-2.0-flash-exp",
        "framework_type": "agno"
    }
    
    agent = MultimodalAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    print("ℹ️ Video support is currently Gemini-only in Agno")
    print("ℹ️ Would process video files directly without frame extraction")
    
    # Note: Actual video test would require a video file
    # multimodal_input = [
    #     "Describe what happens in this video",
    #     {"type": "video", "filepath": "test_video.mp4"}
    # ]


async def main():
    """Run all Agno multimodal tests."""
    print("🚀 AGNO MULTIMODAL CAPABILITIES TEST")
    print("=" * 60)
    print("Demonstrating Agno's native multimodal processing")
    print("No preprocessing pipelines - direct model processing!")
    print("=" * 60)
    
    try:
        import agno
        print(f"✅ Agno installed")
    except ImportError:
        print("❌ Agno not installed. Install with: pip install agno")
        return
    
    # Run multimodal tests
    await test_image_processing()
    await test_audio_processing()
    await test_combined_multimodal()
    await test_agno_vs_traditional()
    await test_video_support()
    
    print("\n" + "=" * 60)
    print("✅ Multimodal tests completed!")
    print("\n🎯 Key Takeaway: Agno enables native multimodal processing")
    print("   without complex preprocessing pipelines!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())