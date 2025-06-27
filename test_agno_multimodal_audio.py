#!/usr/bin/env python3
"""
Comprehensive test for Agno multimodal audio processing capabilities.
This test demonstrates Agno's native multimodal support vs PydanticAI approach.
"""

import asyncio
import requests
import json
import base64
import os
import time
from typing import Dict, Any

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")

def encode_audio_file(file_path: str) -> str:
    """Encode audio file to base64."""
    with open(file_path, "rb") as audio_file:
        audio_data = audio_file.read()
        return base64.b64encode(audio_data).decode('utf-8')

def test_agent_audio(agent_name: str, audio_path: str, test_message: str) -> Dict[str, Any]:
    """Test audio processing for a specific agent."""
    print(f"\n🎵 Testing {agent_name} with audio...")
    
    # Encode audio file
    audio_base64 = encode_audio_file(audio_path)
    audio_data = f"data:audio/wav;base64,{audio_base64}"
    
    payload = {
        "message_content": test_message,
        "message_limit": 200,
        "user": {
            "phone_number": "+555197285829",
            "email": "agno.test@example.com",
            "user_data": {
                "name": "Agno Test User",
                "source": "agno_multimodal_test"
            }
        },
        "message_type": "audio",
        "session_name": f"agno-test-{agent_name}-audio",
        "preserve_system_prompt": False,
        "media_contents": [
            {
                "mime_type": "audio/wav",
                "data": audio_data
            }
        ]
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{agent_name}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=90.0  # Longer timeout for audio processing
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Add timing information
        result["processing_time"] = processing_time
        result["agent_name"] = agent_name
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "agent_name": agent_name,
            "processing_time": time.time() - start_time
        }

