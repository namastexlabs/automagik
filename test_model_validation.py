#!/usr/bin/env python3
"""Test the ClaudeCodeRunRequest model validation."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from automagik.agents.claude_code.models import ClaudeCodeRunRequest
from pydantic import ValidationError


def test_input_format_validation():
    """Test input_format field validation."""
    print("Testing input_format field validation...")
    
    # Test valid input_format values
    try:
        request = ClaudeCodeRunRequest(
            message="Test message",
            input_format="text"
        )
        print("✅ input_format='text' is valid")
    except ValidationError as e:
        print(f"❌ input_format='text' failed: {e}")
    
    try:
        request = ClaudeCodeRunRequest(
            message="Test message",
            input_format="stream-json"
        )
        print("✅ input_format='stream-json' is valid")
    except ValidationError as e:
        print(f"❌ input_format='stream-json' failed: {e}")
    
    # Test default value
    try:
        request = ClaudeCodeRunRequest(
            message="Test message"
        )
        assert request.input_format == "text", f"Expected default 'text', got {request.input_format}"
        print("✅ Default input_format='text' works correctly")
    except ValidationError as e:
        print(f"❌ Default input_format failed: {e}")
    
    # Test invalid input_format
    try:
        request = ClaudeCodeRunRequest(
            message="Test message",
            input_format="invalid"
        )
        print("❌ input_format='invalid' should have failed but didn't")
    except ValidationError as e:
        print("✅ input_format='invalid' correctly rejected")
    
    print("\n🎉 Input format validation tests completed!")


if __name__ == "__main__":
    test_input_format_validation()