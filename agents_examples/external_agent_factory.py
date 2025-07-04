"""Factory for creating external agents with minimal boilerplate.

This factory provides a simple way to create external agents
with automatic tool registration and configuration.
"""
import logging
from typing import Dict, Optional, Callable, List, Any

from automagik.agents.models.placeholder import PlaceholderAgent

logger = logging.getLogger(__name__)


def create_external_agent(
    agent_class: type,
    config: Optional[Dict[str, str]] = None,
    fallback_enabled: bool = True
) -> Any:
    """Create an external agent with automatic error handling.
    
    Args:
        agent_class: The agent class to instantiate
        config: Configuration dictionary
        fallback_enabled: Whether to return PlaceholderAgent on error
        
    Returns:
        Agent instance or PlaceholderAgent if creation fails
    """
    try:
        return agent_class(config or {})
    except Exception as e:
        logger.error(f"Failed to create {agent_class.__name__}: {e}")
        if fallback_enabled:
            logger.info("Returning PlaceholderAgent as fallback")
            return PlaceholderAgent(config or {})
        raise


class ExternalAgentRegistry:
    """Registry for external agents with automatic discovery."""
    
    def __init__(self):
        self._agents: Dict[str, Callable] = {}
    
    def register(self, name: str, factory_func: Callable) -> None:
        """Register an external agent factory function.
        
        Args:
            name: Agent name
            factory_func: Function that creates the agent
        """
        self._agents[name] = factory_func
        logger.info(f"Registered external agent: {name}")
    
    def create(self, name: str, config: Optional[Dict[str, str]] = None) -> Any:
        """Create an agent by name.
        
        Args:
            name: Agent name
            config: Configuration dictionary
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found. Available: {list(self._agents.keys())}")
        
        return self._agents[name](config)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())


# Global registry instance
external_agent_registry = ExternalAgentRegistry()