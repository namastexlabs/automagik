"""Tests for session controller token analytics helper functions."""

import pytest
import json
from datetime import datetime

from automagik.api.controllers.session_controller import _extract_usage_from_messages


class TestSessionControllerAnalyticsHelpers:
    """Test suite for session controller analytics helper functions."""
    
    def test_extract_usage_from_messages_helper_function(self):
        """Test the _extract_usage_from_messages helper function."""
        messages = [
            {
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_requests': 1,
                    'request_tokens': 100,
                    'response_tokens': 200,
                    'total_tokens': 300,
                    'cache_creation_tokens': 25,
                    'cache_read_tokens': 10
                }
            },
            {
                'usage': {
                    'model': 'gpt-3.5-turbo',
                    'framework': 'pydantic_ai',
                    'total_requests': 1,
                    'request_tokens': 50,
                    'response_tokens': 100,
                    'total_tokens': 150,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 5
                }
            }
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 450  # 300 + 150
        assert result['total_requests'] == 2  # 1 + 1
        assert len(result['models']) == 2  # Different models
        assert result['summary']['message_count'] == 2
        assert result['summary']['unique_models'] == 2
        assert result['summary']['total_request_tokens'] == 150  # 100 + 50
        assert result['summary']['total_response_tokens'] == 300  # 200 + 100
        assert result['summary']['total_cache_tokens'] == 40  # (25+10) + (0+5)
    
    def test_extract_usage_from_messages_with_json_strings(self):
        """Test usage extraction when usage data is JSON strings."""
        messages = [
            {
                'usage': json.dumps({
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_tokens': 100,
                    'request_tokens': 40,
                    'response_tokens': 60
                })
            }
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 100
        assert len(result['models']) == 1
        assert result['models'][0]['model'] == 'gpt-4'
    
    def test_extract_usage_from_messages_mixed_data(self):
        """Test usage extraction with mixed valid/invalid data."""
        messages = [
            {'usage': None},  # No usage
            {'usage': 'invalid json'},  # Invalid JSON
            {'usage': {'model': 'gpt-4', 'total_tokens': 100}},  # Valid usage
            {}  # No usage field
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 100  # Only valid usage counted
        assert len(result['models']) == 1
        assert result['summary']['message_count'] == 1  # Only messages with valid usage
    
    def test_extract_usage_from_messages_no_usage_data(self):
        """Test usage extraction when no messages have usage data."""
        messages = [
            {'id': 'msg1', 'text_content': 'No usage'},
            {'id': 'msg2', 'usage': None},
            {'id': 'msg3', 'usage': 'invalid json'}
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 0
        assert result['total_requests'] == 0
        assert result['models'] == []
        assert result['summary']['message_count'] == 0
        assert result['summary']['unique_models'] == 0
    
    def test_extract_usage_from_messages_same_model_framework(self):
        """Test usage extraction with multiple messages from same model/framework."""
        messages = [
            {
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_requests': 1,
                    'request_tokens': 100,
                    'response_tokens': 200,
                    'total_tokens': 300
                }
            },
            {
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_requests': 1,
                    'request_tokens': 150,
                    'response_tokens': 250,
                    'total_tokens': 400
                }
            }
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 700  # 300 + 400
        assert result['total_requests'] == 2  # 1 + 1
        assert len(result['models']) == 1  # Same model/framework aggregated
        assert result['models'][0]['total_tokens'] == 700
        assert result['models'][0]['message_count'] == 2
        assert result['summary']['unique_models'] == 1
    
    def test_extract_usage_from_messages_missing_fields(self):
        """Test usage extraction when some fields are missing."""
        messages = [
            {
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_tokens': 300
                    # Missing other fields
                }
            }
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert result['total_tokens'] == 300
        assert result['total_requests'] == 0  # Missing field defaults to 0
        assert len(result['models']) == 1
        assert result['models'][0]['request_tokens'] == 0
        assert result['models'][0]['response_tokens'] == 0
        assert result['models'][0]['cache_creation_tokens'] == 0
    
    def test_extract_usage_from_messages_empty_list(self):
        """Test usage extraction with empty message list."""
        result = _extract_usage_from_messages([])
        
        # Assertions
        assert result['total_tokens'] == 0
        assert result['total_requests'] == 0
        assert result['models'] == []
        assert result['summary']['message_count'] == 0
        assert result['summary']['unique_models'] == 0
    
    def test_extract_usage_from_messages_analysis_timestamp(self):
        """Test that analysis timestamp is included in results."""
        messages = [
            {
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_tokens': 100
                }
            }
        ]
        
        result = _extract_usage_from_messages(messages)
        
        # Assertions
        assert 'analysis_timestamp' in result['summary']
        # Check that timestamp is a valid ISO format
        timestamp = result['summary']['analysis_timestamp']
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp}")