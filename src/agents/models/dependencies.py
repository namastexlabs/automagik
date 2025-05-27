"""Dependency models for agent implementations.

This module provides typed dependencies for all agents in the system,
following pydantic-ai best practices for dependency injection.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Union
import logging
from datetime import datetime

# Import constants
from src.constants import (
    DEFAULT_MODEL
)

# Import httpx for typed HTTP client if available
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    # Create a placeholder class
    class httpx:
        class AsyncClient:
            pass

# Import pydantic-ai types if available
try:
    from pydantic_ai.tools import RunContext
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.usage import UsageLimits
    from pydantic_ai.settings import ModelSettings
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    # Create placeholder types for better error handling
    class RunContext:
        pass
    class ModelMessage:
        pass
    class UsageLimits:
        pass
    class ModelSettings:
        pass

logger = logging.getLogger(__name__)

@dataclass
class BaseDependencies:
    """Base dependencies shared by all agents.
    
    This class provides core functionality needed by any agent type,
    including memory management, user context, and configuration.
    """
    # Context properties
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    
    # Configuration
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # Database connection (optional, can be None for tests)
    db_connection: Any = None
    
    # Private fields (not part of the initializer)
    _agent_id_numeric: Optional[int] = field(default=None, init=False)
    
    # Memory provider (initialized lazily)
    _memory_provider: Optional[Any] = field(default=None, init=False)
    
    @property
    def memory_provider(self) -> Any:
        """Get the memory provider for this agent.
        
        Returns:
            MemoryProvider instance
        """
        if self._memory_provider is None and self._agent_id_numeric:
            from src.tools.memory_tools.provider import MemoryProvider
            self._memory_provider = MemoryProvider(self._agent_id_numeric)
            logger.debug(f"Created memory provider for agent {self._agent_id_numeric}")
        
        if self._memory_provider is None:
            # Create a fallback provider if agent ID isn't set
            from src.tools.memory_tools.provider import MemoryProvider
            self._memory_provider = MemoryProvider(999)
            logger.warning("Created fallback memory provider with agent ID 999")
        
        return self._memory_provider
    
    def set_agent_id(self, agent_id: int) -> None:
        """Set the agent ID for database operations.
        
        Args:
            agent_id: Numeric ID of the agent in the database
        """
        self._agent_id_numeric = agent_id
        # Reset memory provider to use new agent ID
        self._memory_provider = None
        logger.debug(f"Set agent ID to {agent_id} for dependency object")
    
    async def get_memory(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch memory from database by name.
        
        Args:
            name: Name of the memory to retrieve
            
        Returns:
            Memory object or None if not found
        """
        from src.db import get_memory_by_name
        try:
            if not self._agent_id_numeric:
                logger.warning(f"Agent ID not set for memory retrieval: {name}")
                return None
                
            memory = get_memory_by_name(name, agent_id=self._agent_id_numeric)
            if memory:
                return {
                    "id": str(memory.id),
                    "name": memory.name,
                    "description": memory.description,
                    "content": memory.content,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at
                }
            return None
        except Exception as e:
            logger.error(f"Error in get_memory({name}): {str(e)}")
            return None
    
    async def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories for this agent.
        
        Returns:
            List of all memory objects for this agent
        """
        from src.db import list_memories
        try:
            if not self._agent_id_numeric:
                logger.warning("Agent ID not set for memory listing")
                return []
                
            memories = list_memories(agent_id=self._agent_id_numeric)
            return [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "description": m.description,
                    "content": m.content if hasattr(m, "content") else None
                }
                for m in memories
            ]
        except Exception as e:
            logger.error(f"Error in get_all_memories: {str(e)}")
            return []
    
    async def store_memory(self, 
                          name: str, 
                          content: Union[str, Dict[str, Any]], 
                          description: Optional[str] = None) -> Dict[str, Any]:
        """Store a memory in the database.
        
        Args:
            name: Name of the memory to store
            content: Content to store (string or JSON-serializable dict)
            description: Optional description of the memory
            
        Returns:
            Result of the operation with success status
        """
        from src.db import get_memory_by_name, update_memory, create_memory
        try:
            if not self._agent_id_numeric:
                return {"success": False, "error": "Agent ID not set"}
                
            existing = get_memory_by_name(name, agent_id=self._agent_id_numeric)
            
            if existing:
                memory = update_memory({
                    "id": existing.id,
                    "name": name,
                    "content": content,
                    "description": description or existing.description,
                    "agent_id": self._agent_id_numeric
                })
                # Invalidate memory provider cache
                if self._memory_provider:
                    self._memory_provider.invalidate_cache()
                    
                return {
                    "success": True,
                    "action": "updated",
                    "memory_id": str(memory)
                }
            else:
                memory_data = {
                    "name": name,
                    "content": content,
                    "description": description,
                    "agent_id": self._agent_id_numeric
                }
                memory_id = create_memory(memory_data)
                # Invalidate memory provider cache
                if self._memory_provider:
                    self._memory_provider.invalidate_cache()
                    
                return {
                    "success": True,
                    "action": "created",
                    "memory_id": str(memory_id)
                }
        except Exception as e:
            logger.error(f"Error in store_memory({name}): {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def increment_run_id(self) -> int:
        """Increment and get the run_id for this agent.
        
        Returns:
            The new run_id after incrementing
        """
        from src.db import increment_agent_run_id, get_agent
        try:
            if not self._agent_id_numeric:
                logger.warning("Agent ID not set for run_id increment")
                return 1
                
            increment_agent_run_id(self._agent_id_numeric)
            agent = get_agent(self._agent_id_numeric)
            return agent.run_id if agent and hasattr(agent, "run_id") else 1
        except Exception as e:
            logger.error(f"Error incrementing run_id: {str(e)}")
            return 1
    
    async def get_current_time(self) -> str:
        """Get the current time formatted as a string.
        
        Returns:
            Current time as formatted string
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class AutomagikAgentsDependencies(BaseDependencies):
    """Dependencies for SimpleAgent.
    
    Extends the base dependencies with SimpleAgent-specific
    functionality and data following PydanticAI best practices.
    """
    # Message history for the current conversation - properly typed
    message_history: Optional[List["ModelMessage"]] = None
    
    # Tool-specific configuration
    tool_config: Dict[str, Any] = field(default_factory=dict)
    
    # HTTP client for external API calls
    http_client: Optional[Any] = None  # Type as Any for compatibility
    
    # Model configuration
    model_name: str = DEFAULT_MODEL
    model_settings: Dict[str, Any] = field(default_factory=dict)
    usage_limits: Optional[Any] = None  # Type as Any for compatibility
    
    # Search API keys
    duckduckgo_enabled: bool = False
    tavily_api_key: Optional[str] = None
    
    def get_http_client(self) -> Any:
        """Get or initialize the HTTP client.
        
        Returns:
            Configured HTTP client instance
        """
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available. Install with: pip install httpx")
            return None
            
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30)  # 30 second timeout default
        return self.http_client
    
    async def close_http_client(self) -> None:
        """Close the HTTP client if initialized.
        
        This should be called during cleanup to properly release resources.
        """
        if HTTPX_AVAILABLE and self.http_client is not None:
            await self.http_client.aclose()
            self.http_client = None
    
    def set_message_history(self, message_history: List[Any]) -> None:
        """Set the message history for the agent.
        
        Args:
            message_history: Message history as list of messages
        """
        self.message_history = message_history
    
    def get_message_history(self) -> List[Any]:
        """Get the current message history.
        
        Returns:
            List of model messages or empty list if none
        """
        return self.message_history or []
    
    def clear_message_history(self) -> None:
        """Clear the message history.
        
        This is useful when starting a new conversation.
        """
        self.message_history = None
    
    def enable_duckduckgo_search(self, enabled: bool = True) -> None:
        """Enable or disable DuckDuckGo search functionality.
        
        Args:
            enabled: Whether search should be enabled
        """
        self.duckduckgo_enabled = enabled
    
    def set_tavily_api_key(self, api_key: Optional[str]) -> None:
        """Set the Tavily API key for search.
        
        Args:
            api_key: Tavily API key or None to disable
        """
        self.tavily_api_key = api_key
        
    def is_search_enabled(self) -> bool:
        """Check if any search capability is enabled.
        
        Returns:
            True if either DuckDuckGo or Tavily search is available
        """
        return self.duckduckgo_enabled or self.tavily_api_key is not None
    
    def set_model_settings(self, settings: Dict[str, Any]) -> None:
        """Set model settings for the agent.
        
        Args:
            settings: Dictionary of model settings (temperature, etc.)
        """
        self.model_settings.update(settings)
    
    def set_usage_limits(self, 
                         response_tokens_limit: Optional[int] = None,
                         request_limit: Optional[int] = None,
                         total_tokens_limit: Optional[int] = None) -> None:
        """Set usage limits for the agent.
        
        Args:
            response_tokens_limit: Maximum tokens in response
            request_limit: Maximum number of requests
            total_tokens_limit: Maximum total tokens
        """
        if not PYDANTIC_AI_AVAILABLE:
            logger.warning("pydantic-ai not available, usage limits not applied")
            return
            
        self.usage_limits = UsageLimits(
            response_tokens_limit=response_tokens_limit,
            request_limit=request_limit, 
            total_tokens_limit=total_tokens_limit
        )
    
    async def get_user_preferences(self) -> Dict[str, Any]:
        """Get user preferences from memory if available.
        
        This method fetches user preferences from the agent's memory.
        
        Returns:
            User preferences as a dictionary or empty dict if not found
        """
        prefs = await self.get_memory("user_preferences")
        if prefs and "content" in prefs:
            return prefs["content"] if isinstance(prefs["content"], dict) else {}
        return {}
    
    async def store_user_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Store user preferences in memory.
        
        This method updates or creates user preferences in the agent's memory.
        
        Args:
            preferences: Dictionary of user preferences to store
            
        Returns:
            Dictionary with success status and action performed
        """
        result = await self.store_memory(
            "user_preferences",
            preferences,
            "User preferences and settings"
        )
        return {"success": result.get("success", False), 
                "action": result.get("action", "unknown")}
                
    def configure_for_multimodal(self, enable: bool = True, modality: str = "image") -> None:
        """Configure the agent for multimodal capabilities.
        
        Note: This method doesn't change the model. If the current model doesn't support
        the requested modality, errors will occur naturally when trying to use it.
        
        Args:
            enable: Whether to enable multimodal support
            modality: The modality to support: "image", "audio", or "document"
        """
        # This is now a placeholder method that does nothing
        # We'll let errors occur naturally if the model doesn't support the modality
        pass
        
    def set_user_info(self, user_info: Dict[str, Any]) -> None:
        """Set user information for the current session.
        
        Args:
            user_info: Dictionary with user information including name, phone, etc.
        """
        self.user_info = user_info 
        
    def set_context(self, context: Dict[str, Any]) -> None:
        """Set the context for the agent.
        
        Args:
            context: Dictionary containing the agent's context (user_id, agent_id, etc.)
        """
        self.context = context
        logger.debug(f"Set context in dependencies: {context.keys()}") 