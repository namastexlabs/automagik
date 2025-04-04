"""FlashinhoAgent implementation.

This module provides the FlashinhoAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.flashinho_agent.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.flashinho_agent.agent import FlashinhoAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a FlashinhoAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            FlashinhoAgent instance
        """
        if config is None:
            config = {}
        
        return FlashinhoAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize FlashinhoAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    