"""AutomagikAgent with dependency inversion and framework abstraction."""
import logging
from typing import Dict, Optional, Union, Any, TypeVar, Generic, Type, List
from abc import ABC
import uuid
import asyncio
import os
import time

from automagik.agents.models.dependencies import BaseDependencies
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.ai_frameworks.base import AgentAIFramework
from automagik.agents.models.state_manager import AutomagikStateManager, StateManagerInterface
from automagik.agents.models.framework_types import FrameworkType
from automagik.config import settings

# Import framework implementations
from automagik.agents.models.ai_frameworks.pydantic_ai import PydanticAIFramework
from automagik.agents.models.ai_frameworks.agno import AgnoFramework

# Import common utilities
from automagik.agents.common.prompt_builder import PromptBuilder
from automagik.agents.common.memory_handler import MemoryHandler
from automagik.agents.common.tool_registry import ToolRegistry
from automagik.agents.common.session_manager import validate_agent_id
from automagik.agents.common.dependencies_helper import close_http_client
from automagik.agents.common.multi_prompt_manager import MultiPromptManager

# Import tracing support
try:
    from automagik.tracing import get_tracing_manager
    from automagik.tracing.performance import SamplingDecision
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    get_tracing_manager = None
    SamplingDecision = None

# Import functions that tests expect to mock at module level
try:
    from automagik.db.repository.prompt import get_active_prompt
except ImportError:
    # Handle cases where these modules don't exist in test environments
    get_active_prompt = None

logger = logging.getLogger(__name__)

# Concurrency control for LLM provider calls (shared across all agents)
_llm_semaphore: Optional[asyncio.BoundedSemaphore] = None

def get_llm_semaphore() -> asyncio.BoundedSemaphore:
    """Return a bounded semaphore limiting concurrent LLM calls.
    The semaphore is created lazily using the limit from settings.
    """
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.BoundedSemaphore(settings.AUTOMAGIK_LLM_MAX_CONCURRENT_REQUESTS)
    return _llm_semaphore

# Define a generic type variable for dependencies
T = TypeVar('T', bound=BaseDependencies)


class AgentConfig:
    """Configuration for an agent."""

    def __init__(self, config: Dict[str, str] = None):
        """Initialize the agent configuration."""
        self.config = config or {}
        # Use environment variable for default model, fallback to gpt-4.1-mini
        default_model = os.environ.get("AUTOMAGIK_DEFAULT_MODEL", "gpt-4.1-mini")
        self.model = self.config.get("model", default_model)
        self.temperature = float(self.config.get("temperature", "0.7"))
        self.retries = int(self.config.get("retries", "1"))
        self.framework_type = self.config.get("framework_type", FrameworkType.default().value)
        
        # Backward compatibility properties
        self.model_name = self.model  # For backward compatibility
        
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
        
    def update(self, updates: Dict[str, Any]) -> None:
        """Update the configuration with new values."""
        if updates:
            self.config.update(updates)
            # Update direct properties
            if "model" in updates:
                self.model = updates["model"]
                self.model_name = self.model
            if "temperature" in updates:
                self.temperature = float(updates["temperature"])
            if "retries" in updates:
                self.retries = int(updates["retries"])
            if "framework_type" in updates:
                self.framework_type = updates["framework_type"]
    
    def __getattr__(self, name: str):
        """Allow access to config values as attributes for backward compatibility."""
        if name in self.config:
            return self.config[name]
        # Return None for non-existent attributes (backward compatibility)
        return None


