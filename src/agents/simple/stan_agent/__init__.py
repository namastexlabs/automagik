"""StanAgentAgent implementation.

This module provides the StanAgentAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.stan_agent.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.stan_agent.agent import StanAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a StanAgentAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            StanAgentAgent instance
        """
        if config is None:
            config = {}
        
        return StanAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize StanAgentAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    