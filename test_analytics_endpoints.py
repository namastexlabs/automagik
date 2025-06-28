#!/usr/bin/env python3
"""
Analytics Endpoints Testing Script

Tests the analytics endpoints to verify they properly return the enhanced
usage tracking data we've implemented, including:
- Multimodal content type tracking
- Framework detection (PydanticAI vs Agno)
- Cost estimation
- Processing time tracking
- Content type breakdowns
"""

import requests
import json
import base64
import os
import time
from typing import Dict, Any, List

# API configuration
API_URL = "http://localhost:18891/api/v1"
API_KEY = os.getenv("AM_API_KEY", "namastex888")

def make_api_request(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Make an API request with proper headers."""
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        status_code = 500
        if hasattr(e, 'response') and e.response is not None:
            status_code = getattr(e.response, 'status_code', 500)
        return {"error": str(e), "status_code": status_code}

def test_simple_agent_run() -> str:
    """Test simple agent with text to generate usage data."""
    print("🔄 Running simple agent to generate usage data...")
    
    payload = {
        "message_content": "What is artificial intelligence? Explain in 2 sentences.",
        "message_type": "text",
        "session_name": "analytics-test-session",
        "user": {
            "phone_number": "+555999888",
            "email": "analytics.test@example.com",
            "user_data": {"name": "Analytics Test User"}
        }
    }
    
    result = make_api_request("/agent/simple/run", "POST", payload)
    
    if "error" in result:
        print(f"❌ Agent run failed: {result['error']}")
        return None
    
    # Extract session_id for analytics testing
    session_id = result.get("session_id")
    print(f"✅ Agent run successful, session_id: {session_id}")
    return session_id

def test_multimodal_agent_run() -> str:
    """Test agent with image to generate multimodal usage data."""
    print("🖼️ Running agent with image to generate multimodal usage data...")
    
    # Create a small test image (1x1 pixel PNG)
    test_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGA4y+Y9wAAAABJRU5ErkJggg=="
    
    payload = {
        "message_content": "Analyze this image and describe what you see.",
        "message_type": "image",
        "session_name": "analytics-multimodal-test-session",
        "user": {
            "phone_number": "+555999777",
            "email": "multimodal.test@example.com",
            "user_data": {"name": "Multimodal Test User"}
        },
        "media_contents": [
            {
                "mime_type": "image/png",
                "data": f"data:image/png;base64,{test_image_data}"
            }
        ]
    }
    
    result = make_api_request("/agent/simple/run", "POST", payload)
    
    if "error" in result:
        print(f"❌ Multimodal agent run failed: {result['error']}")
        return None
    
    session_id = result.get("session_id")
    print(f"✅ Multimodal agent run successful, session_id: {session_id}")
    return session_id

def analyze_session_usage(session_id: str) -> None:
    """Test and analyze session usage analytics."""
    print(f"\n📊 Testing session usage analytics for: {session_id}")
    
    result = make_api_request(f"/analytics/sessions/{session_id}/usage")
    
    if "error" in result:
        print(f"❌ Session analytics failed: {result['error']}")
        return
    
    print("✅ Session analytics retrieved successfully!")
    
    # Check for enhanced usage tracking fields
    print(f"  Session ID: {result.get('session_id')}")
    print(f"  Total Tokens: {result.get('total_tokens', 0)}")
    print(f"  Total Requests: {result.get('total_requests', 0)}")
    print(f"  Message Count: {result.get('summary', {}).get('message_count', 0)}")
    print(f"  Unique Models: {result.get('summary', {}).get('unique_models', 0)}")
    
    # Analyze models used
    models = result.get('models', [])
    print(f"\n🤖 Models Analysis ({len(models)} models):")
    for i, model in enumerate(models, 1):
        print(f"  {i}. Framework: {model.get('framework', 'unknown')}")
        print(f"     Model: {model.get('model', 'unknown')}")
        print(f"     Request Tokens: {model.get('request_tokens', 0)}")
        print(f"     Response Tokens: {model.get('response_tokens', 0)}")
        print(f"     Total Tokens: {model.get('total_tokens', 0)}")
        print(f"     Messages: {model.get('message_count', 0)}")
        print()
    
    # Check if the analytics extraction function needs enhancement
    print("🔍 Enhanced Usage Tracking Check:")
    
    # Check for enhanced_analytics section
    if "enhanced_analytics" in result:
        print("  ✅ Found enhanced_analytics section!")
        enhanced = result["enhanced_analytics"]
        for key, value in enhanced.items():
            print(f"    {key}: {value}")
    else:
        print("  ❌ No enhanced_analytics section found")
    
    # Look for enhanced fields in the raw response
    enhanced_fields = [
        'content_types', 'processing_time_ms', 'estimated_cost_usd',
        'cost_breakdown', 'media_costs', 'framework_events'
    ]
    
    found_enhanced = False
    for model in models:
        for field in enhanced_fields:
            if field in model:
                print(f"  ✅ Found enhanced field in model: {field} = {model[field]}")
                found_enhanced = True
    
    if not found_enhanced:
        print("  ⚠️ No enhanced usage fields found in model data")
    
    # Show raw response keys for debugging
    print(f"  📋 Response top-level keys: {list(result.keys())}")
    if models:
        print(f"  📋 Model keys: {list(models[0].keys())}")

def test_top_usage_sessions() -> None:
    """Test top usage sessions endpoint."""
    print("\n🏆 Testing top usage sessions analytics...")
    
    result = make_api_request("/analytics/sessions/top-usage?limit=5&days=7")
    
    if "error" in result:
        print(f"❌ Top usage sessions failed: {result['error']}")
        return
    
    print("✅ Top usage sessions retrieved successfully!")
    print(f"  Sessions Found: {result.get('count', 0)}")
    print(f"  Days Analyzed: {result.get('days_analyzed', 0)}")
    
    sessions = result.get('sessions', [])
    if sessions:
        print("\n📈 Top Sessions:")
        for i, session in enumerate(sessions[:3], 1):  # Show top 3
            print(f"  {i}. Session: {session.get('session_id', 'unknown')[:8]}...")
            print(f"     Total Tokens: {session.get('total_tokens', 0)}")
            print(f"     Messages: {session.get('message_count', 0)}")
            print(f"     Models: {', '.join(session.get('models_used', []))}")
            print()
    else:
        print("  📝 No sessions with usage data found")

def check_analytics_data_structure() -> None:
    """Check if analytics endpoints are extracting enhanced usage data."""
    print("\n🔬 ANALYTICS DATA STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # Get all sessions to find one with usage data
    result = make_api_request("/analytics/sessions/top-usage?limit=1&days=30")
    
    if "error" in result:
        print(f"❌ Failed to get sessions for analysis: {result['error']}")
        return
    
    sessions = result.get('sessions', [])
    if not sessions:
        print("❌ No sessions found for analysis")
        return
    
    session_id = sessions[0]['session_id']
    print(f"🎯 Analyzing session: {session_id}")
    
    # Get detailed session usage
    session_result = make_api_request(f"/analytics/sessions/{session_id}/usage")
    
    if "error" in session_result:
        print(f"❌ Failed to get session details: {session_result['error']}")
        return
    
    print("\n📋 Current Analytics Data Structure:")
    print(f"  Session Level Fields: {list(session_result.keys())}")
    
    models = session_result.get('models', [])
    if models:
        model = models[0]
        print(f"  Model Level Fields: {list(model.keys())}")
        
        # Check for enhanced fields
        enhanced_fields = {
            'content_types': 'Content type tracking (text, image, audio)',
            'processing_time_ms': 'Processing time in milliseconds',
            'estimated_cost_usd': 'Cost estimation in USD',
            'cost_breakdown': 'Detailed cost breakdown',
            'media_costs': 'Multimodal media costs',
            'framework_events': 'Framework-specific events',
            'image_tokens': 'Image token usage',
            'audio_tokens': 'Audio token usage'
        }
        
        print("\n🔍 Enhanced Usage Fields Status:")
        for field, description in enhanced_fields.items():
            if field in model:
                print(f"  ✅ {field}: {description}")
                print(f"      Value: {model[field]}")
            else:
                print(f"  ❌ {field}: {description} - NOT FOUND")
        
        # Raw model data for debugging
        print(f"\n🔧 Raw Model Data Sample:")
        print(json.dumps(model, indent=2)[:500] + "..." if len(str(model)) > 500 else json.dumps(model, indent=2))
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Check if _extract_usage_from_messages() in analytics_routes.py extracts enhanced fields")
    print("2. Ensure usage data is being saved with enhanced fields in message storage")
    print("3. Verify UnifiedUsageCalculator is being used and data is persisted")

def main():
    """Run comprehensive analytics testing."""
    print("🔬 ANALYTICS ENDPOINTS TESTING")
    print("=" * 50)
    
    # Step 1: Generate some usage data
    print("\n📝 STEP 1: GENERATING USAGE DATA")
    text_session_id = test_simple_agent_run()
    time.sleep(1)  # Brief pause
    multimodal_session_id = test_multimodal_agent_run()
    
    # Step 2: Test session analytics
    print("\n📊 STEP 2: TESTING SESSION ANALYTICS")
    if text_session_id:
        analyze_session_usage(text_session_id)
    
    if multimodal_session_id:
        analyze_session_usage(multimodal_session_id)
    
    # Step 3: Test top usage sessions
    test_top_usage_sessions()
    
    # Step 4: Analyze data structure
    check_analytics_data_structure()
    
    print("\n🎉 ANALYTICS TESTING COMPLETE!")
    print("\nKey areas to verify:")
    print("1. ✅ Enhanced usage fields in analytics responses")
    print("2. ✅ Framework detection (pydantic_ai vs agno)")
    print("3. ✅ Content type tracking (text, image, audio)")
    print("4. ✅ Cost estimation and breakdown")
    print("5. ✅ Processing time tracking")

if __name__ == "__main__":
    main()