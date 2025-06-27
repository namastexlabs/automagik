#!/usr/bin/env python3
"""
Comprehensive Usage Tracking Test

Tests the enhanced usage tracking system that addresses:
1. PydanticAI bias in current tracking
2. Multimodal cost blindness
3. Framework switching overhead
4. Real cost calculations
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

def test_text_usage_tracking(agent_name: str) -> Dict[str, Any]:
    """Test usage tracking for text-only requests."""
    print(f"\n📝 Testing {agent_name} text usage tracking...")
    
    payload = {
        "message_content": "Explain the concept of artificial intelligence in exactly 100 words.",
        "message_type": "text",
        "session_name": f"test-{agent_name}-text-usage",
        "user": {
            "phone_number": "+555000001",
            "email": "usage.test@example.com",
            "user_data": {"name": "Usage Test User"}
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
        result["test_processing_time"] = processing_time
        result["test_type"] = "text"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "test_type": "text",
            "test_processing_time": time.time() - start_time
        }

def test_multimodal_usage_tracking(agent_name: str, audio_path: str) -> Dict[str, Any]:
    """Test usage tracking for multimodal requests."""
    print(f"\n🎵 Testing {agent_name} multimodal usage tracking...")
    
    # Encode audio
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    payload = {
        "message_content": "Please analyze this audio file comprehensively. Transcribe any speech and describe all audio characteristics you can identify.",
        "message_type": "audio",
        "session_name": f"test-{agent_name}-multimodal-usage",
        "user": {
            "phone_number": "+555000001",
            "email": "usage.test@example.com",
            "user_data": {"name": "Usage Test User"}
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
            timeout=90.0
        )
        
        processing_time = time.time() - start_time
        response.raise_for_status()
        result = response.json()
        result["test_processing_time"] = processing_time
        result["test_type"] = "multimodal"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "test_type": "multimodal",
            "test_processing_time": time.time() - start_time
        }

def analyze_usage_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze usage data for completeness and accuracy."""
    analysis = {
        "test_type": result.get("test_type", "unknown"),
        "success": result.get("success", False),
        "processing_time": result.get("test_processing_time", 0),
        "error": result.get("error"),
        "usage_present": False,
        "usage_completeness": {},
        "cost_tracking": {},
        "framework_identified": False,
        "multimodal_tracking": False
    }
    
    # Check if usage data is present
    usage = result.get("usage", {})
    if usage:
        analysis["usage_present"] = True
        
        # Check completeness of usage data
        required_fields = ["framework", "model", "request_tokens", "response_tokens", "total_tokens"]
        for field in required_fields:
            analysis["usage_completeness"][field] = field in usage
        
        # Check framework identification
        framework = usage.get("framework", "unknown")
        analysis["framework_identified"] = framework != "unknown"
        analysis["detected_framework"] = framework
        analysis["detected_model"] = usage.get("model", "unknown")
        
        # Check cost tracking (enhanced feature)
        if "estimated_cost_usd" in usage:
            analysis["cost_tracking"]["has_cost_estimate"] = True
            analysis["cost_tracking"]["cost_usd"] = usage.get("estimated_cost_usd", 0)
        
        if "cost_breakdown" in usage:
            analysis["cost_tracking"]["has_cost_breakdown"] = True
            analysis["cost_tracking"]["breakdown"] = usage.get("cost_breakdown", {})
        
        # Check multimodal tracking (key enhancement)
        if "media_costs" in usage and usage["media_costs"]:
            analysis["multimodal_tracking"] = True
            analysis["media_costs"] = usage["media_costs"]
        
        # Enhanced tracking fields
        enhanced_fields = ["processing_time_ms", "framework_events", "request_timestamp"]
        analysis["enhanced_features"] = {field: field in usage for field in enhanced_fields}
        
        # Usage data completeness score
        total_fields = len(required_fields) + len(enhanced_fields)
        present_fields = sum(analysis["usage_completeness"].values()) + sum(analysis["enhanced_features"].values())
        analysis["completeness_score"] = present_fields / total_fields
    
    return analysis

