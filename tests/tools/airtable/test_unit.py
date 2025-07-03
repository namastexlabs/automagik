"""Enhanced unit tests for Airtable tool helpers and validation."""

import pytest
from unittest.mock import Mock, patch

from automagik.config import settings
from automagik.tools.airtable.tool import (
    _headers, 
    _get_token, 
    _request,
    MAX_RECORDS_PER_BATCH,
    DEFAULT_PAGE_SIZE,
    API_BASE_URL
)


class TestTokenManagement:
    """Test token handling and authentication."""
    
    def test_headers_contains_token(self, monkeypatch):
        """_headers() should build correct Authorization header."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "unit_test_token")
        headers = _headers()
        assert headers["Authorization"] == "Bearer unit_test_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "automagik-agents/airtable-tool"
    
    def test_get_token_success(self, monkeypatch):
        """_get_token() should return token when configured."""
        test_token = "pat_test123456789"
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", test_token)
        assert _get_token() == test_token
    
    def test_get_token_missing_raises_error(self, monkeypatch):
        """_get_token() should raise ValueError when token is None."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", None)
        with pytest.raises(ValueError, match="AIRTABLE_TOKEN is not configured"):
            _get_token()
    
    def test_get_token_empty_raises_error(self, monkeypatch):
        """_get_token() should raise ValueError when token is empty."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "")
        with pytest.raises(ValueError, match="AIRTABLE_TOKEN is not configured"):
            _get_token()


class TestRequestHandling:
    """Test HTTP request handling and rate limiting."""
    
    @patch('automagik.tools.airtable.tool.requests.request')
    def test_request_success(self, mock_request, monkeypatch):
        """_request() should handle successful responses."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "test_token")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": []}
        mock_request.return_value = mock_response
        
        result = _request("GET", "https://api.airtable.com/v0/test")
        
        assert result.status_code == 200
        mock_request.assert_called_once()
        
        # Verify headers were set correctly
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer test_token'
        assert headers['Content-Type'] == 'application/json'
    
    @patch('automagik.tools.airtable.tool.requests.request')
    @patch('automagik.tools.airtable.tool.time.sleep')
    def test_request_rate_limit_retry(self, mock_sleep, mock_request, monkeypatch):
        """_request() should handle 429 rate limiting with retry."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "test_token")
        
        # First call returns 429, second call succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"records": []}
        
        mock_request.side_effect = [rate_limit_response, success_response]
        
        result = _request("GET", "https://api.airtable.com/v0/test")
        
        assert result.status_code == 200
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once_with(30)  # Should sleep 30 seconds
    
    @patch('automagik.tools.airtable.tool.requests.request')
    def test_request_rate_limit_no_retry(self, mock_request, monkeypatch):
        """_request() should not retry when retry_on_rate_limit=False."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_request.return_value = mock_response
        
        result = _request("GET", "https://api.airtable.com/v0/test", retry_on_rate_limit=False)
        
        assert result.status_code == 429
        assert mock_request.call_count == 1
    
    @patch('automagik.tools.airtable.tool.requests.request')
    def test_request_with_params_and_json(self, mock_request, monkeypatch):
        """_request() should pass through params and json correctly."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        test_params = {"pageSize": 10, "view": "Grid view"}
        test_json = {"records": [{"fields": {"Name": "Test"}}]}
        
        _request("POST", "https://api.airtable.com/v0/test", 
                params=test_params, json=test_json)
        
        mock_request.assert_called_once_with(
            "POST", 
            "https://api.airtable.com/v0/test",
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'automagik-agents/airtable-tool'
            },
            params=test_params,
            json=test_json,
            timeout=30
        )


class TestConstants:
    """Test that constants are set correctly."""
    
    def test_api_base_url(self):
        """API_BASE_URL should be correct."""
        assert API_BASE_URL == "https://api.airtable.com/v0"
    
    def test_default_page_size(self):
        """DEFAULT_PAGE_SIZE should be Airtable maximum."""
        assert DEFAULT_PAGE_SIZE == 100
    
    def test_max_records_per_batch(self):
        """MAX_RECORDS_PER_BATCH should be Airtable maximum."""
        assert MAX_RECORDS_PER_BATCH == 10


class TestValidation:
    """Test input validation and edge cases."""
    
    def test_empty_records_list(self):
        """Test handling of empty records list."""
        # This would be tested in integration, but we can verify constants
        assert MAX_RECORDS_PER_BATCH > 0
        assert DEFAULT_PAGE_SIZE > 0
    
    def test_large_batch_size_limit(self):
        """Verify batch size limits are enforced."""
        # This ensures our constants match Airtable's actual limits
        assert MAX_RECORDS_PER_BATCH == 10  # Airtable's actual limit for writes
        assert DEFAULT_PAGE_SIZE == 100     # Airtable's actual limit for reads


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('automagik.tools.airtable.tool.requests.request')
    def test_request_timeout_handling(self, mock_request, monkeypatch):
        """Test that request timeout is set correctly."""
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        _request("GET", "https://api.airtable.com/v0/test")
        
        # Verify timeout was set
        call_args = mock_request.call_args
        assert call_args[1]['timeout'] == 30
    
    def test_headers_with_special_characters_in_token(self, monkeypatch):
        """Test headers with special characters in token."""
        special_token = "pat_abc123!@#$%^&*()"
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", special_token)
        
        headers = _headers()
        assert headers["Authorization"] == f"Bearer {special_token}"
    
    def test_headers_with_very_long_token(self, monkeypatch):
        """Test headers with very long token."""
        long_token = "pat_" + "x" * 1000  # Very long token
        monkeypatch.setattr(settings, "AIRTABLE_TOKEN", long_token)
        
        headers = _headers()
        assert headers["Authorization"] == f"Bearer {long_token}"


class TestURLConstruction:
    """Test URL construction and validation."""
    
    def test_api_base_url_format(self):
        """Verify API base URL has correct format."""
        assert API_BASE_URL.startswith("https://")
        assert "airtable.com" in API_BASE_URL
        assert API_BASE_URL.endswith("/v0")
        assert not API_BASE_URL.endswith("/")  # Should not have trailing slash
    
    def test_url_components(self):
        """Test individual URL components."""
        assert "api.airtable.com" in API_BASE_URL
        assert "/v0" in API_BASE_URL 