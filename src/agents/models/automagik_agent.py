import logging
from typing import Dict, Optional, Union,  Any, TypeVar, Generic
from abc import ABC, abstractmethod
import uuid
import datetime
import asyncio

from src.memory.message_history import MessageHistory
from src.agents.models.dependencies import BaseDependencies
from src.agents.models.response import AgentResponse
from src.config import settings

# Configure logging to reduce Neo4j driver verbosity
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neo4j.io").setLevel(logging.ERROR)
logging.getLogger("neo4j.bolt").setLevel(logging.ERROR)

# Shared Graphiti client for all agents
_shared_graphiti_client = None
_graphiti_initialized = False
_graphiti_init_lock = asyncio.Lock()  # Lock to prevent concurrent initialization

# Concurrency control for LLM provider calls (shared across all agents)
_llm_semaphore: Optional[asyncio.BoundedSemaphore] = None

def get_llm_semaphore() -> asyncio.BoundedSemaphore:
    """Return a bounded semaphore limiting concurrent LLM calls.
    The semaphore is created lazily using the limit from settings.
    """
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.BoundedSemaphore(settings.LLM_MAX_CONCURRENT_REQUESTS)
    return _llm_semaphore

# Try to import Graphiti, but don't fail if not available
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    
    # Synchronous version for non-async contexts
    def get_graphiti_client():
        global _shared_graphiti_client
        return _shared_graphiti_client
    
    # Async version with retry logic
    async def get_graphiti_client_async(max_retries: int = 5, retry_delay: float = 1.0):
        """Get or initialize the shared Graphiti client with retry logic.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Initial delay between retries (will increase but capped)
            
        Returns:
            Initialized Graphiti client or None if all attempts fail
        """
        global _shared_graphiti_client, _graphiti_initialized
        
        
        if _shared_graphiti_client is not None:
            return _shared_graphiti_client
            
        # Use a lock to prevent multiple initialization attempts
        async with _graphiti_init_lock:
            # Double-check inside the lock
            if _shared_graphiti_client is not None:
                return _shared_graphiti_client
                
            if _graphiti_initialized:
                return None  # Already tried and failed
                
            if not settings.NEO4J_URI or not settings.NEO4J_USERNAME or not settings.NEO4J_PASSWORD:
                logger.warning("Neo4j settings not fully configured. Graphiti client will not be initialized.")
                _graphiti_initialized = True
                return None
                
            # Try to initialize with retries
            attempt = 0
            # Cap maximum delay to prevent excessive waiting, especially in development
            max_delay = 5.0  # Maximum delay between retries
            
            while attempt < max_retries:
                attempt += 1
                try:
                    logger.info(f"Attempt {attempt}/{max_retries}: Initializing shared Graphiti client with Neo4j at {settings.NEO4J_URI}")
                    
                    client = Graphiti(
                        settings.NEO4J_URI,
                        settings.NEO4J_USERNAME,
                        settings.NEO4J_PASSWORD
                    )
                    
                    # Test the connection by trying to access a property
                    # This will trigger a connection attempt
                    await client.build_indices_and_constraints()
                    
                    _shared_graphiti_client = client
                    _graphiti_initialized = True
                    
                    logger.info(f"✅ Shared Graphiti client successfully initialized on attempt {attempt}")
                    
                    return _shared_graphiti_client
                    
                except asyncio.CancelledError:
                    # Handle async cancellation properly
                    logger.info("Graphiti client initialization cancelled")
                    _graphiti_initialized = True
                    raise
                    
                except Exception as e:
                    logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
                    
                    if attempt < max_retries:
                        # Wait with capped exponential backoff
                        wait_time = min(retry_delay * (2 ** (attempt - 1)), max_delay)
                        logger.info(f"Waiting {wait_time:.1f}s before retry...")
                        
                        # Use interruptible async sleep
                        try:
                            # Sleep in small intervals to allow cancellation
                            intervals = int(wait_time * 10)
                            for _ in range(intervals):
                                await asyncio.sleep(0.1)
                        except asyncio.CancelledError:
                            logger.info("Graphiti retry sleep cancelled")
                            _graphiti_initialized = True
                            raise
                    else:
                        logger.error(f"Failed to initialize shared Graphiti client after {max_retries} attempts: {e}")
            
            _graphiti_initialized = True  # Mark as attempted even if all retries fail
            return None
        
except ImportError:
    Graphiti = None
    def get_graphiti_client():
        return None
    async def get_graphiti_client_async(max_retries: int = 5, retry_delay: float = 1.0):
        return None

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

