"""Simple integration tests for agent API usage field in responses."""

import pytest
import uuid
from unittest.mock import Mock, patch
from automagik.api.controllers.agent_controller import handle_agent_run
from automagik.api.models import AgentRunRequest
from automagik.agents.models.response import AgentResponse


class TestAgentResponseUsageField:
    """Test suite for agent response usage field functionality."""
    
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
    
    @pytest.mark.asyncio
    async def test_agent_response_includes_usage_when_available(self, sample_usage_data):
        """Test that agent response includes usage field when available."""
        # Create test user ID first
        test_user_id = str(uuid.uuid4())
        
        # Create mock agent response with usage
        mock_response = AgentResponse(
            text="Test response",
            success=True,
            usage=sample_usage_data
        )
        
        # Mock the agent execution to return our mock response
        with patch('automagik.api.controllers.agent_controller.get_agent_by_name') as mock_get_agent, \
             patch('automagik.api.controllers.agent_controller.AgentFactory') as mock_factory_class, \
             patch('automagik.api.controllers.agent_controller.run_in_threadpool') as mock_threadpool, \
             patch('automagik.api.controllers.agent_controller.MessageHistory') as mock_history_class, \
             patch('automagik.api.controllers.agent_controller.get_or_create_user') as mock_get_user:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message.return_value = mock_response
            
            mock_factory = Mock()
            mock_factory.get_agent.return_value = mock_agent
            mock_factory_class.return_value = mock_factory
            
            mock_db_agent = Mock()
            mock_db_agent.agent_type = "test_type"
            mock_get_agent.return_value = mock_db_agent
            
            mock_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            mock_history = Mock()
            mock_history.session_id = "test-session-id"
            mock_history_class.return_value = mock_history
            
            # Mock user creation
            mock_get_user.return_value = test_user_id
            
            # Create request  
            request = AgentRunRequest(
                message_content="Test message",
                user_id=test_user_id
            )
            
            # Call the function
            result = await handle_agent_run("test-agent", request)
            
            # Assertions
            assert "message" in result
            assert "success" in result
            assert "usage" in result
            assert result["success"] is True
            assert result["message"] == "Test response"
            assert result["usage"] == sample_usage_data
    
    @pytest.mark.asyncio
    async def test_agent_response_without_usage_field(self):
        """Test that agent response works without usage field."""
        # Create test user ID first
        test_user_id = str(uuid.uuid4())
        
        # Create mock agent response without usage
        mock_response = AgentResponse(
            text="Test response",
            success=True,
            usage=None
        )
        
        # Mock the agent execution to return our mock response
        with patch('automagik.api.controllers.agent_controller.get_agent_by_name') as mock_get_agent, \
             patch('automagik.api.controllers.agent_controller.AgentFactory') as mock_factory_class, \
             patch('automagik.api.controllers.agent_controller.run_in_threadpool') as mock_threadpool, \
             patch('automagik.api.controllers.agent_controller.MessageHistory') as mock_history_class, \
             patch('automagik.api.controllers.agent_controller.get_or_create_user') as mock_get_user:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message.return_value = mock_response
            
            mock_factory = Mock()
            mock_factory.get_agent.return_value = mock_agent
            mock_factory_class.return_value = mock_factory
            
            mock_db_agent = Mock()
            mock_db_agent.agent_type = "test_type"
            mock_get_agent.return_value = mock_db_agent
            
            mock_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            mock_history = Mock()
            mock_history.session_id = "test-session-id"
            mock_history_class.return_value = mock_history
            
            # Mock user creation
            mock_get_user.return_value = test_user_id
            
            # Create request  
            request = AgentRunRequest(
                message_content="Test message",
                user_id=test_user_id
            )
            
            # Call the function
            result = await handle_agent_run("test-agent", request)
            
            # Assertions
            assert "message" in result
            assert "success" in result
            assert result["success"] is True
            assert result["message"] == "Test response"
            assert "usage" not in result  # Should not include usage when None
    
    @pytest.mark.asyncio
    async def test_agent_response_with_dict_response(self, sample_usage_data):
        """Test that agent response handles dict responses with usage."""
        # Create test user ID first
        test_user_id = str(uuid.uuid4())
        
        # Create mock dict response with usage
        mock_response = {
            "text": "Test response",
            "success": True,
            "tool_calls": [],
            "tool_outputs": [],
            "usage": sample_usage_data
        }
        
        # Mock the agent execution to return our mock response
        with patch('automagik.api.controllers.agent_controller.get_agent_by_name') as mock_get_agent, \
             patch('automagik.api.controllers.agent_controller.AgentFactory') as mock_factory_class, \
             patch('automagik.api.controllers.agent_controller.run_in_threadpool') as mock_threadpool, \
             patch('automagik.api.controllers.agent_controller.MessageHistory') as mock_history_class, \
             patch('automagik.api.controllers.agent_controller.get_or_create_user') as mock_get_user:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message.return_value = mock_response
            
            mock_factory = Mock()
            mock_factory.get_agent.return_value = mock_agent
            mock_factory_class.return_value = mock_factory
            
            mock_db_agent = Mock()
            mock_db_agent.agent_type = "test_type"
            mock_get_agent.return_value = mock_db_agent
            
            mock_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            mock_history = Mock()
            mock_history.session_id = "test-session-id"
            mock_history_class.return_value = mock_history
            
            # Mock user creation
            mock_get_user.return_value = test_user_id
            
            # Create request  
            request = AgentRunRequest(
                message_content="Test message",
                user_id=test_user_id
            )
            
            # Call the function
            result = await handle_agent_run("test-agent", request)
            
            # Assertions
            assert "message" in result
            assert "success" in result
            assert "usage" in result
            assert result["success"] is True
            assert result["message"] == "Test response"
            assert result["usage"] == sample_usage_data
    
    @pytest.mark.asyncio
    async def test_agent_response_with_string_response(self):
        """Test that agent response handles simple string responses."""
        # Create test user ID first
        test_user_id = str(uuid.uuid4())
        
        # Mock the agent execution to return a simple string
        with patch('automagik.api.controllers.agent_controller.get_agent_by_name') as mock_get_agent, \
             patch('automagik.api.controllers.agent_controller.AgentFactory') as mock_factory_class, \
             patch('automagik.api.controllers.agent_controller.run_in_threadpool') as mock_threadpool, \
             patch('automagik.api.controllers.agent_controller.MessageHistory') as mock_history_class:
            
            # Setup mocks
            mock_agent = Mock()
            mock_agent.process_message.return_value = "Simple string response"
            
            mock_factory = Mock()
            mock_factory.get_agent.return_value = mock_agent
            mock_factory_class.return_value = mock_factory
            
            mock_db_agent = Mock()
            mock_db_agent.agent_type = "test_type"
            mock_get_agent.return_value = mock_db_agent
            
            mock_threadpool.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
            
            mock_history = Mock()
            mock_history.session_id = "test-session-id"
            mock_history_class.return_value = mock_history
            
            # Mock user creation
            mock_get_user.return_value = test_user_id
            
            # Create request  
            request = AgentRunRequest(
                message_content="Test message",
                user_id=test_user_id
            )
            
            # Call the function
            result = await handle_agent_run("test-agent", request)
            
            # Assertions
            assert "message" in result
            assert "success" in result
            assert result["success"] is True
            assert result["message"] == "Simple string response"
            assert "usage" not in result  # String responses don't have usage