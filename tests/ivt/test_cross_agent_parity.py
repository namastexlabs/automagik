"""Integration Verification Tests (IVT) for Cross-Agent Feature Parity.

These tests verify that synchronized features work identically across 
Simple and Sofia agents in real-world scenarios.
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from src.agents.simple.simple.agent import SimpleAgent
from src.agents.simple.sofia.agent import SofiaAgent


class TestCrossAgentParity:
    """Integration tests verifying feature parity between agents."""
    
    @pytest.fixture
    def agent_config(self):
        """Common configuration for both agents."""
        return {
            "model_name": "openai:gpt-4.1-mini",  # Default model preference
            "max_tokens": "1000",
        }
    
    @pytest.fixture
    def simple_agent(self, agent_config):
        """Initialize Simple agent for testing."""
        return SimpleAgent(agent_config)
    
    @pytest.fixture
    def sofia_agent(self, agent_config):
        """Initialize Sofia agent for testing."""
        return SofiaAgent(agent_config)
    
    @pytest.fixture
    def sample_evolution_payload(self):
        """Sample WhatsApp Evolution payload for testing."""
        return {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test_message_id"
            },
            "message": {
                "conversation": "Hello, how are you?"
            },
            "messageTimestamp": 1640995200,
            "pushName": "Test User"
        }
    
    @pytest.fixture
    def sample_multimodal_content(self):
        """Sample multimodal content for testing."""
        return {
            "images": [
                {
                    "data": "https://example.com/test-image.jpg",
                    "mime_type": "image/jpeg"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_whatsapp_integration_parity(self, simple_agent, sofia_agent, sample_evolution_payload):
        """Test that both agents handle WhatsApp Evolution payloads identically."""
        
        test_input = "Hello there!"
        
        # Mock both agents' core methods
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Simple prompt"), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Sofia prompt"), \
             patch.object(simple_agent, '_agent_instance') as simple_mock, \
             patch.object(sofia_agent, '_agent_instance') as sofia_mock:
            
            # Configure mock responses
            simple_mock.run = AsyncMock()
            simple_mock.run.return_value.data = "Hello from Simple agent!"
            
            sofia_mock.run = AsyncMock()
            sofia_mock.run.return_value.data = "Hello from Sofia agent!"
            
            # Mock extract functions for both agents
            with patch('src.agents.simple.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_outputs', return_value=[]):
                
                # Test Simple agent
                simple_response = await simple_agent.run(
                    test_input,
                    channel_payload=sample_evolution_payload
                )
                
                # Test Sofia agent (with semaphore mock)
                with patch('src.agents.simple.sofia.agent.get_llm_semaphore') as mock_semaphore:
                    mock_sem = AsyncMock()
                    mock_semaphore.return_value = mock_sem
                    
                    sofia_response = await sofia_agent.run(
                        test_input,
                        channel_payload=sample_evolution_payload
                    )
        
        # Verify both agents succeeded
        assert simple_response.success is True
        assert sofia_response.success is True
        
        # Verify both agents processed the Evolution payload
        # (Context should be populated from Evolution data)
        assert "user_phone_number" in simple_agent.context
        assert "user_phone_number" in sofia_agent.context
        assert simple_agent.context["user_phone_number"] == sofia_agent.context["user_phone_number"]
    
    @pytest.mark.asyncio
    async def test_multimodal_processing_parity(self, simple_agent, sofia_agent, sample_multimodal_content):
        """Test that both agents handle multimodal content identically."""
        
        test_input = "What do you see in this image?"
        
        # Mock both agents' core methods
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Simple prompt"), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="Sofia prompt"), \
             patch.object(simple_agent, '_agent_instance') as simple_mock, \
             patch.object(sofia_agent, '_agent_instance') as sofia_mock:
            
            # Configure mock responses
            simple_mock.run = AsyncMock()
            simple_mock.run.return_value.data = "I can see an image with content."
            
            sofia_mock.run = AsyncMock()
            sofia_mock.run.return_value.data = "I can see an image with content."
            
            # Mock extract functions for both agents
            with patch('src.agents.simple.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_outputs', return_value=[]):
                
                # Test Simple agent
                simple_response = await simple_agent.run(
                    test_input,
                    multimodal_content=sample_multimodal_content
                )
                
                # Test Sofia agent (with semaphore mock)
                with patch('src.agents.simple.sofia.agent.get_llm_semaphore') as mock_semaphore:
                    mock_sem = AsyncMock()
                    mock_semaphore.return_value = mock_sem
                    
                    sofia_response = await sofia_agent.run(
                        test_input,
                        multimodal_content=sample_multimodal_content
                    )
        
        # Verify both agents succeeded
        assert simple_response.success is True
        assert sofia_response.success is True
        
        # Verify both agents processed multimodal content
        # Both should have called run with image processing
        simple_mock.run.assert_called_once()
        sofia_mock.run.assert_called_once()
        
        # Verify similar response structure
        assert simple_response.text == sofia_response.text
    
    def test_tool_registry_structure_parity(self, simple_agent, sofia_agent):
        """Test that both agents have expected tool registry structure."""
        
        # Get registered tools
        simple_tools = simple_agent.tool_registry.get_registered_tools()
        sofia_tools = sofia_agent.tool_registry.get_registered_tools()
        
        # Both should have basic tools
        assert len(simple_tools) > 0
        assert len(sofia_tools) > 0
        
        # Common tools that both should have
        expected_common_tools = [
            "send_reaction",
            "send_text_to_user",
            "get_current_date",
            "get_current_time"
        ]
        
        for tool_name in expected_common_tools:
            assert tool_name in simple_tools, f"Simple agent missing tool: {tool_name}"
            assert tool_name in sofia_tools, f"Sofia agent missing tool: {tool_name}"
        
        # Sofia should have more tools (superset)
        assert len(sofia_tools) >= len(simple_tools)
    
    def test_agent_configuration_consistency(self, simple_agent, sofia_agent):
        """Test that both agents handle configuration consistently."""
        
        # Both should use the same model
        assert simple_agent.config.model_name == sofia_agent.config.model_name
        assert simple_agent.config.model_name == "openai:gpt-4.1-mini"  # Default preference
        
        # Both should have dependency objects
        assert simple_agent.dependencies is not None
        assert sofia_agent.dependencies is not None
        
        # Both should have tool registries
        assert simple_agent.tool_registry is not None
        assert sofia_agent.tool_registry is not None
        
        # Both should have context
        assert simple_agent.context is not None
        assert sofia_agent.context is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_consistency(self, simple_agent, sofia_agent):
        """Test that both agents handle errors consistently."""
        
        # Mock initialization failure
        with patch.object(simple_agent, '_initialize_pydantic_agent', side_effect=Exception("Test error")):
            simple_response = await simple_agent.run("Test input")
            assert simple_response.success is False
            assert "Test error" in simple_response.error_message
        
        # Mock initialization failure for Sofia (with semaphore)
        with patch.object(sofia_agent, '_initialize_pydantic_agent', side_effect=Exception("Test error")):
            sofia_response = await sofia_agent.run("Test input")
            assert sofia_response.success is False
            assert "Test error" in sofia_response.error_message
        
        # Both should return AgentResponse objects even on failure
        assert hasattr(simple_response, 'success')
        assert hasattr(simple_response, 'error_message')
        assert hasattr(sofia_response, 'success')
        assert hasattr(sofia_response, 'error_message')
    
    def test_memory_integration_structure(self, simple_agent, sofia_agent):
        """Test that both agents have consistent memory integration."""
        
        # Both should have memory-related methods
        assert hasattr(simple_agent, 'initialize_memory_variables')
        assert hasattr(sofia_agent, 'initialize_memory_variables')
        
        assert hasattr(simple_agent, 'get_filled_system_prompt')
        assert hasattr(sofia_agent, 'get_filled_system_prompt')
        
        # Both should support the same memory template variables
        # This would be tested through actual prompt filling in integration tests
        assert callable(simple_agent.initialize_memory_variables)
        assert callable(sofia_agent.initialize_memory_variables)
    
    @pytest.mark.asyncio
    async def test_concurrent_operation_safety(self, simple_agent, sofia_agent):
        """Test that both agents can handle concurrent operations safely."""
        
        # Mock agent instances for concurrent testing
        with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(sofia_agent, '_initialize_pydantic_agent', new_callable=AsyncMock), \
             patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="prompt"), \
             patch.object(sofia_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="prompt"), \
             patch.object(simple_agent, '_agent_instance') as simple_mock, \
             patch.object(sofia_agent, '_agent_instance') as sofia_mock:
            
            simple_mock.run = AsyncMock(return_value=type('obj', (object,), {'data': 'simple result'}))
            sofia_mock.run = AsyncMock(return_value=type('obj', (object,), {'data': 'sofia result'}))
            
            # Mock extract functions
            with patch('src.agents.simple.simple.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.simple.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_all_messages', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_calls', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.extract_tool_outputs', return_value=[]), \
                 patch('src.agents.simple.sofia.agent.get_llm_semaphore') as mock_semaphore:
                
                mock_sem = AsyncMock()
                mock_semaphore.return_value = mock_sem
                
                # Run multiple concurrent operations
                tasks = []
                for i in range(5):
                    tasks.append(simple_agent.run(f"Simple test {i}"))
                    tasks.append(sofia_agent.run(f"Sofia test {i}"))
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify no exceptions and all succeeded
                for result in results:
                    assert not isinstance(result, Exception)
                    assert result.success is True 