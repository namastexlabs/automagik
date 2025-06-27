#!/usr/bin/env python3
"""Test audio transcription using OpenAI Whisper and Groq Whisper APIs."""

import asyncio
import requests
import json
import base64
import os
from typing import Optional
import tempfile

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")
AGENT_NAME = "simple"

# Whisper API Keys (from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def transcribe_with_openai_whisper(audio_file_path: str) -> Optional[str]:
    """Transcribe audio using OpenAI Whisper API."""
    if not OPENAI_API_KEY:
        print("❌ OpenAI API key not found in environment variables")
        return None
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        return transcription
    except Exception as e:
        print(f"❌ OpenAI Whisper error: {e}")
        return None

def transcribe_with_groq_whisper(audio_file_path: str) -> Optional[str]:
    """Transcribe audio using Groq Whisper API (faster)."""
    if not GROQ_API_KEY:
        print("❌ Groq API key not found in environment variables")
        return None
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
                response_format="text"
            )
        
        return transcription.text
    except Exception as e:
        print(f"❌ Groq Whisper error: {e}")
        return None

def send_transcribed_text_to_agent(transcribed_text: str, session_name: str, original_audio_context: str = "") -> dict:
    """Send transcribed text to the agent instead of raw audio."""
    
    # Create a context-aware message
    message_content = f"""I have audio content that has been transcribed. Here's what was said:

TRANSCRIBED AUDIO:
"{transcribed_text}"

{original_audio_context}

Please analyze and respond to this audio content."""

    payload = {
        "message_content": message_content,
        "message_limit": 100,
        "user": {
            "phone_number": "+555197285829",
            "email": "test@example.com",
            "user_data": {
                "name": "Test User",
                "source": "api"
            }
        },
        "message_type": "text",  # Now sending as text
        "session_name": session_name,
        "preserve_system_prompt": False
    }
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{AGENT_NAME}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": str(e)}

def create_audio_sample_for_testing(duration_seconds: int = 5) -> str:
    """Create a small audio sample for testing if the main file is too large."""
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return None
    
    # Create a smaller sample (first 5 seconds) for faster testing
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()
    
    try:
        # Use ffmpeg to extract first N seconds (if available)
        import subprocess
        subprocess.run([
            "ffmpeg", "-i", audio_file, 
            "-t", str(duration_seconds), 
            "-y", temp_file.name
        ], check=True, capture_output=True)
        
        return temp_file.name
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If ffmpeg not available, just use original file
        print("ℹ️ ffmpeg not available, using full audio file")
        return audio_file

def main():
    """Test audio transcription with both OpenAI and Groq Whisper."""
    print("🎵 AUDIO TRANSCRIPTION + AGENT TEST")
    print("="*60)
    
    # Create or use audio file
    audio_file = create_audio_sample_for_testing(10)  # 10 seconds max
    if not audio_file:
        return
    
    file_size = os.path.getsize(audio_file) / (1024*1024)  # MB
    print(f"📁 Using audio file: {audio_file}")
    print(f"📏 Audio file size: {file_size:.2f} MB")
    
    # Test different transcription services
    transcription_services = [
        {
            "name": "Groq Whisper (Ultra Fast)",
            "function": transcribe_with_groq_whisper,
            "available": bool(GROQ_API_KEY)
        },
        {
            "name": "OpenAI Whisper (Standard)",
            "function": transcribe_with_openai_whisper,
            "available": bool(OPENAI_API_KEY)
        }
    ]
    
    successful_transcriptions = []
    
    for i, service in enumerate(transcription_services, 1):
        print(f"\n{i}. Testing {service['name']}...")
        
        if not service["available"]:
            print(f"   ⚠️ Skipped - API key not configured")
            continue
        
        print(f"   🔄 Transcribing audio...")
        transcription = service["function"](audio_file)
        
        if transcription:
            print(f"   ✅ Transcription successful!")
            print(f"   📝 Text: {transcription[:100]}...")
            successful_transcriptions.append({
                "service": service["name"],
                "text": transcription
            })
        else:
            print(f"   ❌ Transcription failed")
    
    # Test agent response with transcribed text
    if successful_transcriptions:
        print(f"\n{'='*60}")
        print("🤖 TESTING AGENT RESPONSES TO TRANSCRIBED AUDIO")
        print("="*60)
        
        for i, transcription in enumerate(successful_transcriptions, 1):
            print(f"\n{i}. Testing agent with {transcription['service']} transcription...")
            
            result = send_transcribed_text_to_agent(
                transcription["text"],
                f"test-audio-{transcription['service'].lower().replace(' ', '-')}",
                f"Original audio was transcribed using {transcription['service']}"
            )
            
            if "error" in result:
                print(f"   ❌ Agent error: {result['error']}")
            else:
                response = result.get('message', '')
                print(f"   ✅ Agent response: {response[:200]}...")
    else:
        print("\n❌ No successful transcriptions - cannot test agent responses")
    
    # Cleanup temporary file
    if audio_file != "/home/cezar/am-agents-labs/test_audio.wav":
        try:
            os.unlink(audio_file)
        except:
            pass
    
    print(f"\n{'='*60}")
    print("🎯 CONCLUSION:")
    print("This demonstrates how to integrate Whisper transcription with AI agents!")
    print("The pattern: Audio → Whisper → Text → Agent → Response")

if __name__ == "__main__":
    main()