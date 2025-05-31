"""LangGraph Beta Core Builder Agent.

This module contains the Beta agent implementation with LangGraph orchestration capabilities
for core system development and infrastructure building.
"""

from typing import Dict
from .agent import BetaAgent

def create_agent(config: Dict[str, str]) -> BetaAgent:
    """Create a Beta agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        BetaAgent instance
    """ 