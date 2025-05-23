"""SummaryAgentAgent implementation.

This module provides the SummaryAgentAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.summary_agent_agent.prompts.prompt import AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.summary_agent_agent.agent import SummaryAgentAgent
    from src.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a SummaryAgentAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            SummaryAgentAgent instance
        """
        if config is None:
            config = {}
        
        return SummaryAgentAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize SummaryAgentAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    