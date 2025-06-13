"""StanAgentAgent implementation.

This module provides the StanAgentAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

# Removed import of AGENT_PROMPT as it no longer exists in prompt.py
# from src.agents.simple.stan_agent.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from .agent import StanAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a StanAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            StanAgent instance
        """
        if config is None:
            config = {}
        
        return StanAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize StanAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Store error message before function definition
    initialization_error = str(e)
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        return PlaceholderAgent({"name": "stan_agent_error", "error": initialization_error})
    