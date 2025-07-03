"""Agent Configuration utilities for PydanticAI agents.

This module provides mixins and utilities to eliminate boilerplate code
in agent initialization and configuration.
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AgentConfigurationMixin:
    """Mixin providing standard agent configuration patterns."""
    
    def setup_standard_pydantic_agent(
        self,
        config: Dict[str, str],
        prompt: str,
        custom_tools: Optional[List] = None,
        model_override: Optional[str] = None,
        framework_type: str = "pydantic_ai"
    ) -> None:
        """Set up a PydanticAI agent with standard configuration.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            custom_tools: Optional list of custom tools to register
            model_override: Optional model name override
            framework_type: AI framework type (default: pydantic_ai)
        """
        # Initialize base agent
        super().__init__(config, framework_type=framework_type)
        
        # Set prompt
        self._code_prompt_text = prompt
        
        # Initialize dependencies
        self.dependencies = self.create_default_dependencies()
        
        # Override model if specified
        if model_override and hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = model_override
        
        # Set agent ID if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Register custom tools if provided
        if custom_tools:
            for tool in custom_tools:
                self.tool_registry.register_tool(tool)
        
        logger.debug(f"Standard PydanticAI agent setup completed for {self.__class__.__name__}")
    
    def setup_evolution_agent(
        self,
        config: Dict[str, str],
        prompt: str,
        model_override: Optional[str] = None
    ) -> None:
        """Set up an Evolution/WhatsApp agent with standard configuration.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            model_override: Optional model name override
        """
        self.setup_standard_pydantic_agent(config, prompt, model_override=model_override)
        
        # Register Evolution tools
        self.tool_registry.register_evolution_tools(self.context)
        
        logger.debug(f"Evolution agent setup completed for {self.__class__.__name__}")
    
    def setup_api_integration_agent(
        self,
        config: Dict[str, str],
        prompt: str,
        api_tools: List[str],
        model_override: Optional[str] = None
    ) -> None:
        """Set up an API integration agent.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            api_tools: List of API tool names to register
            model_override: Optional model name override
        """
        self.setup_standard_pydantic_agent(config, prompt, model_override=model_override)
        
        # Register API-specific tools based on tool names
        for tool_name in api_tools:
            self._register_api_tool(tool_name)
        
        logger.debug(f"API integration agent setup completed for {self.__class__.__name__}")
    
    def _register_api_tool(self, tool_name: str) -> None:
        """Register a specific API tool by name.
        
        Args:
            tool_name: Name of the API tool to register
        """
        # This method can be overridden by subclasses to handle specific API tools
        logger.warning(f"API tool registration not implemented for: {tool_name}")


class AgentConfigTemplates:
    """Pre-defined agent configuration templates."""
    
    SIMPLE = {
        "model": "openai:gpt-4.1-mini",
        "tools": ["default"],
        "framework": "pydantic_ai"
    }
    
    EVOLUTION = {
        "model": "openai:gpt-4.1-mini",
        "tools": ["default", "evolution"],
        "framework": "pydantic_ai"
    }
    
    BLACKPEARL = {
        "model": "openai:o1-mini",
        "tools": ["default", "blackpearl"],
        "framework": "pydantic_ai",
        "specialized": ["verification", "contact_management"]
    }
    
    DISCORD = {
        "model": "openai:gpt-4.1-mini",
        "tools": ["default", "discord"],
        "framework": "pydantic_ai",
        "multimodal": True
    }
    
    API_INTEGRATION = {
        "model": "openai:gpt-4.1-mini",
        "tools": ["default"],
        "framework": "pydantic_ai",
        "api_timeout": 30
    }
    
    @classmethod
    def get_template(cls, template_name: str) -> Dict[str, Any]:
        """Get a configuration template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Configuration dictionary
        """
        return getattr(cls, template_name.upper(), cls.SIMPLE)
    
    @classmethod
    def merge_with_template(
        cls, 
        template_name: str, 
        overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge user overrides with a template.
        
        Args:
            template_name: Name of the base template
            overrides: Configuration overrides
            
        Returns:
            Merged configuration
        """
        template = cls.get_template(template_name)
        merged = template.copy()
        merged.update(overrides)
        return merged


class StandardAgentFactory:
    """Factory for creating agents with standard configurations."""
    
    @staticmethod
    def create_simple_agent(agent_class, config: Dict[str, str], prompt: str):
        """Create a simple agent with minimal configuration.
        
        Args:
            agent_class: The agent class to instantiate
            config: Configuration dictionary
            prompt: Agent prompt
            
        Returns:
            Configured agent instance
        """
        agent = agent_class.__new__(agent_class)
        if hasattr(agent, 'setup_standard_pydantic_agent'):
            agent.setup_standard_pydantic_agent(config, prompt)
        else:
            # Fallback to standard initialization
            agent.__init__(config)
        return agent
    
    @staticmethod
    def create_evolution_agent(agent_class, config: Dict[str, str], prompt: str):
        """Create an Evolution/WhatsApp agent.
        
        Args:
            agent_class: The agent class to instantiate
            config: Configuration dictionary
            prompt: Agent prompt
            
        Returns:
            Configured Evolution agent instance
        """
        agent = agent_class.__new__(agent_class)
        if hasattr(agent, 'setup_evolution_agent'):
            agent.setup_evolution_agent(config, prompt)
        else:
            # Fallback with manual Evolution setup
            agent.__init__(config)
            if hasattr(agent, 'tool_registry'):
                agent.tool_registry.register_evolution_tools(agent.context)
        return agent
    
    @staticmethod
    def create_from_template(
        agent_class,
        config: Dict[str, str],
        template_name: str,
        prompt: str,
        overrides: Optional[Dict[str, Any]] = None
    ):
        """Create an agent using a configuration template.
        
        Args:
            agent_class: The agent class to instantiate
            config: Base configuration dictionary
            template_name: Name of the template to use
            prompt: Agent prompt
            overrides: Optional configuration overrides
            
        Returns:
            Configured agent instance
        """
        AgentConfigTemplates.get_template(template_name)
        
        if overrides:
            AgentConfigTemplates.merge_with_template(
                template_name, overrides
            )
        
        # Determine setup method based on template
        if template_name.upper() == 'EVOLUTION':
            return StandardAgentFactory.create_evolution_agent(agent_class, config, prompt)
        else:
            return StandardAgentFactory.create_simple_agent(agent_class, config, prompt)


class ConfigurationValidator:
    """Validator for agent configurations."""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate an agent configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['model', 'tools', 'framework']
        
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required configuration field: {field}")
                return False
        
        # Validate model format
        model = config.get('model', '')
        if ':' not in model:
            logger.error(f"Invalid model format: {model}. Expected 'provider:model'")
            return False
        
        return True
    
    @staticmethod
    def validate_tools(tools: List[str]) -> bool:
        """Validate tool configuration.
        
        Args:
            tools: List of tool names
            
        Returns:
            True if valid, False otherwise
        """
        valid_tools = {
            'default', 'evolution', 'blackpearl', 'discord', 
            'airtable', 'gmail', 'omie', 'datetime'
        }
        
        for tool in tools:
            if tool not in valid_tools:
                logger.warning(f"Unknown tool: {tool}")
        
        return True