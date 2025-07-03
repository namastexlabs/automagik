"""Integration tests for usage tracking in agent execution pipeline."""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from automagik.agents.models.ai_frameworks.pydantic_ai import PydanticAIFramework
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.ai_frameworks.base import AgentConfig
from automagik.agents.models.dependencies import BaseDependencies
from automagik.memory.message_history import MessageHistory
from automagik.agents.common.message_parser import format_message_for_db


class TestUsageTrackingIntegration:
    """Test suite for usage tracking integration across the agent pipeline."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic agent configuration for testing."""
        return AgentConfig(
            model="gpt-4",
            retries=1,
            temperature=0.0
        )
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for agent testing."""
        return Mock(spec=BaseDependencies)
    
    @pytest.fixture
    def sample_pydantic_usage(self):
        """Sample PydanticAI usage object."""
        mock_usage = Mock()
        mock_usage.requests = 1
        mock_usage.request_tokens = 100
        mock_usage.response_tokens = 200
        mock_usage.total_tokens = 300
        mock_usage.details = {"cache_creation_tokens": 25, "cache_read_tokens": 10}
        return mock_usage
    
    @pytest.fixture
    def sample_pydantic_result(self, sample_pydantic_usage):
        """Sample PydanticAI result with usage information."""
        mock_result = Mock()
        mock_result.output = "Test agent response"
        
        # Create mock message with usage
        mock_message = Mock()
        mock_message.usage = sample_pydantic_usage
        mock_message.tool_calls = None
        mock_message.tool_call_id = None
        mock_message.content = None
        
        # Mock all_messages method
        mock_result.all_messages.return_value = [mock_message]
        
        return mock_result
    
    @pytest.fixture
    def expected_usage_info(self):
        """Expected usage information structure."""
        return {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_requests": 1,
            "request_tokens": 100,
            "response_tokens": 200,
            "total_tokens": 300,
            "cache_creation_tokens": 25,
            "cache_read_tokens": 10,
            "per_message_usage": [
                {
                    "requests": 1,
                    "request_tokens": 100,
                    "response_tokens": 200,
                    "total_tokens": 300,
                    "details": {"cache_creation_tokens": 25, "cache_read_tokens": 10}
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_usage_extraction(self, basic_config, mock_dependencies, sample_pydantic_result, expected_usage_info):
        """Test that PydanticAI framework correctly extracts usage information."""
        # Create framework instance
        framework = PydanticAIFramework(basic_config)
        
        with patch.object(framework, '_agent_instance') as mock_agent:
            framework.is_initialized = True
            
            # Setup mock agent to return our sample result
            mock_agent.run.return_value = sample_pydantic_result
            
            # Mock other required methods
            framework.format_message_history = Mock(return_value=[])
            framework.extract_tool_calls = Mock(return_value=[])
            framework.extract_tool_outputs = Mock(return_value=[])
            
            # Execute the agent
            response = await framework.run(
                user_input="Test message",
                dependencies=mock_dependencies
            )
            
            # Assertions
            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.text == "Test agent response"
            assert response.usage is not None
            
            # Verify usage information structure
            usage = response.usage
            assert usage["framework"] == "pydantic_ai"
            assert usage["model"] == "gpt-4"
            assert usage["total_requests"] == 1
            assert usage["request_tokens"] == 100
            assert usage["response_tokens"] == 200
            assert usage["total_tokens"] == 300
            assert usage["cache_creation_tokens"] == 25
            assert usage["cache_read_tokens"] == 10
            assert len(usage["per_message_usage"]) == 1
    
    @pytest.mark.asyncio
    async def test_pydantic_ai_no_usage_data(self, basic_config, mock_dependencies):
        """Test PydanticAI framework when no usage data is available."""
        # Create framework instance
        framework = PydanticAIFramework(basic_config)
        
        # Create result without usage
        mock_result = Mock()
        mock_result.output = "Test response"
        mock_result.all_messages.return_value = []  # No messages with usage
        
        with patch.object(framework, '_agent_instance') as mock_agent:
            framework.is_initialized = True
            
            # Setup mock agent
            mock_agent.run.return_value = mock_result
            
            # Mock other required methods
            framework.format_message_history = Mock(return_value=[])
            framework.extract_tool_calls = Mock(return_value=[])
            framework.extract_tool_outputs = Mock(return_value=[])
            
            # Execute the agent
            response = await framework.run(
                user_input="Test message",
                dependencies=mock_dependencies
            )
            
            # Assertions
            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.usage is None  # No usage data available
    
    def test_format_message_for_db_includes_usage(self):
        """Test that format_message_for_db includes usage information."""
        sample_usage = {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_tokens": 300
        }
        
        # Call format_message_for_db with usage
        message = format_message_for_db(
            role="assistant",
            content="Test response",
            agent_id=123,
            usage=sample_usage
        )
        
        # Assertions
        assert message["role"] == "assistant"
        assert message["content"] == "Test response"
        assert message["agent_id"] == 123
        assert message["usage"] == sample_usage
    
    def test_format_message_for_db_without_usage(self):
        """Test that format_message_for_db works without usage information."""
        # Call format_message_for_db without usage
        message = format_message_for_db(
            role="user",
            content="Test message",
            agent_id=123
        )
        
        # Assertions
        assert message["role"] == "user"
        assert message["content"] == "Test message"
        assert message["agent_id"] == 123
        assert "usage" not in message
    
    @pytest.mark.integration
    def test_message_history_add_response_with_usage(self):
        """Test that MessageHistory.add_response stores usage information."""
        session_id = str(uuid.uuid4())
        sample_usage = {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_tokens": 300,
            "request_tokens": 100,
            "response_tokens": 200
        }
        
        with patch('automagik.memory.message_history.create_message') as mock_create_message:
            
            # Create MessageHistory instance in local mode to avoid DB operations
            message_history = MessageHistory(session_id, no_auto_create=True)
            message_history._local_only = True
            
            # Call add_response with usage
            message_history.add_response(
                content="Test response",
                agent_id=123,
                usage=sample_usage
            )
            
            # Since we're in local mode, check that the message was added to local storage
            assert len(message_history._local_messages) == 1
            
            # The actual database integration would be tested in a full integration test
            # with a real database connection
    
    @pytest.mark.integration
    def test_message_history_add_message_with_usage(self):
        """Test that MessageHistory.add_message handles usage information."""
        session_id = str(uuid.uuid4())
        sample_usage = {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_tokens": 300
        }
        
        # Create formatted message with usage
        formatted_message = {
            "role": "assistant",
            "content": "Test response",
            "agent_id": 123,
            "usage": sample_usage
        }
        
        with patch('automagik.memory.message_history.create_message') as mock_create_message:
            
            # Create MessageHistory instance in local mode
            message_history = MessageHistory(session_id, no_auto_create=True)
            message_history._local_only = True
            
            # Call add_message
            message_history.add_message(formatted_message)
            
            # Verify local message was added (since we're in local mode)
            assert len(message_history._local_messages) == 1
    
    def test_usage_extraction_error_handling(self, basic_config):
        """Test that usage extraction errors are handled gracefully."""
        framework = PydanticAIFramework(basic_config)
        
        # Create a result that will cause an exception in usage extraction
        mock_result = Mock()
        mock_result.all_messages.side_effect = Exception("API error")
        
        # Call extract_usage_info
        usage_info = framework.extract_usage_info(mock_result)
        
        # Should return None when there's an error
        assert usage_info is None
    
    def test_usage_extraction_with_multiple_messages(self, basic_config):
        """Test usage extraction with multiple messages containing usage data."""
        framework = PydanticAIFramework(basic_config)
        
        # Create multiple mock messages with usage
        mock_usage1 = Mock()
        mock_usage1.requests = 1
        mock_usage1.request_tokens = 50
        mock_usage1.response_tokens = 100
        mock_usage1.total_tokens = 150
        mock_usage1.details = None
        
        mock_usage2 = Mock()
        mock_usage2.requests = 1
        mock_usage2.request_tokens = 75
        mock_usage2.response_tokens = 125
        mock_usage2.total_tokens = 200
        mock_usage2.details = {"cache_read_tokens": 15}
        
        mock_message1 = Mock()
        mock_message1.usage = mock_usage1
        
        mock_message2 = Mock()
        mock_message2.usage = mock_usage2
        
        mock_result = Mock()
        mock_result.all_messages.return_value = [mock_message1, mock_message2]
        
        # Extract usage info
        usage_info = framework.extract_usage_info(mock_result)
        
        # Verify aggregated totals
        assert usage_info["total_requests"] == 2  # 1 + 1
        assert usage_info["request_tokens"] == 125  # 50 + 75
        assert usage_info["response_tokens"] == 225  # 100 + 125
        assert usage_info["total_tokens"] == 350  # 150 + 200
        assert usage_info["cache_read_tokens"] == 15  # 0 + 15
        assert len(usage_info["per_message_usage"]) == 2
    
    @pytest.mark.unit
    def test_agent_response_usage_field(self):
        """Test that AgentResponse properly handles usage field."""
        usage_data = {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_tokens": 300
        }
        
        # Create AgentResponse with usage
        response = AgentResponse(
            text="Test response",
            success=True,
            usage=usage_data
        )
        
        # Assertions
        assert response.text == "Test response"
        assert response.success is True
        assert response.usage == usage_data
        
        # Test without usage
        response_no_usage = AgentResponse(
            text="Test response",
            success=True
        )
        
        assert response_no_usage.usage is None