import logging
from typing import Dict, Optional, Union,  Any, TypeVar, Generic
from abc import ABC, abstractmethod

from src.memory.message_history import MessageHistory
from src.agents.models.dependencies import BaseDependencies
from src.agents.models.response import AgentResponse

# Import common utilities
from src.agents.common.prompt_builder import PromptBuilder
from src.agents.common.memory_handler import MemoryHandler
from src.agents.common.tool_registry import ToolRegistry
from src.agents.common.session_manager import (
    validate_agent_id,
)
from src.agents.common.dependencies_helper import (
    close_http_client
)

logger = logging.getLogger(__name__)

# Define a generic type variable for dependencies
T = TypeVar('T', bound=BaseDependencies)

class AgentConfig:
    """Configuration for an agent.

    Attributes:
        model: The LLM model to use.
        temperature: The temperature to use for LLM calls.
        retries: The number of retries to perform for LLM calls.
    """

    def __init__(self, config: Dict[str, str] = None):
        """Initialize the agent configuration.

        Args:
            config: A dictionary of configuration options.
        """
        self.config = config or {}
        self.model = self.config.get("model", "openai:gpt-3.5-turbo")
        self.temperature = float(self.config.get("temperature", "0.7"))
        self.retries = int(self.config.get("retries", "1"))
        
    def get(self, key: str, default=None):
        """Get a configuration value.
        
        Args:
            key: The configuration key to get
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        return self.config.get(key, default)
        
    def __getattr__(self, name):
        """Get configuration attribute.
        
        Args:
            name: Attribute name to get
            
        Returns:
            The attribute value or None
            
        Raises:
            AttributeError: If configuration attribute doesn't exist
        """
        if name in self.config:
            return self.config[name]
        return None


class AutomagikAgent(ABC, Generic[T]):
    """Base class for all Automagik agents.

    This class defines the interface that all agents must implement and
    provides common functionality for agent initialization, configuration,
    and utility methods using the common utilities.
    """

    def __init__(self, config: Union[Dict[str, str], AgentConfig], system_prompt: str):
        """Initialize the agent.

        Args:
            config: Dictionary or AgentConfig object with configuration options.
            system_prompt: The system prompt to use for this agent.
        """
        # Convert config to AgentConfig if it's a dictionary
        if isinstance(config, dict):
            self.config = AgentConfig(config)
        else:
            self.config = config
            
        # Store the system prompt
        self.system_prompt = system_prompt
        
        # Initialize agent ID 
        self.db_id = validate_agent_id(self.config.get("agent_id"))
        
        # Initialize core components
        self.tool_registry = ToolRegistry()
        self.template_vars = PromptBuilder.extract_template_variables(system_prompt)
        
        # Initialize context
        self.context = {"agent_id": self.db_id}
        
        # Initialize dependencies (to be set by subclasses)
        self.dependencies = None
        
        logger.info(f"Initialized AutomagikAgent with ID: {self.db_id}")
    
    def register_tool(self, tool_func):
        """Register a tool with the agent.
        
        Args:
            tool_func: The tool function to register
        """
        if not hasattr(self, 'tool_registry') or self.tool_registry is None:
            self.tool_registry = ToolRegistry()
            
        self.tool_registry.register_tool(tool_func)
        logger.info(f"Registered tool: {getattr(tool_func, '__name__', str(tool_func))}")
    
    def update_context(self, context_updates: Dict[str, Any]) -> None:
        """Update the agent's context.
        
        Args:
            context_updates: Dictionary with context updates
        """
        self.context.update(context_updates)
        
        # Update tool registry with new context if it exists
        if hasattr(self, 'tool_registry') and self.tool_registry is not None:
            self.tool_registry.update_context(self.context)
            
        logger.info(f"Updated agent context: {context_updates.keys()}")
    
    async def initialize_memory_variables(self, user_id: Optional[int] = None) -> bool:
        """Initialize memory variables for the agent.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_id or not self.template_vars:
            logger.warning("Cannot initialize memory: No agent ID or template variables")
            return False
            
        try:
            result = MemoryHandler.initialize_memory_variables_sync(
                template_vars=self.template_vars,
                agent_id=self.db_id,
                user_id=user_id
            )
            
            if result:
                logger.info(f"Memory variables initialized for agent ID {self.db_id}")
            else:
                logger.warning(f"Failed to initialize memory variables for agent ID {self.db_id}")
                
            return result
        except Exception as e:
            logger.error(f"Error initializing memory variables: {str(e)}")
            return False
    
    async def fetch_memory_variables(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Fetch memory variables for the agent.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            Dictionary of memory variables
        """
        if not self.db_id or not self.template_vars:
            logger.warning("Cannot fetch memory: No agent ID or template variables")
            return {}
            
        try:
            memory_vars = await MemoryHandler.fetch_memory_vars(
                template_vars=self.template_vars,
                agent_id=self.db_id,
                user_id=user_id
            )
            
            logger.info(f"Fetched {len(memory_vars)} memory variables for agent ID {self.db_id}")
            return memory_vars
        except Exception as e:
            logger.error(f"Error fetching memory variables: {str(e)}")
            return {}
    
    async def get_filled_system_prompt(self, user_id: Optional[int] = None) -> str:
        """Get the system prompt filled with memory variables.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            Filled system prompt
        """
        # Check and ensure memory variables exist
        MemoryHandler.check_and_ensure_memory_variables(
            template_vars=self.template_vars,
            agent_id=self.db_id,
            user_id=user_id
        )
        
        # Fetch memory variables
        memory_vars = await self.fetch_memory_variables(user_id)
        
        # Get run ID from context
        run_id = self.context.get('run_id')
        
        # Fill system prompt with variables
        filled_prompt = await PromptBuilder.get_filled_system_prompt(
            prompt_template=self.system_prompt,
            memory_vars=memory_vars,
            run_id=run_id,
            agent_id=self.db_id,
            user_id=user_id
        )
        
        return filled_prompt
    
    @abstractmethod
    async def run(self, input_text: str, *, multimodal_content=None, 
                 system_message=None, message_history_obj=None) -> AgentResponse:
        """Run the agent with the given input.
        
        Args:
            input_text: Text input for the agent
            multimodal_content: Optional multimodal content
            system_message: Optional system message for this run
            message_history_obj: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with result and metadata
        """
        pass
        
    async def process_message(self, user_message: Union[str, Dict[str, Any]], 
                              session_id: Optional[str] = None, 
                              agent_id: Optional[Union[int, str]] = None, 
                              user_id: int = 1, 
                              context: Optional[Dict] = None, 
                              message_history: Optional['MessageHistory'] = None) -> AgentResponse:
        """Process a user message.
        
        Args:
            user_message: User message text or dictionary with message details
            session_id: Optional session ID to use
            agent_id: Optional agent ID to use
            user_id: User ID to associate with the message (default 1)
            context: Optional context dictionary with additional parameters
            message_history: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with the agent's response
        """
        from src.agents.common.message_parser import parse_user_message
        from src.agents.common.session_manager import create_context, validate_agent_id, validate_user_id, extract_multimodal_content

        # Parse the user message
        content, _ = parse_user_message(user_message)
            
        # Update agent ID and user ID
        if agent_id is not None:
            self.db_id = validate_agent_id(agent_id)
            self.dependencies.set_agent_id(self.db_id)
        
        self.dependencies.user_id = validate_user_id(user_id)
        
        # Update context
        new_context = create_context(
            agent_id=self.db_id, 
            user_id=user_id,
            session_id=session_id,
            additional_context=context
        )
        self.update_context(new_context)
        
        # Extract multimodal content if present
        multimodal_content = extract_multimodal_content(context)
        
        # Load message history if provided
        if message_history:
            db_messages = message_history.all_messages()
            if db_messages:
                self.dependencies.set_message_history(db_messages)
        
        # Run the agent
        response = await self.run(
            content, 
            multimodal_content=multimodal_content,
            message_history_obj=message_history
        )
        
        # Save messages to database if message_history is provided
        if message_history:
            from src.agents.common.message_parser import format_message_for_db
            
            # Save user message
            user_db_message = format_message_for_db(role="user", content=content, agent_id=self.db_id)
            message_history.add_message(message=user_db_message)
            
            # Save agent response
            agent_db_message = format_message_for_db(
                role="assistant", 
                content=response.text,
                tool_calls=response.tool_calls,
                tool_outputs=response.tool_outputs,
                system_prompt=getattr(response, "system_prompt", None),
                agent_id=self.db_id
            )
            message_history.add_message(agent_db_message)
                
        return response
        
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        if hasattr(self.dependencies, 'http_client') and self.dependencies.http_client:
            await close_http_client(self.dependencies.http_client)
            
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup() 