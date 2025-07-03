"""Enhanced Flashinho Agent implementation using new framework patterns.

This demonstrates how the specialized agent framework eliminates massive tool wrapper
boilerplate while maintaining all Flashed API integration functionality.
"""
import logging
from typing import Dict

from automagik.agents.pydanticai.simple.agent import SimpleAgent as BaseSimpleAgent
from automagik.agents.common.tool_wrapper_factory import ToolWrapperFactory
from automagik.tools.flashed.tool import (
    get_user_data, get_user_score, get_user_roadmap, 
    get_user_objectives, get_last_card_round, get_user_energy
)
from .prompts.prompt import AGENT_PROMPT

logger = logging.getLogger(__name__)


class FlashinhoAgent(BaseSimpleAgent):
    """Enhanced Flashinho Agent with specialized Flashed API integration.
    
    Dramatically reduces verbosity from 369 lines while maintaining all
    Flashed API tools and educational gaming functionality.
    """
    
    # Configuration - replaces extensive boilerplate
    default_model = "openai:gpt-4.1"
    
    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize Flashinho Agent with automatic setup."""
        super().__init__(config)
        
        # Set the prompt text
        self._code_prompt_text = AGENT_PROMPT
        
        # Register Flashed API tools using the wrapper factory
        self._register_flashed_tools()
        
        # Register multimodal analysis tools
        self._register_multimodal_tools()
        
        logger.info("Enhanced Flashinho Agent initialized")
    
    def _register_flashed_tools(self) -> None:
        """Register Flashed API tools using the new wrapper factory."""
        # Use the wrapper factory to eliminate 6 massive tool wrapper functions
        flashed_tools = {
            'get_user_data': get_user_data,
            'get_user_score': get_user_score,
            'get_user_roadmap': get_user_roadmap,
            'get_user_objectives': get_user_objectives,
            'get_last_card_round': get_last_card_round,
            'get_user_energy': get_user_energy
        }
        
        for tool_name, tool_func in flashed_tools.items():
            wrapper = ToolWrapperFactory.create_context_wrapper(tool_func, self.context)
            self.tool_registry.register_tool(wrapper)

    def _register_multimodal_tools(self):
        """Register multimodal analysis tools using common helper."""
        from automagik.agents.common.multimodal_helper import register_multimodal_tools
        register_multimodal_tools(self.tool_registry, self.dependencies)


def create_agent(config: Dict[str, str]) -> FlashinhoAgent:
    """Factory function to create enhanced Flashinho agent."""
    try:
        return FlashinhoAgent(config)
    except Exception as e:
        logger.error(f"Failed to create Enhanced Flashinho Agent: {e}")
        from automagik.agents.models.placeholder import PlaceholderAgent
        return PlaceholderAgent(config)