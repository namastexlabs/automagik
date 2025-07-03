from typing import Dict, Type, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent

def initialize_agent(agent_class: Type[AutomagikAgent], config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    """Initialize an agent with configuration.
    
    Args:
        agent_class: The agent class to initialize
        config: Optional configuration override
        
    Returns:
        Initialized agent instance
    """
    if config is None:
        config = {}
    return agent_class(config) 