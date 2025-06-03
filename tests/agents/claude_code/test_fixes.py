"""Fixes for test issues in Claude-Code tests.

This file provides patches and utilities to fix common test issues.
"""
from unittest.mock import Mock, MagicMock


def create_mock_settings():
    """Create a properly mocked settings object."""
    mock_settings = MagicMock()
    
    # Set the AM_ENABLE_CLAUDE_CODE attribute directly
    mock_settings.AM_ENABLE_CLAUDE_CODE = False
    
    # Add a config-like interface for backwards compatibility
    mock_settings.AM_ENABLE_CLAUDE_CODE = False
    
    # Make the mock return appropriate values when accessed as attributes
    def get_attr(name):
        if name == "AM_ENABLE_CLAUDE_CODE":
            return mock_settings._enable_claude_code
        elif name == "config":
            return {"AM_ENABLE_CLAUDE_CODE": mock_settings._enable_claude_code}
        return Mock()
    
    mock_settings._enable_claude_code = False
    mock_settings.__getattr__ = get_attr
    
    return mock_settings