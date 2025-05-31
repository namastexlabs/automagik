"""LangGraph Delta API Builder Agent.

This module contains the Delta agent implementation with LangGraph orchestration capabilities
for API development, FastAPI endpoints, and authentication systems.
"""

from typing import Dict
from .agent import DeltaAgent

def create_agent(config: Dict[str, str]) -> DeltaAgent:
    """Create a Delta agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        DeltaAgent instance
    """
    return DeltaAgent(config) 