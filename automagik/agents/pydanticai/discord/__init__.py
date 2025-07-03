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
    from .agent import DiscordAgent
    
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
    
    # Store the error message for use in the placeholder function
    initialization_error = str(e)
    
    # Create a placeholder function that returns an error agent
    from automagik.agents.models.placeholder import PlaceholderAgent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        return PlaceholderAgent({"name": "discord_agent_error", "error": initialization_error})

__all__ = ["DiscordAgent", "create_agent"]