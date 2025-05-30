"""EstruturarAgent implementation.

This module provides the EstruturarAgent implementation that uses the common utilities
for message parsing, session management, and tool handling.
"""

from typing import Dict, Optional, Any
import os
import logging
import traceback

from src.agents.simple.estruturar.prompts.prompt import ESTRUTURAR_AGENT_PROMPT

# Setup logging first
logger = logging.getLogger(__name__)


try:
    from src.agents.simple.estruturar.agent import EstruturarAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a EstruturarAgent instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            EstruturarAgent instance
        """
        if config is None:
            config = {}
        
        return EstruturarAgent(config)
    
except Exception as e:
    logger.error(f"Failed to initialize EstruturarAgent module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    