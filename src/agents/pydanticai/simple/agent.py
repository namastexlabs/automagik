"""Enhanced Simple Agent using new framework patterns."""
from typing import Dict

from src.agents.common.specialized_agents import SimpleAgent as BaseSimpleAgent
from .prompts.prompt import AGENT_PROMPT

# Export commonly used functions for backward compatibility with tests
from src.agents.common.message_parser import (
    extract_all_messages,
    extract_tool_calls,
    extract_tool_outputs
)


class SimpleAgent(BaseSimpleAgent):
    """Enhanced Simple Agent - ultra-minimal implementation."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize with automatic setup via ChannelHandler system."""
        super().__init__(config, AGENT_PROMPT)
        
        # Register Evolution tools for backward compatibility with tests
        self.tool_registry.register_evolution_tools(self.context)


def create_agent(config: Dict[str, str]) -> SimpleAgent:
    """Factory function to create enhanced simple agent."""
    try:
        return SimpleAgent(config)
    except Exception:
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)