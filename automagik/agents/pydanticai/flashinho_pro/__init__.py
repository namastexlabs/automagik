"""Flashinho Pro Agent - Advanced multimodal Brazilian educational assistant."""
from typing import Dict, Optional, Any
import logging
import traceback

# Setup logging first
logger = logging.getLogger(__name__)

try:
    from .agent import FlashinhoPro
    from automagik.agents.models.placeholder import PlaceholderAgent
    
    # Standardized create_agent function
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Factory function to create Flashinho Pro agent instance. 
        
        Creates an advanced multimodal Brazilian educational assistant powered by
        Google Gemini 2.5 Pro with full Flashed API integration.
        
        Args:
            config: Agent configuration dictionary
            
        Returns:
            FlashinhoPro instance or PlaceholderAgent on failure
        """
        if config is None:
            config = {}
        
        return FlashinhoPro(config)
    
except Exception as e:
    logger.error(f"Failed to initialize Flashinho Pro module: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a placeholder function that returns an error agent
    def create_agent(config: Optional[Dict[str, str]] = None) -> Any:
        """Create a placeholder agent due to initialization error."""
        if config is None:
            config = {}
        return PlaceholderAgent({"name": "flashinho_pro_error", "error": str(e)})