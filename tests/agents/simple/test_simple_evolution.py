"""Test Simple agent Evolution support functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from automagik.agents.pydanticai.simple.agent import SimpleAgent
from automagik.channels.models import EvolutionMessagePayload


class TestSimpleAgentEvolution:
    """Test Evolution support in Simple agent."""
    
    @pytest.fixture
    def simple_agent(self):
        """Create SimpleAgent instance for testing."""
        config = {
            "model_name": "gpt-4.1-mini",
            "max_tokens": "1000",
        }
        return SimpleAgent(config)
    
    @pytest.fixture
    def sample_evolution_payload(self):
        """Sample Evolution payload for testing."""
        return {
            "instance": "test-instance",
            "server_url": "https://test.evolution.api",
            "apikey": "test-api-key",
            "data": {
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "id": "test-message-id",
                    "fromMe": False,
                },
                "message": {
                    "conversation": "Hello test message"
                },
                "messageTimestamp": 1640000000,
                "pushName": "Test User"
            }
        }
    
    def test_evolution_import(self):
        """Test that Evolution types can be imported."""
        from automagik.channels.models import EvolutionMessagePayload
        assert EvolutionMessagePayload is not None
    
    def test_simple_agent_initialization(self, simple_agent):
        """Test that Simple agent initializes with Evolution tools."""
        assert simple_agent is not None
        
        # Check that Evolution tools are registered
        registered_tools = simple_agent.tool_registry.get_registered_tools()
        tool_names = list(registered_tools.keys())
        assert "send_reaction" in tool_names
        assert "send_text_to_user" in tool_names
    
    @pytest.mark.asyncio
    async def test_evolution_payload_parsing(self, simple_agent, sample_evolution_payload):
        """Test that Evolution payload is correctly parsed."""
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Test response"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            result = await simple_agent.run(
                                                "Test message",
                                                channel_payload=sample_evolution_payload
                                            )
                                            
                                            assert result.success is True
                                            # Check that evolution_payload was stored in context
                                            assert "evolution_payload" in simple_agent.context
                                            evolution_payload = simple_agent.context["evolution_payload"]
                                            assert isinstance(evolution_payload, EvolutionMessagePayload)
    
    def test_send_reaction_wrapper_creation(self, simple_agent):
        """Test that send_reaction wrapper is created correctly."""
        wrapper = simple_agent._create_send_reaction_wrapper()
        assert callable(wrapper)
        assert wrapper.__name__ == "send_reaction"
        assert "reaction" in wrapper.__doc__.lower()
    
    def test_send_text_wrapper_creation(self, simple_agent):
        """Test that send_text wrapper is created correctly."""
        wrapper = simple_agent._create_send_text_wrapper()
        assert callable(wrapper)
        assert wrapper.__name__ == "send_text_to_user"
        assert "text" in wrapper.__doc__.lower()
    
    @pytest.mark.asyncio
    async def test_send_reaction_wrapper_functionality(self, simple_agent, sample_evolution_payload):
        """Test send_reaction wrapper functionality."""
        # Create the wrapper
        wrapper = simple_agent._create_send_reaction_wrapper()
        
        # Create a proper evolution payload object
        evolution_payload = EvolutionMessagePayload(**sample_evolution_payload)
        
        # Mock the context with evolution payload
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.context = {"evolution_payload": evolution_payload}
        
        # Mock the underlying evolution API to return success immediately
        with patch('automagik.tools.evolution.api.send_reaction', new_callable=AsyncMock) as mock_api_send:
            mock_api_send.return_value = (True, "Reaction sent successfully")
            
            result = await wrapper(mock_ctx, "👍")
            
            # Verify the result indicates success
            assert result["success"] is True
            # Verify the evolution API was called with correct parameters
            mock_api_send.assert_called_once()
            args, kwargs = mock_api_send.call_args
            assert "👍" in args  # reaction parameter
    
    @pytest.mark.asyncio
    async def test_send_text_wrapper_functionality(self, simple_agent, sample_evolution_payload):
        """Test send_text wrapper functionality."""
        # Create the wrapper
        wrapper = simple_agent._create_send_text_wrapper()
        
        # Create a proper evolution payload object
        evolution_payload = EvolutionMessagePayload(**sample_evolution_payload)
        
        # Mock the context with evolution payload
        mock_ctx = Mock()
        mock_ctx.deps = Mock()
        mock_ctx.deps.context = {"evolution_payload": evolution_payload}
        
        # Mock the underlying HTTP request to avoid actual API calls
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock the response
            mock_response = Mock()
            mock_response.json = AsyncMock(return_value={
                "key": {"id": "test-message-id"},
                "messageTimestamp": 1640000000
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await wrapper(mock_ctx, "Hello from Simple!")
            
            # Verify the result indicates success
            assert result["success"] is True
            # Verify the HTTP request was made
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_group_chat_detection(self, simple_agent):
        """Test group chat detection functionality."""
        group_payload = {
            "instance": "test-instance",
            "data": {
                "key": {
                    "remoteJid": "123456789@g.us",  # Group JID format
                    "id": "test-message-id",
                    "fromMe": False,
                },
                "message": {
                    "conversation": "Hello group"
                },
                "messageTimestamp": 1640000000,
                "pushName": "Test User"
            }
        }
        
        with patch.object(simple_agent, '_check_and_register_prompt', new_callable=AsyncMock):
            with patch.object(simple_agent, 'load_active_prompt_template', new_callable=AsyncMock):
                with patch.object(simple_agent, 'initialize_memory_variables', new_callable=AsyncMock):
                    with patch.object(simple_agent, '_initialize_pydantic_agent', new_callable=AsyncMock):
                        with patch.object(simple_agent, 'get_filled_system_prompt', new_callable=AsyncMock, return_value="test prompt"):
                            with patch.object(simple_agent, '_agent_instance') as mock_agent:
                                mock_result = Mock()
                                mock_result.data = "Test response"
                                mock_agent.run = AsyncMock(return_value=mock_result)
                                
                                # Mock extract functions
                                with patch('automagik.agents.pydanticai.simple.agent.extract_all_messages', return_value=[]):
                                    with patch('automagik.agents.pydanticai.simple.agent.extract_tool_calls', return_value=[]):
                                        with patch('automagik.agents.pydanticai.simple.agent.extract_tool_outputs', return_value=[]):
                                            
                                            await simple_agent.run(
                                                "Test group message",
                                                channel_payload=group_payload
                                            )
                                            
                                            # Check group chat detection
                                            assert simple_agent.context.get("is_group_chat") is True
                                            assert "group_jid" in simple_agent.context


if __name__ == "__main__":
    pytest.main([__file__]) 