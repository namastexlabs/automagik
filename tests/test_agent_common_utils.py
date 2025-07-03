"""Tests for common agent utilities.

This module tests the common utilities in src/agents/common.
"""

import pytest
import logging

from automagik.agents.common import (
    format_message_for_db,
    parse_user_message,
    create_context,
    validate_agent_id,
    validate_user_id,
    parse_model_settings,
    create_usage_limits,
    PromptBuilder,
    ToolRegistry
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestMessageParser:
    """Tests for message parser utilities."""
    
    def test_parse_user_message(self):
        """Test parse_user_message function."""
        # Test with string
        content, metadata = parse_user_message("Hello world")
        assert content == "Hello world"
        assert metadata == {}
        
        # Test with dictionary
        content, metadata = parse_user_message({
            "content": "Hello world",
            "metadata": "test",
            "user_id": 123
        })
        assert content == "Hello world"
        assert metadata == {"metadata": "test", "user_id": 123}
    
    def test_format_message_for_db(self):
        """Test format_message_for_db function."""
        # Basic message
        message = format_message_for_db("user", "Hello")
        assert message["role"] == "user"
        assert message["content"] == "Hello"
        
        # Message with tool calls
        tool_calls = [{"tool_name": "test", "args": {}}]
        message = format_message_for_db("assistant", "Response", tool_calls=tool_calls)
        assert message["role"] == "assistant"
        assert message["content"] == "Response"
        assert message["tool_calls"] == tool_calls
        
        # Full message
        tool_outputs = [{"tool_name": "test", "content": "result"}]
        message = format_message_for_db(
            "assistant", 
            "Response", 
            tool_calls=tool_calls,
            tool_outputs=tool_outputs,
            system_prompt="System prompt"
        )
        assert message["tool_outputs"] == tool_outputs
        assert message["system_prompt"] == "System prompt"

class TestSessionManager:
    """Tests for session manager utilities."""
    
    def test_validate_agent_id(self):
        """Test validate_agent_id function."""
        # Test with None
        assert validate_agent_id(None) is None
        
        # Test with int
        assert validate_agent_id(123) == 123
        
        # Test with string digit
        assert validate_agent_id("123") == 123
        
        # Test with string
        assert validate_agent_id("test") == "test"
    
    def test_validate_user_id(self):
        """Test validate_user_id function."""
        # Test with None
        assert validate_user_id(None) is None
        
        # Test with int
        assert validate_user_id(123) == 123
        
        # Test with string digit
        assert validate_user_id("123") == 123
        
        # Test with string (should convert to int or None)
        assert validate_user_id("test") is None
    
    def test_create_context(self):
        """Test create_context function."""
        # Basic context
        context = create_context(agent_id=123, user_id=456)
        assert context["agent_id"] == 123
        assert context["user_id"] == 456
        assert "session_id" in context
        assert "run_id" in context
        
        # Context with additional data
        context = create_context(
            agent_id=123, 
            user_id=456,
            session_id="test-session",
            additional_context={"test": "value"}
        )
        assert context["session_id"] == "test-session"
        assert context["test"] == "value"

class TestDependenciesHelper:
    """Tests for dependencies helper utilities."""
    
    def test_parse_model_settings(self):
        """Test parse_model_settings function."""
        # Test empty config
        settings = parse_model_settings({})
        assert "temperature" in settings
        assert "max_tokens" in settings
        
        # Test with model_settings prefix
        settings = parse_model_settings({
            "model_settings.temperature": "0.5",
            "model_settings.max_tokens": "1000"
        })
        assert settings["temperature"] == "0.5"
        assert settings["max_tokens"] == "1000"
        
        # Test with mixed settings
        settings = parse_model_settings({
            "model_settings.temperature": "0.5",
            "other_setting": "value"
        })
        assert settings["temperature"] == "0.5"
        assert "other_setting" not in settings
    
    def test_create_usage_limits(self):
        """Test create_usage_limits function."""
        # Test empty config
        limits = create_usage_limits({})
        assert limits is None
        
        # Test with limits
        limits = create_usage_limits({
            "response_tokens_limit": "1000",
            "request_limit": "5",
            "total_tokens_limit": "10000"
        })
        assert limits is not None
        assert limits.response_tokens_limit == 1000
        assert limits.request_limit == 5
        assert limits.total_tokens_limit == 10000

class TestPromptBuilder:
    """Tests for PromptBuilder."""
    
    def test_extract_template_variables(self):
        """Test extract_template_variables method."""
        template = "Hello {{name}}, welcome to {{service}}"
        variables = PromptBuilder.extract_template_variables(template)
        assert "name" in variables
        assert "service" in variables
        assert len(variables) == 2
        
        # Test with duplicate variables
        template = "Hello {{name}}, welcome to {{service}}. Your name is {{name}}."
        variables = PromptBuilder.extract_template_variables(template)
        assert len(variables) == 2
        
        # Test with no variables
        template = "Hello, welcome to the service."
        variables = PromptBuilder.extract_template_variables(template)
        assert len(variables) == 0
    
    def test_create_base_system_prompt(self):
        """Test create_base_system_prompt method."""
        template = "Hello {{name}}"
        prompt = PromptBuilder.create_base_system_prompt(template)
        assert prompt == template
    
    @pytest.mark.asyncio
    async def test_get_filled_system_prompt(self):
        """Test get_filled_system_prompt method."""
        template = "Hello {{name}}, welcome to {{service}}"
        memory_vars = {"name": "John", "service": "Test Service"}
        
        filled_prompt = await PromptBuilder.get_filled_system_prompt(
            prompt_template=template,
            memory_vars=memory_vars
        )
        
        assert filled_prompt == "Hello John, welcome to Test Service"
        
        # Test with missing variables
        memory_vars = {"name": "John"}
        filled_prompt = await PromptBuilder.get_filled_system_prompt(
            prompt_template=template,
            memory_vars=memory_vars
        )
        
        assert "Hello John, welcome to" in filled_prompt
        assert "[No data for service]" in filled_prompt

class TestToolRegistry:
    """Tests for ToolRegistry."""
    
    def test_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        assert registry._registered_tools == {}
    
    def test_register_tool(self):
        """Test register_tool method."""
        registry = ToolRegistry()
        
        def test_tool():
            return "test"
            
        registry.register_tool(test_tool)
        assert "test_tool" in registry._registered_tools
        assert registry._registered_tools["test_tool"] == test_tool

if __name__ == "__main__":
    """Run the tests."""
    pytest.main(["-xvs", __file__]) 