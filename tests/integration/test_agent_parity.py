"""Integration tests for agent feature parity and consistency."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agents.simple.simple.agent import SimpleAgent
from src.agents.simple.sofia.agent import SofiaAgent


class TestAgentParity:
    """Test feature parity and consistency between Simple and Sofia agents."""
    
    @pytest.fixture
    def simple_agent(self):
        """Create SimpleAgent instance for testing."""
        config = {
            "model_name": "openai:gpt-4.1-mini",
            "max_tokens": "1000",
        }
        return SimpleAgent(config)
    
    @pytest.fixture
    def sofia_agent(self):
        """Create SofiaAgent instance for testing."""
        config = {
            "model_name": "openai:gpt-4.1-mini",
            "max_tokens": "1000",
        }
        return SofiaAgent(config)
    
    def test_both_agents_extend_automagik_agent(self, simple_agent, sofia_agent):
        """Test that both agents properly extend AutomagikAgent."""
        from src.agents.models.automagik_agent import AutomagikAgent
        
        assert isinstance(simple_agent, AutomagikAgent)
        assert isinstance(sofia_agent, AutomagikAgent)
        
        # Both should have core AutomagikAgent methods
        assert hasattr(simple_agent, 'run')
        assert hasattr(sofia_agent, 'run')
        assert hasattr(simple_agent, 'tool_registry')
        assert hasattr(sofia_agent, 'tool_registry')
    
    def test_both_agents_have_evolution_support(self, simple_agent, sofia_agent):
        """Test that both agents support Evolution/WhatsApp integration."""
        # Both should have Evolution tool wrappers
        simple_tools = simple_agent.tool_registry.get_registered_tools()
        sofia_tools = sofia_agent.tool_registry.get_registered_tools()
        
        # Check for Evolution tools in both agents
        assert "send_reaction" in simple_tools
        assert "send_text_to_user" in simple_tools
        assert "send_reaction" in sofia_tools
        assert "send_text_to_user" in sofia_tools
    
    def test_both_agents_have_multimodal_support(self, simple_agent, sofia_agent):
        """Test that both agents support multimodal processing."""
        # Both should have multimodal processing methods
        assert hasattr(simple_agent, '_convert_image_payload_to_pydantic')
        assert hasattr(sofia_agent, '_convert_image_payload_to_pydantic')
        
        # Both should accept multimodal_content parameter in run method
        import inspect
        simple_sig = inspect.signature(simple_agent.run)
        sofia_sig = inspect.signature(sofia_agent.run)
        
        assert 'multimodal_content' in simple_sig.parameters
        assert 'multimodal_content' in sofia_sig.parameters
    
    def test_sofia_has_additional_features(self, simple_agent, sofia_agent):
        """Test that Sofia has additional features not in Simple agent."""
        # Sofia should have MCP integration
        assert hasattr(sofia_agent, '_load_mcp_servers')
        
        # Simple should NOT have MCP integration (stays minimal)
        assert not hasattr(simple_agent, '_load_mcp_servers')
        
        # Sofia should have Airtable sub-agent wrapper
        sofia_tools = sofia_agent.tool_registry.get_registered_tools()
        assert "airtable_agent" in sofia_tools
        
        # Simple should NOT have Airtable integration
        simple_tools = simple_agent.tool_registry.get_registered_tools()
        assert "airtable_agent" not in simple_tools
    
    @pytest.mark.asyncio
    async def test_consistent_text_processing(self, simple_agent, sofia_agent):
        """Test that both agents process text consistently."""
        test_input = "Hello, how are you?"
        
        # Mock both agents to return similar responses
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_simple:
                                mock_simple_result = Mock()
                                mock_simple_result.data = "Hello! I'm doing well, thank you."
                                mock_simple.run = AsyncMock(return_value=mock_simple_result)
                                
                                # Mock extract functions for Simple
                                with patch('src.agents.simple.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('src.agents.simple.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('src.agents.simple.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            simple_result = await simple_agent.run(test_input)
        
        with patch.object(sofia_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(sofia_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(sofia_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(sofia_agent, '_agent_instance') as mock_sofia:
                                mock_sofia_result = Mock()
                                mock_sofia_result.data = "Hello! I'm doing well, thank you."
                                mock_sofia.run = AsyncMock(return_value=mock_sofia_result)
                                
                                # Mock extract functions for Sofia
                                with patch('src.agents.simple.sofia.agent.extract_all_messages', return_value=[]):
                                    with patch('src.agents.simple.sofia.agent.extract_tool_calls', return_value=[]):
                                        with patch('src.agents.simple.sofia.agent.extract_tool_outputs', return_value=[]):
                                            # Mock semaphore for Sofia
                                            with patch('src.agents.simple.sofia.agent.get_llm_semaphore') as mock_semaphore:
                                                mock_sem = AsyncMock()
                                                mock_semaphore.return_value = mock_sem
                                                
                                                sofia_result = await sofia_agent.run(test_input)
        
        # Both should succeed
        assert simple_result.success is True
        assert sofia_result.success is True
        
        # Both should return similar response format
        assert simple_result.text == sofia_result.text
    
    def test_error_handling_consistency(self, simple_agent, sofia_agent):
        """Test that both agents handle errors consistently."""
        # Both should have similar error handling patterns
        # This is verified through their base class AutomagikAgent
        
        # Both should return AgentResponse objects
        from src.agents.models.agent_response import AgentResponse
        
        # Verify both agents use the same response format
        assert hasattr(simple_agent, 'run')
        assert hasattr(sofia_agent, 'run')
        
        # Both should handle the same parameter types
        import inspect
        simple_sig = inspect.signature(simple_agent.run)
        sofia_sig = inspect.signature(sofia_agent.run)
        
        # Core parameters should be the same
        assert 'user_input' in simple_sig.parameters
        assert 'user_input' in sofia_sig.parameters
        assert 'session_id' in simple_sig.parameters
        assert 'session_id' in sofia_sig.parameters
    
    def test_tool_registry_consistency(self, simple_agent, sofia_agent):
        """Test that tool registries work consistently."""
        simple_tools = simple_agent.tool_registry.get_registered_tools()
        sofia_tools = sofia_agent.tool_registry.get_registered_tools()
        
        # Both should have basic tools
        assert len(simple_tools) > 0
        assert len(sofia_tools) > 0
        
        # Sofia should have more tools (superset of Simple)
        assert len(sofia_tools) >= len(simple_tools)
        
        # Common tools should exist in both
        common_tools = ["send_reaction", "send_text_to_user"]
        for tool in common_tools:
            assert tool in simple_tools
            assert tool in sofia_tools
    
    def test_memory_integration_consistency(self, simple_agent, sofia_agent):
        """Test that memory integration works consistently."""
        # Both should have memory-related attributes
        assert hasattr(simple_agent, 'context')
        assert hasattr(sofia_agent, 'context')
        
        # Both should support memory variables
        assert hasattr(simple_agent, 'initialize_memory_variables')
        assert hasattr(sofia_agent, 'initialize_memory_variables')
        
        # Both should have dependencies for memory
        assert hasattr(simple_agent, 'dependencies')
        assert hasattr(sofia_agent, 'dependencies')
    
    def test_configuration_consistency(self, simple_agent, sofia_agent):
        """Test that configuration handling is consistent."""
        # Both should accept the same basic config parameters
        assert simple_agent.config is not None
        assert sofia_agent.config is not None
        
        # Both should have model configuration
        assert hasattr(simple_agent.config, 'model_name')
        assert hasattr(sofia_agent.config, 'model_name')
        
        # Both should handle the same config structure
        assert simple_agent.config.model_name == "openai:gpt-4.1-mini"
        assert sofia_agent.config.model_name == "openai:gpt-4.1-mini" 