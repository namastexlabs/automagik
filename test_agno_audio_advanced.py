#!/usr/bin/env python3
"""
Advanced Agno audio testing with proper model selection for audio-capable models.
Tests Agno's framework flexibility and audio handling capabilities.
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

def test_agent_with_audio_model(agent_name: str, audio_path: str, test_message: str, model: str = None) -> Dict[str, Any]:
    """Test audio processing with a specific model."""
    print(f"\n🎵 Testing {agent_name} with audio (model: {model})...")
    
    # Encode audio file
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    audio_data_uri = f"data:audio/wav;base64,{audio_base64}"
    
    payload = {
        "message_content": test_message,
        "message_limit": 200,
        "user": {
            "phone_number": "+555197285829",
            "email": "agno.audio.test@example.com",
            "user_data": {
                "name": "Agno Audio Test User",
                "source": "agno_audio_advanced_test"
            }
        },
        "message_type": "audio",
        "session_name": f"agno-audio-{agent_name}-{model or 'default'}",
        "preserve_system_prompt": False,
        "media_contents": [
            {
                "mime_type": "audio/wav",
                "data": audio_data_uri
            }
        ]
    }
    
    # Add model override if specified
    if model:
        payload["model_override"] = model
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{agent_name}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=120.0  # Even longer timeout for audio processing
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Add test metadata
        result["processing_time"] = processing_time
        result["agent_name"] = agent_name
        result["model_tested"] = model or "default"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "agent_name": agent_name,
            "model_tested": model or "default",
            "processing_time": time.time() - start_time
        }

def test_text_fallback(agent_name: str, test_message: str, model: str = None) -> Dict[str, Any]:
    """Test how agent handles audio-related text requests."""
    print(f"\n📝 Testing {agent_name} with text audio request (model: {model})...")
    
    payload = {
        "message_content": f"{test_message} [NOTE: This is a text simulation of an audio analysis request]",
        "message_limit": 200,
        "user": {
            "phone_number": "+555197285829",
            "email": "agno.text.test@example.com",
            "user_data": {
                "name": "Agno Text Test User",
                "source": "agno_text_fallback_test"
            }
        },
        "message_type": "text",
        "session_name": f"agno-text-{agent_name}-{model or 'default'}",
        "preserve_system_prompt": False
    }
    
    # Add model override if specified
    if model:
        payload["model_override"] = model
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/agent/{agent_name}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Add test metadata
        result["processing_time"] = processing_time
        result["agent_name"] = agent_name
        result["model_tested"] = model or "default"
        result["test_type"] = "text_fallback"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "agent_name": agent_name,
            "model_tested": model or "default",
            "test_type": "text_fallback",
            "processing_time": time.time() - start_time
        }

def analyze_advanced_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced analysis of agent response."""
    analysis = {
        "agent": result.get("agent_name", "unknown"),
        "model": result.get("model_tested", "default"),
        "test_type": result.get("test_type", "audio"),
        "success": result.get("success", False),
        "processing_time": result.get("processing_time", 0),
        "response_length": len(result.get("message", "")),
        "framework": "unknown",
        "error": result.get("error"),
        "capabilities": {
            "handles_audio_gracefully": False,
            "provides_helpful_feedback": False,
            "mentions_audio_limitations": False,
            "suggests_alternatives": False
        }
    }
    
    # Check usage info for framework detection
    usage = result.get("usage", {})
    if usage:
        analysis["framework"] = usage.get("framework", "unknown")
        analysis["token_usage"] = {
            "request": usage.get("request_tokens", 0),
            "response": usage.get("response_tokens", 0),
            "total": usage.get("total_tokens", 0)
        }
    
    # Analyze response content for sophisticated audio handling
    response_text = result.get("message", "").lower()
    
    # Check for graceful audio handling
    graceful_keywords = ["upload", "provide", "share", "audio file", "cannot process", "unable to"]
    analysis["capabilities"]["handles_audio_gracefully"] = any(keyword in response_text for keyword in graceful_keywords)
    
    # Check for helpful feedback
    helpful_keywords = ["help", "assist", "analyze", "process", "transcribe"]
    analysis["capabilities"]["provides_helpful_feedback"] = any(keyword in response_text for keyword in helpful_keywords)
    
    # Check for limitation awareness
    limitation_keywords = ["limitation", "support", "format", "unable", "cannot", "not supported"]
    analysis["capabilities"]["mentions_audio_limitations"] = any(keyword in response_text for keyword in limitation_keywords)
    
    # Check for alternative suggestions
    alternative_keywords = ["try", "instead", "alternative", "different", "text", "image"]
    analysis["capabilities"]["suggests_alternatives"] = any(keyword in response_text for keyword in alternative_keywords)
    
    return analysis

