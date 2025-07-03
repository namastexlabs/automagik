"""SimpleAgent implementation.

This module provides the SimpleAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from .agent import SimpleAgent
    from automagik.agents.models.placeholder import PlaceholderAgent
    
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
    
    # Store error message before function definition
    initialization_error = str(e)
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        return PlaceholderAgent({"name": "simple_agent_error", "error": initialization_error})
    