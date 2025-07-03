"""SofiaAgent implementation.

This module provides the SofiaAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

# Setup logging first
logger = logging.getLogger(__name__)


def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
    """Create a SofiaAgent instance with proper error handling.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        SofiaAgent instance or PlaceholderAgent on error
    """
    if config is None:
        config = {}
    
    try:
        from .agent import SofiaAgent
        return SofiaAgent(config)
    except Exception as e:
        logger.error(f"Failed to create SofiaAgent: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Import PlaceholderAgent inside exception handler to ensure it's available
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent({"name": "sofia_agent_error", "error": str(e)})
    