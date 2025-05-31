"""LangGraph Alpha Orchestrator Agent.

This module contains the Alpha agent implementation with LangGraph orchestration capabilities
for epic analysis, task breakdown, and team coordination.
"""

from typing import Dict
from .agent import AlphaAgent

def create_agent(config: Dict[str, str]) -> AlphaAgent:
    """Create an Alpha agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        AlphaAgent instance
    """
    return AlphaAgent(config) 