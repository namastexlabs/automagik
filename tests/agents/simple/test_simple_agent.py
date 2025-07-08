"""Test Simple Agent basic functionality."""
import pytest
from automagik.agents.pydanticai.simple.agent import SimpleAgent


class TestSimpleAgent:
    """Test Simple Agent basic functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for Simple agent."""
        return {
            "model_name": "gpt-4.1-mini",
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
    
    def test_agent_has_framework_integration(self, basic_config):
        """Test that Simple agent has framework integration capability."""
        agent = SimpleAgent(basic_config)
        # MCP loading is now handled by the framework
        assert hasattr(agent, 'ai_framework')
        assert hasattr(agent, 'framework_type')
        from automagik.agents.models.framework_types import FrameworkType
        assert agent.framework_type == FrameworkType.PYDANTIC_AI.value
    
    @pytest.mark.asyncio
    async def test_framework_initialization(self, basic_config):
        """Test that framework can be initialized without errors."""
        agent = SimpleAgent(basic_config)
        # Framework initialization is now handled internally
        # Just test that the agent can prepare for framework use
        assert not agent.is_framework_ready  # Should be False before initialization
        assert agent.dependencies is not None
    
    @pytest.mark.asyncio
    async def test_agent_run_method(self, basic_config):
        """Test that agent has a working run method."""
        agent = SimpleAgent(basic_config)
        # Agent should have a run method that delegates to framework
        assert hasattr(agent, 'run')
        assert callable(getattr(agent, 'run'))


class TestSimpleAgentFeatures:
    """Test Simple Agent specific features that need to be maintained."""
    
    @pytest.fixture
    def agent_config(self):
        """Configuration for feature testing."""
        return {
            "model_name": "gpt-4.1-mini",
            "model_provider": "openai"
        }
    
    def test_agent_has_framework_integration(self, agent_config):
        """Test that Simple agent has framework integration features."""
        agent = SimpleAgent(agent_config)
        # Check for framework-related methods
        assert hasattr(agent, 'initialize_framework')
        assert hasattr(agent, 'is_framework_ready')
        
    def test_agent_has_retry_logic_imports(self, agent_config):
        """Test that Simple agent has the imports needed for retry logic."""
        # This will test that the imports are available
        from automagik.agents.models.automagik_agent import get_llm_semaphore
        from automagik.config import settings
        
        assert callable(get_llm_semaphore)
        assert hasattr(settings, 'LLM_RETRY_ATTEMPTS')
    
    def test_agent_has_multimodal_support(self, agent_config):
        """Test that Simple agent now has multimodal processing capabilities."""
        agent = SimpleAgent(agent_config)
        # Check that the agent can handle multimodal content in run method
        import inspect
        run_sig = inspect.signature(agent.run)
        assert 'multimodal_content' in run_sig.parameters
        
        # Check that the framework provides multimodal processing
        assert hasattr(agent, '_run_agent')
        framework_sig = inspect.signature(agent._run_agent)
        assert 'multimodal_content' in framework_sig.parameters 