def analyze_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze agent response for multimodal capabilities."""
    analysis = {
        "agent": result.get("agent_name", "unknown"),
        "success": result.get("success", False),
        "processing_time": result.get("processing_time", 0),
        "response_length": len(result.get("message", "")),
        "framework": "unknown",
        "audio_transcribed": False,
        "audio_understood": False,
        "error": result.get("error")
    }
    
    # Check usage info for framework detection
    usage = result.get("usage", {})
    if usage:
        analysis["framework"] = usage.get("framework", "unknown")
        analysis["request_tokens"] = usage.get("request_tokens", 0)
        analysis["response_tokens"] = usage.get("response_tokens", 0)
        analysis["total_tokens"] = usage.get("total_tokens", 0)
    
    # Analyze response content for audio understanding
    response_text = result.get("message", "").lower()
    
    # Keywords that indicate audio transcription/understanding
    transcription_keywords = ["transcribed", "transcript", "said", "spoke", "audio contains", "heard"]
    understanding_keywords = ["understand", "content", "meaning", "message", "audio"]
    
    analysis["audio_transcribed"] = any(keyword in response_text for keyword in transcription_keywords)
    analysis["audio_understood"] = any(keyword in response_text for keyword in understanding_keywords)
    
    # Check for specific content understanding
    if len(response_text) > 50:  # Substantial response indicates processing
        analysis["substantial_response"] = True
    else:
        analysis["substantial_response"] = False
    
    return analysis

def compare_frameworks(results: Dict[str, Dict[str, Any]]) -> None:
    """Compare Agno vs PydanticAI performance and capabilities."""
    print("\n" + "="*80)
    print("🔬 FRAMEWORK COMPARISON: AGNO vs PYDANTICAI MULTIMODAL AUDIO")
    print("="*80)
    
    agno_result = results.get("simple_agno", {})
    pydantic_result = results.get("simple", {})
    
    print(f"\n📊 PERFORMANCE METRICS:")
    print(f"{'Metric':<25} {'Agno':<15} {'PydanticAI':<15} {'Winner':<10}")
    print("-" * 70)
    
    # Processing time comparison
    agno_time = agno_result.get("processing_time", 0)
    pydantic_time = pydantic_result.get("processing_time", 0)
    time_winner = "Agno" if agno_time < pydantic_time else "PydanticAI"
    print(f"{'Processing Time (s)':<25} {agno_time:<15.2f} {pydantic_time:<15.2f} {time_winner:<10}")
    
    # Token usage comparison
    agno_tokens = agno_result.get("total_tokens", 0)
    pydantic_tokens = pydantic_result.get("total_tokens", 0)
    if agno_tokens > 0 and pydantic_tokens > 0:
        token_winner = "Agno" if agno_tokens < pydantic_tokens else "PydanticAI"
        print(f"{'Token Usage':<25} {agno_tokens:<15} {pydantic_tokens:<15} {token_winner:<10}")
    
    # Response length comparison
    agno_length = agno_result.get("response_length", 0)
    pydantic_length = pydantic_result.get("response_length", 0)
    length_winner = "Agno" if agno_length > pydantic_length else "PydanticAI"
    print(f"{'Response Length':<25} {agno_length:<15} {pydantic_length:<15} {length_winner:<10}")
    
    print(f"\n🎯 MULTIMODAL CAPABILITIES:")
    print(f"{'Capability':<25} {'Agno':<15} {'PydanticAI':<15}")
    print("-" * 55)
    
    # Audio transcription
    agno_transcribed = "✅ Yes" if agno_result.get("audio_transcribed", False) else "❌ No"
    pydantic_transcribed = "✅ Yes" if pydantic_result.get("audio_transcribed", False) else "❌ No"
    print(f"{'Audio Transcribed':<25} {agno_transcribed:<15} {pydantic_transcribed:<15}")
    
    # Audio understanding
    agno_understood = "✅ Yes" if agno_result.get("audio_understood", False) else "❌ No"
    pydantic_understood = "✅ Yes" if pydantic_result.get("audio_understood", False) else "❌ No"
    print(f"{'Audio Understood':<25} {agno_understood:<15} {pydantic_understood:<15}")
    
    # Success rate
    agno_success = "✅ Success" if agno_result.get("success", False) else "❌ Failed"
    pydantic_success = "✅ Success" if pydantic_result.get("success", False) else "❌ Failed"
    print(f"{'Overall Success':<25} {agno_success:<15} {pydantic_success:<15}")

def main():
    """Run comprehensive Agno multimodal audio test."""
    print("🚀 AGNO MULTIMODAL AUDIO TESTING")
    print("="*60)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        print("Please ensure the audio file exists for testing.")
        return
    
    # Get file size
    file_size = os.path.getsize(audio_file)
    print(f"📁 Audio file: {audio_file}")
    print(f"📏 File size: {file_size / 1024:.2f} KB")
    
    # Test message for audio analysis
    test_message = "Please analyze this audio file. What do you hear? Can you transcribe any speech or describe the audio content?"
    
    # Test both agents
    agents_to_test = ["simple_agno", "simple"]
    results = {}
    analyses = {}
    
    for agent_name in agents_to_test:
        print(f"\n{'='*50}")
        print(f"🤖 TESTING AGENT: {agent_name.upper()}")
        print(f"{'='*50}")
        
        result = test_agent_audio(agent_name, audio_file, test_message)
        results[agent_name] = result
        
        if "error" in result:
            print(f"❌ Error testing {agent_name}: {result['error']}")
            analyses[agent_name] = {"error": result["error"], "success": False}
            continue
        
        # Analyze the result
        analysis = analyze_response(result)
        analyses[agent_name] = analysis
        
        # Display results
        print(f"✅ Response received!")
        print(f"⏱️  Processing time: {analysis['processing_time']:.2f}s")
        print(f"🔧 Framework: {analysis['framework']}")
        print(f"📝 Response length: {analysis['response_length']} chars")
        
        if analysis.get("request_tokens", 0) > 0:
            print(f"🔢 Tokens: {analysis['request_tokens']} request, {analysis['response_tokens']} response")
        
        print(f"\n📋 Agent Response:")
        response_text = result.get('message', '')
        if len(response_text) > 300:
            print(f"{response_text[:300]}...")
        else:
            print(response_text)
        
        print(f"\n🎯 Multimodal Analysis:")
        print(f"   Audio Transcribed: {'✅' if analysis['audio_transcribed'] else '❌'}")
        print(f"   Audio Understood: {'✅' if analysis['audio_understood'] else '❌'}")
        print(f"   Substantial Response: {'✅' if analysis['substantial_response'] else '❌'}")
    
    # Compare frameworks if we have results for both
    if len(analyses) >= 2:
        compare_frameworks(analyses)
    
    # Final summary
    print(f"\n🎉 AGNO MULTIMODAL TESTING COMPLETE!")
    print(f"Tested {len(agents_to_test)} agents with audio input")
    
    # Check if Agno performed better
    if "simple_agno" in analyses and "simple" in analyses:
        agno_analysis = analyses["simple_agno"]
        pydantic_analysis = analyses["simple"]
        
        if (agno_analysis.get("success", False) and 
            agno_analysis.get("audio_understood", False) and
            agno_analysis.get("processing_time", 999) < pydantic_analysis.get("processing_time", 0)):
            print("🏆 AGNO SHOWS SUPERIOR MULTIMODAL PERFORMANCE!")
        elif pydantic_analysis.get("success", False):
            print("📊 Both frameworks handled multimodal input successfully")
        else:
            print("⚠️  Mixed results - check individual agent responses above")

if __name__ == "__main__":
    main()