class AutomagikAgent(ABC, Generic[T]):
    """Base class for all Automagik agents with dependency inversion.
    
    This class uses dependency inversion to support multiple AI frameworks
    through the AgentAIFramework interface.
    """
    
    # Declarative model configuration (can be overridden by subclasses)
    DEFAULT_MODEL: str = "openai:gpt-4o-mini"
    FALLBACK_MODELS: List[str] = []
    DEFAULT_CONFIG: Dict[str, Any] = {}
    
    # Declarative prompt file (can be overridden by subclasses)
    PROMPT_FILE: str = None  # e.g., "prompt.md"

    def __init__(self, 
                 config: Union[Dict[str, str], AgentConfig],
                 framework_type: Union[str, "FrameworkType"] = None,
                 state_manager: Optional[StateManagerInterface] = None):
        """Initialize the agent with dependency inversion.

        Args:
            config: Dictionary or AgentConfig object with configuration options.
            framework_type: Type of AI framework to use (string or FrameworkType enum)
            state_manager: Optional state manager instance
        """
        # Merge class defaults with provided config
        if isinstance(config, dict):
            # Merge DEFAULT_CONFIG with provided config (provided config takes precedence)
            merged_config = {**self.DEFAULT_CONFIG, **config}
            self.config = AgentConfig(merged_config)
        else:
            # If AgentConfig object, merge defaults into it
            for key, value in self.DEFAULT_CONFIG.items():
                if key not in config.config:
                    config.config[key] = value
            self.config = config
            
        # Set framework type - normalize enum to string value
        raw_framework_type = framework_type or self.config.get("framework_type") or FrameworkType.default()
        
        # Handle enum types
        if hasattr(raw_framework_type, 'value'):
            self.framework_type = raw_framework_type.value
        else:
            # Handle string - normalize to enum
            normalized = FrameworkType.normalize(raw_framework_type)
            self.framework_type = normalized.value
        
        # Initialize state manager
        self.state_manager = state_manager or AutomagikStateManager()
        
        # Initialize current prompt template
        self.current_prompt_template: Optional[str] = None
        
        # Get agent name from config
        self.name = self.config.get("name", self.__class__.__name__.lower())
        
        # Initialize agent ID 
        self.db_id = validate_agent_id(self.config.get("agent_id"))
        
        # Model resolution: config > database > default
        if not self.config.config.get("model"):  # If model not in config, check DB
            self._resolve_model_from_db()
        
        # Backward compatibility: Auto-register agent if no ID provided
        if not self.db_id and self.name != self.__class__.__name__.lower():
            try:
                from automagik.db import get_agent_by_name, register_agent
                
                # Check if agent already exists
                existing_agent = get_agent_by_name(self.name)
                if existing_agent:
                    self.db_id = existing_agent.id
                else:
                    # Register new agent
                    self.db_id = register_agent(
                        name=self.name,
                        agent_type=self.name,
                        model=self.config.model,
                        description=f"{self.name} agent",
                        config=self.config.config
                    )
            except Exception as e:
                logger.error(f"Error during auto-registration for {self.name}: {e}")
        
        # NEW: External Agent Support - Load package environment if specified
        package_env = getattr(self, 'PACKAGE_ENV_FILE', None)
        if package_env:
            self._load_package_env(package_env)
        
        # NEW: External Agent Support - Register external API keys if specified
        external_keys = getattr(self, 'EXTERNAL_API_KEYS', [])
        if external_keys:
            self._register_external_keys(external_keys)
        
        # NEW: Load prompt from file if PROMPT_FILE is specified
        prompt_file = getattr(self, 'PROMPT_FILE', None)
        if prompt_file:
            self._load_prompt_from_file(prompt_file)
        
        # Initialize core components
        self.tool_registry = ToolRegistry()
        self.template_vars = []
        
        # Initialize context
        self.context = {"agent_id": self.db_id}
        
        # Initialize dependencies (to be set by subclasses)
        self.dependencies = None
        
        # Initialize AI framework (will be set during initialization)
        self.ai_framework: Optional[AgentAIFramework] = None
        self._framework_initialized = False
        
        # Initialize tracing manager if available
        self.tracing = None
        self.sampler = None
        if TRACING_AVAILABLE:
            try:
                self.tracing = get_tracing_manager()
                if self.tracing and self.tracing.observability:
                    self.sampler = self.tracing.observability.sampler
            except Exception as e:
                logger.debug(f"Tracing initialization skipped: {e}")
        
        # Framework registry
        self._framework_registry = {
            FrameworkType.PYDANTIC_AI.value: PydanticAIFramework,
            FrameworkType.AGNO.value: AgnoFramework,
            # Add more frameworks here as they're implemented
            # FrameworkType.LANGGRAPH.value: LangGraphFramework,
        }
        
        # Multimodal framework preferences
        self._multimodal_framework = FrameworkType.AGNO.value  # Agno handles multimodal best
        self._text_framework = FrameworkType.PYDANTIC_AI.value  # PydanticAI for text-only
        
        # Multimodal configuration defaults (overridable via `config` or `update_config`).
        self.vision_model: str = self.config.get("vision_model", "openai:gpt-4o")
        # List of supported media types – kept for possible future gating
        self.supported_media: List[str] = self.config.get(
            "supported_media", ["image", "audio", "document"]
        )
        # Whether to enhance prompts automatically when media is present
        self.auto_enhance_prompts: bool = bool(
            self.config.get("auto_enhance_prompts", True)
        )
        # Internal tracker for temporary vision-model switch
        self._original_model: Optional[str] = None
        
        # --------------------------------------------------------
        # Multi-prompt support (status-based prompt switching)
        # --------------------------------------------------------
        self.enable_multi_prompt: bool = bool(self.config.get("enable_multi_prompt", False))
        self.prompt_manager = None  # type: Optional["MultiPromptManager"]

        if self.enable_multi_prompt:
            try:
                # Default directory is <agent module path>/prompts unless caller overrides
                default_prompt_dir = os.path.join(
                    os.path.dirname(self.__class__.__module__.replace(".", "/")),
                    self.config.get("prompt_directory", "prompts"),
                )
                package_name = self.__class__.__module__.rsplit(".", 1)[0]

                self.prompt_manager = MultiPromptManager(self, default_prompt_dir, package_name)
            except Exception as e:
                logger.error(f"Failed to initialise MultiPromptManager: {e}")
                self.enable_multi_prompt = False
        
        logger.debug(f"Initialized {self.__class__.__name__} with framework: {self.framework_type}")
    
    def create_default_dependencies(self):
        """Create default dependencies for the agent.
        
        This convenience method handles the common pattern of creating
        AutomagikAgentsDependencies with model configuration.
        """
        from automagik.agents.models.dependencies import AutomagikAgentsDependencies
        from automagik.agents.common.dependencies_helper import get_model_name, parse_model_settings
        
        dependencies = AutomagikAgentsDependencies(
            model_name=get_model_name(self.config.config),
            model_settings=parse_model_settings(self.config.config)
        )
        
        if self.db_id:
            dependencies.set_agent_id(self.db_id)
            
        return dependencies
    
    def _load_package_env(self, env_file: str) -> None:
        """Load package-specific environment variables.
        
        Args:
            env_file: Relative path to .env file from agent's module directory
        """
        try:
            from dotenv import load_dotenv
        except ImportError:
            logger.warning("python-dotenv not available, package .env file won't be loaded")
            return
            
        import inspect
        from pathlib import Path
        
        try:
            # Get the directory of the agent's module
            agent_module = inspect.getfile(self.__class__)
            agent_dir = Path(agent_module).parent
            env_path = agent_dir / env_file
            
            if env_path.exists():
                # Load with override=True to ensure package values take precedence
                load_dotenv(env_path, override=True)
                logger.info(f"Loaded package environment from {env_path}")
            else:
                logger.debug(f"Package .env file not found at {env_path}")
                
        except Exception as e:
            logger.warning(f"Error loading package environment: {e}")
    
    def _register_external_keys(self, external_keys: List[tuple]) -> None:
        """Register external API keys with the settings system.
        
        Args:
            external_keys: List of (key_name, description) tuples
        """
        try:
            from automagik.config import settings
            
            for key_name, description in external_keys:
                value = os.environ.get(key_name)
                if value:
                    if hasattr(settings, 'add_external_api_key'):
                        settings.add_external_api_key(key_name, value, description)
                    logger.debug(f"Registered external API key: {key_name}")
                else:
                    logger.warning(f"External API key {key_name} not found in environment")
                    
        except Exception as e:
            logger.warning(f"Error registering external keys: {e}")
    
    def _load_prompt_from_file(self, prompt_file: str) -> None:
        """Load prompt from a file relative to the agent's module.
        
        Args:
            prompt_file: Relative path to prompt file (e.g., "prompt.md")
        """
        try:
            from pathlib import Path
            import inspect
            
            # Get the directory of the agent class
            agent_module = inspect.getmodule(self.__class__)
            if agent_module and hasattr(agent_module, '__file__'):
                agent_dir = Path(agent_module.__file__).parent
            else:
                # Fallback to current directory
                agent_dir = Path.cwd()
            
            prompt_path = agent_dir / prompt_file
            
            if prompt_path.exists():
                self._code_prompt_text = prompt_path.read_text(encoding='utf-8')
                logger.info(f"Loaded prompt from file: {prompt_file}")
            else:
                logger.warning(f"Prompt file not found: {prompt_path}")
                
        except Exception as e:
            logger.error(f"Failed to load prompt from file {prompt_file}: {e}")
    
    def register_tools(self, tools) -> None:
        """Convenience method for bulk tool registration.
        
        Args:
            tools: List of tool functions, single tool function, or module with tools
        """
        if callable(tools):
            # Single tool function
            self.tool_registry.register_tool(tools)
        elif isinstance(tools, (list, tuple)):
            # List of tool functions
            for tool in tools:
                if callable(tool):
                    self.tool_registry.register_tool(tool)
        elif hasattr(tools, '__name__'):
            # Module - register all callable functions
            import inspect
            registered_count = 0
            for name, obj in inspect.getmembers(tools):
                if (inspect.iscoroutinefunction(obj) and 
                    not name.startswith('_') and 
                    hasattr(obj, '__module__') and 
                    obj.__module__ == tools.__name__):
                    self.tool_registry.register_tool(obj)
                    registered_count += 1
            logger.debug(f"Auto-registered {registered_count} tools from {tools.__name__}")
    
    async def initialize_framework(self, 
                                  dependencies_type: Type[BaseDependencies],
                                  tools: Optional[List[Any]] = None,
                                  mcp_servers: Optional[List[Any]] = None) -> bool:
        """Initialize the AI framework with dependencies and tools.
        
        Args:
            dependencies_type: Type of dependencies to use
            tools: Optional list of tools to register
            mcp_servers: Optional list of MCP servers
            
        Returns:
            True if initialization was successful
        """
        try:
            # Handle auto framework selection - default to PydanticAI for initialization
            actual_framework_type = self.framework_type
            if self.framework_type in ["auto", FrameworkType.AUTO.value]:
                actual_framework_type = FrameworkType.PYDANTIC_AI.value
            
            # Check if framework is supported
            if actual_framework_type not in self._framework_registry:
                raise ValueError(f"Unsupported framework: {actual_framework_type}")
                
            # Create framework config
            from automagik.agents.models.ai_frameworks.base import AgentConfig as FrameworkConfig
            framework_config = FrameworkConfig(
                model=self.config.model,
                temperature=self.config.temperature,
                retries=self.config.retries,
                tools=tools,
                model_settings={}
            )
            
            # Initialize framework
            framework_class = self._framework_registry[actual_framework_type]
            self.ai_framework = framework_class(framework_config)
            
            # Initialize with tools and dependencies
            tools_to_register = tools or list(self.tool_registry.get_registered_tools().values())
            await self.ai_framework.initialize(
                tools=tools_to_register,
                dependencies_type=dependencies_type,
                mcp_servers=mcp_servers
            )
            
            self._framework_initialized = True
            logger.info(f"Successfully initialized {actual_framework_type} framework for {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.framework_type} framework: {e}")
            self._framework_initialized = False
            return False
    
    @property
    def is_framework_ready(self) -> bool:
        """Check if the AI framework is ready to run."""
        return (self._framework_initialized and 
                self.ai_framework is not None and 
                self.ai_framework.is_ready)
    
    def _resolve_model_from_db(self) -> None:
        """Resolve model from database if not specified in config."""
        try:
            from automagik.db import get_agent_by_name
            agent = get_agent_by_name(self.name)
            if agent and agent.model:
                self.config.model = agent.model
                self.config.model_name = agent.model
                logger.debug(f"Resolved model from DB for {self.name}: {agent.model}")
        except Exception as e:
            logger.debug(f"Could not resolve model from DB for {self.name}: {e}")
    
    def _detect_multimodal_request(self, user_input: Union[str, List[Any]], message_type: str = "text") -> bool:
        """Detect if the request contains multimodal content."""
        # Check message type
        if message_type in ["audio", "video", "image"]:
            return True
            
        # Check for multimodal input format
        if isinstance(user_input, list):
            for item in user_input:
                if isinstance(item, dict) and item.get("type") in ["image", "audio", "video"]:
                    return True
                    
        return False
    
    def _select_optimal_framework(self, user_input: Union[str, List[Any]], message_type: str = "text") -> str:
        """Automatically select the best framework for the request type."""
        # If framework is explicitly set and not "auto", respect that choice
        if (hasattr(self, 'framework_type') and 
            self.framework_type and 
            self.framework_type not in ["auto", FrameworkType.AUTO.value]):
            return self.framework_type
            
        # Auto-select based on content type
        if self._detect_multimodal_request(user_input, message_type):
            logger.info(f"🎯 Multimodal content detected, using {self._multimodal_framework} framework")
            return self._multimodal_framework
        else:
            logger.info(f"📝 Text-only content, using {self._text_framework} framework")
            return self._text_framework
    
    def _should_sample(self, kwargs: Dict[str, Any]) -> Optional['SamplingDecision']:
        """Determine if this run should be sampled for detailed tracing.
        
        Args:
            kwargs: Run kwargs that might influence sampling
            
        Returns:
            SamplingDecision with result and reason, or None if tracing unavailable
        """
        if not TRACING_AVAILABLE or not self.tracing or not self.tracing.observability or not self.sampler:
            return None
        
        # Check if this is the first run for this agent type
        is_first = kwargs.get("is_first_run", False)
        
        return self.sampler.should_sample(
            trace_type=f"agent.{self.name}",
            duration_ms=None,  # Not known yet
            is_error=False,
            attributes={
                "is_first_occurrence": is_first,
                "session_id": kwargs.get("session_id"),
                "has_multimodal": bool(kwargs.get("multimodal_content"))
            }
        )
    
    def _log_usage_to_observability(self, usage: Dict[str, Any], messages: List[Dict[str, str]] = None, response: str = None):
        """Log token usage to observability providers.
        
        Args:
            usage: Usage dictionary with token counts and costs
            messages: Optional messages sent to LLM
            response: Optional response from LLM
        """
        if not self.tracing or not self.tracing.observability:
            return
        
        logger.info(f"📊 Logging usage to observability - providers: {list(self.tracing.observability.providers.keys())}")
        
        # Log to each active provider
        for provider_name, provider in self.tracing.observability.providers.items():
            try:
                logger.info(f"📝 Sending to {provider_name} - usage: {usage}")
                provider.log_llm_call(
                    model=self.config.model,
                    messages=messages or [],
                    response=response or "",
                    usage=usage
                )
            except Exception as e:
                logger.debug(f"Failed to log usage to provider: {e}")

    async def _run_agent(self,
                                input_text: str,
                                system_prompt: Optional[str] = None,
                                message_history: Optional[List[Dict[str, Any]]] = None,
                                multimodal_content: Optional[Dict[str, Any]] = None,
                                channel_payload: Optional[Dict] = None,
                                **kwargs) -> AgentResponse:
        """Run the agent using the configured AI framework.
        
        This method handles all the complexity that was previously duplicated
        in each agent implementation, including:
        - Evolution payload processing
        - MCP server loading  
        - Prompt registration and loading
        - Memory variable initialization
        - Multimodal content handling
        - Error handling and retries
        
        Args:
            input_text: User input text
            system_prompt: Optional system prompt override
            message_history: Optional message history 
            multimodal_content: Optional multimodal content
            channel_payload: Optional Evolution/channel payload
            message_limit: Message history limit
            **kwargs: Additional framework-specific parameters
            
        Returns:
            AgentResponse object
        """
        if not self.is_framework_ready:
            # Try to initialize framework if not ready
            if not await self.initialize_framework(
                dependencies_type=type(self.dependencies) if self.dependencies else None
            ):
                raise RuntimeError(f"AI framework {self.framework_type} could not be initialized")
            
        if not self.dependencies:
            raise RuntimeError("Dependencies not set - call set_dependencies() first")
        
        # Tracing: Record start time
        start_time = time.time()
        success = False
        error_type = None
        
        # Determine if we should trace this run
        sampling_decision = self._should_sample(kwargs)
        should_sample = sampling_decision.should_sample if sampling_decision else False
        
        # Start observability trace if sampled
        trace_ctx = None
        if should_sample and self.tracing and self.tracing.observability:
            trace_ctx = self.tracing.observability.trace_agent_run(
                agent_name=self.name,
                session_id=kwargs.get("session_id", self.context.get("session_id", "unknown")),
                message_preview=input_text[:100] if input_text else ""
            )
            trace_ctx.__enter__()
            
            # Log sampling decision
            if hasattr(trace_ctx, 'attributes'):
                trace_ctx.attributes["sampling.reason"] = sampling_decision.reason
                trace_ctx.attributes["sampling.rate"] = sampling_decision.sample_rate
            
        try:
            # 1. Handle Evolution/WhatsApp payload
            await self._process_channel_payload(channel_payload)
            
            # 2. Register and load prompts
            await self._ensure_prompts_ready()
            
            # 3. Initialize memory variables
            await self._ensure_memory_ready()
            
            # 4. Get filled system prompt (unless overridden)
            if not system_prompt:
                # Try to get user_id from dependencies first, then from context as fallback
                user_id = getattr(self.dependencies, 'user_id', None)
                if not user_id and self.context:
                    # Fallback: check context for user_id (for FlashinhoV2 etc.)
                    context_user_id = self.context.get('user_id')
                    if context_user_id:
                        try:
                            import uuid
                            user_id = uuid.UUID(context_user_id) if isinstance(context_user_id, str) else context_user_id
                        except Exception:
                            pass
                
                system_prompt = await self.get_filled_system_prompt(user_id=user_id)
            
            # 5. Add system message to history
            if system_prompt and message_history:
                message_history = self._add_system_message_to_history(message_history, system_prompt)
            
            # 6. Prepare context and memory
            if self.dependencies:
                # Set user and agent IDs
                self.dependencies.set_agent_id(self.db_id)
                if channel_payload:
                    self.dependencies.set_evolution_payload(channel_payload)
                
                # NEW: Pass multimodal content to dependencies
                if multimodal_content:
                    context = kwargs.get('context', {})
                    context['multimodal_content'] = multimodal_content
                    self.dependencies.update_context(context)
            
            # 🎯 INTELLIGENT FRAMEWORK SELECTION: Auto-select Agno for multimodal, PydanticAI for text
            # Check for message_type in kwargs first, then context, then default to "text"
            message_type = kwargs.get("message_type")
            if not message_type and self.context:
                message_type = self.context.get("message_type", "text")
            if not message_type:
                message_type = "text"
                
            logger.debug(f"Framework selection: message_type={message_type}, multimodal_content={bool(multimodal_content)}")
            
            optimal_framework = self._select_optimal_framework(
                input_text,  # Use input_text for framework selection instead of processed_input
                message_type=message_type
            )
            
            # Re-initialize framework if we need to switch
            if optimal_framework != self.framework_type:
                logger.info(f"🔄 Switching from {self.framework_type} to {optimal_framework} framework")
                self.framework_type = optimal_framework
                # Force re-initialization with new framework
                self._framework_initialized = False
                if not await self.initialize_framework(
                    dependencies_type=type(self.dependencies) if self.dependencies else None
                ):
                    raise RuntimeError(f"Could not initialize {optimal_framework} framework")
            
            # Process multimodal input AFTER framework selection
            processed_input = await self._process_multimodal_input(input_text, multimodal_content)
            
            # Multimodal: auto-switch to a vision-capable model when media is present.
            if multimodal_content and any(multimodal_content.values()):
                # Switch to vision-capable model if not already using one
                try:
                    if self._original_model is None and self.dependencies and hasattr(self.dependencies, "model_name"):
                        self._original_model = self.dependencies.model_name

                    current_model = getattr(self.dependencies, "model_name", "")
                    needs_vision = multimodal_content.get("images") or multimodal_content.get("documents")

                    has_images = bool(multimodal_content.get("images"))
                    has_documents = bool(multimodal_content.get("documents"))
                    logger.info(f"🔍 Vision check: needs_vision=images:{has_images},docs:{has_documents}, current_model={current_model}, is_vision_capable={self._is_vision_capable_model(current_model) if current_model else False}")
                    
                    if needs_vision and current_model and not self._is_vision_capable_model(current_model):
                        if self.dependencies:
                            logger.info(f"🔄 Switching from {current_model} to vision model: {self.vision_model}")
                            self.dependencies.model_name = self.vision_model
                            logger.info(f"✅ Switched to vision model: {self.vision_model}")
                    else:
                        logger.info(f"🚫 No vision model switch needed: needs_vision={needs_vision}, current_model={current_model}, is_vision_capable={self._is_vision_capable_model(current_model) if current_model else False}")
                except Exception as e:
                    logger.warning(f"Unable to auto-switch vision model: {e}")

                # Auto-enhance prompt if enabled
                if self.auto_enhance_prompts and system_prompt:
                    system_prompt = self._enhance_system_prompt(system_prompt, multimodal_content)
            
            # 7. Update dependencies with context
            if hasattr(self.dependencies, 'set_context'):
                self.dependencies.set_context(self.context)
            
            # 8. Run with framework (or mocked agent for tests)
            if hasattr(self, '_mock_agent_instance') and self._mock_agent_instance:
                # Use mocked agent instance for testing
                mock_result = await self._mock_agent_instance.run(processed_input, deps=self.dependencies)
                # Convert mock result to AgentResponse for backward compatibility
                if hasattr(mock_result, 'data'):
                    # Extract tool calls and outputs from mock extraction functions for testing
                    tool_calls = []
                    tool_outputs = []
                    try:
                        # Import from the locations that tests typically mock
                        # First try the current agent's module (for specific agent tests)
                        agent_module = self.__class__.__module__
                        try:
                            import importlib
                            module = importlib.import_module(agent_module)
                            if hasattr(module, 'extract_tool_calls') and hasattr(module, 'extract_tool_outputs'):
                                tool_calls = module.extract_tool_calls(mock_result) or []
                                tool_outputs = module.extract_tool_outputs(mock_result) or []
                            else:
                                raise ImportError("Agent module doesn't have extraction functions")
                        except (ImportError, AttributeError):
                            # Fallback to simple agent (most common test target)
                            try:
                                from automagik.agents.pydanticai.simple.agent import extract_tool_calls, extract_tool_outputs
                                tool_calls = extract_tool_calls(mock_result) or []
                                tool_outputs = extract_tool_outputs(mock_result) or []
                            except ImportError:
                                # Final fallback to common module
                                from automagik.agents.common.message_parser import extract_tool_calls, extract_tool_outputs
                                tool_calls = extract_tool_calls(mock_result) or []
                                tool_outputs = extract_tool_outputs(mock_result) or []
                    except Exception:
                        # If extraction fails, use empty lists
                        pass
                    
                    return AgentResponse(
                        text=mock_result.data,
                        success=True,
                        tool_calls=tool_calls,
                        tool_outputs=tool_outputs
                    )
                else:
                    return mock_result  # Assume it's already an AgentResponse
            else:
                # Use the real framework
                result = await self.ai_framework.run(
                    user_input=processed_input,
                    dependencies=self.dependencies,
                    message_history=message_history,
                    system_prompt=system_prompt,
                    **kwargs
                )
                
                # 9. Postprocess response using channel handler
                result = await self._postprocess_response(result)
                
                # Log usage if available (for observability)
                logger.debug(f"Checking for usage data - has usage: {hasattr(result, 'usage')}, should_sample: {should_sample}")
                if should_sample and self.tracing and self.tracing.observability:
                    # Create comprehensive trace following LangWatch best practices
                    self._create_enhanced_trace(
                        processed_input, 
                        result, 
                        message_history, 
                        system_prompt, 
                        multimodal_content,
                        kwargs
                    )
                
                # Restore original model if we temporarily switched
                try:
                    if self._original_model and self.dependencies and hasattr(self.dependencies, "model_name"):
                        self.dependencies.model_name = self._original_model
                        logger.info("Restored original model after multimodal run")
                finally:
                    self._original_model = None
                
                success = True
                return result
            
        except Exception as e:
            error_type = type(e).__name__
            
            # Log error to observability if sampled
            if should_sample and self.tracing and self.tracing.observability:
                for provider in self.tracing.observability.providers.values():
                    try:
                        provider.log_error(e, {
                            "agent": self.name,
                            "session_id": kwargs.get("session_id", self.context.get("session_id"))
                        })
                    except Exception as log_error:
                        logger.debug(f"Failed to log error to provider: {log_error}")
            
            # Always track errors in telemetry (anonymous)
            if self.tracing and self.tracing.telemetry:
                try:
                    self.tracing.telemetry.track_error(
                        error_type=error_type,
                        component=f"agent.{self.name}"
                    )
                except Exception as tel_error:
                    logger.debug(f"Failed to track error in telemetry: {tel_error}")
            
            logger.error(f"Framework run failed: {e}")
            return AgentResponse(
                text=f"Error running agent: {str(e)}",
                success=False,
                error_message=str(e)
            )
        
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Close observability trace if it was opened
            if trace_ctx:
                try:
                    trace_ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Failed to close trace context: {e}")
            
            # Always send anonymous telemetry (not sampled)
            if self.tracing and self.tracing.telemetry:
                try:
                    self.tracing.telemetry.track_agent_run(
                        agent_type=self.name,
                        framework=self.framework_type,
                        success=success,
                        duration_ms=duration_ms
                    )
                except Exception as tel_error:
                    logger.debug(f"Failed to track agent run in telemetry: {tel_error}")
                
                # Track feature usage
                try:
                    # Track framework selection
                    self.tracing.telemetry.track_feature_usage(
                        f"framework.{self.framework_type}",
                        category="agent_framework"
                    )
                    
                    # Track multimodal usage if applicable
                    if multimodal_content:
                        self.tracing.telemetry.track_feature_usage(
                            "multimodal_content",
                            category="agent_capability"
                        )
                except Exception as feat_error:
                    logger.debug(f"Failed to track feature usage: {feat_error}")
    
    async def _process_channel_payload(self, channel_payload: Optional[Dict]) -> None:
        """Process channel payload using appropriate channel handler."""
        if not channel_payload:
            return
            
        try:
            # Import channel handler system
            from automagik.channels.registry import get_channel_handler
            
            # Get appropriate channel handler
            channel_handler = await get_channel_handler(
                channel_payload=channel_payload,
                context=self.context
            )
            
            if channel_handler:
                # Use channel handler to preprocess the payload
                processed_data = await channel_handler.preprocess_in(
                    input_text="",  # Will be provided separately
                    channel_payload=channel_payload,
                    context=self.context
                )
                
                # Update context with processed data
                if processed_data and "context" in processed_data:
                    self.context.update(processed_data["context"])
                    
                # Store channel handler for later use
                self.context["channel_handler"] = channel_handler
                
                # Register channel-specific tools
                channel_tools = channel_handler.get_tools()
                if channel_tools:
                    for tool in channel_tools:
                        self.tool_registry.register_tool(tool)
                        
                logger.debug(f"Processed payload using {channel_handler.channel_name} handler")
                
                # Legacy compatibility: store user info in memory for template variables
                user_name = self.context.get("whatsapp_user_name") or self.context.get("user_name")
                user_number = self.context.get("whatsapp_user_number") or self.context.get("user_phone_number")
                if self.db_id and (user_number or user_name):
                    await self._store_user_info_in_memory(user_name, user_number)
            else:
                # Fallback to legacy Evolution handling for backward compatibility
                from automagik.agents.common.evolution import EvolutionMessagePayload
                
                evolution_payload = EvolutionMessagePayload(**channel_payload)
                self.context["evolution_payload"] = evolution_payload
                
                user_number = evolution_payload.get_user_number()
                user_name = evolution_payload.get_user_name()
                
                if user_number:
                    self.context["user_phone_number"] = user_number
                if user_name:
                    self.context["user_name"] = user_name
                    
                if evolution_payload.is_group_chat():
                    self.context["is_group_chat"] = True
                    self.context["group_jid"] = evolution_payload.get_group_jid()
                
                if self.db_id and (user_number or user_name):
                    await self._store_user_info_in_memory(user_name, user_number)
                    
                logger.debug("Used legacy Evolution payload processing")
                
        except Exception as e:
            logger.error(f"Error processing channel payload: {e}")
    
    async def _postprocess_response(self, response: AgentResponse) -> AgentResponse:
        """Postprocess agent response using channel handler."""
        try:
            # Check if we have a channel handler
            channel_handler = self.context.get("channel_handler")
            if not channel_handler:
                return response
                
            # Postprocess the response text
            processed_text = await channel_handler.postprocess_out(
                response=response.text,
                context=self.context
            )
            
            # Update the response
            if isinstance(processed_text, dict):
                # Handle structured responses (e.g., multi-part messages)
                if "messages" in processed_text and "type" in processed_text:
                    # For multi-part messages, join them with newlines for now
                    response.text = "\n".join(processed_text["messages"])
                    # Store original structure in metadata for advanced handlers
                    if not hasattr(response, 'metadata'):
                        response.metadata = {}
                    response.metadata["channel_response"] = processed_text
                elif "text" in processed_text:
                    response.text = processed_text["text"]
                else:
                    # Use string representation as fallback
                    response.text = str(processed_text)
            else:
                # Simple text response
                response.text = str(processed_text)
                
            logger.debug(f"Postprocessed response using {channel_handler.channel_name} handler")
            
        except Exception as e:
            logger.error(f"Error postprocessing response: {e}")
            # Return original response if postprocessing fails
            
        return response
    
    async def _ensure_prompts_ready(self) -> None:
        """Ensure agent prompts are registered and loaded."""
        try:
            # Register code-defined prompt if available
            if hasattr(self, '_code_prompt_text') and not getattr(self, '_prompt_registered', False):
                await self._check_and_register_prompt()
                
            # Load active prompt template
            await self.load_active_prompt_template(status_key="default")
            
        except Exception as e:
            logger.warning(f"Error ensuring prompts ready: {e}")
    
    async def _ensure_memory_ready(self) -> None:
        """Ensure memory variables are initialized."""
        try:
            if self.db_id and self.template_vars:
                await self.initialize_memory_variables(
                    getattr(self.dependencies, 'user_id', None)
                )
        except Exception as e:
            logger.warning(f"Error ensuring memory ready: {e}")
    
    def _validate_mime_type(self, mime_type: str) -> str:
        """Validate and normalize MIME type for media content with fallback."""
        if not mime_type:
            logger.debug("Empty MIME type, defaulting to image/jpeg")
            return "image/jpeg"
        
        # Clean the MIME type - remove charset and other parameters
        mime_type = mime_type.split(';')[0].strip().lower()
        
        # If it's not an image type, default to image/jpeg for image processing
        if not mime_type.startswith('image/'):
            logger.debug(f"Non-image MIME type '{mime_type}', defaulting to image/jpeg")
            return "image/jpeg"
        
        # Common image MIME types mapping
        valid_image_types = {
            'image/jpg': 'image/jpeg',  # Normalize jpg to jpeg
            'image/jpeg': 'image/jpeg',
            'image/png': 'image/png',
            'image/gif': 'image/gif',
            'image/webp': 'image/webp',
            'image/bmp': 'image/bmp',
            'image/tiff': 'image/tiff'
        }
        
        # Return normalized MIME type or default
        normalized = valid_image_types.get(mime_type, "image/jpeg")
        if normalized != mime_type:
            logger.debug(f"Normalized MIME type from '{mime_type}' to '{normalized}'")
        
        return normalized
    
    def _process_multimodal_input_for_agno(self, input_text: str, multimodal_content: Optional[Dict]) -> List[Any]:
        """Process multimodal content specifically for Agno framework format."""
        # Agno expects a list with text first, then media items as dicts with 'type' key
        input_list = [input_text] if input_text else []
        
        if not multimodal_content:
            return input_list
            
        logger.debug(f"Processing multimodal content for Agno: {multimodal_content.keys()}")
        
        # Process images
        if "images" in multimodal_content:
            for image_data in multimodal_content["images"]:
                agno_image = {
                    "type": "image"
                }
                
                if isinstance(image_data, dict):
                    # Get the data content
                    data_content = image_data.get("data", "")
                    mime_type = image_data.get("media_type") or image_data.get("mime_type", "image/jpeg")
                    
                    if data_content.startswith("http"):
                        agno_image["url"] = data_content
                    else:
                        # For base64 data, keep it as data URL or raw base64
                        if data_content.startswith("data:"):
                            agno_image["data"] = data_content
                        else:
                            # Convert to data URL format
                            agno_image["data"] = f"data:{mime_type};base64,{data_content}"
                
                input_list.append(agno_image)
                logger.debug(f"Added Agno image: {agno_image.get('type')}")
        
        # Process audio
        if "audio" in multimodal_content:
            for audio_data in multimodal_content["audio"]:
                agno_audio = {
                    "type": "audio"
                }
                
                if isinstance(audio_data, dict):
                    data_content = audio_data.get("data", "")
                    mime_type = audio_data.get("media_type") or audio_data.get("mime_type", "audio/wav")
                    
                    if data_content:
                        # For audio, Agno expects base64 data
                        if data_content.startswith("data:"):
                            agno_audio["data"] = data_content
                        else:
                            agno_audio["data"] = f"data:{mime_type};base64,{data_content}"
                        
                        # Set MIME type for format detection
                        agno_audio["mime_type"] = mime_type
                
                input_list.append(agno_audio)
                logger.debug(f"Added Agno audio: {agno_audio.get('type')}")
        
        # Process videos
        if "videos" in multimodal_content:
            for video_data in multimodal_content["videos"]:
                agno_video = {
                    "type": "video"
                }
                
                if isinstance(video_data, dict):
                    # Videos typically need filepath or URL
                    if "filepath" in video_data:
                        agno_video["filepath"] = video_data["filepath"]
                    elif "url" in video_data:
                        agno_video["url"] = video_data["url"]
                    elif "data" in video_data and video_data["data"].startswith("http"):
                        agno_video["url"] = video_data["data"]
                
                input_list.append(agno_video)
                logger.debug(f"Added Agno video: {agno_video.get('type')}")
        
        # Process documents  
        if "documents" in multimodal_content:
            for doc_data in multimodal_content["documents"]:
                # Agno might not have specific document support, treat as generic data
                agno_doc = {
                    "type": "document"
                }
                
                if isinstance(doc_data, dict):
                    data_content = doc_data.get("data", "")
                    mime_type = doc_data.get("media_type") or doc_data.get("mime_type", "application/pdf")
                    
                    if data_content:
                        if data_content.startswith("http"):
                            agno_doc["url"] = data_content
                        else:
                            agno_doc["data"] = f"data:{mime_type};base64,{data_content}"
                
                input_list.append(agno_doc)
                logger.debug(f"Added Agno document: {agno_doc.get('type')}")
        
        return input_list
    
    async def _download_whatsapp_image(self, image_url: str, mime_type: str) -> Optional[str]:
        """Download WhatsApp encrypted image and return as base64.
        
        Args:
            image_url: WhatsApp encrypted image URL
            mime_type: Expected MIME type of the image
            
        Returns:
            Base64 encoded image data or None if download fails
        """
        try:
            import httpx
            import base64
            import hashlib
            from pathlib import Path
            
            # Create user-specific tmp directory
            user_id = getattr(self.dependencies, 'user_id', 'unknown')
            tmp_dir = Path("./data/tmp") / str(user_id)
            tmp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate a unique filename based on URL hash
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            ext = mime_type.split('/')[-1] if '/' in mime_type else 'jpg'
            filename = f"whatsapp_image_{url_hash}.{ext}"
            file_path = tmp_dir / filename
            
            # Check if already downloaded
            if file_path.exists():
                logger.debug(f"Using cached WhatsApp image: {file_path}")
                with open(file_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            
            # Download the image
            logger.debug(f"Downloading WhatsApp image from: {image_url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    
                    # Save to file
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Convert to base64
                    base64_data = base64.b64encode(response.content).decode('utf-8')
                    logger.debug(f"Successfully downloaded and cached WhatsApp image ({len(response.content)} bytes)")
                    return base64_data
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error downloading WhatsApp image: {e.response.status_code}")
                    return None
                except Exception as e:
                    logger.warning(f"Error downloading WhatsApp image: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to download WhatsApp image: {e}")
            return None
    
    async def _process_multimodal_input(self, input_text: str, multimodal_content: Optional[Dict]) -> Union[str, List[Any]]:
        """Process multimodal content for framework input."""
        if not multimodal_content:
            return input_text
            
        # Check if we're using Agno framework - it needs different format
        if self.framework_type == "agno":
            return self._process_multimodal_input_for_agno(input_text, multimodal_content)
            
        try:
            # Import multimodal types for PydanticAI
            from pydantic_ai import ImageUrl, AudioUrl, DocumentUrl, BinaryContent
            
            # Build multimodal input list
            input_list = [input_text] if input_text else []
            
            logger.debug(f"Processing multimodal content: {type(multimodal_content)}, keys: {multimodal_content.keys() if isinstance(multimodal_content, dict) else 'N/A'}")
            
            # Process images
            if isinstance(multimodal_content, dict) and "images" in multimodal_content:
                images = multimodal_content.get("images", [])
                for image_data in images:
                    if hasattr(image_data, 'url'):  # Already a pydantic-ai object
                        input_list.append(image_data)
                    elif isinstance(image_data, dict):
                        data_content = image_data.get("data")
                        # Support both mime_type and media_type for backward compatibility
                        raw_mime_type = image_data.get("media_type") or image_data.get("mime_type", "")
                        
                        # Validate and normalize MIME type with fallback
                        mime_type = self._validate_mime_type(raw_mime_type)
                        
                        if isinstance(data_content, str) and mime_type.startswith("image/"):
                            if data_content.lower().startswith("http"):
                                # Check if this is a WhatsApp URL that might cause issues
                                if "whatsapp.net" in data_content:
                                    # Try to download the image and convert to base64
                                    try:
                                        downloaded_base64 = await self._download_whatsapp_image(data_content, mime_type)
                                        if downloaded_base64:
                                            # Use the downloaded base64 instead of the URL
                                            data_content = downloaded_base64
                                            logger.debug("Successfully downloaded WhatsApp image, using base64 data")
                                        else:
                                            # Fallback to URL if download fails
                                            input_list.append(ImageUrl(url=data_content))
                                            continue
                                    except Exception as download_error:
                                        logger.warning(f"Failed to download WhatsApp image: {download_error}")
                                        # Fallback to URL if download fails
                                        input_list.append(ImageUrl(url=data_content))
                                        continue
                                else:
                                    input_list.append(ImageUrl(url=data_content))
                            else:
                                # Handle base64 image data properly
                                import base64
                                import re
                                
                                # Remove data URL prefix if present
                                if data_content.startswith('data:'):
                                    data_content = data_content.split(',')[1]
                                
                                # Clean base64 string
                                data_content = re.sub(r'[^A-Za-z0-9+/=]', '', data_content)
                                
                                try:
                                    binary_data = base64.b64decode(data_content)
                                    # Validate binary data size
                                    if len(binary_data) == 0:
                                        raise ValueError("Decoded binary data is empty")
                                    
                                    input_list.append(BinaryContent(
                                        data=binary_data,
                                        media_type=mime_type
                                    ))
                                    logger.debug(f"Converted base64 image to BinaryContent: {len(binary_data)} bytes, MIME: {mime_type}")
                                except (base64.binascii.Error, ValueError) as decode_error:
                                    logger.error(f"Failed to decode base64 image data: {decode_error}")
                                    # Try fallback with ImageUrl if it looks like a URL
                                    if data_content.lower().startswith('http'):
                                        try:
                                            input_list.append(ImageUrl(url=data_content))
                                            logger.debug("Fallback: Using ImageUrl for URL-like data")
                                        except Exception as url_error:
                                            logger.error(f"Fallback ImageUrl failed: {url_error}")
                                            input_list.append(image_data)
                                    else:
                                        # Final fallback: keep original data
                                        input_list.append(image_data)
                                except Exception as content_error:
                                    logger.error(f"Failed to create BinaryContent: {type(content_error).__name__}: {content_error}")
                                    logger.debug(f"Error details - mime_type: {mime_type}, data length: {len(data_content) if data_content else 0}")
                                    # Try with default MIME type
                                    try:
                                        binary_data = base64.b64decode(data_content)
                                        input_list.append(BinaryContent(
                                            data=binary_data,
                                            media_type="image/jpeg"  # Final fallback MIME type
                                        ))
                                        logger.debug("Fallback: Created BinaryContent with default MIME type")
                                    except Exception as final_error:
                                        logger.error(f"All BinaryContent creation attempts failed: {final_error}")
                                        input_list.append(image_data)
            
            # Process audio
            if isinstance(multimodal_content, dict) and "audio" in multimodal_content:
                audio_files = multimodal_content.get("audio", [])
                for audio_data in audio_files:
                    if hasattr(audio_data, 'url'):  # Already a pydantic-ai AudioUrl object
                        input_list.append(audio_data)
                    elif isinstance(audio_data, dict):
                        if "url" in audio_data:
                            input_list.append(AudioUrl(url=audio_data["url"]))
                        elif "data" in audio_data and ("media_type" in audio_data or "mime_type" in audio_data):
                            # Handle base64 data properly
                            data_content = audio_data["data"]
                            if isinstance(data_content, str):
                                # Decode base64 data to bytes for BinaryContent
                                import base64
                                import re
                                
                                # Remove data URL prefix if present
                                if data_content.startswith('data:'):
                                    data_content = data_content.split(',')[1]
                                
                                # Clean base64 string
                                data_content = re.sub(r'[^A-Za-z0-9+/=]', '', data_content)
                                
                                try:
                                    binary_data = base64.b64decode(data_content)
                                    input_list.append(BinaryContent(
                                        data=binary_data,
                                        media_type=audio_data.get("media_type") or audio_data.get("mime_type")
                                    ))
                                    logger.debug(f"Converted base64 audio to BinaryContent: {len(binary_data)} bytes")
                                except Exception as decode_error:
                                    logger.error(f"Failed to decode base64 audio data: {decode_error}")
                            else:
                                # Assume it's already binary data
                                input_list.append(BinaryContent(
                                    data=data_content,
                                    media_type=audio_data.get("media_type") or audio_data.get("mime_type")
                                ))
            
            # Process documents
            if isinstance(multimodal_content, dict) and "documents" in multimodal_content:
                documents = multimodal_content.get("documents", [])
                for doc_data in documents:
                    if hasattr(doc_data, 'url'):  # Already a pydantic-ai object
                        input_list.append(doc_data)
                    elif isinstance(doc_data, dict):
                        if "url" in doc_data:
                            input_list.append(DocumentUrl(url=doc_data["url"]))
                        elif "data" in doc_data and ("media_type" in doc_data or "mime_type" in doc_data):
                            # Handle base64 data properly
                            data_content = doc_data["data"]
                            if isinstance(data_content, str):
                                # Decode base64 data to bytes for BinaryContent
                                import base64
                                import re
                                
                                # Remove data URL prefix if present
                                if data_content.startswith('data:'):
                                    data_content = data_content.split(',')[1]
                                
                                # Clean base64 string
                                data_content = re.sub(r'[^A-Za-z0-9+/=]', '', data_content)
                                
                                try:
                                    binary_data = base64.b64decode(data_content)
                                    input_list.append(BinaryContent(
                                        data=binary_data,
                                        media_type=doc_data.get("media_type") or doc_data.get("mime_type")
                                    ))
                                    logger.debug(f"Converted base64 document to BinaryContent: {doc_data.get('name', 'unnamed')} ({len(binary_data)} bytes)")
                                except Exception as decode_error:
                                    logger.error(f"Failed to decode base64 document data: {decode_error}")
                            else:
                                # Assume it's already binary data
                                input_list.append(BinaryContent(
                                    data=data_content,
                                    media_type=doc_data.get("media_type") or doc_data.get("mime_type")
                                ))
                        
            # Return input_list if we have multimodal content, otherwise return text
            if len(input_list) > 1 or (len(input_list) == 1 and not isinstance(input_list[0], str)):
                return input_list
            else:
                return input_text or ""
            
        except Exception as e:
            logger.warning(f"Error processing multimodal content: {e}")
            return input_text
    
    def _add_system_message_to_history(self, message_history: List[Dict], system_prompt: str) -> List[Dict]:
        """Add system message to history if not present."""
        if not message_history:
            return [{"role": "system", "content": system_prompt}]
            
        # Check if system message already exists
        if message_history:
            first_message = message_history[0]
            # Handle both PydanticAI ModelMessage objects and dictionary messages
            if hasattr(first_message, 'parts'):
                # This is a PydanticAI ModelMessage - check if it's a system message
                from pydantic_ai.messages import SystemPromptPart
                if first_message.parts and isinstance(first_message.parts[0], SystemPromptPart):
                    return message_history
            elif isinstance(first_message, dict) and first_message.get("role") == "system":
                # This is a dictionary message
                return message_history
            
        # Prepend system message
        return [{"role": "system", "content": system_prompt}] + message_history
    
    async def _store_user_info_in_memory(self, user_name: Optional[str], user_number: Optional[str]) -> None:
        """Store user information in memory for template variables."""
        try:
            from automagik.db.models import Memory
            from automagik.db.repository import create_memory
            
            info_dict = {}
            if user_name:
                info_dict["user_name"] = user_name
            if user_number:
                info_dict["user_number"] = user_number
                
            if info_dict:
                memory = Memory(
                    name="user_information",
                    content=str(info_dict),
                    user_id=self.context.get("user_id"),
                    agent_id=self.db_id,
                    read_mode="system_prompt",
                    access="read_write",
                )
                create_memory(memory=memory)
                
        except Exception as e:
            logger.error(f"Error storing user info in memory: {e}")
    
    def set_dependencies(self, dependencies: T) -> None:
        """Set the agent dependencies.
        
        Args:
            dependencies: Agent dependencies instance
        """
        self.dependencies = dependencies
        logger.debug(f"Set dependencies for {self.name}")
    
    def register_tool(self, tool_func):
        """Register a tool with the agent."""
        if not hasattr(self, 'tool_registry'):
            self.tool_registry = ToolRegistry()
            
        self.tool_registry.register_tool(tool_func)
        logger.debug(f"Registered tool: {getattr(tool_func, '__name__', 'unknown')}")
    
    def update_context(self, context_updates: Dict[str, Any]) -> None:
        """Update the agent's context."""
        self.context.update(context_updates)
        
        # Update tool registry with new context if it exists
        if hasattr(self, 'tool_registry') and self.tool_registry is not None:
            self.tool_registry.update_context(self.context)
            
        logger.debug(f"Updated agent context: {list(context_updates.keys())}")
    
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """Update the agent's configuration."""
        if isinstance(self.config, AgentConfig):
            self.config.update(config_updates)
        else:
            self.config = AgentConfig(config_updates)
            
        # Update framework config if needed
        if self.ai_framework and config_updates:
            self.ai_framework.update_config(config_updates)
            
        logger.debug(f"Updated agent config: {list(config_updates.keys())}")
    
    async def get_filled_system_prompt(self, user_id: Optional[uuid.UUID] = None) -> str:
        """Get the system prompt filled with memory variables."""
        # Check if there's a system_prompt override in the context
        if self.context and 'system_prompt' in self.context:
            prompt_template = self.context['system_prompt']
        elif self.current_prompt_template:
            prompt_template = self.current_prompt_template
        else:
            logger.error("No prompt template available")
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
    
    async def fetch_memory_variables(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Fetch memory variables for the agent."""
        if not self.db_id or not self.template_vars:
            logger.warning("Cannot fetch memory: No agent ID or template variables")
            return {}
            
        try:
            memory_vars = await MemoryHandler.fetch_memory_vars(
                template_vars=self.template_vars,
                agent_id=self.db_id,
                user_id=user_id
            )
            
            logger.debug(f"Fetched {len(memory_vars)} memory variables for agent ID {self.db_id}")
            return memory_vars
        except Exception as e:
            logger.error(f"Error fetching memory variables: {str(e)}")
            return {}
    
    async def run(self, input_text: str, *, multimodal_content=None, 
                 system_message=None, message_history_obj=None,
                 channel_payload: Optional[Dict] = None,
                 message_limit: Optional[int] = None) -> AgentResponse:
        """Run the agent with the given input.
        
        Default implementation uses the framework to handle all complexity.
        Agents can override this if they need custom behavior.
        """
        return await self._run_agent(
            input_text=input_text,
            system_prompt=system_message,
            message_history=message_history_obj.get_formatted_pydantic_messages(limit=message_limit or 20) if message_history_obj else [],
            multimodal_content=multimodal_content,
            channel_payload=channel_payload
        )
    
    async def cleanup(self) -> None:
        """Clean up resources used by the agent."""
        if self.dependencies and hasattr(self.dependencies, 'http_client'):
            await close_http_client(self.dependencies.http_client)
            
        if self.ai_framework:
            await self.ai_framework.cleanup()
            
        logger.debug(f"Cleaned up {self.name} agent")
    
    # Backward compatibility methods for existing agents and tests
    async def process_message(self, user_message: Union[str, Dict[str, Any]], 
                              session_id: Optional[str] = None, 
                              agent_id: Optional[Union[int, str]] = None, 
                              user_id: Optional[Union[uuid.UUID, str]] = None, 
                              context: Optional[Dict] = None, 
                              message_history: Optional[Any] = None,
                              channel_payload: Optional[Dict] = None,
                              message_limit: Optional[int] = None) -> AgentResponse:
        """Process a user message - backward compatibility method."""
        from automagik.agents.common.message_parser import parse_user_message
        from automagik.agents.common.session_manager import create_context, validate_agent_id, validate_user_id, extract_multimodal_content

        # Parse the user message
        content, _ = parse_user_message(user_message)
            
        # Update agent ID and user ID
        if agent_id is not None:
            self.db_id = validate_agent_id(agent_id)
            if self.dependencies:
                self.dependencies.set_agent_id(self.db_id)
        
        if self.dependencies:
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
            from automagik.agents.common.message_parser import format_message_for_db
            
            # Save user message
            user_db_message = format_message_for_db(role="user", content=content, agent_id=self.db_id, channel_payload=channel_payload)
            message_history.add_message(message=user_db_message)
            
            # Save agent response
            agent_db_message = format_message_for_db(
                role="assistant", 
                content=response.text,
                tool_calls=getattr(response, 'tool_calls', None),
                tool_outputs=getattr(response, 'tool_outputs', None),
                system_prompt=getattr(response, "system_prompt", None),
                usage=getattr(response, 'usage', None),
                agent_id=self.db_id
            )
            message_history.add_message(agent_db_message)
        
        return response
    
    async def initialize_prompts(self) -> bool:
        """Initialize agent prompts during server startup."""
        # If multi-prompt enabled, delegate to manager.
        if getattr(self, "enable_multi_prompt", False) and self.prompt_manager:
            try:
                await self.prompt_manager.register_all_prompts()
                return True
            except Exception as exc:
                logger.error(f"Multi-prompt registration failed: {exc}")
                return False

        # Check if the agent has the required attributes (single-prompt path)
        has_prompt_text = hasattr(self, '_code_prompt_text') and self._code_prompt_text is not None
        has_registration_flag = hasattr(self, '_prompt_registered')
        
        if not has_prompt_text:
            # ClaudeCodeAgent uses workflow-based prompts, so this is expected
            # Also skip logging for PlaceholderAgent when it's a disabled claude-code
            if self.__class__.__name__ == "ClaudeCodeAgent":
                pass  # Expected - uses workflow prompts
            elif self.__class__.__name__ == "PlaceholderAgent" and hasattr(self, 'name') and "claude-code" in str(getattr(self, 'name', '')):
                pass  # Expected - disabled claude-code placeholder
            else:
                logger.info(f"No _code_prompt_text found for {self.__class__.__name__}, skipping prompt registration")
            return True
            
        if not has_registration_flag:
            self._prompt_registered = False
            
        return await self._check_and_register_prompt()
    
    async def _check_and_register_prompt(self) -> bool:
        """Check if prompt needs registration and register it if needed."""
        if not hasattr(self, '_prompt_registered') or not self._prompt_registered:
            if hasattr(self, '_code_prompt_text') and self.db_id:
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
                        await self.load_active_prompt_template(status_key="default")
                        logger.info(f"Successfully registered and loaded {agent_name} prompt")
                        return True
                    else:
                        logger.warning(f"Failed to register {agent_name} prompt")
                        return False
                except Exception as e:
                    logger.error(f"Error registering prompt: {str(e)}")
                    return False
        return True
    
    async def _register_code_defined_prompt(self, 
                                         code_prompt_text: str, 
                                         status_key: str = "default", 
                                         prompt_name: Optional[str] = None, 
                                         is_primary_default: bool = False) -> Optional[int]:
        """Register a prompt defined in code for this agent."""
        if not self.db_id:
            logger.warning("Cannot register prompt: Agent ID is not set")
            return None
            
        try:
            from automagik.db.repository.prompt import find_code_default_prompt, create_prompt, update_prompt as _update_prompt, set_prompt_active
            from automagik.db.models import PromptCreate, PromptUpdate
            
            # Check if a prompt with is_default_from_code=True exists
            existing_prompt = find_code_default_prompt(self.db_id, status_key)
            
            if existing_prompt:
                logger.info(f"Found existing code-defined prompt for agent {self.db_id}")
                
                # Update the prompt text to ensure code and DB stay in sync
                try:
                    update_success = _update_prompt(
                        existing_prompt.id,
                        PromptUpdate(prompt_text=code_prompt_text)
                    )
                    if update_success:
                        logger.info(f"Updated prompt text for existing code-defined prompt {existing_prompt.id}")
                    else:
                        logger.warning(f"Failed to update prompt text for existing code-defined prompt {existing_prompt.id}")
                except Exception as e:
                    logger.error(f"Error updating existing prompt: {str(e)}")

                # If is_primary_default is True and the prompt is not already active, set it as active
                if is_primary_default and not existing_prompt.is_active:
                    set_prompt_active(existing_prompt.id, True)
                    logger.info(f"Set existing prompt {existing_prompt.id} as active")
                
                return existing_prompt.id
                
            # No existing prompt found, create a new one
            if not prompt_name:
                prompt_name = f"{self.name} {status_key} Prompt"
                
            prompt_data = PromptCreate(
                agent_id=self.db_id,
                prompt_text=code_prompt_text,
                version=1,
                is_active=is_primary_default,
                is_default_from_code=True,
                status_key=status_key,
                name=prompt_name
            )
            
            prompt_id = create_prompt(prompt_data)
            
            if prompt_id:
                logger.info(f"Registered new code-defined prompt for agent {self.db_id}")
                return prompt_id
            else:
                logger.error(f"Failed to create code-defined prompt for agent {self.db_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error registering code-defined prompt: {str(e)}")
            return None
    
    async def load_active_prompt_template(self, status_key: str = "default") -> bool:
        """Load the active prompt template for the given status key."""
        if not self.db_id:
            logger.warning("Cannot load prompt template: Agent ID is not set")
            return False
            
        try:
            # Import locally to avoid module-level import issues
            try:
                from automagik.db.repository.prompt import get_active_prompt as local_get_active_prompt
            except ImportError:
                logger.error("get_active_prompt function not available")
                return False
                
            active_prompt = local_get_active_prompt(self.db_id, status_key)
            
            if not active_prompt:
                if status_key != "default":
                    logger.warning(f"No active prompt found for agent {self.db_id}, status {status_key}. Trying default.")
                    active_prompt = local_get_active_prompt(self.db_id, "default")
                    
                if not active_prompt:
                    logger.error(f"No active prompt found for agent {self.db_id}")
                    return False
            
            self.current_prompt_template = active_prompt.prompt_text
            self.template_vars = PromptBuilder.extract_template_variables(self.current_prompt_template)
            
            logger.info(f"Loaded active prompt for agent {self.db_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading active prompt template: {str(e)}")
            return False
    
    async def initialize_memory_variables(self, user_id: Optional[int] = None) -> bool:
        """Initialize memory variables for the agent."""
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
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):  # type: ignore
        """Async context manager exit."""
        await self.cleanup()
    
    # Legacy method compatibility for tests
    async def _initialize_pydantic_agent(self):
        """Legacy method for backward compatibility - now handled by framework."""
        if not self._framework_initialized and self.dependencies:
            return await self.initialize_framework(type(self.dependencies))
        return True
    
    def _create_send_reaction_wrapper(self):
        """Legacy method for backward compatibility - creates reaction sending wrapper."""
        async def send_reaction(ctx, emoji: str = "👍"):
            """Send a reaction emoji to a message in the current conversation.
            
            Args:
                ctx: Context containing evolution payload
                emoji: The emoji to send as reaction
                
            Returns:
                Dictionary with success status and result
            """
            try:
                # Get evolution payload from context
                evolution_payload = ctx.deps.context.get("evolution_payload") if hasattr(ctx, 'deps') else None
                if not evolution_payload:
                    return {"success": False, "error": "No evolution payload available"}
                
                # Import and call the evolution API
                from automagik.tools.evolution.api import send_reaction as api_send_reaction
                result = await api_send_reaction(
                    evolution_payload.server_url,
                    evolution_payload.apikey,
                    evolution_payload.instance,
                    evolution_payload.data.key.remoteJid,
                    evolution_payload.data.key.id,
                    emoji
                )
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Error in send_reaction wrapper: {e}")
                return {"success": False, "error": str(e)}
                
        send_reaction.__name__ = "send_reaction"
        return send_reaction
    
    def _create_send_text_wrapper(self):
        """Legacy method for backward compatibility - creates text sending wrapper."""
        async def send_text_to_user(ctx, message: str):
            """Send a text message to the user in the current conversation.
            
            Args:
                ctx: Context containing evolution payload  
                message: The text message to send
                
            Returns:
                Dictionary with success status and result
            """
            try:
                # Get evolution payload from context
                evolution_payload = ctx.deps.context.get("evolution_payload") if hasattr(ctx, 'deps') else None
                if not evolution_payload:
                    return {"success": False, "error": "No evolution payload available"}
                
                # Send message via HTTP request to Evolution API
                import aiohttp
                
                url = f"{evolution_payload.server_url}/message/sendText/{evolution_payload.instance}"
                headers = {
                    "apikey": evolution_payload.apikey,
                    "Content-Type": "application/json"
                }
                data = {
                    "number": evolution_payload.get_user_number(),
                    "text": message
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        return {"success": True, "result": result}
                        
            except Exception as e:
                return {"success": False, "error": str(e)}
                
        send_text_to_user.__name__ = "send_text_to_user"
        return send_text_to_user
    
    def _convert_image_payload_to_pydantic(self, image_data):
        """Legacy method for backward compatibility - now handled by framework."""
        # This is now handled in _process_multimodal_input
        return self._process_multimodal_input("", {"images": [image_data]})
    
    async def _initialize_agent(self):
        """Legacy method for backward compatibility."""
        return await self._initialize_pydantic_agent()
    
    async def _load_mcp_servers(self):
        """Legacy method for backward compatibility - now handled by framework."""
        if self.ai_framework and hasattr(self.ai_framework, '_load_mcp_servers'):
            return await self.ai_framework._load_mcp_servers()
        return []
    
    @property
    def _agent_instance(self):
        """Legacy property for backward compatibility."""
        if hasattr(self, '_mock_agent_instance'):
            return self._mock_agent_instance
        return getattr(self.ai_framework, '_agent_instance', None) if self.ai_framework else None
    
    @_agent_instance.setter
    def _agent_instance(self, value):
        """Allow setting _agent_instance for testing."""
        self._mock_agent_instance = value
    
    @_agent_instance.deleter
    def _agent_instance(self):
        """Allow deleting _agent_instance for testing."""
        if hasattr(self, '_mock_agent_instance'):
            delattr(self, '_mock_agent_instance')


    def _is_vision_capable_model(self, model_name: str) -> bool:
        """Check if a model is vision-capable.
        
        Args:
            model_name: The model name to check
            
        Returns:
            True if the model can handle vision/multimodal content
        """
        if not model_name:
            return False
            
        model_lower = model_name.lower()
        vision_indicators = [
            "vision", "gpt-4o", "gpt-4-vision", 
            "gemini-2.5-pro", "gemini-2.5-flash",  # Gemini models are vision-capable
            "gemini-pro-vision", "gemini-flash-vision",  # Explicit vision variants
            "claude-3", "claude-sonnet", "claude-haiku",  # Claude 3 models
            "claude-3.5-sonnet", "claude-3.5-haiku",  # Claude 3.5 models
            "multimodal", "vision-preview"  # Generic indicators
        ]
        
        return any(indicator in model_lower for indicator in vision_indicators)

    # Helper: append media context information to a system prompt.
    def _enhance_system_prompt(self, prompt: str, mc: Dict) -> str:
        """Return prompt appended with information about attached media."""
        try:
            if not mc or not any(mc.values()):
                return prompt or ""

            enhancement = "\n\nYou have access to analyze the following media types in this conversation:"

            if mc.get("images"):
                enhancement += "\n- Images: You can see and analyze visual content"
            if mc.get("audio"):
                enhancement += "\n- Audio: You can process audio content"
            if mc.get("documents"):
                enhancement += "\n- Documents: You can read and analyze documents"

            return (prompt or "") + enhancement
        except Exception as e:
            logger.warning(f"Failed to enhance system prompt: {e}")
            return prompt or ""

    async def load_prompt_by_status(self, status: str) -> bool:
        """Load a prompt by status (multi-prompt mode), fallback to single-prompt."""
        if getattr(self, "enable_multi_prompt", False) and self.prompt_manager:
            return await self.prompt_manager.load_prompt_by_status(status)

        # Single-prompt behaviour: just load active template for given status key
        return await self.load_active_prompt_template(status_key=str(status))

    def _create_enhanced_trace(self, processed_input, result, message_history, system_prompt, multimodal_content, kwargs):
        """Create enhanced LangWatch trace following best practices for agent observability."""
        import time
        import uuid
        
        # Generate unique IDs for this trace with proper hierarchy
        trace_id = str(uuid.uuid4())
        run_id = kwargs.get("run_id", str(uuid.uuid4()))
        session_id = kwargs.get("session_id", self.context.get("session_id"))
        
        # Create span IDs for proper hierarchy
        root_span_id = str(uuid.uuid4())
        config_span_id = str(uuid.uuid4())
        input_span_id = str(uuid.uuid4())
        llm_span_id = str(uuid.uuid4())
        output_span_id = str(uuid.uuid4())
        
        for provider_name, provider in self.tracing.observability.providers.items():
            try:
                logger.debug(f"Creating enhanced trace for {provider_name}")
                
                # 1. Start the main agent execution trace
                provider.start_trace(
                    trace_id=trace_id,
                    span_id=root_span_id,
                    name=f"Agent: {self.name}",
                    input_text=processed_input,
                    metadata={
                        "user_id": kwargs.get("user_id", self.context.get("user_id")),
                        "thread_id": session_id,  # LangWatch uses thread_id for conversations
                        "agent_name": self.name,
                        "agent_id": self.db_id,
                        "framework": self.framework_type,
                        "run_id": run_id,
                        "session_origin": kwargs.get("session_origin", "automagik"),
                        "multimodal": bool(multimodal_content),
                        "message_type": kwargs.get("message_type", "text")
                    }
                )
                
                # 2. Log agent configuration as a child span
                provider.log_agent_config(
                    trace_id=trace_id,
                    span_id=config_span_id,
                    parent_span_id=root_span_id,
                    agent_name=self.name,
                    model=self.config.model,
                    system_prompt=system_prompt,
                    memory_variables=getattr(self, 'memory_variables', {}),
                    framework=self.framework_type
                )
                
                # 3. Log input processing span as child
                provider.log_input_processing(
                    trace_id=trace_id,
                    span_id=input_span_id,
                    parent_span_id=root_span_id,
                    raw_input=processed_input,
                    processed_input=processed_input,
                    message_history=message_history,
                    multimodal_content=multimodal_content
                )
                
                # 4. Log the main LLM execution as child
                full_messages = self._build_conversation_messages(message_history, system_prompt, processed_input)
                provider.log_llm_call(
                    model=self.config.model,
                    messages=full_messages,
                    response=result.text if hasattr(result, 'text') else str(result),
                    usage=result.usage if hasattr(result, 'usage') and result.usage else {},
                    trace_id=trace_id,
                    span_id=llm_span_id,
                    parent_span_id=root_span_id
                )
                
                # 5. Log tool executions as children of LLM span
                if hasattr(result, 'tool_calls') and result.tool_calls:
                    for tool_call in result.tool_calls:
                        if isinstance(tool_call, dict):
                            provider.log_tool_call(
                                tool_name=tool_call.get("name", "unknown"),
                                args=tool_call.get("args", {}),
                                result=tool_call.get("result", ""),
                                trace_id=trace_id,
                                parent_span_id=llm_span_id  # Tools are children of LLM
                            )
                
                # 6. Log output generation span as child
                provider.log_output_generation(
                    trace_id=trace_id,
                    span_id=output_span_id,
                    parent_span_id=root_span_id,
                    raw_output=str(result),
                    final_output=result.text if hasattr(result, 'text') else str(result),
                    tool_calls=getattr(result, 'tool_calls', []),
                    usage=getattr(result, 'usage', {})
                )
                
                # 7. Complete the trace
                provider.complete_trace(
                    trace_id=trace_id,
                    final_output=result.text if hasattr(result, 'text') else str(result)
                )
                
            except Exception as e:
                logger.error(f"Failed to create enhanced trace for {provider_name}: {e}")
    
    def _build_conversation_messages(self, message_history, system_prompt, current_input):
        """Build complete conversation message array for tracing."""
        messages = []
        
        # Add message history if available (which already includes system prompt)
        if message_history:
            for msg in message_history:
                if isinstance(msg, dict):
                    messages.append(msg)
        else:
            # Only add system prompt if no message history
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
        
        # Add current user input
        messages.append({"role": "user", "content": current_input})
        
        return messages