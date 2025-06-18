"""Integration tests for agent API usage tracking functionality."""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.agents.models.response import AgentResponse


class TestAgentAPIUsageIntegration:
    """Integration test suite for agent API usage tracking."""
    
    @pytest.fixture
    def valid_agent_name(self):
        """Valid agent name for testing."""
        return "test-agent"
    
    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data structure."""
        return {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_requests": 1,
            "request_tokens": 150,
            "response_tokens": 300,
            "total_tokens": 450,
            "cache_creation_tokens": 25,
            "cache_read_tokens": 10
        }
    
    @pytest.fixture
    def agent_response_with_usage(self, sample_usage_data):
        """Agent response object with usage data."""
        return AgentResponse(
            text="This is a test response",
            success=True,
            error_message=None,
            tool_calls=[],
            tool_outputs=[],
            raw_message=None,
            system_prompt=None,
            usage=sample_usage_data
        )
    
    @pytest.fixture
    def agent_response_without_usage(self):
        """Agent response object without usage data."""
        return AgentResponse(
            text="This is a test response",
            success=True,
            error_message=None,
            tool_calls=[],
            tool_outputs=[],
            raw_message=None,
            system_prompt=None,
            usage=None
        )
    
    def test_agent_run_includes_usage_in_response(self, client, valid_agent_name, agent_response_with_usage):
        """Test that agent run API includes usage information in response."""
        with patch('src.api.controllers.agent_controller.get_agent_by_name') as mock_get_agent_by_name, \
             patch('src.api.controllers.agent_controller.AgentFactory') as mock_agent_factory_class, \
             patch('src.api.controllers.agent_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.agent_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message = AsyncMock(return_value=agent_response_with_usage)
            
            # Mock agent factory
            mock_factory = Mock()
            mock_factory.get_agent.return_value = mock_agent
            mock_agent_factory_class.return_value = mock_factory
            
            # Mock database agent
            mock_db_agent = Mock()
            mock_db_agent.name = valid_agent_name
            mock_db_agent.agent_type = "test_type"
            mock_get_agent_by_name.return_value = mock_db_agent
            
            mock_run_in_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            # Mock message history
            mock_message_history = Mock()
            mock_message_history.session_id = str(uuid.uuid4())
            mock_message_history.get_session_info.return_value = {"id": mock_message_history.session_id}
            mock_message_history_class.return_value = mock_message_history
            
            # Test data
            request_data = {
                "content": "Test message",
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
            
            # Make request
            response = client.post(f"/api/v1/agent/{valid_agent_name}/run", json=request_data)
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify basic response structure
            assert "message" in data
            assert "success" in data
            assert "session_id" in data
            assert data["success"] is True
            assert data["message"] == "This is a test response"
            
            # Verify usage information is included
            assert "usage" in data
            usage = data["usage"]
            assert usage["framework"] == "pydantic_ai"
            assert usage["model"] == "gpt-4"
            assert usage["total_tokens"] == 450
            assert usage["request_tokens"] == 150
            assert usage["response_tokens"] == 300
            assert usage["total_requests"] == 1
    
    def test_agent_run_without_usage_data(self, client, valid_agent_name, agent_response_without_usage):
        """Test that agent run API works when no usage data is available."""
        with patch('src.api.controllers.agent_controller.get_agent') as mock_get_agent, \
             patch('src.api.controllers.agent_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.agent_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message = AsyncMock(return_value=agent_response_without_usage)
            mock_get_agent.return_value = mock_agent
            mock_run_in_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            # Mock message history
            mock_message_history = Mock()
            mock_message_history.session_id = str(uuid.uuid4())
            mock_message_history.get_session_info.return_value = {"id": mock_message_history.session_id}
            mock_message_history_class.return_value = mock_message_history
            
            # Test data
            request_data = {
                "content": "Test message",
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
            
            # Make request
            response = client.post(f"/api/v1/agent/{valid_agent_name}/run", json=request_data)
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify basic response structure
            assert "message" in data
            assert "success" in data
            assert "session_id" in data
            assert data["success"] is True
            assert data["message"] == "This is a test response"
            
            # Verify usage information is not included when not available
            assert "usage" not in data
    
    def test_agent_run_with_string_response(self, client, valid_agent_name):
        """Test that agent run API works with simple string responses."""
        with patch('src.api.controllers.agent_controller.get_agent') as mock_get_agent, \
             patch('src.api.controllers.agent_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.agent_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message = AsyncMock(return_value="Simple string response")
            mock_get_agent.return_value = mock_agent
            mock_run_in_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            # Mock message history
            mock_message_history = Mock()
            mock_message_history.session_id = str(uuid.uuid4())
            mock_message_history.get_session_info.return_value = {"id": mock_message_history.session_id}
            mock_message_history_class.return_value = mock_message_history
            
            # Test data
            request_data = {
                "content": "Test message",
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
            
            # Make request
            response = client.post(f"/api/v1/agent/{valid_agent_name}/run", json=request_data)
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify basic response structure
            assert "message" in data
            assert "success" in data
            assert "session_id" in data
            assert data["success"] is True
            assert data["message"] == "Simple string response"
            
            # Verify no usage information for string responses
            assert "usage" not in data
    
    def test_agent_run_with_dict_response_including_usage(self, client, valid_agent_name, sample_usage_data):
        """Test that agent run API works with dictionary responses that include usage."""
        with patch('src.api.controllers.agent_controller.get_agent') as mock_get_agent, \
             patch('src.api.controllers.agent_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.agent_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks
            mock_agent = Mock()
            dict_response = {
                "text": "Dictionary response",
                "success": True,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": sample_usage_data
            }
            mock_agent.process_message = AsyncMock(return_value=dict_response)
            mock_get_agent.return_value = mock_agent
            mock_run_in_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            # Mock message history
            mock_message_history = Mock()
            mock_message_history.session_id = str(uuid.uuid4())
            mock_message_history.get_session_info.return_value = {"id": mock_message_history.session_id}
            mock_message_history_class.return_value = mock_message_history
            
            # Test data
            request_data = {
                "content": "Test message",
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
            
            # Make request
            response = client.post(f"/api/v1/agent/{valid_agent_name}/run", json=request_data)
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify basic response structure
            assert "message" in data
            assert "success" in data
            assert "session_id" in data
            assert data["success"] is True
            assert data["message"] == "Dictionary response"
            
            # Verify usage information is included
            assert "usage" in data
            usage = data["usage"]
            assert usage["framework"] == "pydantic_ai"
            assert usage["model"] == "gpt-4"
            assert usage["total_tokens"] == 450
    
    def test_agent_run_error_handling_preserves_usage(self, client, valid_agent_name):
        """Test that usage information is preserved even during error scenarios."""
        with patch('src.api.controllers.agent_controller.get_agent') as mock_get_agent, \
             patch('src.api.controllers.agent_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.agent_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks to simulate agent not found
            mock_get_agent.return_value = None
            
            # Test data
            request_data = {
                "content": "Test message",
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
            
            # Make request
            response = client.post(f"/api/v1/agent/{valid_agent_name}/run", json=request_data)
            
            # Assertions - should get error but structure should be consistent
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
    
    def test_session_endpoint_includes_token_analytics(self, client):
        """Test that session endpoint includes token analytics."""
        session_id = str(uuid.uuid4())
        
        with patch('src.api.controllers.session_controller.db_get_session') as mock_get_session, \
             patch('src.api.controllers.session_controller.list_session_messages') as mock_list_messages, \
             patch('src.api.controllers.session_controller.get_system_prompt') as mock_get_prompt, \
             patch('src.api.controllers.session_controller.safe_uuid') as mock_safe_uuid, \
             patch('src.api.controllers.session_controller.run_in_threadpool') as mock_run_in_threadpool, \
             patch('src.api.controllers.session_controller.MessageHistory') as mock_message_history_class:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(session_id)
            mock_run_in_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            # Mock session data
            mock_session_obj = Mock()
            mock_session_obj.to_dict.return_value = {
                'id': session_id,
                'name': 'Test Session',
                'user_id': str(uuid.uuid4()),
                'agent_id': 123
            }
            mock_get_session.return_value = mock_session_obj
            
            # Mock messages with usage data
            mock_messages = [
                {
                    'id': str(uuid.uuid4()),
                    'role': 'assistant',
                    'text_content': 'Response',
                    'usage': {
                        'model': 'gpt-4',
                        'framework': 'pydantic_ai',
                        'total_tokens': 300
                    }
                }
            ]
            mock_list_messages.return_value = (mock_messages, 1)
            
            # Mock message history
            mock_message_history = Mock()
            mock_message_history.get_messages_for_api.return_value = (mock_messages, 1)
            mock_message_history_class.return_value = mock_message_history
            mock_get_prompt.return_value = None
            
            # Make request
            response = client.get(f"/api/v1/sessions/{session_id}")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify session data structure
            assert "id" in data
            assert "messages" in data
            assert "token_analytics" in data
            
            # Verify token analytics structure
            analytics = data["token_analytics"]
            assert "session_id" in analytics
            assert "total_tokens" in analytics
            assert "models" in analytics
            assert "summary" in analytics
            assert analytics["total_tokens"] == 300
    
    def test_analytics_endpoint_session_usage(self, client):
        """Test that analytics endpoint returns proper session usage data."""
        session_id = str(uuid.uuid4())
        
        with patch('src.api.routes.analytics_routes.list_session_messages') as mock_list_messages, \
             patch('src.api.routes.analytics_routes.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(session_id)
            
            # Mock messages with usage data
            mock_messages = [
                {
                    'usage': {
                        'model': 'gpt-4',
                        'framework': 'pydantic_ai',
                        'total_requests': 1,
                        'request_tokens': 100,
                        'response_tokens': 200,
                        'total_tokens': 300
                    }
                }
            ]
            mock_list_messages.return_value = (mock_messages, 1)
            
            # Make request
            response = client.get(f"/api/v1/analytics/sessions/{session_id}/usage")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            
            # Verify analytics response structure
            assert "session_id" in data
            assert "total_tokens" in data
            assert "total_requests" in data
            assert "models" in data
            assert "summary" in data
            
            assert data["session_id"] == session_id
            assert data["total_tokens"] == 300
            assert data["total_requests"] == 1
            assert len(data["models"]) == 1
            assert data["models"][0]["model"] == "gpt-4"