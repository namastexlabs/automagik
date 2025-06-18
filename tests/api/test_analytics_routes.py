"""Tests for analytics API endpoints."""

import pytest
import uuid
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.main import app


class TestAnalyticsRoutes:
    """Test suite for analytics API routes."""
    
    @pytest.fixture
    def valid_session_id(self):
        """Valid session UUID."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def valid_user_id(self):
        """Valid user UUID."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def sample_session_analytics(self, valid_session_id):
        """Sample session analytics response."""
        return {
            "session_id": valid_session_id,
            "total_tokens": 750,
            "total_requests": 5,
            "models": [
                {
                    "model": "gpt-4",
                    "framework": "pydantic_ai",
                    "message_count": 3,
                    "total_requests": 3,
                    "request_tokens": 150,
                    "response_tokens": 300,
                    "total_tokens": 450,
                    "cache_creation_tokens": 50,
                    "cache_read_tokens": 25
                }
            ],
            "summary": {
                "message_count": 5,
                "unique_models": 1,
                "total_request_tokens": 250,
                "total_response_tokens": 500,
                "total_cache_tokens": 75
            }
        }
    
    @pytest.fixture
    def sample_user_analytics(self, valid_user_id):
        """Sample user analytics response."""
        return {
            "user_id": valid_user_id,
            "days_analyzed": 30,
            "total_tokens": 1200,
            "models": [
                {
                    "model": "gpt-4",
                    "framework": "pydantic_ai",
                    "session_count": 3,
                    "message_count": 8,
                    "total_tokens": 1200
                }
            ],
            "summary": {
                "session_count": 3,
                "message_count": 8,
                "unique_models": 1
            }
        }
    
    def test_get_session_usage_success(self, client, valid_session_id, sample_session_analytics):
        """Test successful session usage analytics retrieval."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_session_usage_summary') as mock_service:
            
            # Setup mock
            mock_service.return_value = sample_session_analytics
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == valid_session_id
            assert data["total_tokens"] == 750
            assert data["total_requests"] == 5
            assert len(data["models"]) == 1
            assert data["summary"]["unique_models"] == 1
            
            # Verify service was called with correct parameters
            mock_service.assert_called_once_with(valid_session_id)
    
    def test_get_session_usage_invalid_session_id(self, client):
        """Test session usage analytics with invalid session ID."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_session_usage_summary') as mock_service:
            
            # Setup mock to return error
            mock_service.return_value = {"error": "Invalid session ID"}
            
            # Make request
            response = client.get("/api/v1/analytics/sessions/invalid-uuid/usage")
            
            # Assertions
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "Invalid session ID"
    
    def test_get_session_usage_service_error(self, client, valid_session_id):
        """Test session usage analytics with service error."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_session_usage_summary') as mock_service, \
             patch('src.api.routes.analytics_routes.logger') as mock_logger:
            
            # Setup mock to raise exception
            mock_service.side_effect = Exception("Database connection failed")
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert "Database connection failed" in data["detail"]
            mock_logger.error.assert_called()
    
    def test_get_user_usage_success(self, client, valid_user_id, sample_user_analytics):
        """Test successful user usage analytics retrieval."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_user_usage_summary') as mock_service:
            
            # Setup mock
            mock_service.return_value = sample_user_analytics
            
            # Make request
            response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == valid_user_id
            assert data["days_analyzed"] == 30
            assert data["total_tokens"] == 1200
            
            # Verify service was called with default days
            mock_service.assert_called_once_with(valid_user_id, 30)
    
    def test_get_user_usage_with_custom_days(self, client, valid_user_id, sample_user_analytics):
        """Test user usage analytics with custom days parameter."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_user_usage_summary') as mock_service:
            
            # Setup mock
            sample_user_analytics["days_analyzed"] = 14
            mock_service.return_value = sample_user_analytics
            
            # Make request with custom days
            response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage?days=14")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["days_analyzed"] == 14
            
            # Verify service was called with custom days
            mock_service.assert_called_once_with(valid_user_id, 14)
    
    def test_get_user_usage_invalid_days_parameter(self, client, valid_user_id):
        """Test user usage analytics with invalid days parameter."""
        # Test days too low
        response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage?days=0")
        assert response.status_code == 422
        
        # Test days too high
        response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage?days=500")
        assert response.status_code == 422
    
    def test_get_agent_usage_success(self, client):
        """Test successful agent usage analytics retrieval."""
        agent_id = 123
        sample_agent_analytics = {
            "agent_id": agent_id,
            "days_analyzed": 30,
            "total_tokens": 2400,
            "models": [
                {
                    "model": "gpt-4",
                    "framework": "pydantic_ai",
                    "session_count": 5,
                    "user_count": 3,
                    "message_count": 15,
                    "total_tokens": 2400
                }
            ],
            "summary": {
                "session_count": 5,
                "user_count": 3,
                "message_count": 15,
                "unique_models": 1
            }
        }
        
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_agent_usage_summary') as mock_service:
            
            # Setup mock
            mock_service.return_value = sample_agent_analytics
            
            # Make request
            response = client.get(f"/api/v1/analytics/agents/{agent_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == agent_id
            assert data["total_tokens"] == 2400
            assert data["summary"]["user_count"] == 3
            
            # Verify service was called with correct parameters
            mock_service.assert_called_once_with(agent_id, 30)
    
    def test_get_agent_usage_with_custom_days(self, client):
        """Test agent usage analytics with custom days parameter."""
        agent_id = 123
        
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_agent_usage_summary') as mock_service:
            
            # Setup mock
            mock_service.return_value = {"agent_id": agent_id, "days_analyzed": 7}
            
            # Make request with custom days
            response = client.get(f"/api/v1/analytics/agents/{agent_id}/usage?days=7")
            
            # Assertions
            assert response.status_code == 200
            
            # Verify service was called with custom days
            mock_service.assert_called_once_with(agent_id, 7)
    
    def test_get_top_usage_sessions_success(self, client):
        """Test successful top usage sessions retrieval."""
        sample_top_sessions = [
            {
                "session_id": str(uuid.uuid4()),
                "message_count": 10,
                "total_tokens": 1500,
                "request_tokens": 600,
                "response_tokens": 900,
                "unique_models": 2,
                "models_used": ["gpt-4", "gpt-3.5-turbo"]
            },
            {
                "session_id": str(uuid.uuid4()),
                "message_count": 5,
                "total_tokens": 800,
                "request_tokens": 300,
                "response_tokens": 500,
                "unique_models": 1,
                "models_used": ["gpt-4"]
            }
        ]
        
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_top_usage_sessions') as mock_service:
            
            # Setup mock
            mock_service.return_value = sample_top_sessions
            
            # Make request
            response = client.get("/api/v1/analytics/sessions/top-usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert data["limit"] == 10
            assert data["days_analyzed"] == 7
            assert len(data["sessions"]) == 2
            assert data["sessions"][0]["total_tokens"] == 1500
            
            # Verify service was called with default parameters
            mock_service.assert_called_once_with(10, 7)
    
    def test_get_top_usage_sessions_with_custom_parameters(self, client):
        """Test top usage sessions with custom limit and days parameters."""
        with patch('src.api.routes.analytics_routes.TokenAnalyticsService.get_top_usage_sessions') as mock_service:
            
            # Setup mock
            mock_service.return_value = []
            
            # Make request with custom parameters
            response = client.get("/api/v1/analytics/sessions/top-usage?limit=5&days=14")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 5
            assert data["days_analyzed"] == 14
            assert data["count"] == 0
            
            # Verify service was called with custom parameters
            mock_service.assert_called_once_with(5, 14)
    
    def test_get_top_usage_sessions_invalid_parameters(self, client):
        """Test top usage sessions with invalid parameters."""
        # Test limit too low
        response = client.get("/api/v1/analytics/sessions/top-usage?limit=0")
        assert response.status_code == 422
        
        # Test limit too high
        response = client.get("/api/v1/analytics/sessions/top-usage?limit=200")
        assert response.status_code == 422
        
        # Test days too low
        response = client.get("/api/v1/analytics/sessions/top-usage?days=0")
        assert response.status_code == 422
    
    def test_analytics_endpoints_authentication(self, client):
        """Test that analytics endpoints require authentication."""
        # Note: This test assumes the API uses authentication middleware
        # The actual implementation may vary based on the authentication system
        
        # Create client without API key
        client_no_auth = TestClient(app)
        
        # Remove any default authentication headers if they exist
        if hasattr(client_no_auth, 'headers'):
            client_no_auth.headers.clear()
        
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        agent_id = 123
        
        # Test that endpoints return appropriate authentication errors
        # (The exact status code depends on the authentication middleware)
        endpoints = [
            f"/api/v1/analytics/sessions/{session_id}/usage",
            f"/api/v1/analytics/users/{user_id}/usage",
            f"/api/v1/analytics/agents/{agent_id}/usage",
            "/api/v1/analytics/sessions/top-usage"
        ]
        
        for endpoint in endpoints:
            response = client_no_auth.get(endpoint)
            # Expecting either 401 (Unauthorized) or 403 (Forbidden)
            # depending on the authentication middleware implementation
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"