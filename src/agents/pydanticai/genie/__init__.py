"""Genie orchestrator agent module for PydanticAI framework."""

from typing import Dict, Union
from src.agents.models.placeholder import PlaceholderAgent
import logging

def create_agent(config: Dict[str, str]):
    """Factory function to create Genie agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        GenieAgent instance or PlaceholderAgent on error
    """
    try:
        from .agent import GenieAgent
        return GenieAgent(config)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create GenieAgent: {e}")
        return PlaceholderAgent(config)

__all__ = ["create_agent"]