# Import prompt repository functions
from src.db.repository.prompt import (
    get_active_prompt,
    find_code_default_prompt,
    create_prompt, 
    set_prompt_active,
    update_prompt as _update_prompt
)
from src.db.models import PromptCreate, PromptUpdate

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
        self.model = self.config.get("model", "openai:gpt-4.1-mini-turbo")
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
        
    def __repr__(self):
        """String representation of the configuration."""
        return f"AgentConfig(config={self.config})"
        
    def update(self, updates: Dict[str, Any]) -> None:
        """Update the configuration with new values.
        
        Args:
            updates: Dictionary with configuration updates
        """
        if not updates:
            return
            
        self.config.update(updates)
        
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

    def __init__(self, config: Union[Dict[str, str], AgentConfig]):
        """Initialize the agent.

        Args:
            config: Dictionary or AgentConfig object with configuration options.
        """
        # Convert config to AgentConfig if it's a dictionary
        if isinstance(config, dict):
            self.config = AgentConfig(config)
        else:
            self.config = config
            
        # Initialize current prompt template (will be set by load_active_prompt_template)
        self.current_prompt_template: Optional[str] = None
        
        # Get agent name from config
        self.name = self.config.get("name", self.__class__.__name__.lower())
        
        # Initialize agent ID 
        self.db_id = validate_agent_id(self.config.get("agent_id"))
        
        # Initialize core components
        self.tool_registry = ToolRegistry()
        self.template_vars = []  # Will be populated when a prompt is loaded
        
        # Initialize context
        self.context = {"agent_id": self.db_id}
        
        # Initialize dependencies (to be set by subclasses)
        self.dependencies = None
        
        # Store Graphiti agent ID for later async initialization
        self.graphiti_agent_id = None
        self.graphiti_client = None
        
        # Debug Neo4j configuration
        
        if (settings.GRAPHITI_ENABLED and 
            Graphiti is not None and 
            settings.NEO4J_URI and 
            settings.NEO4J_USERNAME and 
            settings.NEO4J_PASSWORD):
            agent_id = self.db_id if self.db_id else self.name
            self.graphiti_agent_id = f"{settings.GRAPHITI_NAMESPACE_ID}:{agent_id}"
        else:
            if not settings.GRAPHITI_ENABLED:
                logger.info("Graphiti is disabled via GRAPHITI_ENABLED=false")
            else:
                logger.warning("Graphiti is not configured, skipping Graphiti agent ID setup")
        # Register in database if no ID provided
        if self.db_id is None:
            try:
                # Only import here to avoid circular imports
                from src.db import register_agent, get_agent_by_name
                
                # Check if agent already exists in database
                existing_agent = get_agent_by_name(self.name)
                if existing_agent:
                    # Use existing ID
                    self.db_id = existing_agent.id
                    logger.debug(f"Using existing agent ID {self.db_id} for {self.name}")
                else:
                    # Extract agent metadata
                    agent_type = self.name
                    description = getattr(self, "description", f"{self.name} agent")
                    model = getattr(self.config, "model", "openai:gpt-4.1-mini-turbo")
                    
                    # Prepare config for database
                    agent_config = {}
                    if hasattr(self.config, "__dict__"):
                        agent_config = self.config.__dict__
                    elif isinstance(self.config, dict):
                        agent_config = self.config
                    
                    # Register the agent
                    self.db_id = register_agent(
                        name=self.name,
                        agent_type=agent_type,
                        model=model,
                        description=description,
                        config=agent_config
                    )
                    logger.info(f"Registered agent {self.name} with ID {self.db_id}")
                    
                # Update context with new ID
                self.context["agent_id"] = self.db_id
                
            except Exception as e:
                import traceback
                logger.error(f"Error registering agent in database: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.debug(f"Initialized {self.__class__.__name__} with ID: {self.db_id}")
    
    async def initialize_prompts(self) -> bool:
        """Initialize agent prompts during server startup.
        
        This method registers code-defined prompts for the agent during server startup.
        Agent implementations should set self._code_prompt_text and self._prompt_registered
        in their __init__ method.
        
        Returns:
            True if successful, False otherwise
        """
        # Check if the agent has the required attributes
        has_prompt_text = hasattr(self, '_code_prompt_text') and self._code_prompt_text is not None
        has_registration_flag = hasattr(self, '_prompt_registered')
        
        if not has_prompt_text:
            logger.info(f"No _code_prompt_text found for {self.__class__.__name__}, skipping prompt registration")
            return True
            
        if not has_registration_flag:
            # Initialize the registration flag if it doesn't exist
            self._prompt_registered = False
            
        # Use the shared method for prompt registration
        return await self._check_and_register_prompt()
    
    async def _check_and_register_prompt(self) -> bool:
        """Check if prompt needs registration and register it if needed.
        
        This is a helper method used by both initialize_prompts and run methods.
        
        Returns:
            True if the prompt is registered (or already was), False on failure
        """
        if not self._prompt_registered and self.db_id:
            try:
                agent_name = self.__class__.__name__
                prompt_id = await self._register_code_defined_prompt(
                    self._code_prompt_text,
                    status_key="default",
                    prompt_name=f"Default {agent_name} Prompt", 
                    is_primary_default=True
                )
                if prompt_id:
                    self._prompt_registered = True
                    # Load the prompt template to extract template variables
                    await self.load_active_prompt_template(status_key="default")
                    logger.info(f"Successfully registered and loaded {agent_name} prompt with ID {prompt_id}")
                    return True
                else:
                    logger.warning(f"Failed to register {agent_name} prompt during initialization")
                    return False
            except Exception as e:
                logger.error(f"Error initializing {self.__class__.__name__} prompts: {str(e)}")
                return False
        elif not self.db_id:
            logger.warning(f"Cannot register {self.__class__.__name__} prompt: Agent ID is not set")
            return False
        else:  # Already registered
            logger.debug(f"{self.__class__.__name__} prompt already registered")
            return True
    
    async def _register_code_defined_prompt(self, 
                                         code_prompt_text: str, 
                                         status_key: str = "default", 
                                         prompt_name: Optional[str] = None, 
                                         is_primary_default: bool = False) -> Optional[int]:
        """Register a prompt defined in code for this agent.
        
        This will check if a prompt with is_default_from_code=True for this agent_id and status_key exists.
        If not, it will create one. If is_primary_default is True, it will set this prompt as active and
        update the agent's active_default_prompt_id.
        
        Args:
            code_prompt_text: The prompt text from code
            status_key: The status key for this prompt (default: "default")
            prompt_name: Optional name for the prompt (defaults to f"{self.name} {status_key} Prompt")
            is_primary_default: Whether to set this as the primary default prompt for the agent
            
        Returns:
            The prompt ID if successful, None otherwise
        """
        if not self.db_id:
            logger.warning("Cannot register prompt: Agent ID is not set")
            return None
            
        try:
            # Check if a prompt with is_default_from_code=True for this agent_id and status_key exists
            existing_prompt = find_code_default_prompt(self.db_id, status_key)
            
            if existing_prompt:
                logger.info(f"Found existing code-defined prompt for agent {self.db_id}, status {status_key}")
                
                # Always update the prompt text to ensure code and DB stay in sync
                try:
                    update_success = _update_prompt(
                        existing_prompt.id,
                        PromptUpdate(prompt_text=code_prompt_text)
                    )
                    if update_success:
                        logger.info(
                            f"Updated prompt text for existing code-defined prompt {existing_prompt.id} (agent {self.db_id})"
                        )
                    else:
                        logger.warning(
                            f"Failed to update prompt text for existing code-defined prompt {existing_prompt.id}"
                        )
                except Exception as e:
                    logger.error(f"Error while updating existing code-defined prompt text: {str(e)}")

                # If is_primary_default is True and the prompt is not already active, set it as active
                if is_primary_default and not existing_prompt.is_active:
                    set_prompt_active(existing_prompt.id, True)
                    logger.info(f"Set existing prompt {existing_prompt.id} as active")
                
                return existing_prompt.id
                
            # No existing prompt found, create a new one
            if not prompt_name:
                prompt_name = f"{self.name} {status_key} Prompt"
                
            # Create PromptCreate object
            prompt_data = PromptCreate(
                agent_id=self.db_id,
                prompt_text=code_prompt_text,
                version=1,  # First version
                is_active=is_primary_default,  # Set active if is_primary_default
                is_default_from_code=True,
                status_key=status_key,
                name=prompt_name
            )
            
            # Create the prompt
            prompt_id = create_prompt(prompt_data)
            
            if prompt_id:
                logger.info(f"Registered new code-defined prompt for agent {self.db_id}, status {status_key} with ID {prompt_id}")
                
                # No need to call set_prompt_active here as create_prompt handles it when is_active=True
                
                return prompt_id
            else:
                logger.error(f"Failed to create code-defined prompt for agent {self.db_id}, status {status_key}")
                return None
                
        except Exception as e:
            import traceback
            logger.error(f"Error registering code-defined prompt: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def load_active_prompt_template(self, status_key: str = "default") -> bool:
        """Load the active prompt template for the given status key.
        
        This will set self.current_prompt_template and update self.template_vars.
        
        Args:
            status_key: The status key to load the prompt for (default: "default")
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_id:
            logger.warning("Cannot load prompt template: Agent ID is not set")
            return False
            
        try:
            # Get the active prompt for this agent and status key
            active_prompt = get_active_prompt(self.db_id, status_key)
            
            if not active_prompt:
                # Try the default status key if this is not already the default
                if status_key != "default":
                    logger.warning(f"No active prompt found for agent {self.db_id}, status {status_key}. Trying default status.")
                    active_prompt = get_active_prompt(self.db_id, "default")
                    
                # If still no active prompt, return failure
                if not active_prompt:
                    logger.error(f"No active prompt found for agent {self.db_id}, status {status_key} or default")
                    return False
            
            # Set the current prompt template
            self.current_prompt_template = active_prompt.prompt_text
            
            # Update template variables
            self.template_vars = PromptBuilder.extract_template_variables(self.current_prompt_template)
            
            logger.info(f"Loaded active prompt for agent {self.db_id}, status {status_key} (prompt ID: {active_prompt.id})")
            return True
            
        except Exception as e:
            logger.error(f"Error loading active prompt template: {str(e)}")
            return False
    
    def register_tool(self, tool_func):
        """Register a tool with the agent.
        
        Args:
            tool_func: The tool function to register
        """
        if not hasattr(self, 'tool_registry') or self.tool_registry is None:
            self.tool_registry = ToolRegistry()
            
        self.tool_registry.register_tool(tool_func)
        logger.debug(f"Registered tool: {getattr(tool_func, '__name__')}")
    
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
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update the agent's configuration.
        
        Args:
            config_updates: Dictionary with configuration updates
        """
        if isinstance(self.config, AgentConfig):
            # Update the existing AgentConfig
            self.config.update(config_updates)
        else:
            # Replace the entire config
            self.config = AgentConfig(config_updates)
            
        logger.info(f"Updated agent config: {config_updates.keys()}")
    
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
    
    async def get_filled_system_prompt(self, user_id: Optional[uuid.UUID] = None) -> str:
        """Get the system prompt filled with memory variables.
        
        Args:
            user_id: Optional user ID
            
        Returns:
            Filled system prompt
        """
        # Check if there's a system_prompt override in the context
        if self.context and 'system_prompt' in self.context:
            # Use the overridden system prompt
            logger.info("Using system prompt override from context")
            prompt_template = self.context['system_prompt']
        elif self.current_prompt_template:
            # Use the loaded prompt template
            prompt_template = self.current_prompt_template
        else:
            logger.error("No prompt template available. Load a prompt template first.")
            return "ERROR: No prompt template available."
        
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
            prompt_template=prompt_template,
            memory_vars=memory_vars,
            run_id=run_id,
            agent_id=self.db_id,
            user_id=user_id
        )
        
        return filled_prompt
    
    @abstractmethod
    async def run(self, input_text: str, *, multimodal_content=None, 
                 system_message=None, message_history_obj=None,
                 channel_payload: Optional[Dict] = None,
                 message_limit: Optional[int] = None) -> AgentResponse:
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
                              user_id: Optional[Union[uuid.UUID, str]] = None, 
                              context: Optional[Dict] = None, 
                              message_history: Optional['MessageHistory'] = None,
                              channel_payload: Optional[Dict] = None,
                              message_limit: Optional[int] = None,) -> AgentResponse:
        """Process a user message.
        
        Args:
            user_message: User message text or dictionary with message details
            session_id: Optional session ID to use
            agent_id: Optional agent ID to use
            user_id: User ID to associate with the message (default None)
            context: Optional context dictionary with additional parameters
            message_history: Optional MessageHistory instance for DB storage
            
        Returns:
            AgentResponse object with the agent's response
        """
        # Force Graphiti initialization if available
        if hasattr(self, 'initialize_graphiti') and self.graphiti_agent_id:
            await self.initialize_graphiti()
        
        from src.agents.common.message_parser import parse_user_message
        from src.agents.common.session_manager import create_context, validate_agent_id, validate_user_id, extract_multimodal_content

        # Parse the user message
        content, _ = parse_user_message(user_message)
            
        # Update agent ID and user ID
        if agent_id is not None:
            self.db_id = validate_agent_id(agent_id)
            self.dependencies.set_agent_id(self.db_id)
        
        self.dependencies.user_id = validate_user_id(user_id) if user_id is not None else None
        
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
        
        # Run the agent
        response = await self.run(
            content, 
            multimodal_content=multimodal_content,
            message_history_obj=message_history,
            channel_payload=channel_payload,
            message_limit=message_limit,
        )
        
        # Save messages to database if message_history is provided
        if message_history:
            from src.agents.common.message_parser import format_message_for_db
            
            # Save user message
            user_db_message = format_message_for_db(role="user", content=content, agent_id=self.db_id, channel_payload=channel_payload)
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
        
        # Prepare metadata for Graphiti
        additional_metadata = {}
        if hasattr(response, "tool_calls") and response.tool_calls:
            additional_metadata["tool_calls"] = response.tool_calls
        if hasattr(response, "tool_outputs") and response.tool_outputs:
            additional_metadata["tool_outputs"] = response.tool_outputs
            
        # Queue Graphiti processing in background without waiting for it
        if settings.GRAPHITI_ENABLED and settings.GRAPHITI_BACKGROUND_MODE:
            await self._queue_graphiti_episode(
                user_input=content,
                agent_response=response.text,
                metadata=additional_metadata
            )
        else:
            # Legacy: Run directly in background task (fallback mode)
            asyncio.create_task(
                self._add_episode_to_graphiti_background(
                    user_input=content, 
                    agent_response=response.text, 
                    metadata=additional_metadata
                )
            )
                
        return response
    
    async def _queue_graphiti_episode(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None) -> None:
        """Queue Graphiti episode for background processing.
        
        Args:
            user_input: The text input from the user
            agent_response: The text response from the agent
            metadata: Optional additional metadata for the episode
        """
        try:
            from src.utils.graphiti_queue import get_graphiti_queue
            
            # Get user ID from dependencies or metadata
            user_id = None
            if hasattr(self.dependencies, 'user_id') and self.dependencies.user_id:
                user_id = str(self.dependencies.user_id)
            elif metadata and metadata.get("user_id"):
                user_id = str(metadata.get("user_id"))
            elif self.context and self.context.get("user_id"):
                user_id = str(self.context.get("user_id"))
            
            # Use a default user if none found
            if not user_id:
                user_id = "default_user"
            
            # Prepare enhanced metadata
            episode_metadata = {
                "agent_name": self.name,
                "agent_id": str(self.db_id) if self.db_id else None,
                "is_background": True,
                **(metadata or {})
            }
            
            # Add session info if available
            if self.context:
                session_id = self.context.get("session_id")
                if session_id:
                    episode_metadata["session_id"] = str(session_id)
            
            # Enqueue the episode
            queue_manager = get_graphiti_queue()
            operation_id = await queue_manager.enqueue_episode(
                user_id=user_id,
                message=user_input,
                response=agent_response,
                metadata=episode_metadata
            )
            
            logger.debug(f"📝 Queued Graphiti episode {operation_id[:8]}... for agent {self.name}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to queue Graphiti episode for agent {self.name}: {e}")
            # Don't let Graphiti queue failures affect the agent response
        
    async def _add_episode_to_graphiti_background(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None) -> None:
        """Background version of _add_episode_to_graphiti that handles exceptions internally.
        
        Args:
            user_input: The text input from the user
            agent_response: The text response from the agent
            metadata: Optional additional metadata for the episode
        """
        try:
            # Create a copy of metadata with is_background flag
            bg_metadata = metadata.copy() if metadata else {}
            bg_metadata["is_background"] = True
            
            # Call the regular method but catch any exceptions to prevent them from affecting the parent task
            await self._add_episode_to_graphiti(user_input, agent_response, bg_metadata)
        except Exception as e:
            # Log the error but don't propagate it
            logger.error(f"Background Graphiti processing failed: {e}")
            # Don't re-raise the exception since this is running in background
    
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        if hasattr(self.dependencies, 'http_client') and self.dependencies.http_client:
            await close_http_client(self.dependencies.http_client)
        
        # We don't close the graphiti_client here anymore since it's shared
        # The print statements for Graphiti cleanup are also removed
    
    async def _add_episode_to_graphiti(self, user_input: str, agent_response: str, metadata: Optional[Dict] = None) -> None:
        """Add an episode to the Graphiti knowledge graph.
        
        Args:
            user_input: The text input from the user
            agent_response: The text response from the agent
            metadata: Optional additional metadata for the episode
        """
        # Check if client is initialized, initialize if needed
        if not self.graphiti_client and self.graphiti_agent_id:
            await self.initialize_graphiti()
            
        # If still not initialized, skip episode creation
        if not self.graphiti_client:
            return

        try:
            # Only print start message in non-background mode
            if not metadata.get("is_background", False):
                logger.info(f"🔄 GRAPHITI: Adding episode to Graphiti for agent '{self.name}'...")
            
            # Construct episode details (stored as local variables for logging but not used in API call)
            episode_data = {
                "user_input": user_input,
                "llm_response": agent_response,
                "agent_name": self.name,
                "agent_id": str(self.db_id) if self.db_id else None,
            }
            
            # Get user ID if available
            user_id = None
            
            # Add context info if available
            if self.context:
                session_id = self.context.get("session_id")
                if session_id:
                    episode_data["session_id"] = str(session_id)
            
            # Add user_id if available in dependencies
            if hasattr(self.dependencies, 'user_id') and self.dependencies.user_id:
                user_id = str(self.dependencies.user_id)
                episode_data["user_id"] = user_id
            
            # Add additional metadata if provided
            if metadata:
                # If metadata contains user_id, use it
                if metadata.get("user_id") and not user_id:
                    user_id = str(metadata.get("user_id"))
                episode_data.update(metadata)

            # Only print in non-background mode to reduce noise
            if not metadata.get("is_background", False):
                logger.info("🔄 GRAPHITI: Episode data prepared")
                
            # Create a namespaced group ID that includes namespace, agent ID, and user ID
            base_group = self.graphiti_agent_id  # Already contains namespace:agent_id
            
            # Add user ID to the group if available
            group_id = f"{base_group}:user_{user_id}" if user_id else base_group
            
            # Prepare the episode name using the agent ID and user ID
            episode_uuid = uuid.uuid4()
            episode_name = f"conversation_{group_id}_{episode_uuid}"
            
            # Create the episode body text combining user input and agent response
            episode_body = f"User: {user_input}\n\nAgent: {agent_response}"
            
            # Add the episode to Graphiti using the API's actual parameter names
            result = await self.graphiti_client.add_episode(
                name=episode_name,
                episode_body=episode_body,
                source_description=f"Conversation with {self.name}",
                reference_time=datetime.datetime.now(datetime.timezone.utc),
                source=EpisodeType.text,
                group_id=group_id,  # Use the fully namespaced group ID
            )
            
            # Print minimal success message with episode ID
            episode_id = result.episode.uuid if hasattr(result, 'episode') and hasattr(result.episode, 'uuid') else episode_uuid
            logger.info(f"Added episode to Graphiti for agent '{self.name}' - ID: {episode_id} - Group: {group_id}")
        except Exception as e:
            logger.error(f"Failed to add episode to Graphiti for agent '{self.name}': {e}")
            
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def test_neo4j_connection(self) -> bool:
        """Test if the Neo4j connection is working.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            
            # Test the connection
            with driver.session() as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                test_value = record["test"]
                
            driver.close()
            
            if test_value == 1:
                return True
            else:
                return False
                
        except Exception:
            return False 

    async def initialize_graphiti(self, max_retries: int = 5, retry_delay: float = 1.0) -> bool:
        """Initialize the Graphiti client with retry logic.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Initial delay between retries (will increase exponentially)
            
        Returns:
            True if initialization was successful, False otherwise
        """
        
        if not self.graphiti_agent_id:
            return False  # Not configured for Graphiti
            
        if self.graphiti_client:
            return True  # Already initialized
            
        try:
            # Check if the shared client exists
            existing_client = get_graphiti_client()
            if existing_client:
                self.graphiti_client = existing_client
                return True
                
            # Get the shared client with retry logic
            self.graphiti_client = await get_graphiti_client_async(max_retries, retry_delay)
            
            if self.graphiti_client:
                logger.info(f"Using shared Graphiti client for agent '{self.name}' with ID '{self.graphiti_agent_id}'")
                return True
            else:
                logger.warning(f"Shared Graphiti client is not available for agent '{self.name}'")
                return False
        except Exception as e:
            logger.error(f"Failed to set up Graphiti for agent '{self.name}': {e}")
            self.graphiti_client = None
            return False 