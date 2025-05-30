"""StanEmailAgent implementation.

This module provides the StanEmailAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.stan_email.agent import StanEmailAgent

# Setup logging first
logger = logging.getLogger(__name__)


try:
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a StanEmailAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            StanEmailAgent instance
        """
        if config is None:
            config = {}
        
        return StanEmailAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize StanEmailAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    