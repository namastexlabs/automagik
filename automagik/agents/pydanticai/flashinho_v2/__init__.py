"""Flashinho Pro Agent - Advanced multimodal Brazilian educational assistant."""
from typing import Dict, Optional, Any
import logging
import traceback

# Setup logging first
logger = logging.getLogger(__name__)

# Import PlaceholderAgent outside try block so it's available for error handling
from automagik.agents.models.placeholder import PlaceholderAgent

try:
    from .agent import FlashinhoV2
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Factory function to create Flashinho V2 agent instance. 
        
        Creates an advanced multimodal Brazilian educational assistant powered by 
        Google Gemini 2.5 with full Flashed API integration.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            FlashinhoV2 instance or PlaceholderAgent on failure
        """
        if config is None:
            config = {}
        
        return FlashinhoV2(config)
    
except Exception as e:
    error_message = str(e)
    logger.error(f"Failed to initialize Flashinho V2 module: {error_message}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        if config is None:
            config = {}
        return PlaceholderAgent({"name": "flashinho_v2_error", "error": error_message})