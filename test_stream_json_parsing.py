#!/usr/bin/env python3
"""Unit test for stream-json parsing functionality."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from automagik.agents.claude_code.stream_utils import parse_stream_json_line


def test_parse_stream_json_line():
    """Test the parse_stream_json_line function."""
    print("Testing parse_stream_json_line function...")
    
    # Test valid user message
    valid_user = '{"type": "user", "message": "Add error handling to the calculator"}'
    result = parse_stream_json_line(valid_user)
    assert result is not None, "Valid user message should parse successfully"
    assert result["type"] == "user", f"Expected type 'user', got {result['type']}"
    assert result["message"] == "Add error handling to the calculator", f"Message mismatch: {result['message']}"
    print("✅ Valid user message parsed correctly")
    
    # Test valid system message
    valid_system = '{"type": "system", "message": "Focus on performance optimization"}'
    result = parse_stream_json_line(valid_system)
    assert result is not None, "Valid system message should parse successfully"
    assert result["type"] == "system", f"Expected type 'system', got {result['type']}"
    assert result["message"] == "Focus on performance optimization", f"Message mismatch: {result['message']}"
    print("✅ Valid system message parsed correctly")
    
    # Test empty line
    result = parse_stream_json_line("")
    assert result is None, "Empty line should return None"
    print("✅ Empty line handled correctly")
    
    # Test whitespace only
    result = parse_stream_json_line("   \n  ")
    assert result is None, "Whitespace-only line should return None"
    print("✅ Whitespace-only line handled correctly")
    
    # Test invalid JSON
    result = parse_stream_json_line("not valid json")
    assert result is None, "Invalid JSON should return None"
    print("✅ Invalid JSON handled correctly")
    
    # Test missing type field
    result = parse_stream_json_line('{"message": "test message"}')
    assert result is None, "Missing type field should return None"
    print("✅ Missing type field handled correctly")
    
    # Test missing message field
    result = parse_stream_json_line('{"type": "user"}')
    assert result is None, "Missing message field should return None"
    print("✅ Missing message field handled correctly")
    
    # Test invalid type
    result = parse_stream_json_line('{"type": "invalid", "message": "test"}')
    assert result is None, "Invalid type should return None"
    print("✅ Invalid type handled correctly")
    
    # Test empty message
    result = parse_stream_json_line('{"type": "user", "message": ""}')
    assert result is None, "Empty message should return None"
    print("✅ Empty message handled correctly")
    
    # Test non-string message
    result = parse_stream_json_line('{"type": "user", "message": 123}')
    assert result is None, "Non-string message should return None"
    print("✅ Non-string message handled correctly")
    
    print("\n🎉 All tests passed! Stream-JSON parsing is working correctly.")


if __name__ == "__main__":
    test_parse_stream_json_line()