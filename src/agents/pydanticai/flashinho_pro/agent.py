"""Flashinho Pro Agent - Advanced multimodal Brazilian educational assistant.

This agent combines the authentic Brazilian educational coaching personality of Flashinho
with advanced multimodal capabilities powered by Google Gemini 2.5 Pro model.
"""
import logging
from typing import Dict

from src.agents.common.specialized_agents import MultimodalAgent
from src.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy
)
from .prompts.prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


class FlashinhoPro(MultimodalAgent):
    """Advanced multimodal Brazilian educational assistant powered by Google Gemini 2.5 Pro.
    
    Features:
    - Authentic Brazilian Generation Z Portuguese coaching style
    - Multimodal processing: images, audio, documents for educational content
    - Advanced reasoning with Google Gemini 2.5 Pro model
    - Complete Flashed API integration for educational gaming
    - WhatsApp/Evolution channel integration for media handling
    - Cultural authenticity for Brazilian high school students
    """
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho Pro with multimodal and Gemini configuration."""
        super().__init__(
            config=config,
            prompt=AGENT_PROMPT,  # Brazilian educational coaching prompt
            vision_model="google-gla:gemini-2.5-pro-preview-06-05",  # Gemini 2.5 Pro
            supported_media=['image', 'audio', 'document'],  # Full multimodal support
            auto_enhance_prompts=True  # Enable automatic prompt enhancement
        )
        
        # Configure Gemini 2.5 Pro as primary model
        self.dependencies.model_name = "google-gla:gemini-2.5-pro-preview-06-05"
        
        # Register Flashed API tools for educational context
        self._register_flashed_tools()
        
        logger.info("Flashinho Pro initialized with Gemini 2.5 Pro and multimodal support")
    
    def _register_flashed_tools(self) -> None:
        """Register all 6 Flashed API tools for educational gaming functionality."""
        # Register tools using the tool registry (same method used by MultimodalAgent)
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        self.tool_registry.register_tool(get_user_roadmap)
        self.tool_registry.register_tool(get_user_objectives)
        self.tool_registry.register_tool(get_last_card_round)
        self.tool_registry.register_tool(get_user_energy)
        
        logger.debug("Registered 6 Flashed API tools using tool registry")


def create_agent(config: Dict[str, str]) -> FlashinhoPro:
    """Factory function to create Flashinho Pro agent instance."""
    try:
        return FlashinhoPro(config)
    except Exception as e:
        logger.error(f"Failed to create Flashinho Pro Agent: {e}")
        from src.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)