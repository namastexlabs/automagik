"""Unit tests for AutomagikAgent base class and related models.

This module tests the core agent models with 100% coverage target,
including success cases, error handling, and edge cases.
"""

import pytest
import uuid
import os
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict

from automagik.agents.models.automagik_agent import AutomagikAgent, AgentConfig
from automagik.agents.models.agent import MessageModel, HistoryModel, AgentBaseResponse_v2
from automagik.agents.models.response import AgentResponse
from pydantic_ai.messages import SystemPromptPart, UserPromptPart, ModelResponse, ModelRequest


class MockAgent(AutomagikAgent):
    """Mock implementation of AutomagikAgent for testing."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = "Test prompt with {{variable}}"
        self._prompt_registered = False
        
    async def run(self, input_text: str, *, multimodal_content=None, 
                 system_message=None, message_history_obj=None,
                 channel_payload=None, message_limit=None) -> AgentResponse:
        """Mock run implementation."""
        return AgentResponse(
            text="Mock response",
            tool_calls=[],
            tool_outputs=[]
        )


class TestAgentConfig:
    """Test suite for AgentConfig class."""
    
    def test_agent_config_initialization(self):
        """Test AgentConfig initialization with different inputs."""
        # Test with empty config
        config = AgentConfig()
        # Default should now come from env var or fallback to gpt-4.1-mini
        assert config.model == os.environ.get("AUTOMAGIK_DEFAULT_MODEL", "gpt-4.1-mini")
        assert config.temperature == 0.7
        assert config.retries == 1
        
        # Test with custom config
        custom_config = {
            "model": "anthropic:claude-3-5-sonnet",
            "temperature": "0.5",
            "retries": "3",
            "custom_field": "value"
        }
        config = AgentConfig(custom_config)
        assert config.model == "anthropic:claude-3-5-sonnet"
        assert config.temperature == 0.5
        assert config.retries == 3
        assert config.get("custom_field") == "value"
    
    def test_agent_config_get_method(self):
        """Test AgentConfig get method."""
        config = AgentConfig({"key1": "value1"})
        assert config.get("key1") == "value1"
        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"
    
    def test_agent_config_update(self):
        """Test AgentConfig update method."""
        config = AgentConfig({"key1": "value1"})
        config.update({"key2": "value2", "key1": "updated"})
        assert config.get("key1") == "updated"
        assert config.get("key2") == "value2"
        
        # Test update with None
        config.update(None)  # Should not raise error
    
    def test_agent_config_getattr(self):
        """Test AgentConfig __getattr__ method."""
        config = AgentConfig({"custom_attr": "custom_value"})
        assert config.custom_attr == "custom_value"
        assert config.nonexistent_attr is None


class TestMessageModels:
    """Test suite for message-related models."""
    
    def test_message_model(self):
        """Test MessageModel creation and validation."""
        msg = MessageModel(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_history_model_from_message_history(self):
        """Test HistoryModel.from_message_history conversion."""
        # Create mock message history
        history = MagicMock()
        
        # Create mock message parts
        system_part = MagicMock(spec=SystemPromptPart)
        system_part.system_prompt = "System prompt"
        
        user_part = MagicMock(spec=UserPromptPart)
        user_part.prompt = "User message"
        
        # Model response with content
        model_response = MagicMock(spec=ModelResponse)
        content_part = MagicMock()
        content_part.content = "Assistant response"
        model_response.parts = [content_part]
        
        # Model request with parts
        model_request = MagicMock(spec=ModelRequest)
        request_system = MagicMock(spec=SystemPromptPart)
        request_system.content = "Request system"
        request_user = MagicMock(spec=UserPromptPart)
        request_user.content = "Request user"
        model_request.parts = [request_system, request_user]
        
        # Unknown message type
        unknown_msg = MagicMock()
        unknown_msg.content = "Unknown content"
        unknown_msg.role = "custom"
        
        history._messages = [
            system_part,
            user_part,
            model_response,
            model_request,
            unknown_msg
        ]
        
        # Convert to HistoryModel
        history_model = HistoryModel.from_message_history(history)
        
        # Verify conversions
        assert len(history_model.messages) == 6  # 5 original + 1 from model request split
        assert history_model.messages[0].role == "system"
        assert history_model.messages[0].content == "System prompt"
        assert history_model.messages[1].role == "user"
        assert history_model.messages[1].content == "User message"
        assert history_model.messages[2].role == "assistant"
        assert history_model.messages[2].content == "Assistant response"
        assert history_model.messages[3].role == "system"
        assert history_model.messages[3].content == "Request system"
        assert history_model.messages[4].role == "user"
        assert history_model.messages[4].content == "Request user"
        assert history_model.messages[5].role == "custom"
        assert history_model.messages[5].content == "Unknown content"
    
    def test_agent_base_response_v2_from_agent_response(self):
        """Test AgentBaseResponse_v2.from_agent_response method."""
        # Create mock history
        history = MagicMock()
        history.session_id = "test-session-id"
        history.to_dict.return_value = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
        }
        
        # Test successful creation
        response = AgentBaseResponse_v2.from_agent_response(
            message="Test response",
            history=history,
            error=None,
            tool_calls=[{"tool": "test"}],
            tool_outputs=[{"output": "result"}],
            session_id="custom-session-id"
        )
        
        assert response.message == "Test response"
        assert response.session_id == "custom-session-id"
        assert response.error is None
        assert len(response.history["messages"]) == 2
        
        # Test with session_id from history
        response = AgentBaseResponse_v2.from_agent_response(
            message="Test response",
            history=history
        )
        assert response.session_id == "test-session-id"
    
    def test_agent_base_response_v2_error_handling(self):
        """Test AgentBaseResponse_v2 error handling."""
        # Test with invalid history structure
        history = MagicMock()
        history.session_id = "test-session"
        history.to_dict.return_value = "invalid"  # Not a dict
        
        response = AgentBaseResponse_v2.from_agent_response(
            message="Test",
            history=history
        )
        assert response.history == {"messages": []}
        
        # Test with messages that aren't dicts
        history.to_dict.return_value = {
            "messages": ["not a dict", {"role": "user", "content": "valid"}, None]
        }
        
        with patch('automagik.agents.models.agent.logging') as mock_logging:
            response = AgentBaseResponse_v2.from_agent_response(
                message="Test",
                history=history
            )
            assert len(response.history["messages"]) == 1  # Only valid message
            assert response.history["messages"][0]["content"] == "valid"
            mock_logging.warning.assert_called()
        
        # Test with history that raises exception
        history.to_dict.side_effect = Exception("Serialization error")
        
        with patch('automagik.agents.models.agent.logging') as mock_logging:
            response = AgentBaseResponse_v2.from_agent_response(
                message="Test",
                history=history
            )
            assert response.history == {"messages": []}
            mock_logging.error.assert_called_with("Error serializing history: Serialization error")


class TestAutomagikAgent:
    """Test suite for AutomagikAgent base class."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Fixture for mocking agent dependencies."""
        with patch('automagik.agents.models.automagik_agent.validate_agent_id') as mock_validate, \
             patch('automagik.agents.models.automagik_agent.ToolRegistry') as mock_registry, \
             patch('automagik.db.get_agent_by_name') as mock_get_agent, \
             patch('automagik.db.register_agent') as mock_register, \
             patch('automagik.db.list_agents') as mock_list_agents:
            
            mock_validate.return_value = 123
            mock_registry.return_value = MagicMock()
            mock_get_agent.return_value = None  # Agent doesn't exist
            mock_register.return_value = 456
            mock_list_agents.return_value = []  # No existing agents
            
            yield {
                'validate_agent_id': mock_validate,
                'tool_registry': mock_registry,
                'get_agent_by_name': mock_get_agent,
                'register_agent': mock_register,
                'list_agents': mock_list_agents
            }
    
    def test_agent_initialization_with_dict_config(self, mock_dependencies):
        """Test agent initialization with dictionary config."""
        with patch('automagik.agents.models.automagik_agent.settings') as mock_settings:
            mock_settings.GRAPHITI_ENABLED = False
            mock_settings.NEO4J_URI = None
            
            config = {"name": "test_agent", "agent_id": "123"}
            agent = MockAgent(config)
            
            assert isinstance(agent.config, AgentConfig)
            assert agent.name == "test_agent"
            assert agent.db_id == 123
            assert agent.context == {"agent_id": 123}
            assert agent.tool_registry is not None
            assert agent.current_prompt_template is None
            assert agent.graphiti_agent_id is None  # No Graphiti config
    
    def test_agent_initialization_with_agent_config(self, mock_dependencies):
        """Test agent initialization with AgentConfig object."""
        config = AgentConfig({"name": "test_agent"})
        agent = MockAgent(config)
        
        assert agent.config == config
        assert agent.name == "test_agent"
    
    def test_agent_registration_when_no_id_provided(self, mock_dependencies):
        """Test agent auto-registration when no ID is provided."""
        # Mock validate_agent_id to return None for no ID
        mock_dependencies['validate_agent_id'].return_value = None
        
        config = {"name": "new_agent"}
        agent = MockAgent(config)
        
        # Should attempt to register
        mock_dependencies['get_agent_by_name'].assert_called_with("new_agent")
        mock_dependencies['register_agent'].assert_called()
        assert agent.db_id == 456
    
    def test_agent_uses_existing_id_when_found(self, mock_dependencies):
        """Test agent uses existing ID when found in database."""
        # Mock validate_agent_id to return None for no ID
        mock_dependencies['validate_agent_id'].return_value = None
        
        # Mock existing agent
        existing_agent = MagicMock()
        existing_agent.id = 789
        mock_dependencies['get_agent_by_name'].return_value = existing_agent
        
        config = {"name": "existing_agent"}
        agent = MockAgent(config)
        
        assert agent.db_id == 789
        mock_dependencies['register_agent'].assert_not_called()
    
    def test_agent_handles_registration_error(self, mock_dependencies):
        """Test agent handles registration errors gracefully."""
        # Mock validate_agent_id to return None for no ID
        mock_dependencies['validate_agent_id'].return_value = None
        mock_dependencies['register_agent'].side_effect = Exception("DB error")
        
        with patch('automagik.agents.models.automagik_agent.logger') as mock_logger:
            config = {"name": "error_agent"}
            agent = MockAgent(config)
            
            # Should log error but not crash
            mock_logger.error.assert_called()
            assert agent.db_id is None  # No ID assigned on error
    
    @pytest.mark.asyncio
    async def test_initialize_prompts(self, mock_dependencies):
        """Test prompt initialization."""
        agent = MockAgent({"name": "test", "agent_id": "123"})
        
        with patch.object(agent, '_check_and_register_prompt', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            
            result = await agent.initialize_prompts()
            assert result is True
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_prompts_no_code_prompt(self, mock_dependencies):
        """Test prompt initialization when no code prompt is defined."""
        agent = MockAgent({"name": "test", "agent_id": "123"})
        agent._code_prompt_text = None
        
        with patch('automagik.agents.models.automagik_agent.logger') as mock_logger:
            result = await agent.initialize_prompts()
            assert result is True
            mock_logger.info.assert_called_with(
                "No _code_prompt_text found for MockAgent, skipping prompt registration"
            )
    
    @pytest.mark.asyncio
    async def test_load_active_prompt_template(self, mock_dependencies):
        """Test loading active prompt template."""
        agent = MockAgent({"name": "test", "agent_id": "123"})
        
        # Mock prompt
        mock_prompt = MagicMock()
        mock_prompt.id = 1
        mock_prompt.prompt_text = "Test prompt with {{variable}}"
        
        with patch('automagik.db.repository.prompt.get_active_prompt') as mock_get, \
             patch('automagik.agents.models.automagik_agent.PromptBuilder.extract_template_variables') as mock_extract:
            
            mock_get.return_value = mock_prompt
            mock_extract.return_value = ["variable"]
            
            result = await agent.load_active_prompt_template()
            
            assert result is True
            assert agent.current_prompt_template == "Test prompt with {{variable}}"
            assert agent.template_vars == ["variable"]
    
    @pytest.mark.asyncio
    async def test_load_active_prompt_template_fallback_to_default(self, mock_dependencies):
        """Test loading prompt falls back to default status."""
        agent = MockAgent({"name": "test", "agent_id": "123"})
        
        mock_prompt = MagicMock()
        mock_prompt.prompt_text = "Default prompt"
        
        with patch('automagik.db.repository.prompt.get_active_prompt') as mock_get, \
             patch('automagik.agents.models.automagik_agent.PromptBuilder.extract_template_variables') as mock_extract:
            
            # First call returns None, second returns default
            mock_get.side_effect = [None, mock_prompt]
            mock_extract.return_value = []
            
            result = await agent.load_active_prompt_template("custom_status")
            
            assert result is True
            assert mock_get.call_count == 2
            mock_get.assert_any_call(123, "custom_status")
            mock_get.assert_any_call(123, "default")
    
    def test_register_tool(self, mock_dependencies):
        """Test tool registration."""
        agent = MockAgent({"name": "test"})
        
        # Mock tool function
        def mock_tool():
            pass
        mock_tool.__name__ = "mock_tool"
        
        agent.register_tool(mock_tool)
        agent.tool_registry.register_tool.assert_called_with(mock_tool)
    
    def test_update_context(self, mock_dependencies):
        """Test context update."""
        agent = MockAgent({"name": "test"})
        
        agent.update_context({"new_key": "new_value"})
        assert agent.context["new_key"] == "new_value"
        agent.tool_registry.update_context.assert_called_with(agent.context)
    
    def test_update_config(self, mock_dependencies):
        """Test config update."""
        agent = MockAgent({"name": "test"})
        
        agent.update_config({"temperature": "0.9"})
        assert agent.config.get("temperature") == "0.9"
        # Note: AgentConfig stores temperature as an attribute initialized at creation
        # The update method only updates the config dict, not the attributes
        assert agent.config.config["temperature"] == "0.9"
    
    @pytest.mark.asyncio
    async def test_process_message(self, mock_dependencies):
        """Test message processing."""
        agent = MockAgent({"name": "test", "agent_id": "123"})
        
        # Mock dependencies
        agent.dependencies = MagicMock()
        agent.dependencies.set_agent_id = MagicMock()
        agent.dependencies.user_id = None
        
        # Mock message history
        message_history = MagicMock()
        
        with patch('automagik.agents.common.message_parser.parse_user_message') as mock_parse, \
             patch('automagik.agents.common.session_manager.create_context') as mock_context, \
             patch('automagik.agents.common.session_manager.validate_user_id') as mock_validate_user, \
             patch('automagik.agents.common.session_manager.extract_multimodal_content') as mock_extract, \
             patch('automagik.agents.common.message_parser.format_message_for_db') as mock_format, \
             patch.object(agent, 'initialize_graphiti', new_callable=AsyncMock):
            
            mock_parse.return_value = ("Hello", {})
            mock_context.return_value = {"session_id": "test-session"}
            mock_validate_user.return_value = uuid.uuid4()
            mock_extract.return_value = None
            mock_format.side_effect = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Mock response"}
            ]
            
            response = await agent.process_message(
                "Hello",
                session_id="test-session",
                message_history=message_history
            )
            
            assert response.text == "Mock response"
            assert message_history.add_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_dependencies):
        """Test agent cleanup."""
        agent = MockAgent({"name": "test"})
        agent.dependencies = MagicMock()
        agent.dependencies.http_client = MagicMock()
        
        with patch('automagik.agents.models.automagik_agent.close_http_client', new_callable=AsyncMock) as mock_close:
            await agent.cleanup()
            mock_close.assert_called_with(agent.dependencies.http_client)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_dependencies):
        """Test agent as async context manager."""
        agent = MockAgent({"name": "test"})
        
        with patch.object(agent, 'cleanup', new_callable=AsyncMock) as mock_cleanup:
            async with agent as a:
                assert a == agent
            
            mock_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_graphiti_success(self, mock_dependencies):
        """Test successful Graphiti initialization."""
        agent = MockAgent({"name": "test"})
        agent.graphiti_agent_id = "test-agent-id"
        
        mock_client = MagicMock()
        
        with patch('automagik.agents.models.automagik_agent.get_graphiti_client') as mock_get_sync, \
             patch('automagik.agents.models.automagik_agent.get_graphiti_client_async', new_callable=AsyncMock) as mock_get_async:
            
            mock_get_sync.return_value = None
            mock_get_async.return_value = mock_client
            
            result = await agent.initialize_graphiti()
            
            assert result is True
            assert agent.graphiti_client == mock_client
    
    @pytest.mark.asyncio
    async def test_initialize_graphiti_already_exists(self, mock_dependencies):
        """Test Graphiti initialization when client already exists."""
        agent = MockAgent({"name": "test"})
        agent.graphiti_agent_id = "test-agent-id"
        agent.graphiti_client = MagicMock()  # Already set
        
        result = await agent.initialize_graphiti()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_initialize_graphiti_no_agent_id(self, mock_dependencies):
        """Test Graphiti initialization with no agent ID."""
        agent = MockAgent({"name": "test"})
        agent.graphiti_agent_id = None
        
        result = await agent.initialize_graphiti()
        assert result is False
        assert agent.graphiti_client is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])