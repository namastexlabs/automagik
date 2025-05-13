"""Discord agent package.

This package provides a Discord agent that can interact with Discord servers.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

# Setup logging
logger = logging.getLogger(__name__)

try:
    from src.agents.simple.discord_agent.agent import DiscordAgent
    
    # Standardized create_agent function (required by the API)
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a DiscordAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            DiscordAgent instance
        """
        if config is None:
            config = {}
        
        return DiscordAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize Discord agent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

__all__ = ["DiscordAgent", "create_agent"]