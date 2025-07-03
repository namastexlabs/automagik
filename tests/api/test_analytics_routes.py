"""Tests for analytics API endpoints using repository pattern."""

import pytest
import uuid
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from automagik.main import app


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
    def sample_messages_with_usage(self):
        """Sample messages with usage data."""
        return [
            {
                'id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'role': 'assistant',
                'text_content': 'Response 1',
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
                'id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'role': 'assistant',
                'text_content': 'Response 2',
                'usage': {
                    'model': 'gpt-4',
                    'framework': 'pydantic_ai',
                    'total_requests': 1,
                    'request_tokens': 150,
                    'response_tokens': 300,
                    'total_tokens': 450,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 5
                }
            }
        ]
    
    @pytest.fixture
    def sample_sessions(self):
        """Sample sessions data."""
        return [
            {
                'id': str(uuid.uuid4()),
                'user_id': str(uuid.uuid4()),
                'agent_id': 123,
                'name': 'Test Session 1',
                'created_at': '2024-01-01T10:00:00Z'
            },
            {
                'id': str(uuid.uuid4()),
                'user_id': str(uuid.uuid4()),
                'agent_id': 123,
                'name': 'Test Session 2',
                'created_at': '2024-01-02T10:00:00Z'
            }
        ]
    
    def test_get_session_usage_success(self, client, valid_session_id, sample_messages_with_usage):
        """Test successful session usage analytics retrieval."""
        with patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == valid_session_id
            assert data["total_tokens"] == 750  # 300 + 450
            assert data["total_requests"] == 2  # 1 + 1
            assert len(data["models"]) == 1  # Same model/framework
            assert data["models"][0]["model"] == "gpt-4"
            assert data["models"][0]["framework"] == "pydantic_ai"
            assert data["models"][0]["total_tokens"] == 750
            assert data["summary"]["unique_models"] == 1
            assert data["summary"]["message_count"] == 2
    
    def test_get_session_usage_invalid_session_id(self, client):
        """Test session usage analytics with invalid session ID."""
        with patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mock to return None for invalid UUID
            mock_safe_uuid.return_value = None
            
            # Make request
            response = client.get("/api/v1/analytics/sessions/invalid-uuid/usage")
            
            # Assertions
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "Invalid session ID"
    
    def test_get_session_usage_no_messages(self, client, valid_session_id):
        """Test session usage analytics with no messages."""
        with patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_list_messages.return_value = ([], 0)
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == valid_session_id
            assert data["total_tokens"] == 0
            assert data["total_requests"] == 0
            assert data["models"] == []
            assert data["summary"]["message_count"] == 0
    
    def test_get_user_usage_success(self, client, valid_user_id, sample_sessions, sample_messages_with_usage):
        """Test successful user usage analytics retrieval."""
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x == valid_user_id or x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request
            response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == valid_user_id
            assert data["days_analyzed"] == 30
            assert data["total_tokens"] > 0
            assert len(data["models"]) >= 1
            assert data["summary"]["session_count"] == 2
    
    def test_get_user_usage_with_custom_days(self, client, valid_user_id, sample_sessions, sample_messages_with_usage):
        """Test user usage analytics with custom days parameter."""
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x == valid_user_id or x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request with custom days
            response = client.get(f"/api/v1/analytics/users/{valid_user_id}/usage?days=14")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["days_analyzed"] == 14
    
    def test_get_user_usage_invalid_user_id(self, client):
        """Test user usage analytics with invalid user ID."""
        with patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mock to return None for invalid UUID
            mock_safe_uuid.return_value = None
            
            # Make request
            response = client.get("/api/v1/analytics/users/invalid-uuid/usage")
            
            # Assertions
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "Invalid user ID"
    
    def test_get_agent_usage_success(self, client, sample_sessions, sample_messages_with_usage):
        """Test successful agent usage analytics retrieval."""
        agent_id = 123
        
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request
            response = client.get(f"/api/v1/analytics/agents/{agent_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == agent_id
            assert data["days_analyzed"] == 30
            assert data["total_tokens"] > 0
            assert data["summary"]["session_count"] == 2
            assert "user_count" in data["summary"]
    
    def test_get_agent_usage_with_custom_days(self, client, sample_sessions, sample_messages_with_usage):
        """Test agent usage analytics with custom days parameter."""
        agent_id = 123
        
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request with custom days
            response = client.get(f"/api/v1/analytics/agents/{agent_id}/usage?days=7")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["days_analyzed"] == 7
    
    def test_get_top_usage_sessions_success(self, client, sample_sessions, sample_messages_with_usage):
        """Test successful top usage sessions retrieval."""
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = (sample_messages_with_usage, 2)
            
            # Make request
            response = client.get("/api/v1/analytics/sessions/top-usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["days_analyzed"] == 7
            assert data["count"] >= 0
            assert "sessions" in data
    
    def test_get_top_usage_sessions_with_custom_parameters(self, client, sample_sessions):
        """Test top usage sessions with custom limit and days parameters."""
        with patch('automagik.api.routes.analytics_routes.list_sessions') as mock_list_sessions, \
             patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.side_effect = lambda x: uuid.UUID(x) if x in [s['id'] for s in sample_sessions] else uuid.UUID(x)
            mock_list_sessions.return_value = (sample_sessions, 2)
            mock_list_messages.return_value = ([], 0)  # No usage data
            
            # Make request with custom parameters
            response = client.get("/api/v1/analytics/sessions/top-usage?limit=5&days=14")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 5
            assert data["days_analyzed"] == 14
            assert data["count"] == 0  # No sessions with usage data
    
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
    
    def test_extract_usage_from_messages_with_json_string(self, client, valid_session_id):
        """Test that JSON string usage data is properly parsed."""
        import json
        
        messages_with_json_usage = [
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
        
        with patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_list_messages.return_value = (messages_with_json_usage, 1)
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["total_tokens"] == 100
            assert len(data["models"]) == 1
            assert data["models"][0]["model"] == "gpt-4"
    
    def test_extract_usage_from_messages_no_usage_data(self, client, valid_session_id):
        """Test messages without usage data are handled gracefully."""
        messages_without_usage = [
            {'id': str(uuid.uuid4()), 'text_content': 'No usage'},
            {'id': str(uuid.uuid4()), 'usage': None},
            {'id': str(uuid.uuid4()), 'usage': 'invalid json'}
        ]
        
        with patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_list_messages.return_value = (messages_without_usage, 3)
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["total_tokens"] == 0
            assert data["models"] == []
            assert data["summary"]["message_count"] == 0
    
    def test_analytics_endpoints_error_handling(self, client, valid_session_id):
        """Test that analytics endpoints handle errors gracefully."""
        with patch('automagik.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('automagik.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks to raise exception
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_list_messages.side_effect = Exception("Database error")
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{valid_session_id}/usage")
            
            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert "Database error" in data["detail"]