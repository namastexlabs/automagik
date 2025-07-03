"""Unit tests for API authentication middleware.

This module tests the authentication mechanisms including
API key validation, middleware behavior, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request, Response
from starlette.responses import JSONResponse

from fastapi import Depends
from automagik.auth import APIKeyMiddleware, get_api_key, API_KEY_NAME
from automagik.config import settings


class TestAPIKeyMiddleware:
    """Test suite for APIKeyMiddleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return APIKeyMiddleware(MagicMock())
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/test"
        request.headers = {}
        request.query_params = {}
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function."""
        async def call_next(request):
            return Response("Success")
        return AsyncMock(side_effect=call_next)
    
    @pytest.mark.asyncio
    async def test_no_auth_paths_bypass_authentication(self, middleware, mock_call_next):
        """Test that no-auth paths bypass authentication."""
        no_auth_paths = [
            "/health",
            "/",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/mcp/health"
        ]
        
        for path in no_auth_paths:
            request = MagicMock(spec=Request)
            request.url.path = path
            request.headers = {}
            request.query_params = {}
            
            response = await middleware.dispatch(request, mock_call_next)
            
            assert response.body == b"Success"
            mock_call_next.assert_called_with(request)
    
    @pytest.mark.asyncio
    async def test_valid_api_key_in_header(self, middleware, mock_request, mock_call_next):
        """Test valid API key in header allows access."""
        mock_request.headers = {API_KEY_NAME: settings.AM_API_KEY}
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.body == b"Success"
        mock_call_next.assert_called_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_valid_api_key_in_query_params(self, middleware, mock_request, mock_call_next):
        """Test valid API key in query parameters allows access."""
        mock_request.query_params = {API_KEY_NAME: settings.AM_API_KEY}
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.body == b"Success"
        mock_call_next.assert_called_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self, middleware, mock_request, mock_call_next):
        """Test missing API key returns 401."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        assert response.body == b'{"detail":"x-api-key is missing in headers or query parameters"}'
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, middleware, mock_request, mock_call_next):
        """Test invalid API key returns 401."""
        mock_request.headers = {API_KEY_NAME: "invalid-key"}
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        assert response.body == b'{"detail":"Invalid API Key"}'
        mock_call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_header_priority_over_query(self, middleware, mock_request, mock_call_next):
        """Test header API key takes priority over query parameter."""
        mock_request.headers = {API_KEY_NAME: settings.AM_API_KEY}
        mock_request.query_params = {API_KEY_NAME: "invalid-key"}
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.body == b"Success"
        mock_call_next.assert_called_with(mock_request)
    
    @pytest.mark.asyncio
    async def test_case_sensitive_header(self, middleware, mock_request, mock_call_next):
        """Test that header name is case-sensitive."""
        # Wrong case should not work
        mock_request.headers = {"X-API-KEY": settings.AM_API_KEY}  # Wrong case
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 401
        mock_call_next.assert_not_called()


