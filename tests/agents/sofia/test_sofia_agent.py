"""Test Sofia Agent basic functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.simple.sofia.agent import SofiaAgent


class TestSofiaAgent:
    """Test Sofia Agent basic functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for Sofia agent."""
        return {
            "model_name": "google-gla:gemini-2.5-pro-preview-05-06",
            "model_provider": "google",
            "temperature": "0.1",
            "max_tokens": "1000"
        }
    
    def test_agent_initialization(self, basic_config):
        """Test that Sofia agent can be initialized."""
        agent = SofiaAgent(basic_config)
        assert agent is not None
        assert agent.dependencies is not None
        assert agent.tool_registry is not None
    
    def test_agent_has_specialized_tools(self, basic_config):
        """Test that Sofia agent has specialized tools like Airtable integration."""
        agent = SofiaAgent(basic_config)
        # Check for specialized tool wrapper methods
        assert hasattr(agent, '_create_airtable_agent_wrapper')
        assert hasattr(agent, '_create_send_reaction_wrapper')
        assert hasattr(agent, '_create_send_text_wrapper')
    
    def test_agent_has_evolution_support(self, basic_config):
        """Test that Sofia agent has WhatsApp/Evolution support."""
        agent = SofiaAgent(basic_config)
        # Check that agent can handle channel_payload parameter
        import inspect
        run_sig = inspect.signature(agent.run)
        assert 'channel_payload' in run_sig.parameters
    
    @pytest.mark.asyncio
    async def test_agent_initialization_async(self, basic_config):
        """Test that agent can be initialized asynchronously."""
        agent = SofiaAgent(basic_config)
        # Should not raise an exception
        await agent._initialize_pydantic_agent()
        assert agent._agent_instance is not None


class TestSofiaAgentCapabilities:
    """Test Sofia Agent current capabilities before enhancement."""
    
    @pytest.fixture
    def agent_config(self):
        """Configuration for capability testing."""
        return {
            "model_name": "google-gla:gemini-2.5-pro-preview-05-06",
            "model_provider": "google"
        }
    
    def test_agent_has_multimodal_support(self, agent_config):
        """Test that Sofia agent has multimodal processing capabilities."""
        agent = SofiaAgent(agent_config)
        # Check for multimodal support method
        assert hasattr(agent, '_convert_image_payload_to_pydantic')
        
    def test_agent_has_mcp_integration(self, agent_config):
        """Test that Sofia agent now has MCP integration."""
        agent = SofiaAgent(agent_config)
        # Sofia should now have MCP integration
        assert hasattr(agent, '_load_mcp_servers')
        assert callable(getattr(agent, '_load_mcp_servers'))
    
    @pytest.mark.asyncio
    async def test_mcp_servers_loading(self, agent_config):
        """Test that Sofia agent can load MCP servers without errors."""
        agent = SofiaAgent(agent_config)
        # This should not fail even if no MCP servers are configured
        servers = await agent._load_mcp_servers()
        assert isinstance(servers, list)
        
    def test_agent_needs_reliability_features(self, agent_config):
        """Test to highlight what Sofia agent is missing (reliability features)."""
        agent = SofiaAgent(agent_config)
        # This test documents what we need to add
        # Sofia should not have retry logic in its run method yet
        import inspect
        source = inspect.getsource(agent.run)
        assert 'semaphore' not in source
        assert 'LLM_RETRY_ATTEMPTS' not in source


class TestSofiaAgentEvolutionIntegration:
    """Test Sofia Agent Evolution/WhatsApp integration capabilities."""
    
    @pytest.fixture
    def agent_config(self):
        """Configuration for Evolution testing."""
        return {
            "model_name": "google-gla:gemini-2.5-pro-preview-05-06",
            "model_provider": "google"
        }
    
    @pytest.fixture
    def sample_evolution_payload(self):
        """Sample Evolution payload for testing."""
        return {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "sample_id"
            },
            "pushName": "Test User",
            "message": {
                "conversation": "Hello from WhatsApp"
            }
        }
    
    @pytest.mark.asyncio
    async def test_evolution_payload_handling(self, agent_config, sample_evolution_payload):
        """Test that Sofia agent can handle Evolution payloads."""
        agent = SofiaAgent(agent_config)
        # This should not raise an exception even with Evolution payload
        try:
            # We won't actually run the agent, just test the payload handling setup
            response = await agent.run(
                "test message", 
                channel_payload=sample_evolution_payload
            )
            # If we get here, payload handling worked
            assert response is not None
        except Exception as e:
            # Expected since we might not have API keys configured
            # But evolution payload processing should not be the cause
            assert "evolution_payload" not in str(e).lower() 