def display_advanced_results(analyses: Dict[str, Dict[str, Any]]) -> None:
    """Display comprehensive test results."""
    print("\n" + "="*100)
    print("🔬 ADVANCED AGNO MULTIMODAL AUDIO ANALYSIS")
    print("="*100)
    
    # Group by agent
    agents = {}
    for key, analysis in analyses.items():
        agent_name = analysis["agent"]
        if agent_name not in agents:
            agents[agent_name] = []
        agents[agent_name].append((key, analysis))
    
    for agent_name, results in agents.items():
        print(f"\n🤖 AGENT: {agent_name.upper()}")
        print("-" * 80)
        
        for test_key, analysis in results:
            print(f"\n📊 Test: {test_key}")
            print(f"   Model: {analysis['model']}")
            print(f"   Type: {analysis['test_type']}")
            print(f"   Framework: {analysis['framework']}")
            print(f"   Success: {'✅' if analysis['success'] else '❌'}")
            print(f"   Time: {analysis['processing_time']:.2f}s")
            
            if analysis["error"]:
                print(f"   Error: {analysis['error'][:100]}...")
            else:
                print(f"   Response Length: {analysis['response_length']} chars")
                
                # Capability analysis
                caps = analysis["capabilities"]
                print(f"   Capabilities:")
                print(f"     Graceful Handling: {'✅' if caps['handles_audio_gracefully'] else '❌'}")
                print(f"     Helpful Feedback: {'✅' if caps['provides_helpful_feedback'] else '❌'}")
                print(f"     Limitation Aware: {'✅' if caps['mentions_audio_limitations'] else '❌'}")
                print(f"     Suggests Alternatives: {'✅' if caps['suggests_alternatives'] else '❌'}")

def main():
    """Run advanced Agno audio testing."""
    print("🚀 ADVANCED AGNO AUDIO TESTING")
    print("="*80)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    file_size = os.path.getsize(audio_file)
    print(f"📁 Audio file: {audio_file} ({file_size / 1024:.2f} KB)")
    
    test_message = "Please analyze this audio file. Transcribe any speech and describe what you hear."
    
    # Test configurations
    test_configs = [
        ("simple_agno", None, "audio"),  # Agno with default model
        ("simple_agno", "openai:gpt-4o", "audio"),  # Agno with GPT-4o
        ("simple", None, "audio"),  # PydanticAI with default model
        ("simple_agno", None, "text"),  # Agno text fallback
        ("simple", None, "text"),  # PydanticAI text fallback
    ]
    
    results = {}
    analyses = {}
    
    for agent_name, model, test_type in test_configs:
        test_key = f"{agent_name}_{model or 'default'}_{test_type}"
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_key.upper()}")
        print(f"{'='*60}")
        
        if test_type == "audio":
            result = test_agent_with_audio_model(agent_name, audio_file, test_message, model)
        else:
            result = test_text_fallback(agent_name, test_message, model)
        
        results[test_key] = result
        analysis = analyze_advanced_response(result)
        analyses[test_key] = analysis
        
        # Quick result summary
        if analysis["error"]:
            print(f"❌ Failed: {analysis['error'][:100]}...")
        else:
            print(f"✅ Success: {analysis['processing_time']:.2f}s, {analysis['response_length']} chars")
            
            # Show response preview
            response_preview = result.get('message', '')[:200]
            print(f"💬 Response: {response_preview}...")
    
    # Display comprehensive analysis
    display_advanced_results(analyses)
    
    # Final insights
    print(f"\n🎉 ADVANCED TESTING COMPLETE!")
    print("Key Insights:")
    
    # Check Agno vs PydanticAI graceful handling
    agno_graceful = any(a["capabilities"]["handles_audio_gracefully"] 
                       for a in analyses.values() 
                       if a["agent"] == "simple_agno")
    pydantic_graceful = any(a["capabilities"]["handles_audio_gracefully"] 
                           for a in analyses.values() 
                           if a["agent"] == "simple")
    
    if agno_graceful and not pydantic_graceful:
        print("🏆 Agno demonstrates superior graceful audio handling!")
    elif agno_graceful and pydantic_graceful:
        print("📊 Both frameworks handle audio limitations gracefully")
    else:
        print("🔍 Mixed results - check detailed analysis above")

if __name__ == "__main__":
    main()