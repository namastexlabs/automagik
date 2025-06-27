#!/usr/bin/env python3
"""
Test intelligent framework selection between Agno (multimodal) and PydanticAI (text).
Validates that the system automatically chooses the best framework based on content type.
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

def test_text_request(agent_name: str, message: str) -> Dict[str, Any]:
    """Test text-only request (should use PydanticAI)."""
    print(f"\n📝 Testing {agent_name} with TEXT request...")
    
    payload = {
        "message_content": message,
        "message_type": "text",
        "session_name": f"test-{agent_name}-text-selection",
        "user": {
            "phone_number": "+555000000",
            "email": "framework.test@example.com",
            "user_data": {"name": "Framework Test User"}
        }
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
            timeout=30.0
        )
        
        processing_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        result["processing_time"] = processing_time
        result["test_type"] = "text"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "test_type": "text",
            "processing_time": time.time() - start_time
        }

def test_audio_request(agent_name: str, audio_path: str, message: str) -> Dict[str, Any]:
    """Test audio request (should use Agno)."""
    print(f"\n🎵 Testing {agent_name} with AUDIO request...")
    
    # Encode audio
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    payload = {
        "message_content": message,
        "message_type": "audio",
        "session_name": f"test-{agent_name}-audio-selection",
        "user": {
            "phone_number": "+555000000",
            "email": "framework.test@example.com",
            "user_data": {"name": "Framework Test User"}
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
        response = requests.post(
            f"{API_URL}/agent/{agent_name}/run",
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
        processing_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        result["processing_time"] = processing_time
        result["test_type"] = "audio"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "test_type": "audio",
            "processing_time": time.time() - start_time
        }

def analyze_framework_selection(result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze which framework was selected."""
    analysis = {
        "test_type": result.get("test_type", "unknown"),
        "success": result.get("success", False),
        "processing_time": result.get("processing_time", 0),
        "framework_used": "unknown",
        "expected_framework": "agno" if result.get("test_type") == "audio" else "pydantic_ai",
        "framework_correct": False,
        "error": result.get("error")
    }
    
    # Detect framework from usage info
    usage = result.get("usage", {})
    if usage:
        framework = usage.get("framework", "unknown")
        analysis["framework_used"] = framework
        analysis["framework_correct"] = framework == analysis["expected_framework"]
    
    # Check response for framework hints
    response_text = result.get("message", "").lower()
    if "agno" in response_text:
        analysis["framework_mentioned"] = "agno"
    elif "pydantic" in response_text:
        analysis["framework_mentioned"] = "pydantic_ai"
    
    return analysis

def display_framework_selection_results(results: Dict[str, Dict[str, Any]]) -> None:
    """Display comprehensive framework selection analysis."""
    print("\n" + "="*100)
    print("🧠 INTELLIGENT FRAMEWORK SELECTION ANALYSIS")
    print("="*100)
    
    print(f"\n📊 TEST RESULTS SUMMARY:")
    print(f"{'Test Type':<15} {'Expected':<12} {'Actual':<12} {'Correct':<8} {'Time':<8} {'Status':<10}")
    print("-" * 80)
    
    for test_name, analysis in results.items():
        status = "✅ Pass" if analysis["success"] and not analysis["error"] else "❌ Fail"
        correct = "✅ Yes" if analysis["framework_correct"] else "❌ No"
        
        print(f"{analysis['test_type']:<15} {analysis['expected_framework']:<12} {analysis['framework_used']:<12} {correct:<8} {analysis['processing_time']:<8.2f} {status:<10}")
    
    # Check if intelligent selection is working
    print(f"\n🎯 INTELLIGENT SELECTION ANALYSIS:")
    
    text_tests = [a for a in results.values() if a["test_type"] == "text"]
    audio_tests = [a for a in results.values() if a["test_type"] == "audio"]
    
    text_correct = sum(1 for a in text_tests if a["framework_correct"])
    audio_correct = sum(1 for a in audio_tests if a["framework_correct"])
    
    print(f"   📝 Text requests → PydanticAI: {text_correct}/{len(text_tests)} correct")
    print(f"   🎵 Audio requests → Agno: {audio_correct}/{len(audio_tests)} correct")
    
    total_correct = text_correct + audio_correct
    total_tests = len(text_tests) + len(audio_tests)
    
    if total_correct == total_tests:
        print(f"🏆 PERFECT! Intelligent framework selection working 100% ({total_correct}/{total_tests})")
    elif total_correct > total_tests * 0.8:
        print(f"🎯 GOOD! Framework selection working well ({total_correct}/{total_tests})")
    else:
        print(f"⚠️ ISSUES: Framework selection needs improvement ({total_correct}/{total_tests})")
    
    # Performance comparison
    agno_times = [a["processing_time"] for a in results.values() if a["framework_used"] == "agno" and a["success"]]
    pydantic_times = [a["processing_time"] for a in results.values() if a["framework_used"] == "pydantic_ai" and a["success"]]
    
    if agno_times and pydantic_times:
        avg_agno = sum(agno_times) / len(agno_times)
        avg_pydantic = sum(pydantic_times) / len(pydantic_times)
        
        print(f"\n⚡ PERFORMANCE COMPARISON:")
        print(f"   Agno average: {avg_agno:.2f}s")
        print(f"   PydanticAI average: {avg_pydantic:.2f}s")
        
        if avg_agno < avg_pydantic:
            print(f"   🚀 Agno is {avg_pydantic/avg_agno:.1f}x faster!")
        else:
            print(f"   📊 PydanticAI is {avg_agno/avg_pydantic:.1f}x faster")

def main():
    """Test intelligent framework selection."""
    print("🧠 INTELLIGENT FRAMEWORK SELECTION TEST")
    print("="*80)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    # Test configurations
    test_configs = [
        ("simple", "text", "Hello! Please explain what you can help me with."),
        ("simple", "audio", "Please analyze this audio file and tell me what you hear."),
        ("simple_agno", "text", "Hello! Please explain your capabilities."),
        ("simple_agno", "audio", "Please transcribe this audio file."),
    ]
    
    results = {}
    
    for agent_name, test_type, message in test_configs:
        test_key = f"{agent_name}_{test_type}"
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST: {test_key.upper()}")
        print(f"{'='*60}")
        
        if test_type == "text":
            result = test_text_request(agent_name, message)
        else:
            result = test_audio_request(agent_name, audio_file, message)
        
        analysis = analyze_framework_selection(result)
        results[test_key] = analysis
        
        # Quick result
        if analysis["error"]:
            print(f"❌ Failed: {analysis['error'][:100]}...")
        else:
            framework_status = "✅ Correct" if analysis["framework_correct"] else "❌ Wrong"
            print(f"✅ Success: {analysis['processing_time']:.2f}s")
            print(f"🔧 Framework: {analysis['framework_used']} (expected: {analysis['expected_framework']}) {framework_status}")
    
    # Display comprehensive analysis
    display_framework_selection_results(results)
    
    print(f"\n🎉 INTELLIGENT FRAMEWORK SELECTION TEST COMPLETE!")

if __name__ == "__main__":
    main()