"""SimpleAgent implementation.

This module provides the SimpleAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.simple_agent.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.simple_agent.agent import SimpleAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a SimpleAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            SimpleAgent instance
        """
        if config is None:
            config = {}
        
        return SimpleAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize SimpleAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    