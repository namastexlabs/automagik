"""State management interfaces and implementations for AutomagikAgent."""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StateManagerInterface(ABC):
    """Interface for agent state management."""
    
    @abstractmethod
    async def save_state(self, key: str, value: Any) -> bool:
        """Save state value for the given key.
        
        Args:
            key: The state key
            value: The value to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def load_state(self, key: str, default: Any = None) -> Any:
        """Load state value for the given key.
        
        Args:
            key: The state key
            default: Default value if key not found
            
        Returns:
            The state value or default
        """
        pass
    
    @abstractmethod
    async def delete_state(self, key: str) -> bool:
        """Delete state value for the given key.
        
        Args:
            key: The state key
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear_all_state(self) -> bool:
        """Clear all state data.
        
        Returns:
            True if successful, False otherwise
        """
        pass


class AutomagikStateManager(StateManagerInterface):
    """Default in-memory state manager implementation."""
    
    def __init__(self):
        """Initialize the state manager."""
        self._state: Dict[str, Any] = {}
        logger.debug("Initialized AutomagikStateManager")
    
    async def save_state(self, key: str, value: Any) -> bool:
        """Save state value for the given key."""
        try:
            self._state[key] = value
            logger.debug(f"Saved state: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving state for key {key}: {e}")
            return False
    
    async def load_state(self, key: str, default: Any = None) -> Any:
        """Load state value for the given key."""
        try:
            value = self._state.get(key, default)
            logger.debug(f"Loaded state: {key}")
            return value
        except Exception as e:
            logger.error(f"Error loading state for key {key}: {e}")
            return default
    
    async def delete_state(self, key: str) -> bool:
        """Delete state value for the given key."""
        try:
            if key in self._state:
                del self._state[key]
                logger.debug(f"Deleted state: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting state for key {key}: {e}")
            return False
    
    async def clear_all_state(self) -> bool:
        """Clear all state data."""
        try:
            self._state.clear()
            logger.debug("Cleared all state")
            return True
        except Exception as e:
            logger.error(f"Error clearing state: {e}")
            return False
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get a copy of all state data.
        
        Returns:
            Dictionary containing all state data
        """
        return self._state.copy()
    
    def set_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Set the entire state dictionary.
        
        Args:
            state_dict: Dictionary to set as the new state
        """
        self._state = state_dict.copy()
        logger.debug(f"Set state dictionary with {len(state_dict)} items")


class PersistentStateManager(StateManagerInterface):
    """Database-backed state manager for persistent state storage."""
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize the persistent state manager.
        
        Args:
            agent_id: Optional agent ID for namespacing state
        """
        self.agent_id = agent_id
        logger.debug(f"Initialized PersistentStateManager for agent: {agent_id}")
    
    async def save_state(self, key: str, value: Any) -> bool:
        """Save state value to database."""
        try:
            # TODO: Implement database storage
            # For now, log that this would be persisted
            logger.debug(f"Would persist state: {key} for agent {self.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving persistent state for key {key}: {e}")
            return False
    
    async def load_state(self, key: str, default: Any = None) -> Any:
        """Load state value from database."""
        try:
            # TODO: Implement database retrieval
            # For now, return default
            logger.debug(f"Would load persistent state: {key} for agent {self.agent_id}")
            return default
        except Exception as e:
            logger.error(f"Error loading persistent state for key {key}: {e}")
            return default
    
    async def delete_state(self, key: str) -> bool:
        """Delete state value from database."""
        try:
            # TODO: Implement database deletion
            logger.debug(f"Would delete persistent state: {key} for agent {self.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting persistent state for key {key}: {e}")
            return False
    
    async def clear_all_state(self) -> bool:
        """Clear all state data from database."""
        try:
            # TODO: Implement database clearing
            logger.debug(f"Would clear all persistent state for agent {self.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing persistent state: {e}")
            return False