"""Specialized base classes for common PydanticAI agent patterns.

This module provides pre-configured base classes that eliminate boilerplate
for common agent types like Evolution/WhatsApp agents and multi-prompt agents.
"""
import logging
import os
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod

from src.agents.models.automagik_agent import AutomagikAgent
from .agent_configuration import AgentConfigurationMixin
from .tool_wrapper_factory import ToolWrapperFactory, ToolRegistrationHelper
from .multi_prompt_manager import MultiPromptManager

logger = logging.getLogger(__name__)


class EvolutionAgent(AutomagikAgent):
    """Pre-configured base class for WhatsApp/Evolution agents.
    
    Leverages the existing ChannelHandler system for Evolution payload processing.
    The AutomagikAgent framework automatically handles:
    - Evolution payload detection and processing
    - User/group context extraction
    - Evolution-specific tool registration
    - Response formatting for WhatsApp limits
    """
    
    def __init__(self, config: Dict[str, str], prompt: str, model_override: Optional[str] = None) -> None:
        """Initialize Evolution agent with automatic channel handling.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            model_override: Optional model name override
        """
        # Initialize base agent (handles channel processing automatically)
        super().__init__(config, framework_type="pydantic_ai")
        
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
        
        # Register default tools (Evolution tools added automatically by ChannelHandler)
        self.tool_registry.register_default_tools(self.context)
        
        logger.info(f"Evolution agent {self.__class__.__name__} initialized with ChannelHandler system")


class MultiPromptAgent(AutomagikAgent):
    """Base class for agents with multiple status-based prompts."""
    
    # Override these in subclasses
    prompt_directory_name: str = "prompts"
    default_model: str = "openai:gpt-4.1-mini"
    
    def __init__(self, config: Dict[str, str], model_override: Optional[str] = None) -> None:
        """Initialize multi-prompt agent.
        
        Args:
            config: Agent configuration dictionary
            model_override: Optional model name override
        """
        # Initialize base agent
        super().__init__(config, framework_type="pydantic_ai")
        
        # Set up dependencies
        self.dependencies = self.create_default_dependencies()
        
        # Override model if specified
        model_name = model_override or self.default_model
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = model_name
        
        # Set agent ID if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Initialize multi-prompt manager
        prompts_dir = os.path.join(os.path.dirname(self.__class__.__module__.replace('.', '/')), self.prompt_directory_name)
        package_name = self.__class__.__module__.rsplit('.', 1)[0]  # Get parent package
        
        self.prompt_manager = MultiPromptManager(self, prompts_dir, package_name)
        
        # Register specialized tools
        self._register_specialized_tools()
        
        logger.info(f"Multi-prompt agent {self.__class__.__name__} initialized")
    
    async def initialize_prompts(self) -> bool:
        """Initialize all prompts for this agent."""
        try:
            await self.prompt_manager.register_all_prompts()
            return True
        except Exception as e:
            logger.error(f"Error initializing prompts for {self.__class__.__name__}: {str(e)}")
            return False
    
    async def load_prompt_by_status(self, status: Union[str, Any]) -> bool:
        """Load prompt based on status.
        
        Args:
            status: Status key or enum value
            
        Returns:
            True if successful, False otherwise
        """
        return await self.prompt_manager.load_prompt_by_status(status)
    
    def _register_specialized_tools(self) -> None:
        """Register specialized tools for this agent.
        
        Override this method in subclasses to add agent-specific tools.
        """
        pass


class APIIntegrationAgent(AutomagikAgent):
    """Base class for agents that integrate with external APIs."""
    
    # Override these in subclasses
    api_tools: List[str] = []
    api_timeout: int = 30
    default_model: str = "openai:gpt-4.1-mini"
    
    def __init__(
        self, 
        config: Dict[str, str], 
        prompt: str,
        api_tools: Optional[List[str]] = None,
        model_override: Optional[str] = None
    ) -> None:
        """Initialize API integration agent.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            api_tools: Optional list of API tools to register
            model_override: Optional model name override
        """
        # Initialize base agent
        super().__init__(config, framework_type="pydantic_ai")
        
        # Set prompt
        self._code_prompt_text = prompt
        
        # Initialize dependencies
        self.dependencies = self.create_default_dependencies()
        
        # Override model if specified
        model_name = model_override or self.default_model
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = model_name
        
        # Set agent ID if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Register API tools
        tools_to_register = api_tools or self.api_tools
        for tool_name in tools_to_register:
            self._register_api_tool(tool_name)
        
        # Set API-specific configurations
        self.api_timeout = self.api_timeout
        
        logger.info(f"API integration agent {self.__class__.__name__} initialized")
    
    def _register_api_tool(self, tool_name: str) -> None:
        """Register a specific API tool."""
        # Implement API tool registration logic
        # This can be extended by subclasses for specific APIs
        logger.debug(f"Registering API tool: {tool_name}")


