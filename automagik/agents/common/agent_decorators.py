"""Agent decorators for declarative PydanticAI agent configuration.

This module provides decorators that enable declarative agent configuration,
eliminating verbose setup code.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Type
from functools import wraps

from .tool_wrapper_factory import ToolRegistrationHelper

logger = logging.getLogger(__name__)


def pydantic_ai_agent(
    model: str = "openai:gpt-4.1-mini",
    tools: Optional[List[str]] = None,
    prompts: Union[str, List[str], None] = None,
    specialized: Optional[List[str]] = None,
    template: Optional[str] = None,
    framework: str = "pydantic_ai"
):
    """Decorator for declarative PydanticAI agent configuration.
    
    Args:
        model: Model name (e.g., "openai:gpt-4.1-mini")
        tools: List of tool names to register
        prompts: Prompt configuration - 'auto_discover', list of files, or None
        specialized: List of specialized modules/agents to register
        template: Configuration template name
        framework: AI framework type
        
    Example:
        @pydantic_ai_agent(
            model="openai:o1-mini",
            tools=['default', 'blackpearl'],
            prompts='auto_discover',
            specialized=['product_agent', 'backoffice_agent']
        )
        class MyAgent(AutomagikAgent):
            pass
    """
    def decorator(cls):
        original_init = cls.__init__
        
        @wraps(original_init)
        def __init__(self, config: Dict[str, str]) -> None:
            # Initialize base agent
            from automagik.agents.models.automagik_agent import AutomagikAgent
            AutomagikAgent.__init__(self, config, framework_type=framework)
            
            # Set up dependencies
            self.dependencies = self.create_default_dependencies()
            
            # Override model
            if hasattr(self.dependencies, 'model_name'):
                self.dependencies.model_name = model
            
            # Set agent ID if available
            if self.db_id:
                self.dependencies.set_agent_id(self.db_id)
            
            # Register tools
            self._register_decorated_tools(tools or ['default'])
            
            # Handle prompts
            self._setup_decorated_prompts(prompts)
            
            # Register specialized modules
            if specialized:
                self._register_specialized_modules(specialized)
            
            # Call original __init__ if it exists and has additional logic
            if hasattr(cls, '_original_init_logic'):
                cls._original_init_logic(self, config)
            
            logger.info(f"Decorated agent {cls.__name__} initialized with model {model}")
        
        # Replace __init__
        cls.__init__ = __init__
        
        # Store decorator configuration
        cls._decorator_config = {
            'model': model,
            'tools': tools,
            'prompts': prompts,
            'specialized': specialized,
            'template': template,
            'framework': framework
        }
        
        return cls
    
    return decorator


def with_tools(*tool_names: str):
    """Decorator to register specific tools with an agent.
    
    Args:
        *tool_names: Tool names to register
        
    Example:
        @with_tools('evolution', 'blackpearl')
        class MyAgent(AutomagikAgent):
            pass
    """
    def decorator(cls):
        original_init = getattr(cls, '__init__', None)
        
        def __init__(self, *args, **kwargs):
            if original_init:
                original_init(self, *args, **kwargs)
            
            # Register additional tools
            for tool_name in tool_names:
                self._register_tool_by_name(tool_name)
        
        cls.__init__ = __init__
        return cls
    
    return decorator


def multi_prompt(
    prompt_directory: str = "prompts",
    auto_register: bool = True,
    default_status: str = "NOT_REGISTERED"
):
    """Decorator for multi-prompt agent configuration.
    
    Args:
        prompt_directory: Directory containing prompt files
        auto_register: Whether to auto-register prompts on initialization
        default_status: Default status key for fallback
        
    Example:
        @multi_prompt(auto_register=True)
        class StatusBasedAgent(AutomagikAgent):
            pass
    """
    def decorator(cls):
        from .multi_prompt_manager import MultiPromptManager
        import os
        
        original_init = getattr(cls, '__init__', None)
        
        def __init__(self, config: Dict[str, str]) -> None:
            if original_init:
                original_init(self, config)
            
            # Set up multi-prompt manager
            prompts_dir = os.path.join(
                os.path.dirname(cls.__module__.replace('.', '/')), 
                prompt_directory
            )
            package_name = cls.__module__.rsplit('.', 1)[0]
            
            self.prompt_manager = MultiPromptManager(self, prompts_dir, package_name)
            self._default_status = default_status
            
            if auto_register:
                # Schedule prompt registration for later (async)
                self._prompts_need_registration = True
        
        # Add prompt management methods
        async def initialize_prompts(self) -> bool:
            """Initialize all prompts for this agent."""
            if hasattr(self, 'prompt_manager'):
                try:
                    await self.prompt_manager.register_all_prompts()
                    return True
                except Exception as e:
                    logger.error(f"Error initializing prompts: {str(e)}")
                    return False
            return True
        
        async def load_prompt_by_status(self, status: Union[str, Any]) -> bool:
            """Load prompt based on status."""
            if hasattr(self, 'prompt_manager'):
                return await self.prompt_manager.load_prompt_by_status(status)
            return False
        
        cls.__init__ = __init__
        cls.initialize_prompts = initialize_prompts
        cls.load_prompt_by_status = load_prompt_by_status
        
        return cls
    
    return decorator


def evolution_agent(model: str = "openai:gpt-4.1-mini"):
    """Decorator for Evolution/WhatsApp agents.
    
    Args:
        model: Model name to use
        
    Example:
        @evolution_agent()
        class WhatsAppBot(AutomagikAgent):
            pass
    """
    return pydantic_ai_agent(
        model=model,
        tools=['default', 'evolution'],
        template='evolution'
    )


def blackpearl_agent(
    model: str = "openai:o1-mini",
    specialized_agents: Optional[List[str]] = None
):
    """Decorator for BlackPearl integration agents.
    
    Args:
        model: Model name to use
        specialized_agents: List of specialized agent names
        
    Example:
        @blackpearl_agent(specialized_agents=['product_agent', 'backoffice_agent'])
        class BusinessAgent(AutomagikAgent):
            pass
    """
    return pydantic_ai_agent(
        model=model,
        tools=['default', 'blackpearl'],
        prompts='auto_discover',
        specialized=specialized_agents or [],
        template='blackpearl'
    )


def api_integration_agent(
    model: str = "openai:gpt-4.1-mini",
    api_tools: Optional[List[str]] = None
):
    """Decorator for API integration agents.
    
    Args:
        model: Model name to use
        api_tools: List of API tool names
        
    Example:
        @api_integration_agent(api_tools=['discord', 'airtable'])
        class IntegrationBot(AutomagikAgent):
            pass
    """
    return pydantic_ai_agent(
        model=model,
        tools=['default'] + (api_tools or []),
        template='api_integration'
    )


# Helper methods for decorated agents
def _register_decorated_tools(self, tool_names: List[str]) -> None:
    """Register tools based on decorator configuration."""
    for tool_name in tool_names:
        if tool_name == 'default':
            self.tool_registry.register_default_tools(self.context)
        elif tool_name == 'evolution':
            ToolRegistrationHelper.register_evolution_tools(self.tool_registry, self.context)
        elif tool_name == 'blackpearl':
            ToolRegistrationHelper.register_blackpearl_tools(self.tool_registry, self.context)
        else:
            # Try to register as custom tool
            self._register_tool_by_name(tool_name)


def _setup_decorated_prompts(self, prompts_config: Union[str, List[str], None]) -> None:
    """Set up prompts based on decorator configuration."""
    if prompts_config == 'auto_discover':
        # Set up for auto-discovery
        self._prompts_auto_discover = True
    elif isinstance(prompts_config, list):
        # Set up specific prompt files
        self._prompt_files = prompts_config
    # For None or single string, assume single prompt (handled by normal flow)


def _register_specialized_modules(self, specialized: List[str]) -> None:
    """Register specialized modules/agents."""
    for module_name in specialized:
        try:
            # Try to import and register the specialized module
            self._register_specialized_module(module_name)
        except Exception as e:
            logger.warning(f"Failed to register specialized module {module_name}: {str(e)}")


def _register_tool_by_name(self, tool_name: str) -> None:
    """Register a tool by name."""
    # This method should be added to agents that use decorators
    logger.debug(f"Registering tool by name: {tool_name}")


def _register_specialized_module(self, module_name: str) -> None:
    """Register a specialized module."""
    # This method should be implemented by agents that use specialized modules
    logger.debug(f"Registering specialized module: {module_name}")


# Add helper methods to agent classes when using decorators
def add_decorator_methods(cls):
    """Add decorator helper methods to an agent class."""
    cls._register_decorated_tools = _register_decorated_tools
    cls._setup_decorated_prompts = _setup_decorated_prompts
    cls._register_specialized_modules = _register_specialized_modules
    cls._register_tool_by_name = _register_tool_by_name
    cls._register_specialized_module = _register_specialized_module
    return cls


class DecoratorRegistry:
    """Registry for managing decorated agents."""
    
    _decorated_agents: Dict[str, Type] = {}
    
    @classmethod
    def register_agent(cls, agent_class: Type) -> None:
        """Register a decorated agent class."""
        cls._decorated_agents[agent_class.__name__] = agent_class
    
    @classmethod
    def get_agent(cls, name: str) -> Optional[Type]:
        """Get a decorated agent class by name."""
        return cls._decorated_agents.get(name)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered decorated agent names."""
        return list(cls._decorated_agents.keys())


def register_decorated_agent(cls):
    """Decorator to register an agent with the decorator registry."""
    DecoratorRegistry.register_agent(cls)
    return cls