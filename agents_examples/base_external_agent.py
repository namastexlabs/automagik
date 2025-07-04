"""Base class for external agents with simplified initialization.

This base class reduces boilerplate for external agents by:
1. Automatically registering external API keys
2. Setting up common dependencies
3. Providing hooks for customization
"""
import os
import logging
from typing import Dict, Optional, List, Tuple
from abc import abstractmethod

from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies
from automagik.config import get_settings

logger = logging.getLogger(__name__)


class BaseExternalAgent(AutomagikAgent):
    """Base class for external agents with common functionality."""
    
    # Override these in subclasses
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    SUPPORTED_MEDIA = ["image", "audio", "document"]
    EXTERNAL_API_KEYS: List[Tuple[str, str]] = []  # List of (key_name, description)
    EXTERNAL_URLS: List[Tuple[str, str]] = []      # List of (url_name, description)
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize external agent with automatic setup."""
        config = config or {}
        
        # Apply default configurations
        config.setdefault("supported_media", self.SUPPORTED_MEDIA)
        config.setdefault("auto_enhance_prompts", True)
        config.setdefault("enable_multi_prompt", True)
        
        super().__init__(config)
        
        # Register external API keys and URLs
        self._register_external_keys()
        
        # Setup dependencies
        self._setup_dependencies()
        
        # Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Call agent-specific initialization
        self._initialize_agent()
        
        logger.info(f"{self.__class__.__name__} initialized successfully")
    
    def _register_external_keys(self) -> None:
        """Register external API keys and URLs with the settings system."""
        settings = get_settings()
        
        # Register API keys
        for key_name, description in self.EXTERNAL_API_KEYS:
            value = os.environ.get(key_name)
            if value:
                settings.add_external_api_key(key_name, value, description)
                logger.debug(f"Registered external API key: {key_name}")
            else:
                logger.warning(f"External API key {key_name} not found in environment")
        
        # Register URLs
        for url_name, description in self.EXTERNAL_URLS:
            value = os.environ.get(url_name)
            if value:
                settings.add_external_url(url_name, value, description)
                logger.debug(f"Registered external URL: {url_name}")
            else:
                logger.warning(f"External URL {url_name} not found in environment")
    
    def _setup_dependencies(self) -> None:
        """Setup agent dependencies with default model."""
        # Get the primary LLM provider's API key
        api_key_mapping = self._get_api_key_mapping()
        
        self.dependencies = AutomagikAgentsDependencies(
            model_name=self.DEFAULT_MODEL,
            model_settings={
                "temperature": 0.7,
                "max_tokens": 4096
            },
            api_keys=api_key_mapping,
            tool_config={}
        )
        
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
    
    def _get_api_key_mapping(self) -> Dict[str, str]:
        """Get API key mapping based on the default model provider."""
        provider = self.DEFAULT_MODEL.split(":")[0]
        
        key_mappings = {
            "openai": {"openai_api_key": os.environ.get("OPENAI_API_KEY", "")},
            "google": {"google_api_key": os.environ.get("GEMINI_API_KEY", "")},
            "anthropic": {"anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", "")},
        }
        
        return key_mappings.get(provider, {})
    
    @abstractmethod
    def _initialize_agent(self) -> None:
        """Initialize agent-specific functionality.
        
        Override this method to:
        - Set self._code_prompt_text
        - Register custom tools
        - Initialize agent-specific components
        """
        pass
    
    def register_tools_from_module(self, module) -> None:
        """Register all tools from a module automatically.
        
        Args:
            module: Module containing tool functions
            
        Example:
            from tools import flashed
            self.register_tools_from_module(flashed)
        """
        import inspect
        
        registered = 0
        for name, obj in inspect.getmembers(module):
            if inspect.iscoroutinefunction(obj) and not name.startswith('_'):
                # Skip internal functions and imports
                if hasattr(obj, '__module__') and obj.__module__ == module.__name__:
                    self.tool_registry.register_tool(obj)
                    registered += 1
        
        logger.debug(f"Auto-registered {registered} tools from {module.__name__}")