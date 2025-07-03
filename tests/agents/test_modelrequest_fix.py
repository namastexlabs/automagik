"""Test the ModelRequest fix for agent framework refactor."""
import pytest
from unittest.mock import patch
from automagik.agents.models.ai_frameworks.pydantic_ai import PydanticAIFramework
from automagik.agents.models.ai_frameworks.base import AgentConfig
from pydantic_ai.messages import ModelRequest, ModelResponse, SystemPromptPart, UserPromptPart, TextPart


class TestModelRequestFix:
    """Test the fix for ModelRequest object handling in message history."""
    
    @pytest.fixture
    def agent_config(self):
        """Basic agent configuration."""
        return AgentConfig(
            model="gemini-1.5-flash",
            retries=1,
            temperature=0.1
        )
    
    @pytest.fixture
    def framework(self, agent_config):
        """PydanticAI framework instance."""
        return PydanticAIFramework(agent_config)
    
    def test_format_message_history_with_pydantic_messages(self, framework):
        """Test that format_message_history handles PydanticAI ModelMessage objects."""
        # Create PydanticAI ModelMessage objects (like what MessageHistory returns)
        messages = [
            ModelRequest(parts=[SystemPromptPart(content="You are a helpful assistant")]),
            ModelRequest(parts=[UserPromptPart(content="Hello")]),
            ModelResponse(parts=[TextPart(content="Hi there!")])
        ]
        
        # This should not raise an error anymore
        formatted = framework.format_message_history(messages)
        
        # Should return the same messages since they're already in PydanticAI format
        assert len(formatted) == 3
        assert all(hasattr(msg, 'parts') for msg in formatted)
        assert formatted == messages
    
    def test_format_message_history_with_dict_messages(self, framework):
        """Test that format_message_history still handles dictionary messages."""
        # Create dictionary messages (legacy format)
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        formatted = framework.format_message_history(messages)
        
        # Should convert to PydanticAI format
        assert len(formatted) == 3
        assert all(hasattr(msg, 'parts') for msg in formatted)
        
        # Check specific message types
        assert isinstance(formatted[0], ModelRequest)
        assert isinstance(formatted[0].parts[0], SystemPromptPart)
        assert formatted[0].parts[0].content == "You are a helpful assistant"
        
        assert isinstance(formatted[1], ModelRequest)
        assert isinstance(formatted[1].parts[0], UserPromptPart)
        assert formatted[1].parts[0].content == "Hello"
        
        assert isinstance(formatted[2], ModelResponse)
        assert isinstance(formatted[2].parts[0], TextPart)
        assert formatted[2].parts[0].content == "Hi there!"
    
    def test_format_message_history_mixed_messages(self, framework):
        """Test that format_message_history handles mixed message types."""
        # Mix of PydanticAI messages and dictionary messages
        messages = [
            ModelRequest(parts=[SystemPromptPart(content="You are a helpful assistant")]),
            {"role": "user", "content": "Hello"},
            ModelResponse(parts=[TextPart(content="Hi there!")]),
            {"role": "user", "content": "How are you?"}
        ]
        
        formatted = framework.format_message_history(messages)
        
        # Should handle both types correctly
        assert len(formatted) == 4
        assert all(hasattr(msg, 'parts') for msg in formatted)
        
        # First and third should be unchanged (already PydanticAI)
        assert formatted[0] == messages[0]
        assert formatted[2] == messages[2]
        
        # Second and fourth should be converted
        assert isinstance(formatted[1], ModelRequest)
        assert isinstance(formatted[1].parts[0], UserPromptPart)
        assert formatted[1].parts[0].content == "Hello"
        
        assert isinstance(formatted[3], ModelRequest)
        assert isinstance(formatted[3].parts[0], UserPromptPart)
        assert formatted[3].parts[0].content == "How are you?"
    
    def test_format_message_history_with_unknown_types(self, framework):
        """Test that format_message_history handles unknown message types gracefully."""
        # Include some unknown message types
        messages = [
            {"role": "user", "content": "Hello"},
            "invalid_string_message",
            123,  # Invalid number
            ModelRequest(parts=[UserPromptPart(content="Valid message")])
        ]
        
        # Should not raise an error
        formatted = framework.format_message_history(messages)
        
        # Should only include valid messages
        assert len(formatted) == 2
        assert isinstance(formatted[0], ModelRequest)
        assert isinstance(formatted[0].parts[0], UserPromptPart)
        assert formatted[0].parts[0].content == "Hello"
        
        assert formatted[1] == messages[3]  # The valid PydanticAI message
    
    def test_format_message_history_empty_list(self, framework):
        """Test that format_message_history handles empty message list."""
        formatted = framework.format_message_history([])
        assert formatted == []
    
    def test_format_message_history_error_handling(self, framework):
        """Test that format_message_history handles errors gracefully."""
        # Patch the SystemPromptPart inside the method to raise an error
        with patch('pydantic_ai.messages.SystemPromptPart', side_effect=Exception("Test error")):
            messages = [{"role": "system", "content": "Test"}]
            formatted = framework.format_message_history(messages)
            # Should return empty list on error
            assert formatted == []


@pytest.mark.asyncio
class TestSofiaAgentModelRequestFix:
    """Integration test with Sofia agent to verify the fix works end-to-end."""
    
    @pytest.fixture
    def sofia_config(self):
        """Configuration for Sofia agent."""
        return {
            "model_name": "gemini-1.5-flash",
            "model_provider": "google",
            "temperature": "0.1"
        }
    
    async def test_sofia_agent_with_memory_history(self, sofia_config):
        """Test that Sofia agent can handle message history from memory system."""
        from automagik.agents.pydanticai.sofia.agent import SofiaAgent
        from automagik.memory.message_history import MessageHistory
        
        agent = SofiaAgent(sofia_config)
        
        # Initialize the agent framework
        from automagik.agents.models.dependencies import AutomagikAgentsDependencies
        success = await agent.initialize_framework(AutomagikAgentsDependencies)
        assert success, "Framework initialization should succeed"
        assert agent.ai_framework is not None, "AI framework should be initialized"
        
        # Create a message history with PydanticAI messages
        history = MessageHistory("test-session", no_auto_create=True)
        history.add_system_prompt("You are Sofia, a helpful assistant.")
        history.add("Hello Sofia!")
        history.add_response("Hello! How can I help you today?")
        
        # Get the PydanticAI formatted messages
        messages = history.all_messages()
        
        # This should not raise the "'ModelRequest' object has no attribute 'get'" error
        try:
            formatted = agent.ai_framework.format_message_history(messages)
            assert len(formatted) >= 1  # At least the system prompt
            # If we get here, the fix worked
            assert True
        except AttributeError as e:
            if "'ModelRequest' object has no attribute 'get'" in str(e):
                pytest.fail("The ModelRequest fix did not work - still getting attribute error")
            else:
                # Some other AttributeError, re-raise
                raise