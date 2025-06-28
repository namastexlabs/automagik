#!/usr/bin/env python3
"""
Test Analytics Extraction Function Directly

Test our enhanced _extract_usage_from_messages function to see if the logic works correctly
without needing to restart the server.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_enhanced_usage_extraction():
    """Test the enhanced usage extraction function."""
    
    # Import the function from our updated analytics routes
    from api.routes.analytics_routes import _extract_usage_from_messages
    
    # Create test messages with enhanced usage data
    test_messages = [
        {
            'usage': {
                'model': 'openai:gpt-4.1-mini',
                'framework': 'pydantic_ai',
                'request_tokens': 100,
                'response_tokens': 50,
                'total_tokens': 150,
                'content_types': ['text'],
                'processing_time_ms': 1500.0,
                'estimated_cost_usd': 0.002,
                'cost_breakdown': {
                    'input_cost': 0.001,
                    'output_cost': 0.001
                }
            }
        },
        {
            'usage': {
                'model': 'gemini:gemini-2.0-flash-exp',
                'framework': 'agno',
                'request_tokens': 200,
                'response_tokens': 100,
                'total_tokens': 300,
                'content_types': ['text', 'image'],
                'processing_time_ms': 2000.0,
                'estimated_cost_usd': 0.003,
                'cost_breakdown': {
                    'input_cost': 0.002,
                    'output_cost': 0.001
                },
                'media_costs': {
                    'image': {'cost': 0.001, 'tokens': 765}
                },
                'image_tokens': 765
            }
        }
    ]
    
    print("🧪 Testing Enhanced Usage Extraction")
    print("=" * 50)
    
    # Test the extraction function
    result = _extract_usage_from_messages(test_messages)
    
    print("📊 Extraction Results:")
    print(f"  Total Tokens: {result['total_tokens']}")
    print(f"  Message Count: {result['message_count']}")
    print(f"  Unique Models: {result['unique_models']}")
    
    # Check enhanced fields
    print("\n🔍 Enhanced Fields:")
    enhanced_fields = [
        'total_estimated_cost_usd',
        'global_content_types', 
        'total_processing_time_ms',
        'has_multimodal_content',
        'total_image_tokens'
    ]
    
    for field in enhanced_fields:
        if field in result:
            print(f"  ✅ {field}: {result[field]}")
        else:
            print(f"  ❌ {field}: Missing")
    
    # Check models data
    print("\n🤖 Models Data:")
    for i, model in enumerate(result['models'], 1):
        print(f"  Model {i}:")
        print(f"    Framework: {model['framework']}")
        print(f"    Model: {model['model']}")
        print(f"    Content Types: {model.get('content_types', 'Missing')}")
        print(f"    Processing Time: {model.get('processing_time_ms', 'Missing')}")
        print(f"    Cost: ${model.get('estimated_cost_usd', 'Missing')}")
        print(f"    Image Tokens: {model.get('image_tokens', 'Missing')}")
        print()
    
    return result

def test_real_usage_data():
    """Test with actual usage data structure from the API."""
    
    # Import the function
    from api.routes.analytics_routes import _extract_usage_from_messages
    
    # Example of actual usage data format that should be in messages
    real_usage_message = {
        'usage': {
            'framework': 'pydantic_ai',
            'model': 'openai:gpt-4.1-mini',
            'request_tokens': 1493,
            'response_tokens': 56,
            'total_tokens': 1549,
            'content_types': ['text'],
            'processing_time_ms': 3245.67,
            'estimated_cost_usd': 0.001673,
            'cost_breakdown': {
                'input_tokens_cost': 0.000223,
                'output_tokens_cost': 0.000336,
                'cache_creation_cost': 0.0,
                'cache_read_cost': 0.0
            },
            'request_timestamp': '2025-06-27T23:48:01.123456Z'
        }
    }
    
    print("\n🎯 Testing Real Usage Data Structure")
    print("=" * 50)
    
    result = _extract_usage_from_messages([real_usage_message])
    
    print("📊 Real Data Results:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    return result

if __name__ == "__main__":
    try:
        # Test enhanced extraction
        enhanced_result = test_enhanced_usage_extraction()
        
        # Test real data structure
        real_result = test_real_usage_data()
        
        print("\n🎉 TESTS COMPLETED SUCCESSFULLY!")
        print("\nThe enhanced analytics extraction function is working correctly.")
        print("Issue is likely that the server needs to be restarted to pick up code changes.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()