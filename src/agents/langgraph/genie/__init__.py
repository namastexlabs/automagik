"""Genie orchestrator agent module."""

from typing import Dict
from .agent import Genie

def create_agent(config: Dict[str, str]) -> Genie:
    """Create a Genie orchestrator agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        Genie instance
    """
    return Genie(config)

__all__ = ["Genie", "create_agent"]