"""LangGraph Gamma Quality Engineer Agent.

This module contains the Gamma agent implementation with LangGraph orchestration capabilities
for testing, quality assurance, and documentation management.
"""

from typing import Dict
from .agent import GammaAgent

def create_agent(config: Dict[str, str]) -> GammaAgent:
    """Create a Gamma agent instance.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        GammaAgent instance
    """
    return GammaAgent(config) 