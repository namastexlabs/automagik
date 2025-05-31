"""Test Simple Agent basic functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.pydanticai.simple.agent import SimpleAgent


class TestSimpleAgent:
    """Test Simple Agent basic functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for Simple agent."""
        return {
            "model_name": "openai:gpt-4.1-mini",
            "model_provider": "openai",
            "temperature": "0.1",
            "max_tokens": "1000"
        }
    
    def test_agent_initialization(self, basic_config):
        """Test that Simple agent can be initialized."""
        agent = SimpleAgent(basic_config)
        assert agent is not None
        assert agent.dependencies is not None
        assert agent.tool_registry is not None
    
    def test_agent_has_mcp_loading_method(self, basic_config):
        """Test that Simple agent has MCP loading capability."""
        agent = SimpleAgent(basic_config)
        assert hasattr(agent, '_load_mcp_servers')
        assert callable(getattr(agent, '_load_mcp_servers'))
    
    @pytest.mark.asyncio
    async def test_mcp_servers_loading(self, basic_config):
        """Test that MCP servers can be loaded without errors."""
        agent = SimpleAgent(basic_config)
        # This should not fail even if no MCP servers are configured
        servers = await agent._load_mcp_servers()
        assert isinstance(servers, list)
    
    @pytest.mark.asyncio
    async def test_agent_initialization_async(self, basic_config):
        """Test that agent can be initialized asynchronously."""
        agent = SimpleAgent(basic_config)
        # Should not raise an exception
        await agent._initialize_pydantic_agent()
        assert agent._agent_instance is not None


class TestSimpleAgentFeatures:
    """Test Simple Agent specific features that need to be maintained."""
    
    @pytest.fixture
    def agent_config(self):
        """Configuration for feature testing."""
        return {
            "model_name": "openai:gpt-4.1-mini",
            "model_provider": "openai"
        }
    
    def test_agent_has_mcp_integration(self, agent_config):
        """Test that Simple agent has MCP integration features."""
        agent = SimpleAgent(agent_config)
        # Check for MCP-related methods
        assert hasattr(agent, '_load_mcp_servers')
        assert hasattr(agent, '_initialize_pydantic_agent')
        
    def test_agent_has_retry_logic_imports(self, agent_config):
        """Test that Simple agent has the imports needed for retry logic."""
        # This will test that the imports are available
        from src.agents.models.automagik_agent import get_llm_semaphore
        from src.config import settings
        
        assert callable(get_llm_semaphore)
        assert hasattr(settings, 'LLM_RETRY_ATTEMPTS')
    
    def test_agent_has_multimodal_support(self, agent_config):
        """Test that Simple agent now has multimodal processing capabilities."""
        agent = SimpleAgent(agent_config)
        # Check that the agent can handle multimodal content in run method
        import inspect
        run_sig = inspect.signature(agent.run)
        assert 'multimodal_content' in run_sig.parameters
        
        # Check that the run method contains multimodal processing logic
        source = inspect.getsource(agent.run)
        assert '_convert_image_payload_to_pydantic' in source
        assert 'ImageUrl' in source
        assert 'pydantic_ai_input_list' in source 