"""PromptMakerAgent implementation.

This module provides the PromptMakerAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.prompt_maker.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.prompt_maker.agent import PromptMakerAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a PromptMakerAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            PromptMakerAgent instance
        """
        if config is None:
            config = {}
        
        return PromptMakerAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize PromptMakerAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    