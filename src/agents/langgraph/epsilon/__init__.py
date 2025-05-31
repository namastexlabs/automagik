"""LangGraph Epsilon Tool Builder Agent.

This module contains the Epsilon agent implementation with LangGraph orchestration capabilities
for tool development, external integrations, and utility creation.
"""

from typing import Dict
from .agent import EpsilonAgent

def create_agent(config: Dict[str, str]) -> EpsilonAgent:
    """Create an Epsilon agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        EpsilonAgent instance
    """
    return EpsilonAgent(config) 