class TestGetAPIKeyDependency:
    """Test suite for get_api_key dependency function."""
    
    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test valid API key returns successfully."""
        result = await get_api_key(settings.AM_API_KEY)
        assert result == settings.AM_API_KEY
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test missing API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "API key is missing"
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test invalid API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key("invalid-key")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"


class TestJSONParsingMiddleware:
    """Test suite for JSONParsingMiddleware from middleware.py."""
    
    @pytest.fixture
    def json_middleware(self):
        """Create JSONParsingMiddleware instance."""
        from automagik.api.middleware import JSONParsingMiddleware
        return JSONParsingMiddleware(MagicMock())
    
    @pytest.fixture
    def mock_json_request(self):
        """Create mock request with JSON content."""
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/agent/test/run"
        request.headers = {"content-type": "application/json"}
        return request
    
    @pytest.mark.asyncio
    async def test_valid_json_passes_through(self, json_middleware, mock_json_request):
        """Test valid JSON passes through unchanged."""
        valid_json = b'{"message_content": "Hello world"}'
        mock_json_request.body = AsyncMock(return_value=valid_json)
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        response = await json_middleware.dispatch(mock_json_request, call_next)
        
        assert response.body == b"Success"
        assert mock_json_request._body == valid_json
    
    @pytest.mark.asyncio
    async def test_empty_body_passes_through(self, json_middleware, mock_json_request):
        """Test empty body passes through."""
        mock_json_request.body = AsyncMock(return_value=b"")
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        response = await json_middleware.dispatch(mock_json_request, call_next)
        
        assert response.body == b"Success"
        assert not hasattr(mock_json_request, '_body')
    
    @pytest.mark.asyncio
    async def test_non_json_request_ignored(self, json_middleware):
        """Test non-JSON requests are ignored."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/test"
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        response = await json_middleware.dispatch(request, call_next)
        
        assert response.body == b"Success"
        # body() should never be called for GET requests
        # Check that body() wasn't accessed by checking if it was called
        assert not hasattr(request, '_body')
    
    @pytest.mark.asyncio
    async def test_malformed_json_fixed(self, json_middleware, mock_json_request):
        """Test malformed JSON is fixed."""
        # JSON with unescaped newlines
        malformed_json = b'{"message_content": "Line 1\nLine 2"}'
        mock_json_request.body = AsyncMock(return_value=malformed_json)
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        with patch('automagik.api.middleware.logger') as mock_logger:
            response = await json_middleware.dispatch(mock_json_request, call_next)
            
            assert response.body == b"Success"
            # Should be fixed with escaped newline
            fixed_body = mock_json_request._body.decode('utf-8')
            assert '\\n' in fixed_body
            assert '\n' not in fixed_body.replace('\\n', '')
            mock_logger.info.assert_called()
    
    @pytest.mark.asyncio
    async def test_control_characters_removed(self, json_middleware, mock_json_request):
        """Test control characters are sanitized."""
        # JSON with control characters
        json_with_control = b'{"message_content": "Text\x00with\x01control\x02chars"}'
        mock_json_request.body = AsyncMock(return_value=json_with_control)
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        response = await json_middleware.dispatch(mock_json_request, call_next)
        
        assert response.body == b"Success"
        fixed_body = mock_json_request._body.decode('utf-8')
        # Control characters should be replaced with spaces
        assert '\x00' not in fixed_body
        assert '\x01' not in fixed_body
        assert '\x02' not in fixed_body
    
    @pytest.mark.asyncio
    async def test_manual_field_extraction_fallback(self, json_middleware, mock_json_request):
        """Test manual field extraction as last resort."""
        # Severely malformed JSON
        malformed = b'{"message_content": "Broken"quote", "user": {"email": "test@example.com"}}'
        mock_json_request.body = AsyncMock(return_value=malformed)
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        with patch('automagik.api.middleware.logger') as mock_logger:
            response = await json_middleware.dispatch(mock_json_request, call_next)
            
            assert response.body == b"Success"
            # Should attempt manual extraction
            mock_logger.info.assert_any_call("Fixed JSON by manual field extraction")
    
    @pytest.mark.asyncio
    async def test_non_utf8_body_handled(self, json_middleware, mock_json_request):
        """Test non-UTF8 body is handled gracefully."""
        # Invalid UTF-8 bytes
        non_utf8 = b'\x80\x81\x82'
        mock_json_request.body = AsyncMock(return_value=non_utf8)
        
        call_next = AsyncMock(return_value=Response("Success"))
        
        with patch('automagik.api.middleware.logger') as mock_logger:
            response = await json_middleware.dispatch(mock_json_request, call_next)
            
            assert response.body == b"Success"
            assert mock_json_request._body == non_utf8
            mock_logger.warning.assert_called_with("Non-UTF8 request body received")


class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""
    
    @pytest.fixture
    def client(self):
        """Create test client with authentication middleware."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        app.add_middleware(APIKeyMiddleware)
        
        @app.get("/api/v1/protected")
        async def protected_route(api_key: str = Depends(get_api_key)):
            return {"message": "Protected content", "api_key": api_key}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        return TestClient(app)
    
    def test_protected_route_with_valid_key(self, client):
        """Test protected route with valid API key."""
        response = client.get(
            "/api/v1/protected",
            headers={API_KEY_NAME: settings.AM_API_KEY}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Protected content"
        assert response.json()["api_key"] == settings.AM_API_KEY
    
    def test_protected_route_without_key(self, client):
        """Test protected route without API key."""
        response = client.get("/api/v1/protected")
        
        assert response.status_code == 401
        assert "x-api-key is missing" in response.json()["detail"]
    
    def test_health_endpoint_no_auth(self, client):
        """Test health endpoint requires no authentication."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])