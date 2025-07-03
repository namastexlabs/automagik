"""Memory provider for the memory tool.

This module provides a class to manage memory retrieval and caching.
"""
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global registry of memory providers by agent ID
_memory_providers: Dict[int, "MemoryProvider"] = {}

def get_memory_provider_for_agent(agent_id: int) -> Optional["MemoryProvider"]:
    """Get a memory provider for a specific agent.
    
    Args:
        agent_id: The numeric ID of the agent
        
    Returns:
        MemoryProvider instance or None
    """
    return _memory_providers.get(agent_id)

class MemoryProvider:
    """Provider interface for memory-related system prompt functions.
    
    This class acts as a bridge between our database-backed memory system
    and pydantic-ai's dynamic system prompt functions.
    """
    
    def __init__(self, agent_id: int):
        """Initialize the memory provider.
        
        Args:
            agent_id: The ID of the agent this provider serves
        """
        self.agent_id = agent_id
        self._cache_expiry = datetime.now()
        self._memory_cache = {}
        self._cache_ttl = timedelta(seconds=30)  # 30-second TTL by default
        
        # Register this provider in the global registry
        _memory_providers[agent_id] = self
        
    def set_cache_ttl(self, seconds: int) -> None:
        """Set the cache time-to-live in seconds.
        
        Args:
            seconds: Cache TTL in seconds
        """
        self._cache_ttl = timedelta(seconds=seconds)
    
    def invalidate_cache(self) -> None:
        """Invalidate the memory cache to force fresh fetches."""
        self._cache_expiry = datetime.now()
        self._memory_cache = {}
        logger.debug(f"Memory cache for agent {self.agent_id} invalidated")
    
    def _should_refresh_cache(self) -> bool:
        """Check if the cache should be refreshed."""
        return datetime.now() > self._cache_expiry
    
    def _refresh_cache(self) -> None:
        """Refresh the memory cache from database."""
        from automagik.tools.memory.tool import list_memories_in_db
        
        try:
            memories = list_memories_in_db(agent_id=self.agent_id)
            
            # Build a new cache
            new_cache = {}
            for memory in memories:
                if hasattr(memory, 'name') and memory.name:
                    new_cache[memory.name] = memory.content
            
            # Update the cache and expiry
            self._memory_cache = new_cache
            self._cache_expiry = datetime.now() + self._cache_ttl
            logger.debug(f"Refreshed memory cache for agent {self.agent_id} with {len(new_cache)} items")
            
        except Exception as e:
            logger.error(f"Error refreshing memory cache for agent {self.agent_id}: {str(e)}")
    
    def get_memory(self, name: str, default: Any = None) -> Any:
        """Get a memory value by name.
        
        Args:
            name: Name of the memory to retrieve
            default: Default value if memory doesn't exist
            
        Returns:
            Memory content or default value
        """
        # Refresh cache if needed
        if self._should_refresh_cache():
            self._refresh_cache()
        
        # Return from cache
        return self._memory_cache.get(name, default)
    
    def get_all_memories(self) -> Dict[str, Any]:
        """Get all memories as a dictionary.
        
        Returns:
            Dictionary of all memory name-value pairs
        """
        # Refresh cache if needed
        if self._should_refresh_cache():
            self._refresh_cache()
        
        return self._memory_cache.copy()
    
    def get_memories_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all memories with names starting with the given prefix.
        
        Args:
            prefix: Prefix to filter memories by
            
        Returns:
            Dictionary of matching memory name-value pairs
        """
        # Refresh cache if needed
        if self._should_refresh_cache():
            self._refresh_cache()
        
        return {
            name: value for name, value in self._memory_cache.items() 
            if name.startswith(prefix)
        }
    
    def create_system_prompt_function(self, memory_name: str, template: str = "{value}") -> Callable:
        """Create a function that can be used as a system prompt function.
        
        This creates a function that can be decorated with @agent.system_prompt
        to dynamically inject memory values into the system prompt.
        
        Args:
            memory_name: Name of the memory to inject
            template: Template string with {value} placeholder
            
        Returns:
            Function that returns the formatted memory value
        """
        def memory_prompt_function() -> str:
            """System prompt function for memory injection."""
            value = self.get_memory(memory_name, f"No memory found for {memory_name}")
            try:
                return template.format(value=value)
            except Exception as e:
                logger.error(f"Error formatting memory {memory_name}: {str(e)}")
                return f"Error formatting memory {memory_name}"
        
        # Set metadata for better debugging
        memory_prompt_function.__name__ = f"memory_{memory_name}"
        memory_prompt_function.__doc__ = f"Inject memory '{memory_name}' into system prompt"
        
        return memory_prompt_function 