class BlackPearlAgent(MultiPromptAgent):
    """Specialized agent for BlackPearl integration with multi-prompt support."""
    
    default_model: str = "openai:o1-mini"
    
    def __init__(self, config: Dict[str, str], model_override: Optional[str] = None) -> None:
        """Initialize BlackPearl agent.
        
        Args:
            config: Agent configuration dictionary
            model_override: Optional model name override
        """
        super().__init__(config, model_override)
        
        # Register BlackPearl tools
        ToolRegistrationHelper.register_blackpearl_tools(self.tool_registry, self.context)
        
        logger.info(f"BlackPearl agent {self.__class__.__name__} initialized")
    
    def _register_specialized_tools(self) -> None:
        """Register BlackPearl-specific specialized tools."""
        # Register specialized agents if available
        specialized_agents = self._get_specialized_agents()
        if specialized_agents:
            ToolRegistrationHelper.register_specialized_agents(
                self.tool_registry, 
                self.context, 
                specialized_agents
            )
    
    def _get_specialized_agents(self) -> Dict[str, Any]:
        """Get specialized agent functions for this BlackPearl agent.
        
        Override this method in subclasses to provide specialized agents.
        
        Returns:
            Dictionary mapping agent names to agent functions
        """
        return {}
    
    async def handle_contact_management(
        self, 
        channel_payload: Optional[Dict], 
        user_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Handle BlackPearl contact management and prompt selection.
        
        This method should be called before agent execution to set up
        the appropriate prompt based on contact status.
        
        Args:
            channel_payload: Channel-specific payload
            user_id: User ID
            
        Returns:
            BlackPearl contact information if available
        """
        if not channel_payload:
            return None
        
        try:
            # Extract user information from context
            user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
            user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
            
            if not user_number:
                logger.debug("No user number found in context, skipping BlackPearl contact management")
                return None
            
            # Get or create contact - this needs to be implemented by subclass
            contact = await self._get_or_create_blackpearl_contact(user_number, user_name, user_id)
            
            if contact:
                # Update context with BlackPearl information
                self._update_context_with_contact_info(contact)
                
                # Set prompt based on approval status
                status = contact.get("status_aprovacao", "NOT_REGISTERED")
                await self.load_prompt_by_status(status)
                
                # Store user info in memory
                await self._store_user_memory(user_id, user_name, user_number, contact)
                
                logger.info(f"BlackPearl Contact: {contact.get('id')} - {user_name}")
                return contact
            else:
                # Fallback to default prompt
                await self.load_prompt_by_status("NOT_REGISTERED")
                
        except Exception as e:
            logger.error(f"Error in BlackPearl contact management: {str(e)}")
            # Fallback to default prompt
            await self.load_prompt_by_status("NOT_REGISTERED")
        
        return None
    
    async def _get_or_create_blackpearl_contact(
        self, 
        user_number: str, 
        user_name: Optional[str], 
        user_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get or create BlackPearl contact.
        
        This method should be implemented by subclasses.
        
        Args:
            user_number: User phone number
            user_name: User name
            user_id: User ID
            
        Returns:
            BlackPearl contact information
        """
        # This should be implemented by subclasses
        logger.warning("_get_or_create_blackpearl_contact not implemented")
        return None
    
    def _update_context_with_contact_info(self, contact: Dict[str, Any]) -> None:
        """Update agent context with BlackPearl contact information."""
        self.context["blackpearl_contact_id"] = contact.get("id")
        # Add other contact fields as needed
    
    async def _store_user_memory(
        self, 
        user_id: Optional[str], 
        user_name: Optional[str], 
        user_number: Optional[str],
        contact: Dict[str, Any]
    ) -> None:
        """Store user information in memory."""
        if not self.db_id:
            return
        
        try:
            from src.db.models import Memory
            from src.db.repository import create_memory
            
            user_info = {
                "user_id": user_id,
                "user_name": user_name,
                "user_number": user_number,
                "blackpearl_contact_id": contact.get("id"),
                # Add other relevant fields
            }
            
            # Filter out None values
            user_info_content = {k: v for k, v in user_info.items() if v is not None}
            
            memory_to_create = Memory(
                name="user_information",
                content=str(user_info_content),
                user_id=user_id,
                read_mode="system_prompt",
                access="read_write",
                agent_id=self.db_id
            )
            
            create_memory(memory=memory_to_create)
            logger.info(f"Created/Updated user_information memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing user memory: {str(e)}")


class DiscordAgent(AutomagikAgent):
    """Specialized agent for Discord integration with multimodal support."""
    
    def __init__(self, config: Dict[str, str], prompt: str, model_override: Optional[str] = None) -> None:
        """Initialize Discord agent.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
            model_override: Optional model name override
        """
        # Initialize base agent
        super().__init__(config, framework_type="pydantic_ai")
        
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
        
        # Register Discord-specific tools
        self._register_discord_tools()
        
        logger.info(f"Discord agent {self.__class__.__name__} initialized")
    
    def _register_discord_tools(self) -> None:
        """Register Discord-specific tools."""
        # This can be implemented when Discord tools are available
        logger.debug("Discord tools registration placeholder")


class SimpleAgent(AutomagikAgent):
    """Ultra-simplified agent base class."""
    
    def __init__(self, config: Dict[str, str], prompt: str) -> None:
        """Initialize simple agent with minimal configuration.
        
        Args:
            config: Agent configuration dictionary
            prompt: The agent prompt text
        """
        # Initialize base agent
        super().__init__(config, framework_type="pydantic_ai")
        
        # Set prompt
        self._code_prompt_text = prompt
        
        # Initialize dependencies
        self.dependencies = self.create_default_dependencies()
        
        # Set agent ID if available
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        logger.info(f"Simple agent {self.__class__.__name__} initialized")