def compare_framework_usage_tracking(results: Dict[str, Dict[str, Any]]) -> None:
    """Compare usage tracking capabilities across frameworks."""
    print("\n" + "="*100)
    print("💰 COMPREHENSIVE USAGE TRACKING ANALYSIS")
    print("="*100)
    
    frameworks = {}
    for test_name, analysis in results.items():
        framework = analysis.get("detected_framework", "unknown")
        test_type = analysis.get("test_type", "unknown")
        
        if framework not in frameworks:
            frameworks[framework] = {"text": [], "multimodal": []}
        
        frameworks[framework][test_type].append(analysis)
    
    # Framework comparison table with model information
    print(f"\n📊 FRAMEWORK & MODEL USAGE TRACKING COMPARISON:")
    print(f"{'Framework':<15} {'Model':<20} {'Type':<12} {'Usage':<8} {'Cost':<8} {'Multimodal':<12} {'Complete':<10}")
    print("-" * 105)
    
    for framework, tests in frameworks.items():
        for test_type, analyses in tests.items():
            if not analyses:
                continue
                
            analysis = analyses[0]  # Take first result for this framework/type
            
            # Extract model information from the analysis
            model_used = analysis.get("detected_model", "unknown")
            
            usage_ok = "✅" if analysis["usage_present"] else "❌"
            cost_ok = "✅" if analysis["cost_tracking"].get("has_cost_estimate", False) else "❌"
            multimodal_ok = "✅" if analysis["multimodal_tracking"] else ("N/A" if test_type == "text" else "❌")
            completeness = f"{analysis.get('completeness_score', 0):.1%}"
            
            print(f"{framework:<15} {model_used:<20} {test_type:<12} {usage_ok:<8} {cost_ok:<8} {multimodal_ok:<12} {completeness:<10}")
    
    # Detailed cost analysis
    print(f"\n💲 COST TRACKING DETAILS:")
    for framework, tests in frameworks.items():
        print(f"\n🔧 {framework.upper()} Framework:")
        
        for test_type, analyses in tests.items():
            if not analyses:
                continue
                
            analysis = analyses[0]
            cost_data = analysis["cost_tracking"]
            
            if cost_data.get("has_cost_estimate"):
                cost = cost_data.get("cost_usd", 0)
                print(f"   {test_type.title()}: ${cost:.6f} USD")
                
                if cost_data.get("has_cost_breakdown"):
                    breakdown = cost_data.get("breakdown", {})
                    for cost_type, cost_value in breakdown.items():
                        print(f"     - {cost_type}: ${cost_value:.6f}")
            else:
                print(f"   {test_type.title()}: ❌ No cost tracking")
    
    # Multimodal analysis
    print(f"\n🎭 MULTIMODAL COST TRACKING:")
    for framework, tests in frameworks.items():
        multimodal_analyses = tests.get("multimodal", [])
        if multimodal_analyses:
            analysis = multimodal_analyses[0]
            if analysis["multimodal_tracking"]:
                print(f"✅ {framework}: Comprehensive multimodal tracking")
                media_costs = analysis.get("media_costs", {})
                for media_type, cost_data in media_costs.items():
                    if cost_data:
                        print(f"   - {media_type}: {cost_data}")
            else:
                print(f"❌ {framework}: No multimodal cost tracking")
    
    # Overall assessment
    print(f"\n🎯 OVERALL ASSESSMENT:")
    
    # Check if PydanticAI bias is resolved
    pydantic_results = frameworks.get("pydantic_ai", {})
    agno_results = frameworks.get("agno", {})
    
    if pydantic_results and agno_results:
        pydantic_score = 0
        agno_score = 0
        
        for test_type in ["text", "multimodal"]:
            if pydantic_results.get(test_type):
                pydantic_score += pydantic_results[test_type][0].get("completeness_score", 0)
            if agno_results.get(test_type):
                agno_score += agno_results[test_type][0].get("completeness_score", 0)
        
        if abs(pydantic_score - agno_score) < 0.2:
            print("✅ Framework Parity: PydanticAI bias successfully resolved!")
        else:
            higher_framework = "PydanticAI" if pydantic_score > agno_score else "Agno"
            print(f"⚠️ Framework Bias: {higher_framework} still has better tracking")
    
    # Check multimodal blindness resolution
    multimodal_tracking_count = sum(
        1 for framework_tests in frameworks.values()
        for analysis in framework_tests.get("multimodal", [])
        if analysis["multimodal_tracking"]
    )
    
    if multimodal_tracking_count > 0:
        print("✅ Multimodal Blindness: Successfully resolved with comprehensive tracking!")
    else:
        print("❌ Multimodal Blindness: Still present - no framework tracks multimodal costs")

def main():
    """Run comprehensive usage tracking tests."""
    print("💰 COMPREHENSIVE USAGE TRACKING TEST")
    print("="*80)
    
    audio_file = "/home/cezar/am-agents-labs/test_audio.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return
    
    # Test configurations
    test_configs = [
        ("simple", "text"),
        ("simple", "multimodal"),
        ("simple_agno", "text"),
        ("simple_agno", "multimodal"),
    ]
    
    results = {}
    analyses = {}
    
    for agent_name, test_type in test_configs:
        test_key = f"{agent_name}_{test_type}"
        
        print(f"\n{'='*60}")
        print(f"💰 USAGE TEST: {test_key.upper()}")
        print(f"{'='*60}")
        
        if test_type == "text":
            result = test_text_usage_tracking(agent_name)
        else:
            result = test_multimodal_usage_tracking(agent_name, audio_file)
        
        results[test_key] = result
        analysis = analyze_usage_data(result)
        analyses[test_key] = analysis
        
        # Quick result summary
        if analysis["error"]:
            print(f"❌ Failed: {analysis['error'][:100]}...")
        else:
            usage_status = "✅ Complete" if analysis["usage_present"] else "❌ Missing"
            cost_status = "✅ Yes" if analysis["cost_tracking"].get("has_cost_estimate") else "❌ No"
            multimodal_status = "✅ Yes" if analysis["multimodal_tracking"] else ("N/A" if test_type == "text" else "❌ No")
            
            print(f"✅ Success: {analysis['processing_time']:.2f}s")
            print(f"📊 Usage Data: {usage_status}")
            print(f"💲 Cost Tracking: {cost_status}")
            print(f"🎭 Multimodal Costs: {multimodal_status}")
            print(f"🔧 Framework: {analysis.get('detected_framework', 'unknown')}")
            print(f"🤖 Model: {analysis.get('detected_model', 'unknown')}")
    
    # Comprehensive analysis
    compare_framework_usage_tracking(analyses)
    
    print(f"\n🎉 COMPREHENSIVE USAGE TRACKING TEST COMPLETE!")
    print("This test validates the resolution of PydanticAI bias and multimodal cost blindness.")

if __name__ == "__main__":
    main()